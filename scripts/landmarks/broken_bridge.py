"""Source-bound Broken Bridge and sloping approaches; pure shared B mesh API.

No bpy/scene initialization, no water geometry or flat park surface. The main
city owns water, pedestrian topology, deck-height collision and endpoint datum.
Real metre parameters scale once; lm x/z/y already use game units.
"""
from __future__ import annotations
import math
try:
    from city_config import load_city
except ImportError:
    from scripts.city_config import load_city


class _Mesh:
    def __init__(self,b,angle,scale,base_y):
        self.b,self.ca,self.sa,self.s,self.base=b,math.cos(angle),math.sin(angle),scale,base_y
        self.faces=0

    def pt(self,p):
        u,v,z=p
        return ((u*self.ca-v*self.sa)*self.s,(u*self.sa+v*self.ca)*self.s,self.base+z*self.s)

    def face(self,material,points):
        self.b.face(material,[self.pt(p) for p in points]);self.faces+=1

    def box(self,material,point,size):
        u,v,z=point;a,c,d=[x/2 for x in size]
        q=[(u-a,v-c,z-d),(u+a,v-c,z-d),(u+a,v+c,z-d),(u-a,v+c,z-d),
           (u-a,v-c,z+d),(u+a,v-c,z+d),(u+a,v+c,z+d),(u-a,v+c,z+d)]
        for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.face(material,[q[i] for i in ids])

    def beam(self,material,u0,u1,v,z0,z1,width,height):
        q=[(u0,v-width/2,z0-height/2),(u1,v-width/2,z1-height/2),
           (u1,v+width/2,z1-height/2),(u0,v+width/2,z0-height/2),
           (u0,v-width/2,z0+height/2),(u1,v-width/2,z1+height/2),
           (u1,v+width/2,z1+height/2),(u0,v+width/2,z0+height/2)]
        for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.face(material,[q[i] for i in ids])


def _parameters(spec):
    est=spec['estimates']
    radius=spec['clearArchSpanM']/2
    spring=est['archSpringRelativeM']['value']
    ring=est['archRingThicknessM']['value']
    pavement=est['pavementThicknessM']['value']
    length=spec['bridgeLengthM']
    center=-length/2+length*est['archPosition']['value']
    crown=spring+radius+ring+pavement
    return length,center,radius,spring,ring,pavement,crown


def deck_height_metres(u,spec):
    """Shared candidate profile for main integration; u runs SW→NE in real metres."""
    length,center,_,_,_,_,crown=_parameters(spec)
    if u<=center:
        fraction=max(0,min(1,(u+length/2)/(center+length/2)))
        return crown*math.sin(fraction*math.pi/2)
    fraction=max(0,min(1,(length/2-u)/(length/2-center)))
    return crown*math.sin(fraction*math.pi/2)


def arch_soffit_metres(u,spec):
    """No solids are placed below this inner semicircle within the arch opening."""
    _,center,radius,spring,_,_,_=_parameters(spec)
    x=u-center
    if abs(x)<=radius:
        return spring+math.sqrt(max(0,radius*radius-x*x))
    return spring-1.0


def build(b,lm,spec,scale=.6):
    if spec.get('id')!='broken-bridge' or spec.get('cityId')!='hangzhou':
        raise ValueError('Hangzhou Broken Bridge spec required')
    if spec.get('sourceFeatureIds')!=['way/28538289','way/1466925249'] or spec.get('archCount')!=1:
        raise ValueError('Source line/area and single arch must remain intact')
    city=load_city('hangzhou')
    if not math.isclose(scale,city['geography']['scale'],abs_tol=1e-12):
        raise ValueError('Scale disagrees with canonical Hangzhou city')
    if not all(math.isfinite(float(lm.get(k,0))) for k in ['x','z','y']):
        raise ValueError('Finite game-unit anchor required')
    length,center,radius,spring,ring,pavement,crown=_parameters(spec)
    width=spec['bridgeWidthM']
    if min(length,width,radius,ring,pavement,crown)<=0 or not(-length/2+radius<center<length/2-radius):
        raise ValueError('Invalid positive bridge dimensions or arch location')
    old=b.frame;b.frame=(lm['x'],lm['z'],0)
    mesh=_Mesh(b,spec['axisRadiansEastCCW'],scale,float(lm.get('y',0)))
    try:
        # Exact span ends/crest and semicircle samples prevent long faces across a void.
        cuts={-length/2+length*i/64 for i in range(65)}
        cuts.update(center+radius*math.cos(math.pi*i/24) for i in range(25))
        cuts.update([center,center-radius,center+radius])
        cuts=sorted(cuts)
        for u,v in zip(cuts,cuts[1:]):
            if v-u<1e-7:
                continue
            lo0,lo1=arch_soffit_metres(u,spec),arch_soffit_metres(v,spec)
            top0,top1=deck_height_metres(u,spec),deck_height_metres(v,spec)
            hi0,hi1=top0-pavement,top1-pavement
            if min(hi0-lo0,hi1-lo1)<=0:
                raise ValueError('Insufficient solid cover above the arch')
            # Stone body under the deck, with the single opening left free beneath it.
            mesh.face('concrete',[(u,-width/2,hi0),(v,-width/2,hi1),(v,width/2,hi1),(u,width/2,hi0)])
            mesh.face('concrete',[(u,width/2,lo0),(v,width/2,lo1),(v,-width/2,lo1),(u,-width/2,lo0)])
            mesh.face('concrete',[(u,-width/2,lo0),(v,-width/2,lo1),(v,-width/2,hi1),(u,-width/2,hi0)])
            mesh.face('concrete',[(v,width/2,lo1),(u,width/2,lo0),(u,width/2,hi0),(v,width/2,hi1)])
            mesh.face('asphalt',[(u,-width/2,top0),(v,-width/2,top1),(v,width/2,top1),(u,width/2,top0)])
            for side in [-1,1]:
                y=side*width/2
                q=[(u,y,hi0),(v,y,hi1),(v,y,top1),(u,y,top0)]
                if side>0:q.reverse()
                mesh.face('asphalt',q)
            # Coarse stone courses sit only on stone, never across the open arch void.
            for z in [-1.0,-.4,.2,.8,1.4,2.0]:
                if z>max(lo0,lo1)+.08 and z<min(hi0,hi1)-.08:
                    for side in [-1,1]:
                        y=side*(width/2+.018)
                        q=[(u,y,z-.013),(v,y,z-.013),(v,y,z+.013),(u,y,z+.013)]
                        if side>0:q.reverse()
                        mesh.face('roof',q)
        # Stone-and-pavement end caps meet the exact connected source endpoint height.
        for u,sign in [(-length/2,-1),(length/2,1)]:
            top=deck_height_metres(u,spec);low=arch_soffit_metres(u,spec)
            q=[(u,-width/2,low),(u,width/2,low),(u,width/2,top-pavement),(u,-width/2,top-pavement)]
            if sign<0:q.reverse()
            mesh.face('concrete',q)
            q=[(u,-width/2,top-pavement),(u,width/2,top-pavement),(u,width/2,top),(u,-width/2,top)]
            if sign<0:q.reverse()
            mesh.face('asphalt',q)
        # A visible segmented arch ring, at both side faces and beneath the barrel.
        for i in range(24):
            a,t=math.pi*i/24,math.pi*(i+1)/24
            inner=[(center+radius*math.cos(q),spring+radius*math.sin(q)) for q in [a,t]]
            outer=[(center+(radius+ring)*math.cos(q),spring+(radius+ring)*math.sin(q)) for q in [a,t]]
            for side in [-1,1]:
                y=side*(width/2+.025)
                q=[(inner[0][0],y,inner[0][1]),(inner[1][0],y,inner[1][1]),
                   (outer[1][0],y,outer[1][1]),(outer[0][0],y,outer[0][1])]
                if side>0:q.reverse()
                mesh.face('concrete',q)
            # Slim radial joints distinguish the ring from an untextured solid mass.
            for side in [-1,1]:
                y=side*(width/2+.032)
                q=[(center+(radius+.02)*math.cos(a),y,spring+(radius+.02)*math.sin(a)),
                   (center+(radius+ring-.02)*math.cos(a),y,spring+(radius+ring-.02)*math.sin(a)),
                   (center+(radius+ring-.02)*math.cos(a+.009),y,spring+(radius+ring-.02)*math.sin(a+.009)),
                   (center+(radius+.02)*math.cos(a+.009),y,spring+(radius+.02)*math.sin(a+.009))]
                if side<0:q.reverse()
                mesh.face('roof',q)
        est=spec['estimates'];rh=est['railHeightM']['value'];pw=est['railPostWidthM']['value']
        rail_v=width/2-.18
        count=max(2,math.ceil(length/est['railPostPitchM']['value']))
        stations=[-length/2+length*i/count for i in range(count+1)]
        for side in [-1,1]:
            y=side*rail_v
            for u in stations:
                z=deck_height_metres(u,spec)
                mesh.box('concrete',(u,y,z+rh/2),(pw,pw,rh))
                mesh.box('concrete',(u,y,z+rh+.05),(pw*1.4,pw*1.4,.10))
            for u,v in zip(stations,stations[1:]):
                for offset,h in [(.43,.12),(rh-.06,.16)]:
                    mesh.beam('concrete',u,v,y,deck_height_metres(u,spec)+offset,
                              deck_height_metres(v,spec)+offset,.14,h)
    finally:
        b.frame=old
    return {'scope':spec['scope'],'sourceFeatureIds':spec['sourceFeatureIds'],'faces':mesh.faces,
            'sourceRoadNodeIds':spec['sourceRoadNodeIds'],'endpointsWGS84':spec['endpointsWGS84'],
            'deckProfileMetres':[[u,deck_height_metres(u,spec)] for u in cuts],
            'axisRadiansEastCCW':spec['axisRadiansEastCCW'],'bridgeWidthM':width,'archCount':1,
            'clearArchSpanM':radius*2,'archCenterRelativeM':center,'candidateCrestM':crown,
            'endpointHeightGame':float(lm.get('y',0)), 'scaleOnce':scale,
            'materials':['asphalt','concrete','roof'],'lights':0,'waterMeshes':0,
            'integrationContract':spec['integrationContract'],'pending':spec['pendingSubscopes'],
            'accuracyClaim':'reference-informed candidate; dimensions not a current field survey'}

"""Source-bound Hangzhou ICC truncated globe/podium exterior candidate.

Pure B API: caller owns the Blender scene, materials, export, runtime and site.
Real metre dimensions scale once; lm x/z/y are already game units.
"""
from __future__ import annotations
import math


def _cross2(a,b):return a[0]*b[1]-a[1]*b[0]
def _mix(a,b,t):return a+(b-a)*t


def radial_boundary_metres(ring,theta):
    d=(math.cos(theta),math.sin(theta));hits=[]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        edge=(b[0]-a[0],b[1]-a[1]);den=_cross2(d,edge)
        if abs(den)<1e-10:continue
        r=_cross2(a,edge)/den;t=_cross2(a,d)/den
        if r>0 and -1e-9<=t<=1+1e-9:hits.append(r)
    if not hits:raise ValueError('Mapped podium does not surround anchor')
    return max(hits)


def sphere_radius_metres(z,spec):
    radius=spec['diameterM']/2;center=spec['estimates']['sphereSection']['value']['centerHeightM']
    square=radius*radius-(z-center)**2
    if square<=0:raise ValueError('Candidate sphere section leaves the reported diameter')
    return math.sqrt(square)


def _p(theta,r,z):return(r*math.cos(theta),r*math.sin(theta),z)
def _angle_distance(a,b):return abs((a-b+math.pi)%(2*math.pi)-math.pi)


def _source_entry_v(ring,u,front):
    hits=[]
    for (x,y),(s,t) in zip(ring,ring[1:]+ring[:1]):
        if abs(s-x)<1e-10:continue
        f=(u-x)/(s-x)
        if -1e-9<=f<=1+1e-9:hits.append(_mix(y,t,f))
    if not hits:raise ValueError('Estimated connector width outside source entry')
    return max(hits) if front else min(hits)


def ground_footprints(lm,spec,scale=.6):
    """Source/mesh-bound wall strips and canopy posts, world game units.

    Rounded podium roofs are overhead, never a filled whole-sphere disk or
    full annulus at ground. The current candidate has continuous glazed lobby
    walls and door frames, without verified open door geometry. These strips
    preserve that actual mesh and label door/arrival verification unresolved.
    """
    if spec.get('id')!='international-conference-center' or spec.get('cityId')!='hangzhou':raise ValueError('wrong city/object spec')
    if abs(scale-spec['coordinatePolicy']['scaleOnce'])>1e-12:raise ValueError('dimensions require exactly one city scale')
    angle=spec['axisRadiansEastCCW'];ca,sa=math.cos(angle),math.sin(angle);base=float(lm.get('y',0));result=[]
    def world(u,v):return [float(lm['x'])+(u*ca-v*sa)*scale,float(lm['z'])+(u*sa+v*ca)*scale]
    def add(kind,ring,low,high,ids,**extra):
        result.append({'kind':kind,'polygonGame':[world(u,v) for u,v in ring],
          'minYGame':base+low*scale,'maxYGame':base+high*scale,'sourceFeatureIds':ids,
          'basis':'current candidate geometry; .18m collision skin thickness estimated, not surveyed wall section',
          'entryStatus':'unconfirmed current doors/route; do not interpret roof gaps as verified room entry',**extra})
    def strip(kind,a,b,low,high,ids,**extra):
        length=math.dist(a,b)
        if length<1e-8:raise ValueError('zero-length ICC collision wall')
        du,dv=(b[0]-a[0])/length,(b[1]-a[1])/length;t=.09
        ring=[(a[0]-dv*t,a[1]+du*t),(a[0]+dv*t,a[1]-du*t),
          (b[0]+dv*t,b[1]-du*t),(b[0]-dv*t,b[1]+du*t)]
        add(kind,ring,low,high,ids,**extra)
    sec=spec['estimates']['sphereSection']['value'];low=sec['lowerCutM'];front=spec['glazedFaceRelativeRadians']
    radius=sphere_radius_metres(low,spec);step=2*math.pi/96
    for i in range(96):
        a,t=i*step,(i+1)*step
        strip('lobby-glass-wall',_p(a,radius,0)[:2],_p(t,radius,0)[:2],0,low,['way/626838542'])
    pod=spec['estimates']['podium']['value'];cuts=sorted(set([i*step for i in range(97)]+
      [(front+h)%(2*math.pi) for h in [-pod['frontGapHalfRadians'],pod['frontGapHalfRadians']]]+
      [(front+math.pi+h)%(2*math.pi) for h in [-pod['rearGapHalfRadians'],pod['rearGapHalfRadians']]]))
    for a,t in zip(cuts,cuts[1:]):
        mid=(a+t)/2
        if _angle_distance(mid,front)<pod['frontGapHalfRadians'] or _angle_distance(mid,front+math.pi)<pod['rearGapHalfRadians']:continue
        r,s=radial_boundary_metres(spec['outerPodiumUVMetres'],a),radial_boundary_metres(spec['outerPodiumUVMetres'],t)
        strip('podium-outer-skin',_p(a,r,0)[:2],_p(t,s,0)[:2],0,pod['roofRadialStations'][-1][1],['way/626838544'],
          overhangInterior='open below roof in current mesh; no ground-filled wing or whole annulus')
    entry=spec['estimates']['entryGlazing']['value'];half=spec['estimates']['glazedFace']['value']['halfAngleRadians']
    for is_front,key,ident,hi,lo in [(True,'frontEntryUVMetres','way/626838543',entry['frontInnerRoofM'],entry['frontOuterRoofM']),
      (False,'rearEntryUVMetres','way/626838541',entry['rearInnerRoofM'],entry['rearOuterRoofM'])]:
        ring=spec[key];vmin,vmax=min(p[1] for p in ring),max(p[1] for p in ring)
        def roof_height(v):
            f=(v-vmin)/(vmax-vmin);return _mix(lo,hi,f) if is_front else _mix(hi,lo,f)
        for a,b in zip(ring,ring[1:]+ring[:1]):
            heights=[roof_height(a[1]),roof_height(b[1])]
            strip('entry-glass-wall',a,b,0,max(heights),[ident],topEndpointHeightsMetres=heights,
              verticalBound='conservative max of current sloping roof endpoints; true door cutouts unresolved')
        center=0 if is_front else (min(p[0] for p in ring)+max(p[0] for p in ring))/2
        width=entry['frontConnectorMouthWidthM'] if is_front else entry['rearConnectorWidthM']
        for u in [center-width/2,center+width/2]:
            v=_source_entry_v(ring,u,is_front);h=roof_height(v)
            body=_curtain_point(low,u/(radius*math.sin(half)),spec) if is_front else (u,math.sqrt(radius*radius-u*u),low)
            strip('entry-connector-side',(body[0],body[1]),(u,v),0,max(low,h),[ident,'way/626838542'],
              topEndpointHeightsMetres=[low,h],verticalBound='conservative max of actual connector endpoint heights')
    ring=spec['rearEntryUVMetres'];v=max(p[1] for p in ring);u=(min(p[0] for p in ring)+max(p[0] for p in ring))/2
    outer=v+entry['canopyProjectionM'];h=entry['rearOuterRoofM']+.25
    for x in [u-14,u,u+14]:add('rear-canopy-post',[(x-.15,outer-.15),(x+.15,outer-.15),(x+.15,outer+.15),(x-.15,outer+.15)],0,h,
      ['way/626838541'],basis='actual current B.beam .30m square upright, neutral base')
    return result


class _Mesh:
    def __init__(self,b,base,scale):self.b=b;self.base=base;self.scale=scale;self.faces=0;self.materials=set()
    def face(self,mat,pts):
        self.b.face(mat,[(x*self.scale,y*self.scale,self.base+z*self.scale) for x,y,z in pts])
        self.faces+=1;self.materials.add(mat)
    def box(self,mat,center,size):
        x,y,z=center;a,b,c=[v/2 for v in size]
        p=[(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
           (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)]
        for ix in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.face(mat,[p[i] for i in ix])
    def beam(self,mat,a,b,width):
        d=tuple(b[i]-a[i] for i in range(3));length=math.sqrt(sum(v*v for v in d))
        if length<1e-8:raise ValueError('zero length beam')
        d=tuple(v/length for v in d);h=math.hypot(d[0],d[1])
        side=(-d[1]/h,d[0]/h,0) if h>1e-8 else (1,0,0)
        normal=(d[1]*side[2]-d[2]*side[1],d[2]*side[0]-d[0]*side[2],d[0]*side[1]-d[1]*side[0])
        ends=[[tuple(origin[i]+width*.5*(s*side[i]+t*normal[i]) for i in range(3))
               for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]] for origin in [a,b]]
        self.face(mat,ends[0][::-1]);self.face(mat,ends[1])
        for i in range(4):self.face(mat,[ends[0][i],ends[0][(i+1)%4],ends[1][(i+1)%4],ends[1][i]])


def _curtain_point(z,s,spec):
    theta=spec['glazedFaceRelativeRadians'];h=spec['estimates']['glazedFace']['value']['halfAngleRadians']
    depth=spec['estimates']['glazedFace']['value']['recessM'];r=sphere_radius_metres(z,spec)
    forward=r*math.cos(h)-depth;side=r*math.sin(h)*s
    return(forward*math.cos(theta)-side*math.sin(theta),
           forward*math.sin(theta)+side*math.cos(theta),z)


def _entry(mesh,ring,inner_height,outer_height,front):
    # Source cyclic winding may vary between way footprints. Normalize it before
    # forming roof normals/wall sides; the plan itself and height are unchanged.
    if sum(_cross2(a,b) for a,b in zip(ring,ring[1:]+ring[:1]))<0:ring=list(reversed(ring))
    v0,v1=min(p[1] for p in ring),max(p[1] for p in ring)
    def height(v):
        fraction=(v-v0)/(v1-v0)
        return _mix(outer_height,inner_height,fraction) if front else _mix(inner_height,outer_height,fraction)
    top=[(u,v,height(v)) for u,v in ring]
    mesh.face('landmarkglass',top)
    for (u,v),(x,y) in zip(ring,ring[1:]+ring[:1]):
        mesh.face('darkglass',[(u,v,0),(x,y,0),(x,y,height(y)),(u,v,height(v))])
    # Source polygon bounds determine glazed roof/mullions; actual door/camera
    # approach/terrain is intentionally not inferred as a validated entrance.
    lo,hi=min(p[0] for p in ring),max(p[0] for p in ring)
    for v in [v0+(v1-v0)*t for t in [.15,.38,.62,.85]]:
        mesh.beam('steel',(lo+.8,v,height(v)+.06),(hi-.8,v,height(v)+.06),.20)
    return {'sourcePolygonVertices':len(ring),'outerUVMetres':[(lo+hi)/2,v0 if front else v1],
            'roofHeightMetres':outer_height,'datum':'isolated candidate base, not a surveyed arrival'}


def build(b,lm,spec,scale=.6):
    if spec.get('id')!='international-conference-center' or spec.get('cityId')!='hangzhou':raise ValueError('wrong city/object spec')
    if abs(scale-spec['coordinatePolicy']['scaleOnce'])>1e-12:raise ValueError('dimensions require exactly one city scale')
    old=b.frame;mesh=_Mesh(b,float(lm.get('y',0)),scale)
    b.frame=(float(lm['x']),float(lm['z']),spec['axisRadiansEastCCW'])
    sec=spec['estimates']['sphereSection']['value'];floors=spec['estimates']['floorBands']['value']
    low,high=sec['lowerCutM'],sec['goldSkinTopM'];front=spec['glazedFaceRelativeRadians']
    half=spec['estimates']['glazedFace']['value']['halfAngleRadians'];step=2*math.pi/96
    sphere_cuts=[front+half+(2*math.pi-2*half)*i/84 for i in range(85)]
    try:
        # Curved body is clipped at its base/roof, and at the glazed C-face.
        # Each floor has a projecting gold band, horizontal terrace and recessed
        # glass portion. It is neither a generic UV sphere nor an opaque gold ball.
        for level in range(floors['bands']):
            z0,z1=_mix(low,high,level/floors['bands']),_mix(low,high,(level+1)/floors['bands'])
            gold_top=z0+(z1-z0)*(1-floors['glassFraction'])
            r_out=sphere_radius_metres(max(z0,min(z1,sec['centerHeightM'])),spec)
            rg=sphere_radius_metres(gold_top,spec)-floors['recessM']
            rt=sphere_radius_metres(z1,spec)-floors['recessM']
            for a,t in zip(sphere_cuts,sphere_cuts[1:]):
                mesh.face('gold',[_p(a,r_out,z0),_p(t,r_out,z0),_p(t,r_out,gold_top),_p(a,r_out,gold_top)])
                mesh.face('gold',[_p(a,rg,gold_top),_p(a,r_out,gold_top),_p(t,r_out,gold_top),_p(t,rg,gold_top)])
                mesh.face('darkglass',[_p(a,rg,gold_top),_p(t,rg,gold_top),_p(t,rt,z1),_p(a,rt,z1)])
                next_radius=sphere_radius_metres(z1,spec)
                mesh.face('gold',[_p(a,rt,z1),_p(t,rt,z1),_p(t,next_radius,z1),_p(a,next_radius,z1)])
                # Thin seams follow each curved facade segment.
                epsilon=.035/r_out
                mesh.face('steel',[_p(a-epsilon,r_out+.025,z0),_p(a+epsilon,r_out+.025,z0),
                                   _p(a+epsilon,r_out+.025,gold_top),_p(a-epsilon,r_out+.025,gold_top)])
            # Tall actual theatre-facing glazed wedge is separate from gold band.
            for j in range(12):
                s,t=-1+j/6,-1+(j+1)/6
                mesh.face('landmarkglass',[_curtain_point(z0,s,spec),_curtain_point(z0,t,spec),
                                           _curtain_point(z1,t,spec),_curtain_point(z1,s,spec)])
            for s in [-1,-.66,-.33,0,.33,.66,1]:
                mesh.beam('steel',_curtain_point(z0,s,spec),_curtain_point(z1,s,spec),.12)
            mesh.beam('steel',_curtain_point(z0,-1,spec),_curtain_point(z0,1,spec),.14)
        # Solid side jambs bind the rim to the recessed wedge, preserving deep
        # vertical joints seen in the source; detailed engineering is pending.
        for theta,side in [(front-half,-1),(front+half,1)]:
            for k in range(15):
                z0,z1=_mix(low,high,k/15),_mix(low,high,(k+1)/15)
                p=[_p(theta,sphere_radius_metres(z0,spec),z0),_p(theta,sphere_radius_metres(z1,spec),z1),
                   _curtain_point(z1,side,spec),_curtain_point(z0,side,spec)]
                if side>0:p.reverse()
                mesh.face('gold',p)
        # Two representative wide vertical cladding/seam areas on the rear.
        for theta in [front+math.pi-.65,front+math.pi+.65]:
            for k in range(15):
                z0,z1=_mix(low,high,k/15),_mix(low,high,(k+1)/15)
                r0,r1=sphere_radius_metres(z0,spec)+.12,sphere_radius_metres(z1,spec)+.12
                mesh.face('gold',[_p(theta-.026,r0,z0),_p(theta+.026,r0,z0),
                                  _p(theta+.026,r1,z1),_p(theta-.026,r1,z1)])
        # Glass skylight: a shallow cap with concentric/radial framing, never a
        # new85m hemisphere on top of the body.
        cap_radius=sphere_radius_metres(high,spec)
        cap_rings=[cap_radius*f for f in [1,.8,.6,.4,.2]]
        def cap_height(r):return sec['skyRoofTopM']-(sec['skyRoofTopM']-high)*(r/cap_radius)**2
        for r,s in zip(cap_rings,cap_rings[1:]):
            for i in range(96):
                a,t=i*step,(i+1)*step
                mesh.face('landmarkglass',[_p(a,r,cap_height(r)),_p(t,r,cap_height(r)),
                                            _p(t,s,cap_height(s)),_p(a,s,cap_height(s))])
        for i in range(96):
            a,t=i*step,(i+1)*step;r=cap_rings[-1]
            mesh.face('landmarkglass',[_p(a,r,cap_height(r)),_p(t,r,cap_height(r)),(0,0,sec['skyRoofTopM'])])
        for r in cap_rings:
            for i in range(96):
                a,t=i*step,(i+1)*step
                mesh.face('steel',[_p(a,r-.055,cap_height(r)+.025),_p(a,r+.055,cap_height(r)+.025),
                                   _p(t,r+.055,cap_height(r)+.025),_p(t,r-.055,cap_height(r)+.025)])
        for i in range(32):
            theta=i*2*math.pi/32
            for r,s in zip(cap_rings,cap_rings[1:]):
                mesh.beam('steel',_p(theta,r,cap_height(r)+.04),_p(theta,s,cap_height(s)+.04),.12)
        # Glazed support/lobby below the ball, at an explicitly estimated level.
        lobby_radius=sphere_radius_metres(low,spec)
        for i in range(96):
            a,t=i*step,(i+1)*step
            mesh.face('darkglass',[_p(a,lobby_radius,0),_p(t,lobby_radius,0),_p(t,lobby_radius,low),_p(a,lobby_radius,low)])
        # Rounded low oval wings, preserving real source plan and two gaps. This
        # is a dome/barrel-like cladding section, not an elliptical slab or water.
        pod=spec['estimates']['podium']['value'];stations=pod['roofRadialStations']
        cuts=sorted(set([i*step for i in range(97)]+[(front-half_angle)%(2*math.pi) for half_angle in
          [-pod['frontGapHalfRadians'],pod['frontGapHalfRadians']]]+
          [(front+math.pi-half_angle)%(2*math.pi) for half_angle in [-pod['rearGapHalfRadians'],pod['rearGapHalfRadians']]]))
        roof_faces=0
        for a,t in zip(cuts,cuts[1:]):
            mid=(a+t)/2
            if _angle_distance(mid,front)<pod['frontGapHalfRadians'] or _angle_distance(mid,front+math.pi)<pod['rearGapHalfRadians']:continue
            ro0,ro1=radial_boundary_metres(spec['outerPodiumUVMetres'],a),radial_boundary_metres(spec['outerPodiumUVMetres'],t)
            for (f,z),(g,h) in zip(stations,stations[1:]):
                r0,s0=_mix(pod['innerRoofRadiusM'],ro0,f),_mix(pod['innerRoofRadiusM'],ro0,g)
                r1,s1=_mix(pod['innerRoofRadiusM'],ro1,f),_mix(pod['innerRoofRadiusM'],ro1,g)
                mesh.face('gold',[_p(a,r0,z),_p(a,s0,h),_p(t,s1,h),_p(t,r1,z)]);roof_faces+=1
            mesh.face('gold',[_p(a,ro0,0),_p(t,ro1,0),_p(t,ro1,stations[-1][1]),_p(a,ro0,stations[-1][1])])
            # Radial seam on the rounded canopy; each source segment not a mesh.
            for (f,z),(g,h) in zip(stations,stations[1:]):
                r,s=_mix(pod['innerRoofRadiusM'],ro0,f),_mix(pod['innerRoofRadiusM'],ro0,g)
                width=.035/max(r,1)
                mesh.face('steel',[_p(a-width,r,z+.03),_p(a-width,s,h+.03),_p(a+width,s,h+.03),_p(a+width,r,z+.03)])
        entry=spec['estimates']['entryGlazing']['value']
        front_report=_entry(mesh,spec['frontEntryUVMetres'],entry['frontInnerRoofM'],entry['frontOuterRoofM'],True)
        rear_report=_entry(mesh,spec['rearEntryUVMetres'],entry['rearInnerRoofM'],entry['rearOuterRoofM'],False)
        # The two OSM entry pieces describe outer ends, not the entire central
        # glazed connection. Link them to the observed lobby as explicit estimated
        # short corridors, rather than leaving detached roofs floating in a gap.
        rear_u=(min(p[0] for p in spec['rearEntryUVMetres'])+max(p[0] for p in spec['rearEntryUVMetres']))/2
        for is_front,key,center,width,hi,lo in [
            (True,'frontEntryUVMetres',0,entry['frontConnectorMouthWidthM'],entry['frontInnerRoofM'],entry['frontOuterRoofM']),
            (False,'rearEntryUVMetres',rear_u,entry['rearConnectorWidthM'],entry['rearInnerRoofM'],entry['rearOuterRoofM'])]:
            ring=spec[key];vmin,vmax=min(p[1] for p in ring),max(p[1] for p in ring)
            ends=[]
            for i in range(7):
                u=center-width/2+width*i/6;v=_source_entry_v(ring,u,is_front)
                fraction=(v-vmin)/(vmax-vmin);h=_mix(lo,hi,fraction) if is_front else _mix(hi,lo,fraction)
                if is_front:
                    sphere_half=sphere_radius_metres(low,spec)*math.sin(half)
                    body=_curtain_point(low,u/sphere_half,spec)
                else:body=(u,math.sqrt(lobby_radius*lobby_radius-u*u),low)
                ends.append((body,(u,v,h)))
            for (a,d),(bp,c) in zip(ends,ends[1:]):
                mesh.face('landmarkglass',[a,d,c,bp] if is_front else [a,bp,c,d])
            for p,q in [ends[0],ends[-1]]:mesh.face('darkglass',[(p[0],p[1],0),(q[0],q[1],0),q,p])
        # Rear road-side entry canopy represented independently from the roof.
        ring=spec['rearEntryUVMetres'];v=max(p[1] for p in ring);u=(min(p[0] for p in ring)+max(p[0] for p in ring))/2
        width=28;h=entry['rearOuterRoofM'];outer=v+entry['canopyProjectionM']
        mesh.face('landmarkglass',[(u-width/2,v,h),(u+width/2,v,h),(u+width/2,outer,h+.25),(u-width/2,outer,h+.25)])
        for x in [u-width/2,u-width/4,u,u+width/4,u+width/2]:
            mesh.beam('steel',(x,v,h+.1),(x,outer,h+.35),.20)
        for x in [u-width/2,u,u+width/2]:mesh.beam('steel',(x,outer,0),(x,outer,h+.25),.30)
        # Door framing only, no unverified sign/logo or new interactive interior.
        for report in [front_report,rear_report]:
            u,v=report['outerUVMetres'];height=entry['doorHeightM']
            for x in [u-3,u,u+3]:mesh.box('steel',(x,v,height/2),(.12,.14,height))
            mesh.box('steel',(u,v,height),(6,.14,.12))
    finally:b.frame=old
    return {'scope':spec['scope'],'sourceFeatureIds':spec['sourceFeatureIds'],'faces':mesh.faces,
      'materials':sorted(mesh.materials),'sphereDiameterReportedM':spec['diameterM'],'overallHeightReportedM':spec['heightM'],
      'annexHeightReportedM':spec['annexHeightM'],'estimatedSphereSection':sec,'terracedSphereBands':floors['bands'],
      'glazedFaceRadians':front,'glazedFaceHalfRadians':half,'shallowGlassSkylight':True,'roundedPodiumRoofFaces':roof_faces,
      'sourceAxisRadiansEastCCW':spec['axisRadiansEastCCW'],'entryCandidates':[front_report,rear_report],
      'lights':0,'waterMeshes':0,'scaleOnce':scale,'baseHeightGame':float(lm.get('y',0)),
      'materialSubstitutions':'darkglass stands for still-unmatched golden glass; gold for honeycomb; no official photograph textures',
      'integrationContract':spec['integrationContract'],'pending':spec['pendingSubscopes'],
      'accuracyClaim':'reference-informed exterior candidate; no current field survey, site accessibility or runtime acceptance'}

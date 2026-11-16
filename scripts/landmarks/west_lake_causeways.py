"""Source-bound West Lake Bai/Su banks and seven single-arch bridge candidates.

No Blender/scene import; the integrator owns export, lake water, navigation and
runtime height/collision. Broken Bridge is externally owned and never built here.
Source dimensions are real metres, scaled once; lm x/z/y are game units.
"""
from __future__ import annotations
import math
try:
    from city_config import load_city
except ImportError:
    from scripts.city_config import load_city


def _area(r):
    return sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(r,r[1:]+r[:1]))/2


def _ring(ps):
    r=[tuple(p) for p in ps]
    if r[0]==r[-1]:r.pop()
    if len(r)<3 or abs(_area(r))<1e-6:raise ValueError('Nonzero source land outline required')
    return r if _area(r)>0 else list(reversed(r))


def _inside(p,r):
    x,y=p;hit=False
    for (a,b),(c,d) in zip(r,r[1:]+r[:1]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:hit=not hit
    return hit


def _cross(p,q):return p[0]*q[1]-p[1]*q[0]
def _mix(p,q,t):return tuple(a+(b-a)*t for a,b in zip(p,q))


def _caps_minus(rings,exclusions):
    """Scanline fill of land minus the UNION of travel quads (never XOR holes).

    Edge intersections are inserted before forming slabs: changing edge order at
    a ribbon/source crossing cannot cap a travel strip or a real source notch.
    """
    relevant=[q for q in exclusions if not(max(p[0] for p in q)<min(p[0] for p in rings[0]) or
        min(p[0] for p in q)>max(p[0] for p in rings[0]) or
        max(p[1] for p in q)<min(p[1] for p in rings[0]) or min(p[1] for p in q)>max(p[1] for p in rings[0]))]
    allrings=rings+relevant
    edges=[(a,b) for r in allrings for a,b in zip(r,r[1:]+r[:1])]
    cuts=set(p[0] for r in allrings for p in r)
    for i,(a,b) in enumerate(edges):
        d=(b[0]-a[0],b[1]-a[1])
        for c,e in edges[i+1:]:
            v=(e[0]-c[0],e[1]-c[1]);den=_cross(d,v)
            if abs(den)<1e-9:continue
            ca=(c[0]-a[0],c[1]-a[1]);t,u=_cross(ca,v)/den,_cross(ca,d)/den
            if 0<t<1 and 0<u<1:cuts.add(a[0]+t*d[0])
    cuts=sorted(cuts)
    def yat(edge,x):
        a,b=edge;return a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
    for left,right in zip(cuts,cuts[1:]):
        if right-left<1e-7:continue
        mid=(left+right)/2
        crossing=sorted((e for e in edges if min(e[0][0],e[1][0])<mid<max(e[0][0],e[1][0])),key=lambda e:yat(e,mid))
        for low,high in zip(crossing,crossing[1:]):
            y0,y1=yat(low,mid),yat(high,mid)
            p=(mid,(y0+y1)/2)
            if y1-y0<1e-7 or not _inside(p,rings[0]) or any(_inside(p,r) for r in rings[1:]+relevant):continue
            q=[(left,yat(low,left)),(right,yat(low,right)),(right,yat(high,right)),(left,yat(high,left))]
            clean=[]
            for p in q:
                if not clean or math.dist(p,clean[-1])>1e-7:clean.append(p)
            if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-7:clean.pop()
            if len(clean)>2 and abs(_area(clean))>1e-7:yield _ring(clean)


class _Mesh:
    def __init__(self,b,scale,offset,base):
        self.b,self.s,self.offset,self.base=b,scale,offset,base
        self.faces=self.triangles=0;self.materials=set();self.parts={};self.part='unassigned'

    def point(self,p):
        x,y,z=p
        if not all(math.isfinite(v) for v in p):raise ValueError('Nonfinite causeway point')
        return (x+self.offset[0])*self.s,(y+self.offset[1])*self.s,self.base+z*self.s

    def face(self,material,ps):
        self.b.face(material,[self.point(p) for p in ps]);self.faces+=1
        self.triangles+=len(ps)-2;self.parts[self.part]=self.parts.get(self.part,0)+len(ps)-2;self.materials.add(material)

    def beam(self,material,a,b,z0,z1,width,height):
        dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy)
        if l<1e-7:return
        nx,ny=-dy/l*width/2,dx/l*width/2
        p=[(a[0]-nx,a[1]-ny,z0-height/2),(b[0]-nx,b[1]-ny,z1-height/2),
           (b[0]+nx,b[1]+ny,z1-height/2),(a[0]+nx,a[1]+ny,z0-height/2),
           (a[0]-nx,a[1]-ny,z0+height/2),(b[0]-nx,b[1]-ny,z1+height/2),
           (b[0]+nx,b[1]+ny,z1+height/2),(a[0]+nx,a[1]+ny,z0+height/2)]
        for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.face(material,[p[i] for i in ids])


def _context(lm,spec):
    g=load_city('hangzhou')['geography'];a=spec['anchor'];e,n=g['eastMetresPerDegree'],g['northMetresPerDegree']
    return {'g':g,'xy':lambda p:((p[0]-a['lon'])*e,(p[1]-a['lat'])*n),
            'offset':((a['lon']-lm.get('lon',a['lon']))*e,(a['lat']-lm.get('lat',a['lat']))*n)}


def _flat_sections(path,ctx):
    ps=[ctx['xy'](p) for p in path['coordinatesWGS84']];normals=[]
    for p,q in zip(ps,ps[1:]):
        d=(q[0]-p[0],q[1]-p[1]);l=math.hypot(*d)
        if l<1e-5:raise ValueError('Duplicate source road coordinates')
        normals.append((-d[1]/l,d[0]/l))
    result=[];half=path['flatTravelWidthM']/2
    for i,p in enumerate(ps):
        if i==0:v=normals[0]
        elif i==len(ps)-1:v=normals[-1]
        else:
            v=(normals[i-1][0]+normals[i][0],normals[i-1][1]+normals[i][1]);l=math.hypot(*v)
            v=(v[0]/l,v[1]/l);dot=v[0]*normals[i][0]+v[1]*normals[i][1]
            v=(v[0]/max(.8,dot),v[1]/max(.8,dot))
        result.append(((p[0]-v[0]*half,p[1]-v[1]*half),(p[0]+v[0]*half,p[1]+v[1]*half)))
    return result


def bridge_height_metres(s,path):
    """Reference-informed real-metre profile; endpoints are exactly height zero."""
    p=path['bridge'];length=path['sourceLengthM'];center=length*p['archPositionFraction']
    crown=p['springHeightM']+p['clearArchSpanM']/2+p['archRingThicknessM']+p['pavementThicknessM']
    if not 0<=s<=length:return 0.0
    t=s/center if s<=center else (length-s)/(length-center)
    return crown*math.sin(t*math.pi/2)


def arch_soffit_metres(s,path):
    p=path['bridge'];r=p['clearArchSpanM']/2;x=s-path['sourceLengthM']*p['archPositionFraction']
    return p['springHeightM']+math.sqrt(max(0,r*r-x*x)) if abs(x)<=r else p['springHeightM']-1.0


def _bridge_sections(path,ctx):
    ps=[ctx['xy'](p) for p in path['coordinatesWGS84']]
    if len(ps)!=2:raise ValueError('Frozen seven bridge ways each have exactly two source nodes')
    a,b=ps;length=math.dist(a,b);p=path['bridge'];center=length*p['archPositionFraction'];radius=p['clearArchSpanM']/2
    if not math.isclose(length,path['sourceLengthM'],abs_tol=1e-5):raise ValueError('Bridge source length changed')
    axis=((b[0]-a[0])/length,(b[1]-a[1])/length);normal=(-axis[1],axis[0])
    cuts={length*i/64 for i in range(65)}
    cuts.update(center+radius*math.cos(math.pi*i/24) for i in range(25));cuts.update([center,center-radius,center+radius])
    cuts=sorted(cuts)
    def pt(s,v,z):return (a[0]+axis[0]*s+normal[0]*v,a[1]+axis[1]*s+normal[1]*v,z)
    def width(s):
        # The reported net bridge width is distinct from planted-land width.
        # Approach taper only; it does not turn an entire way into a wide arch.
        core_half=min(p['coreBodyLengthM']/2,min(center,length-center)*.90)
        t=min(1,max(0,abs(s-center)-core_half)/(max(center,length-center)-core_half))
        return p['netTravelWidthM']+(path['flatTravelWidthM']-p['netTravelWidthM'])*t
    return {'cuts':cuts,'pt':pt,'width':width,'axis':axis,'normal':normal,'center':center,'radius':radius,'length':length}


def _bridge(m,path,ctx):
    p=path['bridge'];v=_bridge_sections(path,ctx);pt=v['pt'];cuts=v['cuts'];width=v['width']
    pavement=p['pavementThicknessM']
    for s,t in zip(cuts,cuts[1:]):
        if t-s<1e-7:continue
        h0,h1=bridge_height_metres(s,path),bridge_height_metres(t,path)
        z0,z1=arch_soffit_metres(s,path),arch_soffit_metres(t,path)
        w0,w1=width(s)/2+.26,width(t)/2+.26
        if min(h0-pavement-z0,h1-pavement-z1)<=0:raise ValueError('Bridge arch lost solid cover')
        m.face('concrete',[pt(s,-w0,h0-pavement),pt(t,-w1,h1-pavement),pt(t,w1,h1-pavement),pt(s,w0,h0-pavement)])
        m.face('concrete',[pt(s,w0,z0),pt(t,w1,z1),pt(t,-w1,z1),pt(s,-w0,z0)])
        m.face('asphalt',[pt(s,-w0,h0),pt(t,-w1,h1),pt(t,w1,h1),pt(s,w0,h0)])
        for side in [-1,1]:
            q=[pt(s,side*w0,z0),pt(t,side*w1,z1),pt(t,side*w1,h1-pavement),pt(s,side*w0,h0-pavement)]
            if side>0:q.reverse()
            m.face('concrete',q)
            q=[pt(s,side*w0,h0-pavement),pt(t,side*w1,h1-pavement),pt(t,side*w1,h1),pt(s,side*w0,h0)]
            if side>0:q.reverse()
            m.face('asphalt',q)
            # Coarse stone courses are trimmed to the true stone mass, no arch cap.
            for z in [-1,-.4,.2,.8,1.4,2.0,2.6,3.2]:
                if z>max(z0,z1)+.08 and z<min(h0,h1)-pavement-.06:
                    q=[pt(s,side*(w0+.018),z-.014),pt(t,side*(w1+.018),z-.014),pt(t,side*(w1+.018),z+.014),pt(s,side*(w0+.018),z+.014)]
                    if side>0:q.reverse()
                    m.face('roof',q)
    for s,sign in [(0,-1),(v['length'],1)]:
        w=width(s)/2+.26;lo=arch_soffit_metres(s,path);h=bridge_height_metres(s,path)
        q=[pt(s,-w,lo),pt(s,w,lo),pt(s,w,h),pt(s,-w,h)]
        if sign<0:q.reverse()
        m.face('concrete',q)
    # Segmented stone arch barrel/ring; semicircle remains visibly open.
    center,r=v['center'],v['radius'];spring=p['springHeightM'];ring=p['archRingThicknessM']
    for i in range(24):
        a,b=math.pi*i/24,math.pi*(i+1)/24
        for side in [-1,1]:
            edge=p['netTravelWidthM']/2+.285
            q=[pt(center+r*math.cos(a),side*edge,spring+r*math.sin(a)),
               pt(center+r*math.cos(b),side*edge,spring+r*math.sin(b)),
               pt(center+(r+ring)*math.cos(b),side*edge,spring+(r+ring)*math.sin(b)),
               pt(center+(r+ring)*math.cos(a),side*edge,spring+(r+ring)*math.sin(a))]
            # Arc ordering is opposite to the straight side-wall strip above.
            if side<0:q.reverse()
            m.face('concrete',q)
            joint=[pt(center+(r+.02)*math.cos(a),side*(edge+.01),spring+(r+.02)*math.sin(a)),
                   pt(center+(r+ring-.02)*math.cos(a),side*(edge+.01),spring+(r+ring-.02)*math.sin(a)),
                   pt(center+(r+ring-.02)*math.cos(a+.012),side*(edge+.01),spring+(r+ring-.02)*math.sin(a+.012)),
                   pt(center+(r+.02)*math.cos(a+.012),side*(edge+.01),spring+(r+.02)*math.sin(a+.012))]
            if side>0:joint.reverse()
            m.face('roof',joint)
    # Low stone rail family: Su open balusters and central panels; Bai plain panels.
    count=max(2,math.ceil(v['length']/p['railPitchM']));stations=[v['length']*i/count for i in range(count+1)]
    for side in [-1,1]:
        for s in stations:
            h=bridge_height_metres(s,path);x,y,_=pt(s,side*(width(s)/2+.11),0)
            axis=v['axis'];a=(x-axis[0]*.12,y-axis[1]*.12);b=(x+axis[0]*.12,y+axis[1]*.12)
            m.beam('concrete',a,b,h+p['railHeightM']/2,h+p['railHeightM']/2,.24,p['railHeightM'])
            m.beam('concrete',a,b,h+p['railHeightM']+.04,h+p['railHeightM']+.04,.32,.08)
        for index,(s,t) in enumerate(zip(stations,stations[1:])):
            a=pt(s,side*(width(s)/2+.11),0)[:2];b=pt(t,side*(width(t)/2+.11),0)[:2]
            h0,h1=bridge_height_metres(s,path),bridge_height_metres(t,path);rh=p['railHeightM']
            m.beam('concrete',a,b,h0+rh-.08,h1+rh-.08,.16,.15)
            if p['parapetStyle']=='solid-stone-panel':
                m.beam('concrete',a,b,h0+rh/2,h1+rh/2,.12,rh-.20)
            elif index==count//2:
                m.beam('concrete',a,b,h0+.45,h1+.45,.13,.65) # center plaque, inscription not fabricated
            else:
                m.beam('concrete',a,b,h0+.14,h1+.14,.16,.14)
                for f in [.33,.67]:
                    x,y=_mix(a,b,f);h=h0+(h1-h0)*f
                    # Low-poly carved-bracket silhouette, no literal decorative motif claim.
                    axis=v['axis'];u=(x-axis[0]*.14,y-axis[1]*.14);w=(x+axis[0]*.14,y+axis[1]*.14)
                    m.beam('concrete',u,w,h+.42,h+.42,.13,.40)
    return {'wayId':path['wayId'],'profileMetres':[[s,bridge_height_metres(s,path)] for s in cuts],
            'clearArchSpanM':p['clearArchSpanM'],'netTravelWidthM':p['netTravelWidthM'],'archCount':1,
            'coreBodyLengthM':p['coreBodyLengthM'],'coreWidthPlacement':'source corridor middle, estimated registration; individual core/net width retained',
            'archPositionFraction':p['archPositionFraction'],'sourceEndpointsWGS84':[path['coordinatesWGS84'][0],path['coordinatesWGS84'][-1]],
            'sourceNodeIds':path['nodes'],'estimatedVerticalDatum':True}


def walk_surfaces(lm,spec,scale=.6):
    """Integration metadata, not solid-building colliders. No lake polygons."""
    ctx=_context(lm,spec);result=[]
    for path in spec['paths']:
        result.append({'sourceId':path['sourceId'],'sourceNodeIds':path['nodes'],'coordinatesWGS84':path['coordinatesWGS84'],
            'travelWidthM':path['bridge']['netTravelWidthM'] if path['bridge'] else path['flatTravelWidthM'],
            'bridge':bool(path['bridge']),'heightProfileMetres':[[s,bridge_height_metres(s,path)] for s in _bridge_sections(path,ctx)['cuts']] if path['bridge'] else [[0,0],[path['sourceLengthM'],0]],
            'baseHeightGame':float(lm.get('y',0)),'heightScaleOnce':scale,'walkable':True})
    return result


def bridge_height_at(lon,lat,lm,spec,scale=.6):
    """Return game-unit deck height at a source bridge corridor, else None."""
    ctx=_context(lm,spec);point=ctx['xy']((lon,lat))
    for path in spec['paths']:
        if not path['bridge']:continue
        p=ctx['xy'](path['coordinatesWGS84'][0]);v=_bridge_sections(path,ctx);d=(point[0]-p[0],point[1]-p[1])
        s=d[0]*v['axis'][0]+d[1]*v['axis'][1];side=d[0]*v['normal'][0]+d[1]*v['normal'][1]
        if -1e-6<=s<=v['length']+1e-6 and abs(side)<=v['width'](s)/2:
            return float(lm.get('y',0))+bridge_height_metres(max(0,min(v['length'],s)),path)*scale
    return None


def build(b,lm,spec,scale=.6):
    if spec.get('id')!='west-lake-causeways' or spec.get('cityId')!='hangzhou':raise ValueError('Hangzhou causeways spec required')
    if len(spec['paths'])!=19 or sum(bool(p['bridge']) for p in spec['paths'])!=7:raise ValueError('Frozen path/bridge scope changed')
    if 28538289 in [p['wayId'] for p in spec['paths']]:raise ValueError('Broken Bridge belongs to external module')
    ctx=_context(lm,spec)
    if not math.isclose(scale,ctx['g']['scale'],abs_tol=1e-12):raise ValueError('Use canonical Hangzhou scale exactly once')
    if not all(math.isfinite(float(lm.get(k,0))) for k in ['x','z','y']):raise ValueError('Finite game anchor required')
    m=_Mesh(b,scale,ctx['offset'],float(lm.get('y',0)));old=b.frame;b.frame=(lm['x'],lm['z'],0)
    travel=[];bridges=[];landArea=0;capArea=0
    try:
        for path in spec['paths']:
            if path['bridge']:
                v=_bridge_sections(path,ctx);a=v['pt'](0,-path['flatTravelWidthM']/2-.3,0)[:2];bb=v['pt'](v['length'],-path['flatTravelWidthM']/2-.3,0)[:2]
                c=v['pt'](v['length'],path['flatTravelWidthM']/2+.3,0)[:2];d=v['pt'](0,path['flatTravelWidthM']/2+.3,0)[:2]
                travel.append(_ring([a,bb,c,d]));m.part='bridge-'+str(path['wayId']);bridges.append(_bridge(m,path,ctx))
            else:
                sections=_flat_sections(path,ctx);m.part='path-'+str(path['wayId'])
                for (a,d),(bb,c) in zip(sections,sections[1:]):
                    q=_ring([a,bb,c,d]);travel.append(q)
                    m.face('asphalt',[(*p,0) for p in q])
                    for p,r in [(a,bb),(d,c)]:m.beam('pavement',p,r,-.015,-.015,.16,.08)
        for land in spec['landStrips']:
            rings=[_ring([ctx['xy'](p) for p in r]) for r in land['ringsWGS84']]
            m.part='bank-'+land['sourceId'].replace('/','-');top=land['topHeightM'];landArea+=abs(_area(rings[0]))-sum(abs(_area(r)) for r in rings[1:])
            for q in _caps_minus(rings,travel):
                m.face('park',[(*p,top) for p in q]);capArea+=abs(_area(q))
            for r in rings:
                for p,q in zip(r,r[1:]+r[:1]):
                    # Source edges stay exact; low retaining wall is not a lake surface.
                    m.face('concrete',[(*p,spec['bankBottomM']),(*q,spec['bankBottomM']),(*q,top),(*p,top)])
                    mid=((p[0]+q[0])/2,(p[1]+q[1])/2)
                    if not any(_inside(mid,t) for t in travel):
                        m.beam('pavement',p,q,spec['bankCopingTopM']-.045,spec['bankCopingTopM']-.045,spec['bankCopingWidthM'],.09)
    finally:b.frame=old
    if m.triangles>spec['budget']['maxTriangles']:raise ValueError('Causeway candidate exceeds triangle budget')
    return {'scope':spec['scope'],'sourceFeatureIds':spec['sourceFeatureIds'],'sourceSnapshotSha256':spec['sourceSnapshotSha256'],
        'faces':m.faces,'triangles':m.triangles,'materials':sorted(m.materials),'partTriangles':m.parts,
        'pathCount':19,'bridgeCount':len(bridges),'bridges':bridges,'landStripCount':len(spec['landStrips']),
        'sourceLandAreaM2':landArea,'candidateGrassCapAreaM2':capArea,'walkSurfaces':walk_surfaces(lm,spec,scale),
        'externalWayIds':[28538289],'baseBuildingIdsToExclude':[],'baseRoadIdsToSuppressVisual':spec['baseRoadIdsToSuppressVisual'],
        'baseGreenIdsToSuppressVisual':spec['baseGreenIdsToSuppressVisual'],'waterMeshes':0,'newLights':0,'newTextures':0,'scaleOnce':scale,
        'baseHeightGame':float(lm.get('y',0)),'groundFootprints':'none; use walk_surfaces, never whole causeway as solid building collision',
        'integrationContract':spec['integrationContract'],'pending':spec['pendingSubscopes'],
        'accuracyClaim':'finite reference-informed exterior candidate, OSM measured plan/official reported bridge dimensions; vertical/Jindai dimensions estimated'}

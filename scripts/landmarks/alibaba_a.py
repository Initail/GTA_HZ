"""Source-bound current Alibaba A exterior candidate; no Blender side effects.

Eight mappedoffice objects plusfour mappedlinks are not equated with architect
2013 sixunits. A9/phasecrosswalk/full>1km links retain blockers. Mappedholes and
concave sourceboundaries stay intact; individual heights are boundedestimates.
KKAA0.30mfold/2meave are reported; other facade/roof/link geometry estimated.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city
except ImportError:
    from scripts.city_config import load_city


def _area(r):
    return sum(x*v-u*y for (x,y),(u,v) in zip(r,r[1:]+r[:1]))/2


def _ring(points, ccw=True):
    r = [tuple(p) for p in points]
    if r[0] == r[-1]:
        r.pop()
    if len(r)<3 or abs(_area(r))<1e-6:
        raise ValueError('A campus needs a nonzero source outline')
    return r if (_area(r)>0)==ccw else list(reversed(r))


def _mix(a,b,t):
    return tuple(x+(y-x)*t for x,y in zip(a,b))


def _center(r):
    # Bbox center rather than a vertex average affected by collinear vertices.
    return tuple((min(p[k] for p in r)+max(p[k] for p in r))/2 for k in (0,1))


def _inside(p,r):
    x,y = p; hit = False
    for (a,b),(c,d) in zip(r,r[1:]+r[:1]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:
            hit = not hit
    return hit


def _bands(rings):
    """Convex scanline quads of concave outlines with holes, in unscaled metres.

    Sorted vertex-x intervals never cross a boundary corner. Pairing all edge
    intersections by odd/even fill preserves inner holes and visitor's notch.
    This replaces a triangle fan which would otherwise cap the campus voids.
    """
    cuts = sorted(set(p[0] for r in rings for p in r))
    edges = [(a,b) for r in rings for a,b in zip(r,r[1:]+r[:1])]
    def y_at(edge,x):
        (a,b),(c,d) = edge
        return b+(d-b)*(x-a)/(c-a)
    for left,right in zip(cuts,cuts[1:]):
        if right-left<1e-7:
            continue
        mid = (left+right)/2
        crossing = sorted((e for e in edges if min(e[0][0],e[1][0])<mid<max(e[0][0],e[1][0])),
                          key=lambda e:y_at(e,mid))
        if len(crossing)%2:
            raise ValueError('Unpaired A campus polygon crossing')
        for low,high in zip(crossing[::2],crossing[1::2]):
            r = [(left,y_at(low,left)),(right,y_at(low,right)),
                 (right,y_at(high,right)),(left,y_at(high,left))]
            # Collapse only duplicate endpoints; never bridge a real atrium.
            clean = []
            for p in r:
                if not clean or math.dist(p,clean[-1])>1e-7:
                    clean.append(p)
            if len(clean)>2 and math.dist(clean[0],clean[-1])<1e-7:
                clean.pop()
            if len(clean)>2 and abs(_area(clean))>1e-7:
                yield _ring(clean)


class _Mesh:
    def __init__(self,b,scale,offset,base):
        self.b,self.scale,self.offset,self.base = b,scale,offset,base
        self.faces = self.triangles = 0
        self.materials = set(); self.parts = {}; self.part = 'unassigned'

    def point(self,p):
        if not all(math.isfinite(v) for v in p):
            raise ValueError('Nonfinite A campus vertex')
        x,y,z = p
        return (x+self.offset[0])*self.scale,(y+self.offset[1])*self.scale,z*self.scale+self.base

    def face(self,material,ps):
        self.b.face(material,[self.point(p) for p in ps])
        self.faces += 1; n = len(ps)-2; self.triangles += n
        self.parts[self.part] = self.parts.get(self.part,0)+n
        self.materials.add(material)

    def slab(self,rings,bottom,top,material='concrete'):
        for r in rings:
            for p,q in zip(r,r[1:]+r[:1]):
                self.face(material,[(*p,bottom),(*q,bottom),(*q,top),(*p,top)])
        for r in _bands(rings):
            self.face(material,[(*p,top) for p in r])
            self.face(material,[(*p,bottom) for p in reversed(r)])

    def box(self,material,p,size):
        x,y,z = p; a,c,h = [v/2 for v in size]
        r = [(x-a,y-c),(x+a,y-c),(x+a,y+c),(x-a,y+c)]
        self.slab([r],z-h,z+h,material)


def _split_edges(r,ctx):
    """Split collinear source boundaries so adjacent modules do not z-fight."""
    for a,b in zip(r,r[1:]+r[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);cuts={0.,1.}
        for p in ctx['vertices']:
            t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length)
            if 1e-6<t<1-1e-6 and abs((p[0]-a[0])*dy-(p[1]-a[1])*dx)/length<.02:cuts.add(t)
        cuts=sorted(cuts)
        for low,high in zip(cuts,cuts[1:]):
            if (high-low)*length>.03:yield _mix(a,b,low),_mix(a,b,high)


def _visible_intervals(obj,p,q,ctx):
    bottom,top=obj['bodyBottomM'],obj['height']['value']-.7
    length=math.dist(p,q);out=((q[1]-p[1])/length,-(q[0]-p[0])/length)
    mid=_mix(p,q,.5);probe=(mid[0]+out[0]*.04,mid[1]+out[1]*.04)
    intervals=[(bottom,top)]
    for neighbor,rs in ctx['objects']:
        if neighbor is obj or not _inside(probe,rs[0]):continue
        lo,hi=neighbor['bodyBottomM'],neighbor['height']['value']
        remaining=[]
        for a,b in intervals:
            if hi<=a or lo>=b:remaining.append((a,b));continue
            if a<lo:remaining.append((a,lo))
            if hi<b:remaining.append((hi,b))
        intervals=remaining
    return intervals


def _context(lm,spec):
    if spec.get('id')!='alibaba-a' or spec.get('cityId')!='hangzhou':raise ValueError('A requires its own Hangzhou specification')
    geo=load_city('hangzhou')['geography'];e,n=geo['eastMetresPerDegree'],geo['northMetresPerDegree'];a=spec['anchor']
    objects=[(o,[_ring([((lon-a['lon'])*e,(lat-a['lat'])*n) for lon,lat in r],i==0)
                  for i,r in enumerate(o['ringsWGS84'])]) for o in spec['objects']]
    return {'objects':objects,'vertices':[p for _,rs in objects for r in rs for p in r],'geo':geo,
        'offset':((a['lon']-lm.get('lon',a['lon']))*e,(a['lat']-lm.get('lat',a['lat']))*n)}


def _wall(m,obj,p,q,intervals,spec,inner=False):
    length=math.dist(p,q);tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=ty,-tx
    def pt(u,z,out=0):return p[0]+tx*u+nx*out,p[1]+ty*u+ny*out,z
    facade=spec['facade'];count=max(1,round(length/facade['bayM']))
    for low,high in intervals:
        if high-low<.02:continue
        for k in range(count):
            u,v=k*length/count,(k+1)*length/count;mid=(u+v)/2
            depth=facade['foldDepthM']*(.35 if inner else 1)
            m.face('landmarkglass',[pt(u,low),pt(mid,low,depth),pt(mid,high,depth),pt(u,high)])
            m.face('landmarkglass',[pt(mid,low,depth),pt(v,low),pt(v,high),pt(mid,high,depth)])
            m.face('darkglass',[pt(u-.055,low,.03),pt(u+.055,low,.03),pt(u+.055,high,.03),pt(u-.055,high,.03)])
        pitch=(obj['height']['value']-obj['bodyBottomM'])/obj['courses']
        for k in range(1,obj['courses']+1):
            z=obj['bodyBottomM']+pitch*k
            if not low<z<=high+.01:continue
            out=facade['floorFinM']*(.45 if inner else 1);th=facade['finThicknessM']
            m.face('silver',[pt(0,z-th,.02),pt(length,z-th,.02),pt(length,z-th,out),pt(0,z-th,out)])
            m.face('silver',[pt(0,z,out),pt(length,z,out),pt(length,z,.02),pt(0,z,.02)])
            m.face('silver',[pt(0,z-th,out),pt(length,z-th,out),pt(length,z,out),pt(0,z,out)])


def _rooflight(obj,r,spec):
    """Optional estimated glassroof stripe, never an inventedground courtyard."""
    p,q=max(zip(r,r[1:]+r[:1]),key=lambda e:math.dist(*e));length=math.dist(p,q)
    tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=-ty,tx
    us=[x*tx+y*ty for x,y in r];vs=[x*nx+y*ny for x,y in r]
    u0,u1=min(us),max(us);v0,v1=min(vs),max(vs)
    half=min(65,(u1-u0)*spec['unmappedRooflight']['lengthFraction'])/2;w=spec['unmappedRooflight']['widthM']/2
    def point(u,v):return u*tx+v*nx,u*ty+v*ny
    for offset in (0,-.15,.15,-.25,.25):
        cu,cv=(u0+u1)/2,(v0+v1)/2+(v1-v0)*offset
        for factor in (1,.72,.5):
            slit=[point(cu-half*factor,cv-w),point(cu+half*factor,cv-w),point(cu+half*factor,cv+w),point(cu-half*factor,cv+w)]
            if all(_inside(p,r) for p in slit):return _ring(slit,False)
    return None


def _roof(m,obj,rings,spec):
    h=obj['height']['value'];outer=rings[0];slit=None
    if len(rings)==1:slit=_rooflight(obj,outer,spec)
    solids=rings+([slit] if slit else [])
    for band in _bands(solids):m.face('roof',[(*p,h) for p in band])
    if slit:
        m.face('landmarkglass',[(*p,h+.025) for p in reversed(slit)])
        for p,q in zip(slit,slit[1:]+slit[:1]):m.face('silver',[(*p,h+.03),(*q,h+.03),(*q,h+.12),(*p,h+.12)])
    rail=spec['facade']['roofRailHeightM']
    for p,q in zip(outer,outer[1:]+outer[:1]):
        length=math.dist(p,q);tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=-ty,tx
        a,b=(p[0]+nx*.12,p[1]+ny*.12),(q[0]+nx*.12,q[1]+ny*.12)
        m.face('silver',[(*a,h+rail-.04),(*b,h+rail-.04),(*b,h+rail+.04),(*a,h+rail+.04)])
        for k in range(max(1,int(length/7))):
            c=_mix(a,b,(k+.5)/max(1,int(length/7)))
            m.face('silver',[(c[0]-.04,c[1],h),(c[0]+.04,c[1],h),(c[0]+.04,c[1],h+rail),(c[0]-.04,c[1],h+rail)])
    # A few rooftop louver/screens, kept within sourceoccupied polygon and
    # away from all sourcecourtyard holes / candidate glassroof stripe.
    p,q=max(zip(outer,outer[1:]+outer[:1]),key=lambda e:math.dist(*e));l=math.dist(p,q)
    tx,ty=(q[0]-p[0])/l,(q[1]-p[1])/l;nx,ny=-ty,tx
    for t in (.22,.61):
        x,y=p[0]+tx*l*t+nx*4,p[1]+ty*l*t+ny*4
        rect=[(x+tx*u+nx*v,y+ty*u+ny*v) for u,v in ((-4,-1.2),(4,-1.2),(4,1.2),(-4,1.2))]
        if all(_inside(a,outer) and not any(_inside(a,r) for r in solids[1:]) for a in rect):
            m.slab([_ring(rect)],h,h+spec['facade']['roofEquipmentHeightM'],'silver')
    return slit is not None


def _line_strip(m,mat,point,a,b,width):
    dx,dz=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dz)
    if length<.001:return
    nx,nz=-dz/length*width/2,dx/length*width/2
    m.face(mat,[point(a[0]-nx,a[1]-nz),point(b[0]-nx,b[1]-nz),point(b[0]+nx,b[1]+nz),point(a[0]+nx,a[1]+nz)])


def _link_supports(obj,r,spec):
    side=spec['links']['columnSideM'];result=[]
    for p,q in zip(r,r[1:]+r[:1]):
        length=math.dist(p,q);tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=-ty,tx
        count=max(1,int(length/spec['links']['columnPitchM']))
        for k in range(count):
            x,y=p[0]+tx*length*(k+.5)/count+nx*.8,p[1]+ty*length*(k+.5)/count+ny*.8
            if all(_inside((x+sx*side/2,y+sy*side/2),r) for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1))):result.append((x,y))
    return result


def _links(m,obj,rings,ctx,spec):
    bottom,top=obj['bodyBottomM'],obj['height']['value'];links=spec['links']
    # Mappedlink holes are not filled by a fan. Both decks are elevated and
    # only estimated supports become groundcolliders; library/sports uses
    # remain source facts, without invented interactable interiors.
    for band in _bands(rings):
        m.face('roof',[(*p,top) for p in band]);m.face('concrete',[(*p,bottom) for p in reversed(band)])
    for x,y in _link_supports(obj,rings[0],spec):m.box('concrete',(x,y,bottom/2),(links['columnSideM'],links['columnSideM'],bottom))
    colour='gold' if obj['sourceId'] in links['warmSourceIds'] else 'silver'
    lattice=0;trusses=0
    for i,r in enumerate(rings):
        for edge,(p,q) in enumerate(zip(r,r[1:]+r[:1])):
            length=math.dist(p,q);tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=ty,-tx
            def pt(u,z,out=.08):return p[0]+tx*u+nx*out,p[1]+ty*u+ny*out,z
            visible=_visible_intervals(obj,p,q,ctx) if i==0 else [(bottom,top)]
            for low,high in visible:
                if high-low>.02:m.face('landmarkglass',[pt(0,low,0),pt(length,low,0),pt(length,high,0),pt(0,high,0)])
            if i>0:continue
            count=max(1,math.ceil(length/links['trussPitchM']))
            middle=(bottom+top)/2
            for k in range(count):
                a,b=k*length/count,(k+1)*length/count
                for lo,hi in ((bottom,middle),(middle,top)):
                    _line_strip(m,'steel',lambda u,z:pt(u,z,.10),(a,lo),((a+b)/2,hi),.17)
                    _line_strip(m,'steel',lambda u,z:pt(u,z,.10),((a+b)/2,hi),(b,lo),.17)
                    trusses+=1
                _line_strip(m,'steel',lambda u,z:pt(u,z,.10),(a,bottom),(a,top),.18)
            if length<8:continue
            # Coarse authored woven shade, with real geometric openings.
            # Architectreported2meave/mesh type; exactstrand pitch/profile
            # and per-edge orange/silver registration stay estimated.
            for level,z0 in enumerate((bottom+.5,top)):
                def shade(u,depth):
                    t=u/length
                    phase=(t+edge%3*.17)%1
                    bend=links['eaveSlopeM']*(1-abs(2*phase-1))
                    return pt(u,z0+bend+depth*.38,depth)
                rows=max(1,round(length/links['meshSampleM']));width=.07
                for k in range(rows+1):
                    u=k*length/rows
                    m.face(colour,list(reversed([shade(u-width/2,.12),shade(u+width/2,.12),shade(u+width/2,links['eaveDepthM']),shade(u-width/2,links['eaveDepthM'])])));lattice+=1
                segments=max(1,math.ceil(length/8))
                for d in (.2,1.05,1.95):
                    for k in range(segments):
                        a,b=k*length/segments,(k+1)*length/segments
                        m.face(colour,list(reversed([shade(a,d-.035),shade(b,d-.035),shade(b,d+.035),shade(a,d+.035)])))
    return lattice,trusses


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('Positive finite scale required')
    ctx=_context(lm,spec);previous=b.frame;b.frame=(lm['x'],lm['z'],0)
    m=_Mesh(b,scale,ctx['offset'],lm.get('y',0));slits=meshstrands=trusses=0
    try:
        for obj,rings in ctx['objects']:
            m.part=obj['label']
            if obj['kind']=='link':
                a,c=_links(m,obj,rings,ctx,spec);meshstrands+=a;trusses+=c;continue
            for i,r in enumerate(rings):
                for p,q in (_split_edges(r,ctx) if i==0 else zip(r,r[1:]+r[:1])):
                    visible=_visible_intervals(obj,p,q,ctx) if i==0 else [(0,obj['height']['value'])]
                    _wall(m,obj,p,q,visible,spec,i>0)
            slits+=_roof(m,obj,rings,spec)
    finally:b.frame=previous
    if m.triangles>spec['budget']['maxTriangles']:raise ValueError('A budget exceeded: '+str(m.triangles))
    return {'id':'alibaba-a','scope':spec['scope'],'mappedOfficeObjects':8,'mappedLinkObjects':4,
        'modeledSourceObjects':12,'sourceHoleCount':sum(len(rs)-1 for _,rs in ctx['objects']),
        'estimatedNonGroundRooflightCount':slits,'linkLatticeCrossStrandCount':meshstrands,'linkTrussBayCount':trusses,
        'historicalSixUnitMapping':'unresolved; no1..6 automatic mapping','newLights':0,'photoTextures':0,
        'generatedFaces':m.faces,'triangleCountBeforeExport':m.triangles,'materials':sorted(m.materials),'partTriangles':m.parts,
        'sourceFootprintIds':spec['baseBuildingIdsToExclude'],'geographyCityId':'hangzhou','projectionOriginWGS84':ctx['geo']['originWGS84'],
        'pendingSubscopes':spec['pendingSubscopes'],'excludedSubscopeBlockers':spec['excludedSubscopeBlockers']}


def ground_footprints(lm,spec,scale=.6):
    """Mapped office solids minus mapped holes, estimated link supports only.

    Glassroof estimates do not create fictitiousground holes. Real doors,
    precise columns/clearance/navigation and terrain remain integrationpending.
    """
    ctx=_context(lm,spec);solids=[];side=spec['links']['columnSideM']/2
    for obj,rs in ctx['objects']:
        if obj['kind']=='office':solids.extend(_bands(rs))
        else:
            for x,y in _link_supports(obj,rs[0],spec):solids.append([(x-side,y-side),(x+side,y-side),(x+side,y+side),(x-side,y+side)])
    dx,dy=ctx['offset']
    return [[[lm['x']+(x+dx)*scale,lm['z']+(y+dy)*scale] for x,y in r] for r in solids]

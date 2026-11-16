"""Evidence-gated Alibaba Xixi C (Phase5) exterior candidate; no bpy side effects.

Six individual mapped footprints/atria, visitor, exchange bridges, and Media Roof.
Per-building heights, rooftop recesses and facade/link dimensions are explicitly
estimated in docs/hangzhou/research/ali/alibaba-c-round2/spec.json. The reported
project80m/15F is not assigned to every building. No photo textures or new lights.
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
        raise ValueError('C campus needs a nonzero source outline')
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
            raise ValueError('Unpaired C campus polygon crossing')
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


def _context(lm,spec):
    if spec.get('id')!='alibaba-c' or spec.get('cityId')!='hangzhou':
        raise ValueError('Alibaba C requires its own Hangzhou specification')
    geo = load_city('hangzhou')['geography']
    east,north = geo['eastMetresPerDegree'],geo['northMetresPerDegree']
    a = spec['anchor']; lon,lat = a['lon'],a['lat']
    def convert(rs):
        return [_ring([((x-lon)*east,(y-lat)*north) for x,y in r],i==0) for i,r in enumerate(rs)]
    buildings = [(obj,convert(obj['ringsWGS84'])) for obj in spec['buildings']]
    roof = convert(spec['mediaRoof']['ringsWGS84'])
    offset = ((lon-lm.get('lon',lon))*east,(lat-lm.get('lat',lat))*north)
    return {'geo':geo,'offset':offset,'buildings':buildings,'roof':roof}


class _Mesh:
    def __init__(self,b,scale,offset,base):
        self.b,self.scale,self.offset,self.base = b,scale,offset,base
        self.faces = self.triangles = 0
        self.materials = set(); self.parts = {}; self.part = 'unassigned'

    def point(self,p):
        if not all(math.isfinite(v) for v in p):
            raise ValueError('Nonfinite C campus vertex')
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


def _facade(m,r,top,courses,spec,interior=False):
    facade = spec['facade']; pitch = (top-2)/courses
    for edge,(p,q) in enumerate(zip(r,r[1:]+r[:1])):
        length = math.dist(p,q)
        if length<1e-6:
            continue
        tx,ty = (q[0]-p[0])/length,(q[1]-p[1])/length
        nx,ny = ty,-tx
        def point(u,z,out=0):
            return p[0]+tx*u+nx*out,p[1]+ty*u+ny*out,z
        m.face('landmarkglass',[point(0,0),point(length,0),point(length,top-1.6),point(0,top-1.6)])
        bays = max(1,round(length/facade['bayM']))
        # Horizontal floor rails and projecting major belts. The observed
        # three-storey macro-rhythm is separate from estimated actual floors.
        for course in range(1,courses+1):
            z = min(top-1.7,pitch*course)
            m.face('silver',[point(0,z-.07,.03),point(length,z-.07,.03),
                              point(length,z+.07,.03),point(0,z+.07,.03)])
            if not interior and course%facade['majorEveryCourses']==0:
                out = facade['majorFinProjectionM']
                m.face('silver',[point(0,z,.02),point(length,z,.02),point(length,z,out),point(0,z,out)])
                m.face('silver',[point(0,z-.15,out),point(length,z-.15,out),point(length,z-.15,.02),point(0,z-.15,.02)])
                m.face('steel',[point(0,z-.15,out),point(length,z-.15,out),point(length,z,out),point(0,z,out)])
        for bay in range(bays+1):
            u = bay*length/bays; w = facade['ribWidthM']
            m.face('silver',[point(u-w/2,0,.24),point(u+w/2,0,.24),
                              point(u+w/2,top-.3,.24),point(u-w/2,top-.3,.24)])
            if not interior:
                m.face('steel',[point(u-w/2,0,.035),point(u-w/2,0,.24),
                                 point(u-w/2,top-.3,.24),point(u-w/2,top-.3,.035)])
            for course in range(1,courses):
                # Sparse authored opaque/privacy panels: current photos show
                # irregular pale window panels, not identical window boxes.
                if bay==bays or (bay+course+edge)%3:
                    continue
                lo = pitch*course+.4; hi = min(top-1.8,lo+pitch*.32)
                if hi>lo:
                    material = 'concrete' if (bay+2*course+edge)%5==0 else 'darkglass'
                    m.face(material,[point(u+.28,lo,.025),point(u+length/bays-.28,lo,.025),
                                     point(u+length/bays-.28,hi,.025),point(u+.28,hi,.025)])


def _office_roof(m,obj,rings):
    h = obj['height']['value']; setback = obj['roofSetbackM']['value']
    # Source holes remain lightwells. Roof solid bands are triangulated with
    # holes; mapped atria are covered only by a separate authored skylight.
    for r in _bands(rings):
        m.face('roof',[(*p,h-1.5) for p in r])
    for i,r in enumerate(rings):
        for p,q in zip(r,r[1:]+r[:1]):
            m.face('silver',[(*p,h-1.5),(*q,h-1.5),(*q,h-.25),(*p,h-.25)])
        if i==0:
            continue
        m.face('landmarkglass',[(*p,h-.8) for p in reversed(r)])
        # Recessed central roof-light and repeated transverse frames, using
        # source-derived long direction, not a guessed north/south rotation.
        long = max(zip(r,r[1:]+r[:1]),key=lambda e:math.dist(*e))
        a,b = long; dx,dy = b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
        tx,ty = dx/length,dy/length; nx,ny=-ty,tx
        c = _center(r); width = abs(sum((p[0]-c[0])*nx+(p[1]-c[1])*ny for p in r[:1]))*2
        # Use min/max projection rather than polygon vertex order for width.
        v = [p[0]*nx+p[1]*ny for p in r]; width = max(v)-min(v)
        u = [p[0]*tx+p[1]*ty for p in r]; low,high = min(u),max(u)
        vc = (min(v)+max(v))/2
        for k in range(1,17):
            uc = low+(high-low)*k/17
            def pt(uu,vv,z):return uu*tx+vv*nx,uu*ty+vv*ny,z
            m.face('silver',[pt(uc-.11,vc-width/2,h-.70),pt(uc+.11,vc-width/2,h-.70),
                              pt(uc+.11,vc+width/2,h-.70),pt(uc-.11,vc+width/2,h-.70)])
    # Shallow recessed roof-edge screens/terrace frames observed in scheme.
    # They are not extra tower setbacks or claimed photovoltaic equipment.
    r = rings[0]; cx,cy = _center(r)
    w = max(x for x,y in r)-min(x for x,y in r)
    d = max(y for x,y in r)-min(y for x,y in r)
    inner = [(cx+(x-cx)*(1-2*setback/w),cy+(y-cy)*(1-2*setback/d)) for x,y in r]
    for p,q in zip(inner,inner[1:]+inner[:1]):
        m.face('steel',[(*p,h-.95),(*q,h-.95),(*q,h-.55),(*p,h-.55)])


def _boundary_exit(c,target,r):
    """Last outer-boundary crossing from body reference toward next body."""
    dx,dy = target[0]-c[0],target[1]-c[1]; candidates=[]
    for a,b in zip(r,r[1:]+r[:1]):
        ex,ey=b[0]-a[0],b[1]-a[1]; det=dx*ey-dy*ex
        if abs(det)<1e-9:continue
        ax,ay=a[0]-c[0],a[1]-c[1]
        t=(ax*ey-ay*ex)/det; u=(ax*dy-ay*dx)/det
        if 0<=t<=1 and 0<=u<=1:candidates.append(t)
    if not candidates:raise ValueError('Bridge has no body boundary crossing')
    return _mix(c,target,max(candidates))


def _strip(a,b,width):
    dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
    if length<.5:return None
    nx,ny=-dy/length*width/2,dx/length*width/2
    return _ring([(a[0]-nx,a[1]-ny),(b[0]-nx,b[1]-ny),
                  (b[0]+nx,b[1]+ny),(a[0]+nx,a[1]+ny)])


def bridge_segments(ctx,spec):
    objects={obj['label']:rings[0] for obj,rings in ctx['buildings']}
    sequence=spec['exchangeRing']['sequence']; result=[]
    for left,right in zip(sequence,sequence[1:]):
        a,b=objects[left],objects[right]; ca,cb=_center(a),_center(b)
        pa,pb=_boundary_exit(ca,cb,a),_boundary_exit(cb,ca,b)
        r=_strip(pa,pb,spec['exchangeRing']['widthM'])
        if r:result.append((left,right,pa,pb,r))
    return result


def _links(m,ctx,spec):
    ring=spec['exchangeRing']; top=ring['deckTopM']
    links=bridge_segments(ctx,spec)
    for left,right,a,b,r in links:
        m.part='exchange-'+left+'-'+right
        m.slab([r],top-ring['deckThicknessM'],top,'concrete')
        # Glazed sides stop below the top silver handrail; underpass stays
        # unfilled. Elevated geometry is not a ground collision blocker.
        for p,q in ((r[0],r[1]),(r[2],r[3])):
            m.face('landmarkglass',[(*p,top),(*q,top),(*q,top+ring['glassRailM']),(*p,top+ring['glassRailM'])])
            m.face('silver',[(*p,top+ring['glassRailM']),(*q,top+ring['glassRailM']),
                              (*q,top+ring['glassRailM']+.08),(*p,top+ring['glassRailM']+.08)])
    return len(links)


def _media_roof(m,ctx,spec):
    roof=spec['mediaRoof']; top=roof['deckTopM']; rings=ctx['roof']
    m.part='south-media-roof'
    m.slab(rings,top-roof['deckThicknessM'],top,'silver')
    # The long south roof is a thin elevated plate, not a486m solid box.
    # Source geometry includes two sides; identify its longest edge direction.
    r=rings[0]; a,b=max(zip(r,r[1:]+r[:1]),key=lambda e:math.dist(*e))
    dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy); tx,ty=dx/length,dy/length; nx,ny=-ty,tx
    us=[p[0]*tx+p[1]*ty for p in r]; vs=[p[0]*nx+p[1]*ny for p in r]
    u0,u1=min(us),max(us); v0,v1=min(vs),max(vs)
    support=[]
    count=max(1,int((u1-u0)/roof['columnPitchM']))
    for k in range(1,count):
        u=u0+(u1-u0)*k/count
        for v in (v0+3,v1-3):
            x,y=u*tx+v*nx,u*ty+v*ny
            if _inside((x,y),r):
                m.box('concrete',(x,y,(top-roof['deckThicknessM'])/2),(1.0,1.0,top-roof['deckThicknessM']))
                support.append((x,y))
    return support


def _visitor_portal(m,obj,rings,spec):
    # Scheme roof/visitor shows a glazed arrival hall. Exact location is still
    # pending; this shallow authored accent is not an interactive entrance.
    r=rings[0]; edges=list(zip(r,r[1:]+r[:1]))
    p,q=max((e for e in edges if e[1][0]>e[0][0]),key=lambda e:math.dist(*e))
    length=math.dist(p,q); t=spec['visitorEntry']['widthM']/length/2
    a,b=_mix(p,q,.5-t),_mix(p,q,.5+t); h=spec['visitorEntry']['heightM']
    dx,dy=(q[0]-p[0])/length,(q[1]-p[1])/length; nx,ny=dy,-dx
    pa,pb=(a[0]+nx*.09,a[1]+ny*.09),(b[0]+nx*.09,b[1]+ny*.09)
    m.part='visitor-estimated-arrival-accent'
    m.face('darkglass',[(*pa,0),(*pb,0),(*pb,h),(*pa,h)])
    m.face('concrete',[(*pa,h),(*pb,h),(pb[0]+nx*1.6,pb[1]+ny*1.6,h),
                       (pa[0]+nx*1.6,pa[1]+ny*1.6,h)])


def build(b,lm,spec,scale=.6):
    """Append B-face geometry; caller owns scene, grouping and export.

    lm.x/z/y are already game units. WGS84 metres and heights scale once.
    Neither rendering nor source checks import city_mesh or initialize Blender.
    """
    if not math.isfinite(scale) or scale<=0:raise ValueError('Positive scale required')
    ctx=_context(lm,spec); previous=b.frame; b.frame=(lm['x'],lm['z'],0)
    m=_Mesh(b,scale,ctx['offset'],lm.get('y',0))
    try:
        for obj,rings in ctx['buildings']:
            m.part=obj['label']+'-facade-and-roof'
            for i,r in enumerate(rings):_facade(m,r,obj['height']['value'],obj['facadeCourses'],spec,i>0)
            _office_roof(m,obj,rings)
            if obj['label']=='访客中心':_visitor_portal(m,obj,rings,spec)
        link_count=_links(m,ctx,spec)
        supports=_media_roof(m,ctx,spec)
    finally:
        b.frame=previous
    if m.triangles>spec['budget']['maxTriangles']:raise ValueError('Alibaba C triangle budget exceeded: '+str(m.triangles))
    return {'id':'alibaba-c','scope':spec['scope'],'officeCount':6,'visitorCount':1,
        'sourceAtriumCount':6,'bridgeCount':link_count,'mediaRoofSupportCount':len(supports),
        'generatedFaces':m.faces,'triangleCountBeforeExport':m.triangles,'materials':sorted(m.materials),
        'partTriangles':m.parts,'heightEstimatesM':{obj['label']:obj['height'] for obj,r in ctx['buildings']},
        'sourceFootprintIds':spec['baseBuildingIdsToExclude'],'photoTextures':0,'newLights':0,
        'geographyCityId':'hangzhou','projectionOriginWGS84':ctx['geo']['originWGS84'],
        'pendingSubscopes':spec['pendingSubscopes']}


def ground_footprints(lm,spec,scale=.6):
    """Source bodies with atria/notch retained, plus sparse roof support columns.

    Candidate data-layer collision only. All bridges/Media Roof are elevated;
    entire campus or roof bbox MUST NOT become ground collision. Interior/entry
    access and ground/terrain datum require main integration and real driving.
    """
    ctx=_context(lm,spec); solids=[r for _,rs in ctx['buildings'] for r in _bands(rs)]
    # Collect support geometry separately without initializing a scene.
    class Sink:
        def face(self,*args):pass
    m=_Mesh(Sink(),1,(0,0),0)
    for x,y in _media_roof(m,ctx,spec):solids.append([(x-.5,y-.5),(x+.5,y-.5),(x+.5,y+.5),(x-.5,y+.5)])
    dx,dy=ctx['offset']
    return [[[lm['x']+(x+dx)*scale,lm['z']+(y+dy)*scale] for x,y in r] for r in solids]

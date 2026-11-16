"""Finite source-bound Alibaba B / NBBJ PhaseIV exterior candidate.

Two connected beehive clusters are composed of19 source arms/junctions/visitor
plus2 mapped low green roofs. Central roofs0741/0742 remain outside scope with
explicit blockers. All heights and ground recesses are estimates, not surveyed.
No bpy/city_mesh/scene/export side effects, photo textures or new lights.
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
        raise ValueError('B campus needs a nonzero source outline')
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
            raise ValueError('Unpaired B campus polygon crossing')
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
            raise ValueError('Nonfinite B campus vertex')
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


def _simple(r,tolerance=1e-7):
    """Reject all nonadjacent edge crossings/touches, including collinear ones."""
    def turn(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on(a,b,p):
        return abs(turn(a,b,p))<=tolerance and min(a[0],b[0])-tolerance<=p[0]<=max(a[0],b[0])+tolerance and min(a[1],b[1])-tolerance<=p[1]<=max(a[1],b[1])+tolerance
    if len(r)<3 or abs(_area(r))<tolerance:return False
    for i,(a,b) in enumerate(zip(r,r[1:]+r[:1])):
        if math.dist(a,b)<.02:return False
        for j in range(i+1,len(r)):
            if j==i+1 or (i==0 and j==len(r)-1):continue
            c,d=r[j],r[(j+1)%len(r)]
            p,q,u,v=turn(a,b,c),turn(a,b,d),turn(c,d,a),turn(c,d,b)
            if (p*q<0 and u*v<0) or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b):return False
    return True


def _miter(r,distance):
    result=[]
    for i,p in enumerate(r):
        a,q=r[i-1],r[(i+1)%len(r)]
        d1,d2=math.dist(a,p),math.dist(p,q)
        n1=(-(p[1]-a[1])/d1,(p[0]-a[0])/d1)
        n2=(-(q[1]-p[1])/d2,(q[0]-p[0])/d2)
        den=1+n1[0]*n2[0]+n1[1]*n2[1]
        if den<.01:return None
        point=(p[0]+(n1[0]+n2[0])*distance/den,p[1]+(n1[1]+n2[1])*distance/den)
        if not _inside(point,r):return None
        result.append(point)
    return result


def _inset_with_distance(r,distance):
    """Bound the estimated miter target by this source polygon's topology.

    Being inside at every vertex does NOT prevent a narrow concave arm's offset
    edges from crossing. Preserve all source vertices and reduce the estimated
    recess only when its full boundary becomes invalid; never repair a bow tie
    or remove a collision cell. A 4cm margin avoids collapsed offset edges.
    """
    if distance<=0 or not _simple(r):raise ValueError('Positive inset and simple source polygon required')
    def feasible(d):
        candidate=_miter(r,d)
        return candidate if candidate and _area(candidate)>0 and _simple(candidate) else None
    candidate=feasible(distance)
    if candidate:return _ring(candidate),distance
    low=min(.01,distance/100);high=distance
    if not feasible(low):raise ValueError('Source outline cannot support even a minimal recess')
    for _ in range(36):
        middle=(low+high)/2
        if feasible(middle):low=middle
        else:high=middle
    effective=max(.005,low-.04)
    candidate=feasible(effective)
    if not candidate:raise ValueError('Topology-bounded recess failed')
    return _ring(candidate),effective


def _inset(r,distance):
    return _inset_with_distance(r,distance)[0]


def _context(lm,spec):
    if spec.get('id')!='alibaba-b' or spec.get('cityId')!='hangzhou':raise ValueError('B requires its own Hangzhou specification')
    geo=load_city('hangzhou')['geography'];east,north=geo['eastMetresPerDegree'],geo['northMetresPerDegree']
    anchor=spec['anchor'];lon,lat=anchor['lon'],anchor['lat']
    def point(p):return (p[0]-lon)*east,(p[1]-lat)*north
    objects=[(o,[_ring([point(p) for p in r],i==0) for i,r in enumerate(o['ringsWGS84'])]) for o in spec['objects']]
    centers={k:point(p) for k,p in spec['groupCenters'].items()}
    vertices=[p for _,rs in objects for r in rs for p in r]
    return {'geo':geo,'offset':((lon-lm.get('lon',lon))*east,(lat-lm.get('lat',lat))*north),
            'objects':objects,'centers':centers,'vertices':vertices}


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


def _facade(m,obj,rings,ctx,spec):
    top=obj['height']['value'];base=obj['bodyBottomM'];courses=obj['courses']
    pitch=(top-base-1.2)/courses;f=spec['facade']
    center=ctx['centers'].get(obj['group'],_center(rings[0]))
    for p,q in _split_edges(rings[0],ctx):
        length=math.dist(p,q);tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=ty,-tx
        mid=_mix(p,q,.5);outer=(mid[0]-center[0])*nx+(mid[1]-center[1])*ny>0
        vertical=outer and obj['kind']!='visitor'
        def pt(u,z,out=0):return p[0]+tx*u+nx*out,p[1]+ty*u+ny*out,z
        intervals=_visible_intervals(obj,p,q,ctx)
        for low,high in intervals:
            if high-low<.02:continue
            m.face('landmarkglass',[pt(0,low),pt(length,low),pt(length,high),pt(0,high)])
            for k in range(1,courses+1):
                z=base+pitch*k
                if low<z<high:
                    m.face('silver',[pt(0,z-.08,.06),pt(length,z-.08,.06),pt(length,z+.08,.06),pt(0,z+.08,.06)])
            if vertical:
                count=max(1,round(length/f['finPitchM']));w=f['ribWidthM'];d=f['finProjectionM']
                for k in range(count+1):
                    u=k*length/count
                    m.face('gold',[pt(u-w/2,low,d),pt(u+w/2,low,d),pt(u+w/2,high,d),pt(u-w/2,high,d)])
                    m.face('gold',[pt(u-w/2,low,.04),pt(u-w/2,low,d),pt(u-w/2,high,d),pt(u-w/2,high,.04)])
            else:
                # Current courtyard views show many thin horizontal rails,
                # separate from the floor slabs; no animated shade claim.
                rows=max(1,round((high-low)/1.2))
                for k in range(1,rows):
                    z=low+(high-low)*k/rows
                    m.face('silver',[pt(0,z-.055,.22),pt(length,z-.055,.22),pt(length,z+.055,.22),pt(0,z+.055,.22)])
                count=max(1,round(length/f['innerBayM']))
                for k in range(count+1):
                    u=k*length/count
                    m.face('silver',[pt(u-.065,low,.04),pt(u+.065,low,.04),pt(u+.065,high,.04),pt(u-.065,high,.04)])
        # Candidate white edge/parapet remains thin, rather than a solid box.
        for low,high in _visible_intervals(dict(obj,bodyBottomM=top-.7,height={'value':top+.7}),p,q,ctx):
            if high-low>.02:m.face('silver',[pt(0,low,.01),pt(length,low,.01),pt(length,min(top,high),.01),pt(0,min(top,high),.01)])


def _supports(obj,r,spec):
    if obj['bodyBottomM']<=0:return []
    pitch=spec['facade']['columnPitchM'];side=spec['facade']['columnSideM'];result=[]
    for p,q in zip(r,r[1:]+r[:1]):
        length=math.dist(p,q);tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=-ty,tx
        count=max(1,int(length/pitch))
        for k in range(count):
            u=length*(k+.5)/count;x,y=p[0]+tx*u+nx*.8,p[1]+ty*u+ny*.8
            if all(_inside((x+sx*side/2,y+sy*side/2),r) for sx,sy in ((1,1),(1,-1),(-1,1),(-1,-1))):result.append((x,y))
    return result


def _lower_body(m,obj,r,spec):
    bottom=obj['bodyBottomM']
    if bottom<=0:return None
    if obj['kind']=='office-arm':
        inner=_inset(r,spec['facade']['groundInsetM'])
        for p,q in zip(inner,inner[1:]+inner[:1]):m.face('landmarkglass',[(*p,0),(*q,0),(*q,bottom-.25),(*p,bottom-.25)])
    else:inner=None
    for x,y in _supports(obj,r,spec):m.box('concrete',(x,y,bottom/2),(spec['facade']['columnSideM'],spec['facade']['columnSideM'],bottom))
    # Upper occupied body has a closed underside, but no ground-level slab
    # is invented underneath a junction/connector underpass.
    for band in _bands([r]):m.face('concrete',[(*p,bottom) for p in reversed(band)])
    return inner


def _roof(m,obj,rings,spec):
    h=obj['height']['value']
    for band in _bands(rings):m.face('roof',[(*p,h-.05) for p in band])
    # Recessed green terrace strip on the lower connecting arms. This is
    # authored roof cover; exact planter inventory remains pending.
    if obj['kind']=='junction':
        inner=_inset(rings[0],2)
        for band in _bands([inner]):m.face('leaf',[(*p,h+.015) for p in band])
        return
    # A few authored roof service modules, not a photo-baked rooftop.
    # Place only where the rectangle fits within the source occupied polygon.
    r=rings[0];count=0
    for p,q in zip(r,r[1:]+r[:1]):
        length=math.dist(p,q)
        if length<25:continue
        tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=-ty,tx
        for t in (.28,.66):
            cx,cy=p[0]+tx*length*t+nx*5,p[1]+ty*length*t+ny*5
            corners=[(cx+tx*u+nx*v,cy+ty*u+ny*v) for u,v in ((-3,-1.5),(3,-1.5),(3,1.5),(-3,1.5))]
            if all(_inside(pt,r) for pt in corners):
                m.slab([_ring(corners)],h,h+1.2,'silver');count+=1
                if count>=6:return


def _garden_cells(obj,r,spec):
    roof=spec['gardenRoof'];radius=roof['cellRadiusM'];a=math.radians(17.4);c,s=math.cos(a),math.sin(a)
    pr=[(x*c+y*s,-x*s+y*c) for x,y in r];xmin,xmax=min(p[0] for p in pr),max(p[0] for p in pr);ymin,ymax=min(p[1] for p in pr),max(p[1] for p in pr)
    dx,dy=radius*1.5,radius*math.sqrt(3)
    def p(u,v):return u*c-v*s,u*s+v*c
    cells=[]
    for i in range(math.floor(xmin/dx)-1,math.ceil(xmax/dx)+1):
        for j in range(math.floor(ymin/dy)-1,math.ceil(ymax/dy)+1):
            u,v=i*dx,(j+.5*(i%2))*dy
            hexagon=[p(u+radius*.93*math.cos(k*math.tau/6),v+radius*.93*math.sin(k*math.tau/6)) for k in range(6)]
            if not all(_inside(pt,r) for pt in hexagon):continue
            # Triangle located inside a hex cell near a corner; exact real
            # skylight registration/count remains an explicit estimate.
            side=roof['triangleSideM'];rr=side/math.sqrt(3)
            triangle=[p(u+radius*.25+rr*math.cos(math.pi/2+k*math.tau/3),v+rr*math.sin(math.pi/2+k*math.tau/3)) for k in range(3)]
            cells.append((_ring(hexagon),_ring(triangle,False)))
    return cells


def _garden(m,obj,rings,spec):
    h=obj['height']['value'];r=rings[0];roof=spec['gardenRoof']
    m.slab(rings,h-roof['roofThicknessM'],h,'concrete')
    # Completed photos show low glazed occupied space beneath roof gardens;
    # door registration is not inferred. These source-shaped rooms are not
    # new interactive interiors, and arrival targets must remain outside.
    for p,q in zip(r,r[1:]+r[:1]):m.face('landmarkglass',[(*p,0),(*q,0),(*q,h-roof['roofThicknessM']),(*p,h-roof['roofThicknessM'])])
    cells=_garden_cells(obj,r,spec)
    for index,(green,triangle) in enumerate(cells):
        rise=roof['cellRiseM']*(1+(index%3)*.22)
        m.slab([green,triangle],h+.03,h+rise,'leaf')
        m.face('landmarkglass',[(*p,h+rise+.015) for p in reversed(triangle)])
        for p,q in zip(triangle,triangle[1:]+triangle[:1]):
            m.face('silver',[(*p,h+rise+.02),(*q,h+rise+.02),(*q,h+rise+.09),(*p,h+rise+.09)])
    return len(cells)


def _visitor_accent(m,obj,r,spec):
    # Identify a south-facing source edge, not an arbitrary rotated portal.
    options=[]
    for p,q in zip(r,r[1:]+r[:1]):
        length=math.dist(p,q)
        if -(q[0]-p[0])/length<-.4:options.append((length,p,q))
    _,p,q=max(options);length=math.dist(p,q);a,b=_mix(p,q,.5-spec['visitorEntry']['widthM']/length/2),_mix(p,q,.5+spec['visitorEntry']['widthM']/length/2)
    tx,ty=(q[0]-p[0])/length,(q[1]-p[1])/length;nx,ny=ty,-tx;h=spec['visitorEntry']['heightM']
    m.face('darkglass',[(a[0]+nx*.02,a[1]+ny*.02,0),(b[0]+nx*.02,b[1]+ny*.02,0),(b[0]+nx*.02,b[1]+ny*.02,h),(a[0]+nx*.02,a[1]+ny*.02,h)])
    m.face('silver',[(*a,h),(*b,h),(b[0]+nx*2,b[1]+ny*2,h),(a[0]+nx*2,a[1]+ny*2,h)])


def build(b,lm,spec,scale=.6):
    if not math.isfinite(scale) or scale<=0:raise ValueError('Scale must be positive')
    ctx=_context(lm,spec);previous=b.frame;b.frame=(lm['x'],lm['z'],0)
    m=_Mesh(b,scale,ctx['offset'],lm.get('y',0));garden_count=0
    try:
        for obj,rings in ctx['objects']:
            m.part=obj['label']
            if obj['kind']=='garden-roof':garden_count+=_garden(m,obj,rings,spec);continue
            _lower_body(m,obj,rings[0],spec)
            _facade(m,obj,rings,ctx,spec)
            _roof(m,obj,rings,spec)
            if obj['kind']=='visitor':_visitor_accent(m,obj,rings[0],spec)
    finally:b.frame=previous
    if m.triangles>spec['budget']['maxTriangles']:raise ValueError('B candidate exceeds budget: '+str(m.triangles))
    return {'id':'alibaba-b','scope':spec['scope'],'mainOfficeClusterCount':2,'visitorCount':1,
        'sourceBuildingAndJunctionParts':19,'modeledSourceObjectCount':21,'gardenRoofCount':2,'gardenCellCount':garden_count,
        'physicalIndependentBuildingCount':'unknown; not23','triangleCountBeforeExport':m.triangles,
        'generatedFaces':m.faces,'materials':sorted(m.materials),'partTriangles':m.parts,
        'sourceFootprintIds':spec['baseBuildingIdsToExclude'],'newLights':0,'photoTextures':0,
        'geographyCityId':'hangzhou','projectionOriginWGS84':ctx['geo']['originWGS84'],
        'pendingSubscopes':spec['pendingSubscopes'],'excludedSubscopeBlockers':spec['excludedSubscopeBlockers'],
        'estimatedGroundRecesses':[{'sourceId':obj['sourceId'],'requestedInsetM':spec['facade']['groundInsetM'],
            'effectiveInsetM':_inset_with_distance(rs[0],spec['facade']['groundInsetM'])[1],
            'basis':'estimated target bounded by source concave topology; not surveyed ground footprint'}
            for obj,rs in ctx['objects'] if obj['kind']=='office-arm']}


def ground_footprints(lm,spec,scale=.6):
    """Estimated recessed ground bodies/supports, source visitor/low rooms only.

    Whole B parcel and elevated junction footprints do not become colliders.
    Exact doors, piloti traversals and navigation require actual integration.
    """
    ctx=_context(lm,spec);solids=[];side=spec['facade']['columnSideM']/2
    for obj,rs in ctx['objects']:
        r=rs[0]
        # Keep one simple concave footprint rather than splitting it into tiny
        # artificial scanline collision cells. Real inner rings still use the
        # hole-preserving partition. No collision area is dropped to pass tests.
        if obj['kind'] in ('visitor','garden-roof'):solids.extend([r] if len(rs)==1 else _bands(rs))
        if obj['kind']=='office-arm':solids.append(_inset(r,spec['facade']['groundInsetM']))
        for x,y in _supports(obj,r,spec):solids.append([(x-side,y-side),(x+side,y-side),(x+side,y+side),(x-side,y+side)])
    dx,dy=ctx['offset']
    return [[[lm['x']+(x+dx)*scale,lm['z']+(y+dy)*scale] for x,y in r] for r in solids]

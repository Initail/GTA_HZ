"""Source-bound Cainiao candidate with the same outer and inner east portal.

Revision of cainiao_headquarters.py; original candidate source remains frozen.

The outer plan is Geofabrik way/1355173307. Five storeys, four courtyards,
diagonal connections and bird-mouth canopy are architect-reported. Heights,
interior widths, canopy profile and facade sampling are bounded estimates in
docs/hangzhou/research/ali/cainiao-round2/spec.json. No photos are textures.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city
except ImportError:
    from scripts.city_config import load_city


def _v(spec, name):
    return spec['estimates'][name]['value']


def _area(ring):
    return sum(x*v-u*y for (x, y), (u, v) in zip(ring, ring[1:]+ring[:1]))/2


def _ccw(ring):
    ring = [tuple(p) for p in ring]
    if ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3 or abs(_area(ring)) < 1e-5:
        raise ValueError('Cainiao outer footprint needs a nonzero closed outline')
    return ring if _area(ring) > 0 else list(reversed(ring))


def _mix(p, q, t):
    return tuple(a+(b-a)*t for a, b in zip(p, q))


def _rect(x, y, width, depth):
    return [(x-width/2,y-depth/2), (x+width/2,y-depth/2),
            (x+width/2,y+depth/2), (x-width/2,y+depth/2)]


def _arm(a, b, width):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    if length <= width:
        raise ValueError('Cainiao diagonal connection has invalid length')
    nx, ny = -dy/length*width/2, dx/length*width/2
    return _ccw([(a[0]+nx,a[1]+ny), (a[0]-nx,a[1]-ny),
                 (b[0]-nx,b[1]-ny), (b[0]+nx,b[1]+ny)])


def _context(lm, spec):
    if spec.get('id') != 'cainiao-headquarters' or spec.get('cityId') != 'hangzhou':
        raise ValueError('Cainiao builder requires its Hangzhou specification')
    geo = load_city('hangzhou')['geography']
    east, north = geo['eastMetresPerDegree'], geo['northMetresPerDegree']
    anchor = spec['anchor']
    outer = _ccw([((lon-anchor['lon'])*east, (lat-anchor['lat'])*north)
                  for lon, lat in spec['footprintWGS84']])
    half_x = (max(x for x,y in outer)-min(x for x,y in outer))/2
    half_y = (max(y for x,y in outer)-min(y for x,y in outer))/2
    width = _v(spec, 'ringWidthM')
    if not 0 < width < min(half_x, half_y)/3:
        raise ValueError('Cainiao ring width is outside its frozen envelope')
    # Source has no inner rings. This corresponding inset is explicitly an
    # estimate, preserving a real opening instead of capping the entire campus.
    inner = [(x*(1-width/half_x), y*(1-width/half_y)) for x,y in outer]
    hw, hd = _v(spec,'centralWidthM')/2, _v(spec,'centralDepthM')/2
    arms = []
    for sx,sy in ((1,1),(-1,1),(-1,-1),(1,-1)):
        tip = max(inner,key=lambda p:sx*p[0]+sy*p[1])
        # Connect just into the peripheral band, rather than extending a
        # rectangular diagonal tip past a rounded mapped exterior corner.
        arms.append(_arm((sx*hw*.8,sy*hd*.8),(tip[0]*1.035,tip[1]*1.035),
                         _v(spec,'diagonalWidthM')))
    offset = ((anchor['lon']-lm.get('lon',anchor['lon']))*east,
              (anchor['lat']-lm.get('lat',anchor['lat']))*north)
    return {'outer':outer,'inner':inner,'half_x':half_x,'half_y':half_y,
            'arms':arms,'center':_rect(0,0,2*hw,2*hd),'offset':offset,'geo':geo}


class _Mesh:
    def __init__(self, builder, scale, offset, base_y):
        self.b, self.scale, self.offset, self.base_y = builder, scale, offset, base_y
        self.faces = self.triangles = 0
        self.materials = set()
        self.part = 'unassigned'
        self.parts = {}

    def point(self, p):
        x, y, z = p
        if not all(math.isfinite(v) for v in p):
            raise ValueError('Cainiao generated a non-finite vertex')
        return ((x+self.offset[0])*self.scale, (y+self.offset[1])*self.scale,
                z*self.scale+self.base_y)

    def face(self, material, points):
        self.b.face(material, [self.point(p) for p in points])
        self.faces += 1
        self.triangles += len(points)-2
        self.materials.add(material)
        self.parts[self.part] = self.parts.get(self.part,0)+len(points)-2

    def box(self, material, p, size):
        x,y,z = p
        a,c,h = [s/2 for s in size]
        q = [(x-a,y-c,z-h),(x+a,y-c,z-h),(x+a,y+c,z-h),(x-a,y+c,z-h),
             (x-a,y-c,z+h),(x+a,y-c,z+h),(x+a,y+c,z+h),(x-a,y+c,z+h)]
        for ids in ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.face(material,[q[i] for i in ids])

    def prism(self, material, ring, bottom, top, roof='roof', walls=True):
        # Only convex arm/atrium rectangles use this fan. The concave mapped
        # campus outline is never passed here and is never filled by a fan.
        if walls:
            for p,q in zip(ring,ring[1:]+ring[:1]):
                self.face(material,[(*p,bottom),(*q,bottom),(*q,top),(*p,top)])
        c = tuple(sum(p[i] for p in ring)/len(ring) for i in (0,1))
        for p,q in zip(ring,ring[1:]+ring[:1]):
            self.face(roof,[(*c,top),(*p,top),(*q,top)])
            self.face(material,[(*c,bottom),(*q,bottom),(*p,bottom)])


def _segments(outer, inner, pitch=3.5):
    for i,p in enumerate(outer):
        j = (i+1)%len(outer)
        q = outer[j]
        count = max(1,math.ceil(math.dist(p,q)/pitch))
        for k in range(count):
            a,c = k/count,(k+1)/count
            yield _mix(p,q,a),_mix(p,q,c),_mix(inner[i],inner[j],a),_mix(inner[i],inner[j],c)


def _portal(p, q, ctx, spec):
    x,y = _mix(p,q,.5)
    return x > ctx['half_x']-2 and abs(y) < _v(spec,'groundPortalWidthM')/2


def _strip(m, material, point, a, b, width):
    dx,dz = b[0]-a[0],b[1]-a[1]
    length = math.hypot(dx,dz)
    nx,nz = -dz/length*width/2,dx/length*width/2
    m.face(material,[point(a[0]-nx,a[1]-nz,.12),point(b[0]-nx,b[1]-nz,.12),
                     point(b[0]+nx,b[1]+nz,.12),point(a[0]+nx,a[1]+nz,.12)])


def _facade(m, ring, spec, interior=False, context=None, portal_flags=None):
    height = _v(spec,'bodyHeightM')-.8
    floors = spec['floorElevationsM']
    for edge,(p,q) in enumerate(zip(ring,ring[1:]+ring[:1])):
        length = math.dist(p,q)
        if length < .05:
            continue
        tx,ty = (q[0]-p[0])/length,(q[1]-p[1])/length
        nx,ny = ty,-tx
        is_portal = portal_flags[edge] if portal_flags is not None else bool(context and _portal(p,q,context,spec))
        bottom = _v(spec,'groundPortalHeightM') if is_portal else 0

        def point(u,z,out=0):
            return p[0]+tx*u+nx*out,p[1]+ty*u+ny*out,z

        m.face('landmarkglass',[point(0,bottom),point(length,bottom),point(length,height),point(0,height)])
        for floor in floors[1:]:
            if floor > bottom:
                m.face('silver',[point(0,floor-.055,.035),point(length,floor-.055,.035),
                                  point(length,floor+.055,.035),point(0,floor+.055,.035)])
        bays = max(1,round(length/_v(spec,'facadeBayM')))
        for bay in range(bays+1):
            u = bay*length/bays
            rib = _v(spec,'facadeRibM')*(1.4 if interior else 1)
            m.face('silver',[point(u-rib/2,bottom,.07),point(u+rib/2,bottom,.07),
                              point(u+rib/2,height,.07),point(u-rib/2,height,.07)])
        if interior or length < 2:
            continue
        # Observed angular glass frit becomes authored sparse open chevrons.
        # Shared silver geometry; no photo texture, font, light or exact logo claim.
        for floor,(lo,hi) in enumerate(zip(floors[1:-1],floors[2:])):
            if hi <= bottom:
                continue
            count = max(1,int(length/_v(spec,'nestMotifPitchM')))
            for col in range(count):
                if (col+floor+edge)%4 == 0:
                    continue
                u = (col+.5)*length/count
                z = (lo+hi)/2+(.6 if col%2 else -.45)
                for a,b in (((u-.34,z+.34),(u,z-.30)),((u,z-.30),(u+.34,z+.34))):
                    _strip(m,'silver',point,a,b,.045)


def inner_portal_ring(ctx, spec):
    """Split only at original corners and matched outer portal transitions.

    Preserve the original facade sampling elsewhere. The inner ring runs in
    reverse, so its outgoing edge inherits the previous forward edge's flag.
    """
    vertices, flags = [], []
    for i,p in enumerate(ctx['outer']):
        j=(i+1)%len(ctx['outer']);q=ctx['outer'][j]
        count=max(1,math.ceil(math.dist(p,q)/3.5));previous=None
        for k in range(count):
            flag=_portal(_mix(p,q,k/count),_mix(p,q,(k+1)/count),ctx,spec)
            if k==0 or flag!=previous:
                vertices.append(_mix(ctx['inner'][i],ctx['inner'][j],k/count));flags.append(flag)
            previous=flag
    n=len(vertices)
    return list(reversed(vertices)),[flags[(n-2-k)%n] for k in range(n)]


def _ring(m, ctx, spec):
    h = _v(spec,'bodyHeightM')
    m.part = 'peripheral-ring'
    for p,q,a,c in _segments(ctx['outer'],ctx['inner']):
        m.face('roof',[(*p,h-.8),(*q,h-.8),(*c,h-.8),(*a,h-.8)])
        if not _portal(p,q,ctx,spec):
            m.face('concrete',[(*a,.05),(*c,.05),(*q,.05),(*p,.05)])
        m.face('silver',[(*p,h-.8),(*q,h-.8),(*q,h),(*p,h)])
        m.face('silver',[(*c,h-.8),(*a,h-.8),(*a,h),(*c,h)])
    # Sampled source exterior prevents one long eastern segment from making
    # an oversized portal. All source corners remain in the physical outline.
    outer = [p for p,q,a,c in _segments(ctx['outer'],ctx['inner'])]
    _facade(m,outer,spec,context=ctx)
    inner, flags = inner_portal_ring(ctx,spec)
    _facade(m,inner,spec,interior=True,portal_flags=flags)


def _connections(m, ctx, spec):
    h = _v(spec,'bodyHeightM')-.8
    for i,arm in enumerate(ctx['arms']):
        m.part = f'diagonal-connection-{i+1}'
        m.prism('landmarkglass',arm,0,h,walls=False)
        _facade(m,arm,spec,interior=True)
    m.part = 'central-atrium'
    m.prism('landmarkglass',ctx['center'],0,h,'concrete')
    w,d = _v(spec,'centralWidthM'),_v(spec,'centralDepthM')
    # Recessed authored roof-light/frame; dimensions remain estimates.
    glass = _rect(0,0,w*.74,d*.74)
    m.face('darkglass',[(*p,h+.025) for p in glass])
    for i in range(1,9):
        x = -w*.37+i*w*.74/9
        m.box('silver',(x,0,h+.06),(.10,d*.74,.08))
    for i in range(1,7):
        y = -d*.37+i*d*.74/7
        m.box('silver',(0,y,h+.06),(w*.74,.10,.08))
    # A small number of observed cantilever-like bays instead of invented interiors.
    m.part = 'courtyard-meeting-bays'
    for sx,sy in ((1,1),(-1,1),(-1,-1),(1,-1)):
        x,y = sx*w*.58,sy*d*.66
        m.box('landmarkglass',(x,y,h*.62),(9,7,4))
        m.box('concrete',(x,y,h*.62-2.1),(9.2,7.2,.20))


def _canopy(m, ctx, spec):
    m.part = 'layered-east-canopy'
    span,projection = _v(spec,'canopySpanM'),_v(spec,'canopyProjectionM')
    peak,edge = _v(spec,'canopyPeakM'),_v(spec,'canopyEdgeM')
    layers = spec['facade']['canopyLayers']
    segments = spec['facade']['canopySegments']
    for layer in range(layers):
        def pt(t,front,z_delta=0):
            y = (t-.5)*span
            arch = max(0,1-(2*t-1)**2)
            z = edge-layer*.35+(peak-layer*1.6-edge+layer*.35)*arch
            x = ctx['half_x']+(projection*(.34+.66*arch) if front else -.20)
            return x,y,z+z_delta
        for i in range(segments):
            a,b = i/segments,(i+1)/segments
            fl,fr = pt(a,True,-.43),pt(b,True,-.43)
            fu,ru = pt(a,True,.43),pt(b,True,.43)
            bl,br = pt(a,False,-.43),pt(b,False,-.43)
            bu,ur = pt(a,False,.43),pt(b,False,.43)
            m.face('gold',[fl,fr,ru,fu])
            m.face('gold',[fu,ru,ur,bu])
            m.face('gold',[br,fr,fl,bl])
            m.face('gold',[bu,ur,br,bl])
            if i == 0:
                m.face('gold',[fl,fu,bu,bl])
            if i == segments-1:
                m.face('gold',[ur,ru,fr,br])
    # Reference front/oblique photos show glazing folding down to the upper
    # beak ribbon. A coarse continuous sail carries the sill curve into the
    # upper curtain wall; its projection is part of the canopy estimate.
    m.part = 'folded-east-approach-glass'
    def sail(t,g):
        arch = max(0,1-(2*t-1)**2)
        low = edge+(peak-edge)*arch+.44
        z = low+(_v(spec,'bodyHeightM')-.8-low)*g
        x = ctx['half_x']+.045+projection*(.34+.66*arch)*(1-g)**2
        return x,(t-.5)*span,z
    for i in range(segments):
        a,b = i/segments,(i+1)/segments
        for j in range(4):
            lo,hi = j/4,(j+1)/4
            m.face('landmarkglass',[sail(a,lo),sail(b,lo),sail(b,hi),sail(a,hi)])
        for j in range(4):
            lo,hi = j/4,(j+1)/4
            m.face('silver',[sail(a-.00045,lo),sail(a+.00045,lo),
                              sail(a+.00045,hi),sail(a-.00045,hi)])


def build(b, lm, spec, scale=.6):
    """Append estimated exterior; anchor/base height already use game units."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('scale must be positive and finite')
    ctx = _context(lm,spec)
    previous = b.frame
    b.frame = (lm['x'],lm['z'],0)
    m = _Mesh(b,scale,ctx['offset'],lm.get('y',0))
    try:
        _ring(m,ctx,spec)
        _connections(m,ctx,spec)
        _canopy(m,ctx,spec)
    finally:
        b.frame = previous
    if m.triangles > spec['budget']['maxTriangles']:
        raise ValueError(f'Cainiao candidate exceeds triangle budget: {m.triangles}')
    return {'id':'cainiao-headquarters','scope':spec['status'],
            'courtyardCount':4,'diagonalConnectionCount':4,'canopyLayerCount':spec['facade']['canopyLayers'],
            'heightEstimateM':_v(spec,'bodyHeightM'),'heightEstimateErrorM':spec['estimates']['bodyHeightM']['errorPlusMinus'],
            'generatedFaces':m.faces,'triangleCountBeforeExport':m.triangles,
            'materials':sorted(m.materials),'partTriangles':m.parts,'newLights':0,'photoTextures':0,
            'geographyCityId':'hangzhou','projectionOriginWGS84':ctx['geo']['originWGS84'],
            'sourceFootprintId':spec['sourceFootprintId'],
            'source_spec':'docs/hangzhou/research/ali/cainiao-round2/spec.json',
            'pendingSubscopes':spec['pendingSubscopes']}


def ground_footprints(lm, spec, scale=.6):
    """Candidate solid strips/arms only; four courtyards and east portal stay open.

    This is data-layer collision geometry, not a verified navigable entrance.
    Do not use it to claim an exact interior or select a spawn/arrival target.
    """
    ctx = _context(lm,spec)
    rings = [[p,q,c,a] for p,q,a,c in _segments(ctx['outer'],ctx['inner'])
             if not _portal(p,q,ctx,spec)]
    rings += ctx['arms']+[ctx['center']]
    dx,dy = ctx['offset']
    return [[[lm['x']+(x+dx)*scale,lm['z']+(y+dy)*scale] for x,y in ring]
            for ring in rings]

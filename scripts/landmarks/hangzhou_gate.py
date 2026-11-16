"""Source-bound Hangzhou Gate exterior candidate; no scene/export side effects.

The two mapped tower footprints are real OSM data. Upper profiles, crown drop,
facade widths and saddle cross-camber are reference-informed estimates recorded
in docs/hangzhou/research/core/gate-round2/spec.json. This module is not a final
visual/collision acceptance. Official photos are not used as textures.
"""
from __future__ import annotations
import math

try:
    from city_config import load_city
except ImportError:
    from scripts.city_config import load_city


def _estimate(spec, key):
    return spec['estimates'][key]['value']


def _area(ring):
    return sum(x*v-u*y for (x, y), (u, v) in zip(ring, ring[1:]+ring[:1]))/2


def _open_ccw(ring):
    ring = [tuple(p) for p in ring]
    if ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3 or abs(_area(ring)) < 1e-6:
        raise ValueError('Gate footprint must be a valid nonzero polygon')
    return ring if _area(ring) > 0 else list(reversed(ring))


def _mix(a, b, t):
    return tuple(x+(y-x)*t for x, y in zip(a, b))


def _sections(spec, height):
    rows = _estimate(spec, 'bodySections')
    for lower, upper in zip(rows, rows[1:]):
        if height <= upper[0]:
            t = max(0, (height-lower[0])/(upper[0]-lower[0]))
            return _mix(lower[1:], upper[1:], t)
    return tuple(rows[-1][1:])


def _perimeter_samples(ring, count):
    segments = list(zip(ring, ring[1:]+ring[:1]))
    lengths = [math.dist(a, b) for a, b in segments]
    total = sum(lengths)
    points = []
    for i in range(count):
        target = total*i/count
        for (a, b), length in zip(segments, lengths):
            if target <= length:
                points.append(_mix(a, b, target/max(length, 1e-9)))
                break
            target -= length
        else:
            points.append(ring[0])
    return points


class _Mesh:
    """Keep real-metre geometry separate from game-unit anchor/base height."""
    def __init__(self, builder, scale, u, v, offset, base_y):
        self.b, self.scale, self.u, self.v = builder, scale, u, v
        self.offset, self.base_y = offset, base_y
        self.faces = self.triangles = 0
        self.materials = set()

    def point(self, p):
        x, y, z = p
        return ((x*self.u[0]+y*self.v[0]+self.offset[0])*self.scale,
                (x*self.u[1]+y*self.v[1]+self.offset[1])*self.scale,
                z*self.scale+self.base_y)

    def face(self, material, points):
        self.b.face(material, [self.point(p) for p in points])
        self.faces += 1
        self.triangles += len(points)-2
        self.materials.add(material)

    def box(self, material, center, size):
        x, y, z = center
        a, c, h = [value/2 for value in size]
        points = [(x-a,y-c,z-h), (x+a,y-c,z-h), (x+a,y+c,z-h), (x-a,y+c,z-h),
                  (x-a,y-c,z+h), (x+a,y-c,z+h), (x+a,y+c,z+h), (x-a,y+c,z+h)]
        for indexes in ((0,3,2,1), (4,5,6,7), (0,1,5,4), (1,2,6,5), (2,3,7,6), (3,0,4,7)):
            self.face(material, [points[i] for i in indexes])


def _context(lm, spec):
    if spec.get('id') != 'hangzhou-gate' or spec.get('cityId') != 'hangzhou':
        raise ValueError('Hangzhou Gate builder needs its Hangzhou specification')
    geography = load_city('hangzhou')['geography']
    east, north = geography['eastMetresPerDegree'], geography['northMetresPerDegree']
    anchor = spec['anchor']

    def project(lon, lat):
        return ((lon-anchor['lon'])*east, (lat-anchor['lat'])*north)

    towers = []
    for item in spec['towers']:
        center = project(*item['centroidWGS84'])
        towers.append({'source': item, 'center_en': center,
                       'ring_en': _open_ccw([project(*p) for p in item['footprintWGS84']])})
    if len(towers) != 2:
        raise ValueError('Gate candidate must contain exactly two mapped towers')
    towers.sort(key=lambda t: t['source']['centroidWGS84'][0])
    dx = towers[1]['center_en'][0]-towers[0]['center_en'][0]
    dy = towers[1]['center_en'][1]-towers[0]['center_en'][1]
    separation = math.hypot(dx, dy)
    if separation < 1:
        raise ValueError('Gate tower centers overlap')
    u, v = (dx/separation, dy/separation), (-dy/separation, dx/separation)
    for side, tower in zip((-1, 1), towers):
        cx, cy = tower['center_en']
        tower['side'] = side
        tower['center'] = (cx*u[0]+cy*u[1], cx*v[0]+cy*v[1])
        tower['ring'] = [((x-cx)*u[0]+(y-cy)*u[1], (x-cx)*v[0]+(y-cy)*v[1])
                         for x, y in tower['ring_en']]
        outward = [side*p[0] for p in tower['ring']]
        tower['outward_bounds'] = min(outward), max(outward)
    offset = ((anchor['lon']-lm.get('lon', anchor['lon']))*east,
              (anchor['lat']-lm.get('lat', anchor['lat']))*north)
    return towers, u, v, offset, geography


def _tower_point(tower, p, height, spec, top=False, outset=0):
    fu, fv = _sections(spec, height)
    x, y = p
    radius = max(math.hypot(x, y), 1e-8)
    x, y = x*(fu+outset/radius), y*(fv+outset/radius)
    if top:
        lo, hi = tower['outward_bounds']
        t = (tower['side']*p[0]-lo)/(hi-lo)
        height = tower['source']['heightM']-_estimate(spec, 'crownDropM')*(1-t)
    return tower['center'][0]+x, tower['center'][1]+y, height


def _tower(m, tower, spec):
    ring = tower['ring']
    heights = [row[0] for row in _estimate(spec, 'bodySections')]
    rows = [[_tower_point(tower, p, z, spec) for p in ring] for z in heights]
    rows.append([_tower_point(tower, p, tower['source']['heightM'], spec, top=True) for p in ring])
    for lower, upper in zip(rows, rows[1:]):
        for i in range(len(ring)):
            j = (i+1) % len(ring)
            m.face('landmarkglass', [lower[i], lower[j], upper[j], upper[i]])
    # Source-derived base; sloped crown closing faces are a candidate approximation.
    m.face('concrete', list(reversed(rows[0])))
    center_top = tuple(sum(p[k] for p in rows[-1])/len(ring) for k in (0,1,2))
    for i in range(len(ring)):
        m.face('darkglass', [center_top, rows[-1][i], rows[-1][(i+1) % len(ring)]])
    band_width = _estimate(spec, 'facadeHorizontalBandM')
    division = spec['facade']['floorBandDivisions']
    occupied_top = tower['source']['heightM']-_estimate(spec, 'crownDropM')-4
    for floor in range(1, division+1):
        z = occupied_top*floor/(division+1)
        low = [_tower_point(tower, p, z-band_width/2, spec, outset=.035) for p in ring]
        high = [_tower_point(tower, p, z+band_width/2, spec, outset=.035) for p in ring]
        for i in range(len(ring)):
            j = (i+1) % len(ring)
            m.face('silver', [low[i], low[j], high[j], high[i]])
    # Ribbons share existing materials and one builder group; no per-window objects.
    samples = _perimeter_samples(ring, _estimate(spec, 'facadePerimeterDivisions'))
    rib_width = _estimate(spec, 'facadeVerticalRibM')
    for i, p in enumerate(samples):
        prior, nxt = samples[i-1], samples[(i+1) % len(samples)]
        tx, ty = nxt[0]-prior[0], nxt[1]-prior[1]
        length = max(math.hypot(tx, ty), 1e-8)
        a = (p[0]-tx/length*rib_width/2, p[1]-ty/length*rib_width/2)
        b = (p[0]+tx/length*rib_width/2, p[1]+ty/length*rib_width/2)
        for z0, z1 in zip(heights, heights[1:]):
            m.face('steel', [_tower_point(tower,a,z0,spec,outset=.055), _tower_point(tower,b,z0,spec,outset=.055),
                            _tower_point(tower,b,z1,spec,outset=.055), _tower_point(tower,a,z1,spec,outset=.055)])
        m.face('steel', [_tower_point(tower,a,heights[-1],spec,outset=.055),
                        _tower_point(tower,b,heights[-1],spec,outset=.055),
                        _tower_point(tower,b,310,spec,top=True,outset=.055),
                        _tower_point(tower,a,310,spec,top=True,outset=.055)])


def _bridge(m, spec):
    bridge = spec['bridge']
    half = bridge['spanM']/2
    depth = _estimate(spec, 'curtainDepthM')
    floor, garden = bridge['banquetFloorM'], bridge['roofGardenM']
    rise = _estimate(spec, 'archUndersideRiseM')
    # Arch fill below the banquet deck leaves a real central void; no ground box.
    for i in range(36):
        x0, x1 = -half+i*bridge['spanM']/36, -half+(i+1)*bridge['spanM']/36
        z0, z1 = rise*(1-(x0/half)**2), rise*(1-(x1/half)**2)
        m.face('concrete', [(x0,-depth/2,z0), (x0,depth/2,z0), (x1,depth/2,z1), (x1,-depth/2,z1)])
        m.face('landmarkglass', [(x0,-depth/2,z0), (x1,-depth/2,z1), (x1,-depth/2,floor), (x0,-depth/2,floor)])
        m.face('landmarkglass', [(x1,depth/2,z1), (x0,depth/2,z0), (x0,depth/2,floor), (x1,depth/2,floor)])
    m.box('steel', (0,0,floor-.4), (bridge['spanM'],depth,.8))
    m.box('landmarkglass', (0,0,(floor+garden)/2), (bridge['spanM'],depth-.3,garden-floor))
    m.box('concrete', (0,0,garden-.2), (bridge['spanM'],depth,.4))
    for side in (-1,1):
        y = side*depth/2
        for j in range(25):
            x = -half+j*bridge['spanM']/24
            m.face('silver', [(x-.06,y,floor),(x+.06,y,floor),(x+.06,y,garden),(x-.06,y,garden)])

    def saddle(x, y):
        qu, qv = x/half, y/(depth/2)
        z = bridge['curtainLowM']+(bridge['curtainHighM']-bridge['curtainLowM'])*qu**2
        z += _estimate(spec, 'curtainCrossCamberM')*(1-qu**2)*(1-qv**2)
        return x, y, z

    # Coarse open panels represent the reviewed staggered/perforated curtain.
    # Grid resolution and gaps are modelling representation, not a claimed
    # engineering panel schedule or proof of the real fire-safety opening ratio.
    nu, nv = 40, 16
    du, dv = bridge['spanM']/nu, depth/nv
    for i in range(nu):
        for j in range(nv):
            x, y = -half+(i+.5)*du, -depth/2+(j+.5)*dv
            a, b = du*.37, dv*.44
            material = 'silver' if (i+j) % 3 == 0 else 'landmarkglass'
            top = [saddle(x-a,y-b),saddle(x+a,y-b),saddle(x+a,y+b),saddle(x-a,y+b)]
            # Closed thin panels remain visible from below with normal material
            # culling, without changing shared runtime/PBR settings.
            thickness = _estimate(spec, 'curtainPanelThicknessM')
            bottom = [(px,py,pz-thickness) for px,py,pz in top]
            m.face(material, top)
            m.face(material, list(reversed(bottom)))
            for k in range(4):
                q = (k+1) % 4
                m.face(material, [bottom[k],bottom[q],top[q],top[k]])
    for side in (-1,1):
        for i in range(nu):
            x0, x1 = -half+i*du, -half+(i+1)*du
            y = side*depth/2
            p0, p1 = saddle(x0,y), saddle(x1,y)
            m.face('silver', [p0,p1,(p1[0],p1[1],p1[2]+.22),(p0[0],p0[1],p0[2]+.22)])


def build(b, lm, spec, scale=.6):
    """Append to B; preserve frame, city projection and glTF direction contract."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('scale must be positive and finite')
    towers, u, v, offset, geography = _context(lm, spec)
    # lm values are already scene units; physical geometry gets scale once.
    previous = b.frame
    b.frame = (lm['x'], lm['z'], 0)
    m = _Mesh(b, scale, u, v, offset, lm.get('y', 0))
    try:
        for tower in towers:
            _tower(m, tower, spec)
        _bridge(m, spec)
    finally:
        b.frame = previous
    if m.triangles > spec['budget']['maxTriangles']:
        raise ValueError(f'Gate candidate exceeds triangle budget: {m.triangles}')
    return {'id': 'hangzhou-gate', 'scope': 'exterior candidate; needs GLB and visual review',
            'tower_count': 2, 'bridge_count': 1, 'curtain_count': 1,
            'max_height': 310*scale, 'geographyCityId': 'hangzhou',
            'projectionOriginWGS84': geography['originWGS84'],
            'generatedFaces': m.faces, 'triangleCountBeforeExport': m.triangles,
            'materials': sorted(m.materials), 'newLights': 0,
            'source_spec': 'docs/hangzhou/research/core/gate-round2/spec.json'}


def ground_footprints(lm, spec, scale=.6):
    """Mapped tower ground polygons only; never close the gate's arch passage."""
    towers, _, _, offset, _ = _context(lm, spec)
    return [[[lm['x']+(x+offset[0])*scale, lm['z']+(y+offset[1])*scale]
             for x,y in tower['ring_en']] for tower in towers]

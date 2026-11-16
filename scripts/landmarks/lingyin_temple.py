"""Source-bound five-hall Lingyin exterior candidate. Pure B API, no bpy import.

Read docs/hangzhou/research/core/lingyin-round2/spec.json for provenance and
uncertainty. This does not reconstruct the whole monastery or mountain datum.
Dimensions are real metres; existing game-unit lm x/z/y are scaled only once.
Blender east/north/up and the existing GLB/Babylon direction remain unchanged.
"""
from __future__ import annotations
import math
try:
    from city_config import load_city
except ImportError:
    from scripts.city_config import load_city


class _Hall:
    def __init__(self, b, hall, scale, base_y):
        self.b, self.hall, self.s, self.base = b, hall, scale, base_y
        self.cx, self.cy = hall['offsetEastNorthM']
        a = hall['widthAxisRadiansEastCCW']
        self.ca, self.sa = math.cos(a), math.sin(a)
        self.faces = 0

    def pt(self, p):
        x, y, z = p
        return ((self.cx + x * self.ca - y * self.sa) * self.s,
                (self.cy + x * self.sa + y * self.ca) * self.s,
                self.base + (self.hall['baseElevationRelativeM'] + z) * self.s)

    def face(self, material, points):
        self.b.face(material, [self.pt(p) for p in points])
        self.faces += 1

    def box(self, material, p, size):
        x, y, z = p
        a, c, d = [v / 2 for v in size]
        q = [(x-a,y-c,z-d),(x+a,y-c,z-d),(x+a,y+c,z-d),(x-a,y+c,z-d),
             (x-a,y-c,z+d),(x+a,y-c,z+d),(x+a,y+c,z+d),(x-a,y+c,z+d)]
        for indices in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
            self.face(material, [q[i] for i in indices])

    def cylinder(self, material, x, y, low, high, radius, divisions=6):
        rings = [[(x + radius * math.cos(i * math.tau / divisions),
                   y + radius * math.sin(i * math.tau / divisions), z)
                  for i in range(divisions)] for z in [low, high]]
        for i in range(divisions):
            j = (i+1) % divisions
            self.face(material, [rings[0][i],rings[0][j],rings[1][j],rings[1][i]])
        self.face(material, list(reversed(rings[0])))
        self.face(material, rings[1])

    def panel(self, material, q, thickness, close_edges=True):
        # Every patch has an underside: no dependence on double-sided materials.
        # Offset in the face-normal direction also supports vertical fascia/gables.
        a = [q[1][i]-q[0][i] for i in range(3)]
        c = [q[2][i]-q[0][i] for i in range(3)]
        normal = [a[1]*c[2]-a[2]*c[1],a[2]*c[0]-a[0]*c[2],a[0]*c[1]-a[1]*c[0]]
        length = math.sqrt(sum(v*v for v in normal))
        if length <= 1e-12:
            raise ValueError('Degenerate panel')
        self.face(material, q)
        delta = [v*thickness/length for v in normal]
        bottom = [tuple(p[i]-delta[i] for i in range(3)) for p in q]
        self.face(material, list(reversed(bottom)))
        if close_edges:
            for i in range(len(q)):
                j = (i+1) % len(q)
                self.face(material, [q[j],q[i],bottom[i],bottom[j]])


def _roof(mesh, width, depth, eave, top, lift, thickness):
    """Hipped lower surfaces plus gabled upper cap, curved eave-to-ridge profile.

    Closed tessellated patches are intentional for the shared B material culling.
    This roof expresses nine-ridge/hipped-gabled silhouette, not surveyed joinery.
    """
    shoulder_z = eave + (top-eave) * .48
    g, shoulder_y = width * .32, depth * .20
    outer = [(-width/2,-depth/2),(width/2,-depth/2),
             (width/2,depth/2),(-width/2,depth/2)]
    inner = [(-g,-shoulder_y),(g,-shoulder_y),(g,shoulder_y),(-g,shoulder_y)]
    for side in range(4):
        j = (side+1) % 4

        def point(u, t):
            ox = outer[side][0] * (1-u) + outer[j][0] * u
            oy = outer[side][1] * (1-u) + outer[j][1] * u
            ix = inner[side][0] * (1-u) + inner[j][0] * u
            iy = inner[side][1] * (1-u) + inner[j][1] * u
            corner = abs(2*u-1) ** 8
            z = eave + (shoulder_z-eave) * t**.72 + lift * corner * (1-t)**4
            return (ox*(1-t)+ix*t, oy*(1-t)+iy*t, z)

        for a in range(4):
            u, v = a/4, (a+1)/4
            for r in range(3):
                t, s = r/3, (r+1)/3
                mesh.panel('roof', [point(u,t),point(v,t),point(v,s),point(u,s)], thickness,False)
        # Red fascia follows upturned eaves, without an emissive outline.
        for a in range(4):
            p, q = point(a/4,0), point((a+1)/4,0)
            mesh.panel('civicred', [q,p,(p[0],p[1],p[2]-.32),(q[0],q[1],q[2]-.32)], .05)
    # Upper roof slopes meet at a straight main ridge; side triangles are gables.
    for sign in [-1,1]:
        def slope(x, t):
            return (x, sign*shoulder_y*(1-t),
                    shoulder_z + (top-shoulder_z)*t**.85)
        for a in range(4):
            x, y = -g+2*g*a/4, -g+2*g*(a+1)/4
            for r in range(3):
                t, s = r/3, (r+1)/3
                q = [slope(x,t),slope(y,t),slope(y,s),slope(x,s)]
                if sign > 0:
                    q.reverse()
                mesh.panel('roof', q, thickness,False)
    for x in [-g,g]:
        q = [(x,-shoulder_y,shoulder_z),(x,0,top),(x,shoulder_y,shoulder_z)]
        if x > 0:
            q.reverse()
        mesh.panel('civicred', q, .10)
    # The actual ridge carving is pending; a narrow raised strip gives its rhythm.
    mesh.box('gold', (0,0,top+.12), (2*g,.22,.24))
    for x in [-g,g]:
        mesh.box('gold', (x,0,top+.38), (.34,.28,.65))


def _facade(mesh, width, depth, bottom, eave, bay_count, lower, plaque):
    h = eave-bottom
    body_w, body_d = width*.88, depth*.86
    mesh.box('gold', (0,0,bottom+h/2), (body_w,body_d,h))
    # Pillars on the visible front and back bays; their centers remain outside walls.
    for y in [-body_d/2-.10, body_d/2+.10]:
        for i in range(bay_count+1):
            x = -body_w/2 + body_w*i/bay_count
            mesh.cylinder('civicred', x,y,bottom,eave,.22)
            mesh.box('concrete', (x,y,bottom+.18), (.68,.68,.36))
        mesh.box('civicred', (0,y,eave-.32), (body_w+.48,.40,.52))
    # Side corner columns and blue-green upper windows stay distinct from yellow walls.
    for x in [-body_w/2-.10,body_w/2+.10]:
        for y in [-body_d*.26,0,body_d*.26]:
            mesh.cylinder('civicred', x,y,bottom,eave,.22)
    for y in [-body_d/2-.16,body_d/2+.16]:
        for i in range(bay_count):
            x = -body_w/2 + body_w*(i+.5)/bay_count
            pw = body_w/bay_count*.75
            ph = h*(.60 if lower else .43)
            cz = bottom+h*(.42 if lower else .46)
            mesh.box('darkglass' if lower else 'landmarkglass',(x,y,cz),(pw,.12,ph))
            # Coarse fretwork repeats the photographed red window/door pattern.
            for k in [-.36,0,.36]:
                mesh.box('civicred',(x+pw*k,y-.03 if y<0 else y+.03,cz),(.065,.16,ph))
            for k in [0]:
                mesh.box('civicred',(x,y-.03 if y<0 else y+.03,cz+ph*k),(pw,.16,.065))
    # Sources fix inscription identity; lettering is expressly pending, not traced.
    if plaque:
        y = -body_d/2-.29
        ph, pw, z = min(h*.28,2.6), width*.28, bottom+h*.80
        mesh.box('gold',(0,y,z),(pw,.16,ph))
        mesh.box('civicred',(0,y-.10,z),(pw-.32,.08,ph-.32))
    if not lower:
        # Green/gold frieze beneath the eave, a reference-informed geometric rhythm.
        y = -body_d/2-.25
        mesh.box('landmarkglass',(0,y,eave-.62),(body_w,.10,.55))
        for i in range(bay_count*2):
            x = -body_w/2+body_w*(i+.5)/(bay_count*2)
            mesh.box('gold',(x,y-.07,eave-.62),(.08,.10,.45))


def build(b, lm, spec, scale=.6):
    """Append the five independently positioned halls; preserve caller's B frame."""
    if spec.get('id') != 'lingyin-temple' or spec.get('cityId') != 'hangzhou':
        raise ValueError('Lingyin Hangzhou spec required')
    city = load_city('hangzhou')
    if not math.isclose(scale, city['geography']['scale'], abs_tol=1e-12):
        raise ValueError('Scale disagrees with canonical Hangzhou configuration')
    halls = spec.get('halls', [])
    expected = [434365023,434365024,434365025,434366739,434366741]
    if spec.get('baseBuildingIdsToExclude') != expected or len(halls) != 5:
        raise ValueError('The five hall identities/footprints must remain intact')
    if not all(math.isfinite(float(lm.get(k,0))) for k in ['x','z','y']):
        raise ValueError('Finite game-unit anchor required')
    old_frame = b.frame
    b.frame = (lm['x'], lm['z'], 0)
    report = []
    try:
        for hall in halls:
            mesh = _Hall(b,hall,scale,float(lm.get('y',0)))
            w,d,height = hall['widthM'],hall['depthM'],hall['heightM']
            if min(w,d,height) <= 0:
                raise ValueError('Positive real-metre building dimensions required')
            mesh.box('concrete',(0,0,.25),(w*.94,d*.94,.50))
            triple = hall['eaveTiers'] == 3
            profile = spec['estimates']['roofProfiles']['value']
            eaves = profile['threeTierEaveHeightFractions'] if triple else profile['twoTierEaveHeightFractions']
            tops = profile['threeTierTopHeightFractions'] if triple else profile['twoTierTopHeightFractions']
            wf = [1,*profile['threeTierUpperPlanFactors']] if triple else [1,profile['twoTierUpperPlanFactors'][0]]
            df = [1,.80,.63] if triple else [1,profile['twoTierUpperPlanFactors'][1]]
            bottom = .5
            for tier,(e,t,fw,fd) in enumerate(zip(eaves,tops,wf,df)):
                eave,top = height*e,height*t-(profile['topRidgeDecorationAllowanceM'] if t==1 else 0)
                _facade(mesh,w*fw,d*fd,bottom,eave,hall['bayCount'],tier==0,True)
                _roof(mesh,w*fw,d*fd,eave,top,height*profile['cornerLiftFraction'],profile['roofThicknessM'])
                bottom = eave
            report.append({'id':hall['id'],'name':hall['name'],
                           'sourceFeatureIds':hall['sourceFeatureIds'], 'faces':mesh.faces,
                           'heightM':height,'heightBasis':hall['heightBasis'],
                           'eaveTiers':hall['eaveTiers'],'baseElevationRelativeM':0})
    finally:
        b.frame = old_frame
    return {'scope':spec['scope'],'halls':report,'scaleOnce':scale,
            'materials':['concrete','gold','civicred','roof','darkglass','landmarkglass'],
            'lights':0,'sourceFeatureIds':spec['sourceFeatureIds'],
            'accuracyClaim':'reference-informed five-shell exterior candidate',
            'pending':spec['pendingSubscopes'],
            'groundPolicy':spec['groundPolicy'],
            'plaqueLettering':'pending; no photograph-derived textures'}

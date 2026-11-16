"""Lingyin five-hall site adapter and limited exterior details. Pure B API.

The caller MUST supply five absolute game-unit plinth-base Y values. They are
not multiplied by scale and are not added to lm.y. The frozen round2 geometry
is reused unchanged. Terraces/stairs/details are openly estimated candidates,
not a reconstructed monastery boundary or surveyed ground profile.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import math
from pathlib import Path

BASE_MODULE_SHA256 = '0c215b8a4deb1a36cdcf09eae68a17deef82f24b40aa0226fae15af537052011'
HALL_IDS = ('kings', 'grand', 'medicine', 'dharma', 'huayan')
SOURCE_IDS = [434365023, 434365024, 434365025, 434366739, 434366741]


def _original():
    path = Path(__file__).with_name('lingyin_temple.py')
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_MODULE_SHA256:
        raise ValueError('Frozen Lingyin round2 module changed; rebind provenance before building')
    loader = importlib.util.spec_from_file_location('lingyin_round2_frozen_site_dependency', path)
    result = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(result)
    return result


def _validated(lm, spec, scale, hall_base_y_game=None):
    if spec.get('id') != 'lingyin-temple' or spec.get('cityId') != 'hangzhou' or spec.get('siteVersion') != 3:
        raise ValueError('Lingyin Hangzhou site round3 spec required')
    if not math.isfinite(scale) or abs(scale-spec['coordinatePolicy']['scaleOnce']) > 1e-12:
        raise ValueError('Dimensions must use the single canonical city scale')
    if not all(math.isfinite(float(lm[k])) for k in ['x', 'z']):
        raise ValueError('Finite game-unit east/north anchor required')
    base = spec['baseHallSpec']
    if [h['id'] for h in base['halls']] != list(HALL_IDS) or base['baseBuildingIdsToExclude'] != SOURCE_IDS:
        raise ValueError('Five fixed source hall identities required')
    if any(h['baseElevationRelativeM'] != 0 for h in base['halls']):
        raise ValueError('Frozen halls must not hide a second relative ground offset')
    encoded = json.dumps(base, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    if hashlib.sha256(encoded).hexdigest() != spec['baseHallSpecCanonicalSha256']:
        raise ValueError('Embedded frozen hall spec does not match its provenance hash')
    values = hall_base_y_game if hall_base_y_game is not None else lm.get('hallBaseYGame', spec.get('hallBaseYGame'))
    if not isinstance(values, dict) or set(values) != set(HALL_IDS):
        raise ValueError('Supply hallBaseYGame for all five halls; no implicit DSM or all-zero floor')
    if any(v is None or isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values.values()):
        raise ValueError('Each hall base must be an explicit finite absolute game-unit Y')
    for hall in base['halls']:
        ent = spec['terraces'][hall['id']]
        if min(hall['widthM'], hall['depthM'], hall['heightM'], ent['frontLengthM'], ent['dropM'], ent['stairWidthM'], ent['treadM'], ent['nominalMaxRiserM']) <= 0:
            raise ValueError('Positive dimensions required')
        if ent['stairWidthM'] >= ent['widthM'] or ent['dropM'] < .1:
            raise ValueError('Keep a central stair opening and finite terrace sides')
    return base, {k: float(values[k]) for k in HALL_IDS}


def _tiers(hall, spec):
    p = spec['estimates']['roofProfiles']['value']
    triple = hall['eaveTiers'] == 3
    eaves = p['threeTierEaveHeightFractions'] if triple else p['twoTierEaveHeightFractions']
    tops = p['threeTierTopHeightFractions'] if triple else p['twoTierTopHeightFractions']
    wf = [1, *p['threeTierUpperPlanFactors']] if triple else [1, p['twoTierUpperPlanFactors'][0]]
    df = [1, .80, .63] if triple else [1, p['twoTierUpperPlanFactors'][1]]
    bottom = .5
    for tier, (e, t, fw, fd) in enumerate(zip(eaves, tops, wf, df)):
        eave = hall['heightM']*e
        top = hall['heightM']*t-(p['topRidgeDecorationAllowanceM'] if t == 1 else 0)
        yield tier, hall['widthM']*fw, hall['depthM']*fd, bottom, eave, top
        bottom = eave


def _shell(mesh, hall, base_spec, original):
    w, d = hall['widthM'], hall['depthM']
    mesh.box('concrete', (0, 0, .25), (w*.94, d*.94, .50))
    p = base_spec['estimates']['roofProfiles']['value']
    for tier, width, depth, bottom, eave, top in _tiers(hall, base_spec):
        original._facade(mesh, width, depth, bottom, eave, hall['bayCount'], tier == 0, True)
        original._roof(mesh, width, depth, eave, top, hall['heightM']*p['cornerLiftFraction'], p['roofThicknessM'])


def _terrace_bounds(hall, ent):
    back = -hall['depthM']*.94/2
    front = back-ent['frontLengthM']
    return -ent['widthM']/2, ent['widthM']/2, front, back


def _stairs(hall, ent):
    _, _, front, _ = _terrace_bounds(hall, ent)
    count = math.ceil(ent['dropM']/ent['nominalMaxRiserM'])
    low = .5-ent['dropM']
    for i in range(count):
        near = front-i*ent['treadM']
        far = near-ent['treadM']
        yield i, far, near, low, .5-ent['dropM']*i/count


def _rail_boxes(a, c, top, spec):
    """Closed pale stone posts/panels following an explicitly bounded segment."""
    rail = spec['detailEstimates']['stoneRails']['value']
    dx, dy = c[0]-a[0], c[1]-a[1]
    n = max(1, math.ceil(math.hypot(dx, dy)/rail['pitchM']))
    angle = math.atan2(dy, dx)
    # Return rotated panel geometry in the caller's hall coordinates, not world.
    for i in range(n+1):
        x, y = a[0]+dx*i/n, a[1]+dy*i/n
        yield 'post', (x, y, top+rail['heightM']/2), (rail['postWidthM'], rail['postWidthM'], rail['heightM']), 0
    for i in range(n):
        x, y = a[0]+dx*(i+.5)/n, a[1]+dy*(i+.5)/n
        length = math.hypot(dx, dy)/n-rail['postWidthM']
        for height, thickness in [(rail['heightM']*.90, .12), (rail['heightM']*.43, .22)]:
            yield 'panel', (x, y, top+height), (length, rail['panelDepthM'], thickness), angle


def _oriented_box(mesh, mat, center, size, angle, omit_faces=()):
    ca, sa = math.cos(angle), math.sin(angle)
    cx, cy, cz = center
    w, d, h = [t/2 for t in size]
    pts = [(cx+x*ca-y*sa, cy+x*sa+y*ca, cz+z) for x, y, z in
           [(-w,-d,-h),(w,-d,-h),(w,d,-h),(-w,d,-h),(-w,-d,h),(w,-d,h),(w,d,h),(-w,d,h)]]
    for index, ids in enumerate([(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]):
        if index in omit_faces:
            continue
        mesh.face(mat, [pts[i] for i in ids])


def _rails(hall, ent):
    left, right, front, back = _terrace_bounds(hall, ent)
    gap = ent['stairWidthM']/2+.20
    return [((left, back), (left, front)), ((right, front), (right, back)),
            ((left, front), (-gap, front)), ((gap, front), (right, front))]


def _site(mesh, hall, spec):
    ent = spec['terraces'][hall['id']]
    left, right, front, back = _terrace_bounds(hall, ent)
    low = .5-ent['dropM']
    # A local hall-front masonry terrace only; no rectangular whole-monastery slab.
    _oriented_box(mesh, 'concrete', (0, (front+back)/2, (low+.5)/2), (right-left, back-front, ent['dropM']), 0, (0,))
    # Sparse paired paving seams, independently authored from the visible stone rhythm.
    pitch = spec['detailEstimates']['paving']['value']['pitchM']
    for y in [front+(back-front)*i/4 for i in range(1,4)]:
        mesh.box('roof', (0, y, .504), (right-left-.10, .016, .007))
    for x in [-pitch, 0, pitch]:
        if left+.2 < x < right-.2:
            mesh.box('roof', (x, (front+back)/2, .504), (.016, back-front-.10, .007))
    for _, far, near, bottom, top in _stairs(hall, ent):
        # The shared bottom and uphill face are fully covered by the adjacent
        # higher step/terrace. Retain visible top, downhill and side surfaces.
        _oriented_box(mesh, 'concrete', (0, (far+near)/2, (bottom+top)/2), (ent['stairWidthM'], near-far, top-bottom), 0, (0,4))
    for a, c in _rails(hall, ent):
        for kind, p, size, angle in _rail_boxes(a, c, .5, spec):
            # Panel end caps touch stone posts; post bottoms touch the terrace.
            # Omitting only these hidden contact surfaces keeps the budget.
            _oriented_box(mesh, 'concrete', p, size, angle, (3,5) if kind=='panel' else (0,))


def _plaques(mesh, hall, spec):
    tiers = list(_tiers(hall, spec['baseHallSpec']))
    for inscription in spec['inscriptions'][hall['id']]:
        _, w, d, bottom, eave, _ = tiers[inscription['tier']]
        h = eave-bottom
        ph, pw, z = min(h*.28, 2.6), w*.28, bottom+h*.80
        y = -d*.86/2-.29-.15
        mesh.box(inscription['backgroundMaterial'], (0, y-.012, z), (pw-.34, .023, ph-.34))
        text = inscription['text']
        # Traditional boards are read right to left in the checked references.
        visual = list(reversed(text)) if inscription['visualOrder'] == 'right-to-left' else list(text)
        letter_h = min(ph-.52, (pw-.60)/len(text)*.92)
        pitch = letter_h*1.07
        for index, glyph in enumerate(visual):
            cx = (index-(len(text)-1)/2)*pitch
            for x1, y1, x2, y2 in spec['glyphRectangles'][glyph]:
                xlo, xhi = cx+(x1-.5)*letter_h, cx+(x2-.5)*letter_h
                zlo, zhi = z+(.5-y2)*letter_h, z+(.5-y1)*letter_h
                mesh.face(inscription['letterMaterial'], [(xlo,y-.029,zlo),(xhi,y-.029,zlo),(xhi,y-.029,zhi),(xlo,y-.029,zhi)])


def _ridge_details(mesh, hall, spec):
    """Modest ceramic curl silhouettes, not scanned/traced ornament carvings."""
    estimate = spec['detailEstimates']['ridgeEnds']['value']
    for _, w, _, _, _, top in _tiers(hall, spec['baseHallSpec']):
        for sign in [-1, 1]:
            cx = sign*w*.32
            # A short closed curved strip forms an upward ridge-end silhouette.
            # Their dimensions/placement are modelling estimates from an official
            # temple roof detail whose individual hall assignment is unknown.
            rings = []
            for i in range(estimate['segments']+1):
                t = i/estimate['segments']
                x = cx+sign*estimate['curlLengthM']*(t-.1)
                z = top+.12+estimate['curlRiseM']*math.sin(t*math.pi*.8)
                rings.append([(x,-.10,z-.08),(x,.10,z-.08),(x,.10,z+.08),(x,-.10,z+.08)])
            faces = [list(reversed(rings[0])), rings[-1]]
            for a,c in zip(rings,rings[1:]):
                for i in range(4):
                    j=(i+1)%4
                    faces.append([a[i],a[j],c[j],c[i]])
            for face in faces:
                mesh.face('concrete', face if sign>0 else list(reversed(face)))


def build_with_hall_bases(b, lm, spec, hall_base_y_game, scale=.6, include_details=True):
    """Absolute plinth-base Ys in game units; no lm.y addition or second .60.

    include_details=False is provided for the exact frozen-shell CPU comparison.
    No value is inferred from Copernicus DSM, a broad filter or a photograph.
    """
    base, bases = _validated(lm, spec, scale, hall_base_y_game)
    original = _original()
    city = original.load_city('hangzhou')
    if abs(scale-city['geography']['scale']) > 1e-12:
        raise ValueError('Canonical Hangzhou scale disagrees with supplied spec')
    old = b.frame
    b.frame = (float(lm['x']), float(lm['z']), 0)
    reports = []
    try:
        for hall in base['halls']:
            mesh = original._Hall(b, hall, scale, bases[hall['id']])
            _shell(mesh, hall, base, original)
            shell_faces = mesh.faces
            if include_details:
                _site(mesh, hall, spec)
                _plaques(mesh, hall, spec)
                _ridge_details(mesh, hall, spec)
            reports.append({'id':hall['id'], 'sourceFeatureIds':hall['sourceFeatureIds'],
                            'baseYGame':bases[hall['id']], 'thresholdYGame':bases[hall['id']]+.5*scale,
                            'baseYBasis':'external explicit value; source quality remains caller responsibility',
                            'frozenShellFaces':shell_faces, 'faces':mesh.faces,
                            'estimatedStairCount':len(list(_stairs(hall, spec['terraces'][hall['id']]))),
                            'stairCountBasis':'procedural estimate, not observed or measured'})
    finally:
        b.frame = old
    return {'scope':spec['scope'], 'halls':reports, 'scaleOnce':scale,
            'absoluteGameBaseYUnscaled':True, 'lmYUsed':False,
            'sourceFeatureIds':base['sourceFeatureIds'], 'frozenDependencySha256':BASE_MODULE_SHA256,
            'materials':['concrete','gold','civicred','roof','darkglass','landmarkglass'], 'lights':0,
            'pending':spec['pendingSubscopes'], 'plaqueLettering':'OFL font geometry, reference transcription; not a facsimile',
            'accuracyClaim':'source-bound original shells and explicitly estimated local site details'}


def build(b, lm, spec, scale=.6):
    return build_with_hall_bases(b, lm, spec, None, scale)


def _hall_local(x, z, lm, hall, scale):
    dx = (x-float(lm['x']))/scale-hall['offsetEastNorthM'][0]
    dz = (z-float(lm['z']))/scale-hall['offsetEastNorthM'][1]
    a = hall['widthAxisRadiansEastCCW']
    ca, sa = math.cos(a), math.sin(a)
    return dx*ca+dz*sa, -dx*sa+dz*ca


def _to_game(u, v, lm, hall, scale):
    ca, sa = math.cos(hall['widthAxisRadiansEastCCW']), math.sin(hall['widthAxisRadiansEastCCW'])
    return [float(lm['x'])+(hall['offsetEastNorthM'][0]+u*ca-v*sa)*scale,
            float(lm['z'])+(hall['offsetEastNorthM'][1]+u*sa+v*ca)*scale]


def floor_height_game(x, z, lm, spec, hall_id, scale=.6, hall_base_y_game=None):
    """Explicit hall-front terrace/stair surface only, or None.

    This API does not certify real-world entry, terrain joining or accessibility.
    Original closed hall walls remain obstacles; no fictional indoor route.
    """
    base, bases = _validated(lm, spec, scale, hall_base_y_game)
    hall = next((h for h in base['halls'] if h['id'] == hall_id), None)
    if hall is None:
        raise ValueError('Choose one of the five fixed halls')
    ent = spec['terraces'][hall_id]
    u, v = _hall_local(float(x), float(z), lm, hall, scale)
    left, right, front, back = _terrace_bounds(hall, ent)
    eps = 1e-9
    if left-eps <= u <= right+eps and front-eps <= v <= back+eps:
        return bases[hall_id]+.5*scale
    if abs(u) <= ent['stairWidthM']/2+eps:
        for _, far, near, _, top in _stairs(hall, ent):
            if far-eps <= v <= near+eps:
                return bases[hall_id]+top*scale
    return None


def ground_footprints(lm, spec, scale=.6, hall_base_y_game=None):
    """Actual candidate body/terrace/stair/post solids with vertical bounds.

    Only the five halls and estimated front aprons are represented. Floors use
    floor_height_game; no all-monastery polygon, false entrance hole or DSM slab.
    """
    base, bases = _validated(lm, spec, scale, hall_base_y_game)
    result = []
    def add(hall, kind, center, size, angle=0):
        cx, cy, cz = center
        w, d, h = size
        ca, sa = math.cos(angle), math.sin(angle)
        ring = [_to_game(cx+u*ca-v*sa, cy+u*sa+v*ca, lm, hall, scale)
                for u, v in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
        result.append({'kind':kind, 'hallId':hall['id'], 'polygonGame':ring,
                       'minYGame':bases[hall['id']]+(cz-h/2)*scale,
                       'maxYGame':bases[hall['id']]+(cz+h/2)*scale,
                       'sourceFeatureIds':hall['sourceFeatureIds'],
                       'basis':'candidate mesh bounds; closed shells and estimated site, not surveyed site clearance',
                       'entranceVerified':False})
    for hall in base['halls']:
        w, d = hall['widthM'], hall['depthM']
        add(hall, 'frozen-plinth', (0,0,.25), (w*.94,d*.94,.5))
        for _, tw, td, bottom, eave, _ in _tiers(hall, base):
            add(hall, 'frozen-closed-wall-body', (0,0,(bottom+eave)/2), (tw*.88,td*.86,eave-bottom))
        ent = spec['terraces'][hall['id']]
        left, right, front, back = _terrace_bounds(hall, ent)
        low = .5-ent['dropM']
        add(hall, 'estimated-local-masonry-terrace', (0,(front+back)/2,(low+.5)/2), (right-left,back-front,ent['dropM']))
        for _, far, near, bottom, top in _stairs(hall, ent):
            add(hall, 'estimated-local-stair-solid', (0,(far+near)/2,(bottom+top)/2), (ent['stairWidthM'],near-far,top-bottom))
        for a, c in _rails(hall, ent):
            for kind, p, size, angle in _rail_boxes(a, c, .5, spec):
                add(hall, 'estimated-stone-rail-'+kind, p, size, angle)
    return result

"""CPU-only meaningful geometric/source checks; does not load Blender or browser."""
import ast
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
MODULE = ROOT/'scripts/landmarks/cainiao_headquarters.py'
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Collector:
    def __init__(self, fault_after=None):
        self.frame = (7,11,.2)
        self.initial = self.frame
        self.faces = []
        self.fault_after = fault_after

    def face(self, material, points, uv=None):
        if self.fault_after is not None and len(self.faces) == self.fault_after:
            raise RuntimeError('deliberate receiver failure')
        bx,by,angle = self.frame
        c,s = math.cos(angle),math.sin(angle)
        p = [(x*c-y*s+bx,x*s+y*c+by,z) for x,y,z in points]
        self.faces.append((material,p))


def inside(point, ring):
    x,y = point
    hit = False
    for (a,b),(c,d) in zip(ring,ring[1:]+ring[:1]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:
            hit = not hit
    return hit


def main():
    spec = json.loads((HERE/'spec.json').read_text())
    evidence = ROOT/spec['evidencePath']
    assert sha(evidence) == spec['evidenceSha256']
    assert sha(ROOT/spec['sourceFootprintPath']) == spec['sourceFootprintSha256']
    manifest = json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    assert sha(ROOT/'data/processed/hangzhou/buildings.geojson') == manifest['sha256']['buildings']
    src = json.loads((ROOT/spec['sourceFootprintPath']).read_text())
    assert src['feature']['geometry']['coordinates'][0][0] == spec['footprintWGS84']
    tree = ast.parse(MODULE.read_text())
    assert all(not (isinstance(n,ast.Import) and any(a.name=='bpy' for a in n.names)) for n in ast.walk(tree))
    ref = importlib.util.spec_from_file_location('cainiao_candidate',MODULE)
    mod = importlib.util.module_from_spec(ref)
    ref.loader.exec_module(mod)
    geo = load_city('hangzhou')['geography']
    lon,lat = spec['anchor']['lon'],spec['anchor']['lat']
    lm = {'lon':lon,'lat':lat,'x':125,'z':-75,'y':4}
    c = Collector()
    report = mod.build(c,lm,spec,.6)
    assert c.frame == c.initial
    assert report['triangleCountBeforeExport'] == sum(len(p)-2 for _,p in c.faces)
    assert report['triangleCountBeforeExport'] <= spec['budget']['maxTriangles']
    assert len(report['materials']) <= spec['budget']['maxMaterials']
    assert report['courtyardCount']==4 and report['diagonalConnectionCount']==4
    assert report['canopyLayerCount']==5 and report['newLights']==0 and report['photoTextures']==0
    assert all(math.isfinite(v) for _,p in c.faces for point in p for v in point)
    vertices = {tuple(round(v,5) for v in p[:2]) for _,poly in c.faces for p in poly}
    for lo,la in spec['footprintWGS84']:
        expected = (round(125+(lo-lon)*geo['eastMetresPerDegree']*.6,5),
                    round(-75+(la-lat)*geo['northMetresPerDegree']*.6,5))
        assert expected in vertices,('source vertex lost',expected)
    full = Collector()
    mod.build(full,lm,spec,1)
    assert len(c.faces)==len(full.faces)
    for (_,p),(_,q) in zip(c.faces,full.faces):
        for a,b in zip(p,q):
            for k,origin in enumerate((125,-75,4)):
                assert math.isclose(a[k]-origin,(b[k]-origin)*.6,rel_tol=1e-9,abs_tol=1e-8)
    # Same WGS84 placement when integration provides a different landmark marker.
    shifted = dict(lm,lon=lon+.001,lat=lat-.001,
                   x=125+geo['eastMetresPerDegree']*.001*.6,
                   z=-75-geo['northMetresPerDegree']*.001*.6)
    moved = Collector()
    mod.build(moved,shifted,spec,.6)
    for (_,p),(_,q) in zip(c.faces,moved.faces):
        assert all(math.dist(a,b)<1e-6 for a,b in zip(p,q))
    failed = Collector(5)
    try:
        mod.build(failed,lm,spec,.6)
        raise AssertionError('receiver fault was swallowed')
    except RuntimeError:
        assert failed.frame == failed.initial
    collisions = mod.ground_footprints(lm,spec,.6)
    outer = [[125+(lo-lon)*geo['eastMetresPerDegree']*.6,
              -75+(la-lat)*geo['northMetresPerDegree']*.6] for lo,la in spec['footprintWGS84'][:-1]]
    def on_boundary(p):
        for a,b in zip(outer,outer[1:]+outer[:1]):
            dx,dy = b[0]-a[0],b[1]-a[1]
            t = max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
            if math.dist(p,(a[0]+dx*t,a[1]+dy*t))<1e-6:
                return True
        return False
    assert all(inside(p,outer) or on_boundary(p) for ring in collisions for p in ring), 'solid tip exceeds source outline'
    # These are four source-supported courtyard sectors; no roof or collision
    # polygon may cap them. This catches the common solid-square campus proxy.
    court_points = [(125+x*.6,-75+y*.6) for x,y in ((72,0),(0,72),(-72,0),(0,-72))]
    roof_polygons = [[(p[0],p[1]) for p in poly] for material,poly in c.faces
                     if material=='roof' and len({round(p[2],4) for p in poly})==1]
    for p in court_points:
        assert not any(inside(p,ring) for ring in collisions),('courtyard collision filled',p)
        assert not any(inside(p,ring) for ring in roof_polygons),('courtyard roof filled',p)
    portal = (125+116*.6,-75)
    assert not any(inside(portal,ring) for ring in collisions),'estimated east portal capped'
    assert any(inside((125,-75),ring) for ring in collisions),'central connector missing'
    result = {'checkedAt':'2026-10-13','scope':'CPU candidate geometry/source integrity only; no GLB/GPU/browser validation',
              'sourceModule':str(MODULE.relative_to(ROOT)),'sourceModuleSha256':sha(MODULE),
              'specSha256':sha(HERE/'spec.json'),'evidenceSha256':sha(evidence),
              'checks':{'sourceFootprintCycle':True,'currentGeofabrikHash':True,'finiteGeometry':True,
                        'singleScalingAndGameHeight':True,'offsetProjection':True,'frameRestorationIncludingError':True,
                        'sourceOuterVerticesRetained':True,'fourRoofAndCollisionVoids':True,'estimatedPortalOpen':True,
                        'solidTipsWithinMappedExterior':True,
                        'triangleMaterialBudget':True,'noSceneExportOrBpyImport':True},
              'report':report,'collisionPolygonCount':len(collisions),'courtProbePositionsGame':court_points,
              'limitations':['void probes are finite data checks, not a full collision/navigation or visual review',
                             'entry position and interior dimensions remain estimates',
                             'material GPU response, all-side shape and actual GLB resource size not tested']}
    (HERE/'cpu-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks':result['checks'],'triangles':report['triangleCountBeforeExport'],
                      'materials':report['materials'],'partTriangles':report['partTriangles']},ensure_ascii=False))


if __name__ == '__main__':
    main()

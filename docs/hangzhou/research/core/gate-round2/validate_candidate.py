"""CPU geometry contract checks; does not import bpy or claim GPU/GLB validation."""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO/'scripts'))
from city_config import load_city, project


class Recorder:
    def __init__(self):
        self.frame = (17, 29, .34)
        self.faces = []

    def face(self, material, points, uv=None):
        x, y, angle = self.frame
        c, s = math.cos(angle), math.sin(angle)
        self.faces.append((material, [(u*c-v*s+x,u*s+v*c+y,z) for u,v,z in points]))


def triangle_area(a, b, c):
    u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
    cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    return math.sqrt(sum(x*x for x in cross))/2


def main():
    source = REPO/'scripts/landmarks/hangzhou_gate.py'
    loader = importlib.util.spec_from_file_location('gate_candidate', source)
    gate = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(gate)
    spec = json.loads((HERE/'spec.json').read_text())
    city = load_city('hangzhou')
    anchor = spec['anchor']
    xy = project(anchor['lon'], anchor['lat'], city)
    lm = {'x':xy[0], 'z':xy[1], 'lon':anchor['lon'], 'lat':anchor['lat'], 'y':2.5}
    recorder = Recorder()
    result = gate.build(recorder, lm, spec)
    assert recorder.frame == (17,29,.34), 'Shared builder frame was not restored'
    points = [p for _,face in recorder.faces for p in face]
    assert all(math.isfinite(v) for p in points for v in p)
    assert abs(max(p[2] for p in points)-188.5) < 1e-8, '310m scale/base contract failed'
    assert abs(min(p[2] for p in points)-2.5) < 1e-8, 'Game-unit base height got rescaled'
    assert len(result['materials']) <= spec['budget']['maxMaterials']
    degenerate = [(index, i) for index,(_,face) in enumerate(recorder.faces)
                  for i in range(1,len(face)-1)
                  if triangle_area(face[0],face[i],face[i+1]) < 1e-10]
    assert not degenerate, f'Degenerate triangle fans: {degenerate[:8]}'
    expected = {tuple(project(*p,city)) for tower in spec['towers'] for p in tower['footprintWGS84']}
    polygons = gate.ground_footprints(lm, spec)
    actual = {tuple(p) for ring in polygons for p in ring}
    assert all(min(math.dist(p,q) for q in actual) < 1e-8 for p in expected), 'Footprints diverge from shared city projection'
    result['checks'] = {'finiteVertices': True, 'nondegenerateTriangleFans': True,
                        'sharedProjectionAgreement': True, 'frameRestored': True,
                        'heightAndBaseScaledOnce': True, 'materialsWithinBudget': True}
    result['sourceModuleSha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    result['specSha256'] = hashlib.sha256((HERE/'spec.json').read_bytes()).hexdigest()
    result['validationScope'] = 'CPU B-interface record only; no bpy, GLB, physics, shader, game browser or FPS result'
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()

"""Host-side B contract and geometry checks; never imports scene-resetting city_mesh."""
from __future__ import annotations
from collections import defaultdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'scripts'))
from city_config import load_city, project
OUT = Path(__file__).resolve().parent


class Recorder:
    def __init__(self):
        self.frame = (11,22,.3)
        self.groups = defaultdict(list)
        self.faces = []

    def face(self, material, points, uv=None):
        ox, oy, angle = self.frame
        ca, sa = math.cos(angle), math.sin(angle)
        transformed = [(x*ca-y*sa+ox,x*sa+y*ca+oy,z) for x,y,z in points]
        self.groups[material].append(transformed)
        self.faces.append((material,transformed))


def area(a,b,c):
    u=[b[i]-a[i] for i in range(3)]
    v=[c[i]-a[i] for i in range(3)]
    w=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    return math.sqrt(sum(x*x for x in w))/2


def main():
    spec=json.loads((OUT/'spec.json').read_text())
    source=ROOT/'scripts/landmarks/lingyin_temple.py'
    modspec=importlib.util.spec_from_file_location('lingyin_candidate',source)
    module=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(module)
    city=load_city('hangzhou'); s=city['geography']['scale']
    x,z=project(spec['anchor']['lon'],spec['anchor']['lat'],city)
    lm={'x':x,'z':z,'y':13.25,'id':spec['id']}
    b=Recorder(); old=b.frame
    report=module.build(b,lm,spec,s)
    assert b.frame==old, 'caller B frame was changed'
    assert len(report['halls'])==5
    assert [r['eaveTiers'] for r in report['halls']]==[2,3,2,2,2]
    assert set(b.groups)==set(report['materials'])
    assert len(b.groups)<=spec['budget']['maxMaterials']
    assert report['lights']==0
    triangles=0;minimum=math.inf
    for material,face in b.faces:
        assert len(face)>=3
        assert all(math.isfinite(v) for p in face for v in p)
        for i in range(1,len(face)-1):
            measured=area(face[0],face[i],face[i+1])
            assert measured>1e-10, ('degenerate fan triangle',material,face)
            minimum=min(minimum,measured);triangles+=1
    assert triangles<=spec['budget']['maxTriangles'], f'budget exceeded: {triangles}'
    rows=[];cursor=0
    for hall,item in zip(spec['halls'],report['halls']):
        chunk=b.faces[cursor:cursor+item['faces']];cursor+=item['faces']
        assert item['sourceFeatureIds']==hall['sourceFeatureIds']
        # First six faces are a symmetric plinth. Its center is a real placement check.
        base=[p for _,face in chunk[:6] for p in face]
        center=(sum(p[0] for p in base)/len(base),sum(p[1] for p in base)/len(base))
        expected=project(*hall['centroidWGS84'],city)
        assert max(abs(center[i]-expected[i]) for i in range(2))<1e-6, 'city projection/scale/axis mismatch'
        pts=[p for _,face in chunk for p in face]
        low=min(p[2] for p in pts); high=max(p[2] for p in pts)
        assert abs(low-lm['y'])<1e-8, 'game-unit base Y was rescaled'
        assert abs((high-lm['y'])/s-hall['heightM'])<.03, 'roof height was scaled twice or exceeds declared height'
        rows.append({'id':hall['id'],'sourceFeatureIds':hall['sourceFeatureIds'],
                     'centerGame':center,'heightGame':high-low,'heightBasis':hall['heightBasis']})
    assert cursor==len(b.faces)
    shifted=Recorder(); shift=[21.5,-33.75,7.125]
    module.build(shifted,{**lm,'x':x+shift[0],'z':z+shift[1],'y':lm['y']+shift[2]},spec,s)
    for (_,oldface),(_,newface) in zip(b.faces,shifted.faces):
        for p,q in zip(oldface,newface):
            assert max(abs(q[i]-p[i]-shift[i]) for i in range(3))<1e-8, 'anchor translation contract failed'
    invalid=Recorder()
    try:
        module.build(invalid,lm,spec,s*s)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid double scale was accepted')
    assert not invalid.faces and invalid.frame==(11,22,.3)
    result={'schemaVersion':1,'status':'passed-host-contract-only',
            'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'reviewedBy':'landmark_evidence CPU recorder',
            'sourceModuleSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'sourceSpecSha256':hashlib.sha256((OUT/'spec.json').read_bytes()).hexdigest(),
            'hallCount':5,'faces':len(b.faces),'trianglesBeforeBlenderExport':triangles,
            'materials':sorted(b.groups),'lights':0,'minimumFanTriangleAreaGameUnits2':minimum,
            'hallPlacement':rows,
            'checks':['finite/nondegenerate triangle fans','five distinct source hall identities',
                      'double/triple-eave counts','canonical WGS84 centroid placement',
                      'uniform 0.60 dimension scale','game-unit baseY and translation preservation',
                      'B frame restored','reject repeated scale','provisional triangle/material/light budgets'],
            'limitations':['No Blender was started; real exporter may triangulate differently.',
                          'This check is not visual, collision, browser or performance acceptance.',
                          'Roof samples have back faces; watertight joinery was not tested.',
                          'All five ground offsets are neutral candidate zero, not actual terrain.']}
    (OUT/'cpu-geometry-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()

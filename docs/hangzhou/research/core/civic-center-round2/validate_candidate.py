"""Pure FakeB checks; no Blender, GLB, browser or acceptance claim."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import math
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project


class FakeB:
    def __init__(self,fail_at=None):self.frame=(13,-22,.7);self.faces=[];self.fail_at=fail_at
    def face(self,mat,pts,uv=None):
        if self.fail_at is not None and len(self.faces)>=self.fail_at:raise RuntimeError('deliberate FakeB failure')
        x,y,a=self.frame;c,s=math.cos(a),math.sin(a)
        self.faces.append((mat,[(x+u*c-v*s,y+u*s+v*c,z) for u,v,z in pts]))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def vertices(b):return [p for mat,pts in b.faces for p in pts]


def area3(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    return math.sqrt(sum(q*q for q in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])))


def main():
    source=ROOT/'scripts/landmarks/civic_center.py';p=HERE/'spec.json';spec=json.loads(p.read_text());city=load_city('hangzhou');a=spec['anchor'];x,z=project(a['lon'],a['lat'],city)
    module_spec=importlib.util.spec_from_file_location('civic_cpu_candidate',source);m=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(m)
    lm={'lon':a['lon'],'lat':a['lat'],'x':x,'z':z,'y':2.5};b=FakeB();old=b.frame;report=m.build(b,lm,spec)
    assert b.frame==old
    pts=vertices(b);assert all(math.isfinite(v) for p in pts for v in p)
    assert all(area3(p[0],p[i],p[i+1])>1e-9 for mat,p in b.faces for i in range(1,len(p)-1))
    assert report['triangleCountBeforeExport']==sum(len(p)-2 for mat,p in b.faces)
    assert report['towerCount']==6 and report['podiumCount']==4 and report['roofPavilionCount']==2
    assert report['annularSkybridge'] and report['centralGardenOpen']
    assert math.isclose(max(p[2] for p in pts)-lm['y'],109.6*.6,abs_tol=1e-6)
    small=FakeB();m.build(small,lm,spec,.3)
    for full,half in zip(pts,vertices(small)):
        assert math.isclose(full[0]-x,2*(half[0]-x),abs_tol=1e-7)
        assert math.isclose(full[1]-z,2*(half[1]-z),abs_tol=1e-7)
        assert math.isclose(full[2]-lm['y'],2*(half[2]-lm['y']),abs_tol=1e-7)
    sx,sz=project(a['lon']+.001,a['lat']-.001,city);shifted=dict(lm,lon=a['lon']+.001,lat=a['lat']-.001,x=sx,z=sz)
    sh=FakeB();m.build(sh,shifted,spec)
    assert all(math.isclose(v,w,abs_tol=1e-7) for p,q in zip(pts,vertices(sh)) for v,w in zip(p,q))
    failure=FakeB(fail_at=4);before=failure.frame
    try:m.build(failure,lm,spec)
    except RuntimeError:pass
    else:raise AssertionError('Expected fakefailure')
    assert failure.frame==before
    foot=m.ground_footprints(lm,spec);assert len(foot)==11
    expected=[c for c in spec['components'] if c['role'] in ('tower','podium')]
    for c,ring in zip(expected,foot):
        for (u,v),(lon,lat) in zip(ring,c['footprintWGS84'][:-1]):
            want=project(lon,lat,city);assert math.isclose(u,want[0],abs_tol=1e-6) and math.isclose(v,want[1],abs_tol=1e-6)
    # Ear clipping retains each true concave L area rather than its boundingbox.
    parts,rings,offset,g=m._context(lm,spec)
    for c in parts:
        poly=c['ring'];pa=abs(sum(x*v-u*y for (x,y),(u,v) in zip(poly,poly[1:]+poly[:1])))/2
        ta=sum(abs(m._cross(*tri))/2 for tri in m._triangulate(poly));assert math.isclose(pa,ta,rel_tol=1e-8)
    # Bridge bottom/top horizontal faces are annuli, never full center caps.
    bridge=FakeB();mesh=m._Mesh(bridge,.6,(0,0),0);m._bridge(mesh,rings,spec)
    assert min(math.hypot(p[0]-13,p[1]+22) for mat,points in bridge.faces for p in points)>39
    assert report['triangleCountBeforeExport']<=spec['budget']['maxTriangles'] and len(report['materials'])<=spec['budget']['maxMaterials']
    forbidden={'bpy','city_mesh'}
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.Import):assert all(n.name.split('.')[0] not in forbidden for n in node.names)
        if isinstance(node,ast.ImportFrom):assert (node.module or '').split('.')[-1] not in forbidden
    assert len(spec['baseBuildingIdsToExclude'])==13 and all(i not in spec['baseBuildingIdsToExclude'] for i in spec['preserveUndergroundIds'])
    report.update(checks={'finiteVertices':True,'noDegenerateTriangleFans':True,'sixFourTwoComponentCounts':True,
        'mappedFootprintAndConcavePodiumArea':True,'annularBridgeDoesNotCapCenter':True,'oneTimeScaleAndGameBasePreserved':True,
        'sourceAnchorSurvivesShiftedLm':True,'frameRestoredSuccessAndFailure':True,'cpuBudget':True,'noSceneImports':True,'undergroundNotRemoved':True},
        sourceModuleSha256=sha(source),specSha256=sha(p),boundsGameENU={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]},
        validationScope='Pure CPU FakeB primitive accounting/projection only, not final Blender/GLB bytes or triangulation, visual/PBR, terrain, access/collision, GPU/browser/night/FPS acceptance.')
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()

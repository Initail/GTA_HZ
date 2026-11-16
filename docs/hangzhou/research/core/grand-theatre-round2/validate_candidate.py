"""Pure CPU FakeB geometry checks; no GLB, Blender or browser acceptance."""
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
    def __init__(self,fail_at=None):self.frame=(12,-33,.3);self.faces=[];self.fail_at=fail_at
    def face(self,mat,points,uv=None):
        if self.fail_at is not None and len(self.faces)>=self.fail_at:raise RuntimeError('deliberate FakeB failure')
        x,y,a=self.frame;c,s=math.cos(a),math.sin(a);self.faces.append((mat,[(x+u*c-v*s,y+u*s+v*c,z) for u,v,z in points]))


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def vertices(b):return [p for mat,points in b.faces for p in points]


def area3(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    return math.sqrt(sum(x*x for x in [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]))


def main():
    source=ROOT/'scripts/landmarks/grand_theatre.py';spec_path=HERE/'spec.json';spec=json.loads(spec_path.read_text());city=load_city('hangzhou');a=spec['anchor'];x,z=project(a['lon'],a['lat'],city)
    module_spec=importlib.util.spec_from_file_location('grand_theatre_cpu',source);m=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(m)
    lm={'lon':a['lon'],'lat':a['lat'],'x':x,'z':z,'y':2.5};b=FakeB();before=b.frame;report=m.build(b,lm,spec);assert b.frame==before
    pts=vertices(b);assert all(math.isfinite(v) for p in pts for v in p)
    for mat,p in b.faces:
        for i in range(1,len(p)-1):assert area3(p[0],p[i],p[i+1])>1e-9,(mat,p)
    assert report['triangleCountBeforeExport']==sum(len(p)-2 for mat,p in b.faces)
    assert report['moonContourCount']==11 and report['sourceFeatureCoverageCount']==14
    profile=spec['estimates']['operaProfile']['value']
    assert profile[0][1]<profile[2][1] and profile[2][1]>profile[3][1]<profile[4][1]
    assert max(f for z,f in spec['estimates']['operaRoofProfile']['value'])>max(f for z,f in profile)
    assert abs((max(p[2] for p in pts)-lm['y'])/.6-spec['reported']['mainHeightM'])<.25
    assert report['candidateWaterPlanes']==0 and 'water' not in report['materials']
    small=FakeB();m.build(small,lm,spec,.3)
    for p,q in zip(pts,vertices(small)):
        assert math.isclose(p[0]-x,2*(q[0]-x),abs_tol=1e-7)
        assert math.isclose(p[1]-z,2*(q[1]-z),abs_tol=1e-7)
        assert math.isclose(p[2]-lm['y'],2*(q[2]-lm['y']),abs_tol=1e-7)
    sx,sz=project(a['lon']+.001,a['lat']-.001,city);shifted=dict(lm,lon=a['lon']+.001,lat=a['lat']-.001,x=sx,z=sz);sh=FakeB();m.build(sh,shifted,spec)
    assert all(math.isclose(u,v,abs_tol=1e-7) for p,q in zip(pts,vertices(sh)) for u,v in zip(p,q))
    fail=FakeB(fail_at=4);old=fail.frame
    try:m.build(fail,lm,spec)
    except RuntimeError:pass
    else:raise AssertionError('Expected deliberate failure')
    assert fail.frame==old
    foot=m.ground_footprints(lm,spec);assert len(foot)==1
    raw=next(c['footprintWGS84'] for c in spec['components'] if c['role']=='main-ground')
    for p,q in zip(foot[0],raw[:-1]):
        want=project(*q,city);assert all(math.isclose(u,v,abs_tol=1e-6) for u,v in zip(p,want))
    parts,contours,offset,g=m._context(lm,spec)
    for c in parts+contours:
        ring=c['ring'];pa=abs(sum(x*v-u*y for (x,y),(u,v) in zip(ring,ring[1:]+ring[:1])))/2
        ta=sum(abs(m._cross(*tri))/2 for tri in m._triangulate(ring));assert math.isclose(pa,ta,rel_tol=1e-8)
    rows=[m._crescent_row(c,spec) for c in contours];assert len(set(map(len,rows)))==1
    assert all(math.isclose(row[0][0],c['ring'][0][0],abs_tol=1e-6) and math.isclose(row[len(row)//2][1],c['ring'][c['splitIndex']][1],abs_tol=1e-6) for row,c in zip(rows,contours))
    assert report['triangleCountBeforeExport']<=spec['budget']['maxTriangles'] and len(report['materials'])<=spec['budget']['maxMaterials']
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.Import):assert all(n.name.split('.')[0] not in {'bpy','city_mesh'} for n in node.names)
        if isinstance(node,ast.ImportFrom):assert (node.module or '').split('.')[-1] not in {'bpy','city_mesh'}
    assert all(i not in spec['baseBuildingIdsToExclude'] for i in spec['preserveNeighborIds'])
    report.update(checks={'finiteVertices':True,'nondegenerateTriangleFans':True,'mappedFootprintAndConcaveCapArea':True,
        'elevenConsistentMoonControlPlans':True,'reportedRoofHeightEnvelope':True,'twoTierFrontSeparateFromMoon':True,
        'noCandidateWaterGeometry':True,'onceScaleAndGameBasePreserved':True,'shiftedLmSourceAnchor':True,
        'frameRestoredSuccessAndFailure':True,'cpuBudget':True,'noSceneImports':True,'neighborsNotRemoved':True},
        sourceModuleSha256=sha(source),specSha256=sha(spec_path),boundsGameENU={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]},
        validationScope='Pure CPU FakeB geometry/projection/counts only; not Blender/GLB bytes or final triangulation, named exterior/PBR, water/site, door/stair terrain/collision, browser/night or FPS acceptance.')
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()

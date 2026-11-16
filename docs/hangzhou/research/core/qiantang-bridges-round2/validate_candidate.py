"""CPU geometry/source-profile contract only; no GLB or driving acceptance."""
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
    def __init__(self,fail_at=None):self.frame=(77,-63,.73);self.faces=[];self.fail_at=fail_at
    def face(self,mat,points,uv=None):
        if self.fail_at is not None and len(self.faces)>=self.fail_at:raise RuntimeError('deliberate failure')
        x,y,a=self.frame;c,s=math.cos(a),math.sin(a);self.faces.append((mat,[(x+u*c-v*s,y+u*s+v*c,z) for u,v,z in points]))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verts(b):return [p for mat,points in b.faces for p in points]
def area3(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];return math.sqrt(sum(x*x for x in w))
def main():
    source=ROOT/'scripts/landmarks/qiantang_bridges.py';sp=HERE/'spec.json';spec=json.loads(sp.read_text());city=load_city('hangzhou');a=spec['anchor'];x,z=project(a['lon'],a['lat'],city);lm={'x':x,'z':z,'lon':a['lon'],'lat':a['lat'],'y':2.75}
    ms=importlib.util.spec_from_file_location('bridge_candidate_cpu',source);m=importlib.util.module_from_spec(ms);ms.loader.exec_module(m)
    b=FakeB();old=b.frame;report=m.build(b,lm,spec);assert b.frame==old;points=verts(b)
    assert all(math.isfinite(v) for p in points for v in p)
    for mat,p in b.faces:
        for i in range(1,len(p)-1):assert area3(p[0],p[i],p[i+1])>1e-9,(mat,p)
    assert report['triangleCountBeforeExport']==sum(len(p)-2 for mat,p in b.faces)
    assert report['triangleCountBeforeExport']<=spec['budget']['maxTriangles']
    assert len(report['materials'])<=spec['budget']['maxMaterials']
    assert report['bridgeCount']==3 and report['candidateWaterPlanes']==0 and report['candidateRoadTopPlanes']==0 and not report['xixingAndBoaoRendered']
    assert report['bridges'][0]['trussSpans']==16 and report['bridges'][1]['largeArches']==2 and report['bridges'][1]['smallArches']==9 and report['bridges'][2]['archPylons']==2
    small=FakeB();m.build(small,lm,spec,.3)
    for p,q in zip(points,verts(small)):
        for k,base in enumerate([x,z,lm['y']]):assert math.isclose(p[k]-base,2*(q[k]-base),abs_tol=1e-7)
    shifted=dict(lm,lon=a['lon']+.001,lat=a['lat']-.001);shifted['x'],shifted['z']=project(shifted['lon'],shifted['lat'],city);bs=FakeB();m.build(bs,shifted,spec)
    assert all(math.isclose(a,b,abs_tol=1e-7) for p,q in zip(points,verts(bs)) for a,b in zip(p,q))
    fail=FakeB(8);before=fail.frame
    try:m.build(fail,lm,spec)
    except RuntimeError:pass
    else:raise AssertionError('Expected FakeB failure')
    assert fail.frame==before
    try:m.source_road_profiles(spec,lm['y'])
    except ValueError:pass
    else:raise AssertionError('Estimated profile must require explicit opt-in')
    profiles=m.source_road_profiles(spec,lm['y'],allow_estimated=True,include_outer_continuations=False);rail=m.source_rail_profiles(spec,lm['y'],allow_estimated=True)
    assert len(profiles)==11 and len(rail)==1 and all(r['mode']=='road' and not r['navigationAccepted'] for r in profiles)
    source_features={f['id']:f for f in json.loads((HERE/'fixed-bridge-features.geojson').read_text())['features']}
    shared={};shared_cases=[]
    for r in profiles:
        raw=source_features[r['id']];assert r['nodeIds']==raw['properties']['nodeIds'] and r['coordinatesWGS84']==raw['geometry']['coordinates']
        assert len(r['points'])==len(r['heights'])==len(r['nodeIds'])
        for n,q,p,h in zip(r['nodeIds'],r['coordinatesWGS84'],r['points'],r['heights']):
            expected=project(*q,city);assert all(math.isclose(a,b,abs_tol=1e-6) for a,b in zip(p,expected))
            h2=m.road_height_at(r['id'],*q,spec,lm['y'],allow_estimated=True);assert math.isclose(h,h2,abs_tol=1e-7)
            key=(r['mode'],r['deck'],n)
            if key in shared:assert math.isclose(shared[key],h,abs_tol=1e-8);shared_cases.append(key)
            shared[key]=h
        assert max(math.dist(a['point'],b['point'])/.6 for a,b in zip(r['profileSamples'],r['profileSamples'][1:]))<=20+1e-8
    # A real rail/road source-node collision has different level heights.
    ref='3351280499';q=next(r for r in profiles if r['id']=='way/4348186');lo=rail[0]
    assert ref in q['nodeIds'] and ref in lo['nodeIds']
    delta=q['heights'][q['nodeIds'].index(ref)]-lo['heights'][lo['nodeIds'].index(ref)]
    assert math.isclose(delta,10.7*.6,abs_tol=1e-8)
    assert 'way/826790145' not in [r['id'] for r in profiles+rail]
    # External source branch endpoints are honored in game units without re-scaling.
    target='1667167465';v=lm['y']+12*.6;altered=m.source_road_profiles(spec,lm['y'],{target:v},allow_estimated=True)
    changed=next(r for r in altered if r['id']=='way/4348186');assert changed['heights'][0]==v
    # Shared Fuxing source-way boundary remains exact, including supplied override.
    ref='1667217046';v=lm['y']+21*.6;changed=m.source_road_profiles(spec,lm['y'],{ref:v},allow_estimated=True)
    hs=[r['heights'][r['nodeIds'].index(ref)] for r in changed if ref in r['nodeIds']];assert len(hs)==2 and hs==[v,v]
    ext=m.source_road_profiles(spec,lm['y'],allow_estimated=True);assert len(ext)==15
    southern={'3112466937','3112466958'};adj=json.loads((HERE/'endpoint-adjacency.json').read_text())
    expected={'3112466937':{'way/306360719','way/589558020'},'3112466958':{'way/306360714','way/306360716'}}
    for n,ids in expected.items():
        core='way/306360721' if n=='3112466937' else 'way/589558021'
        assert ids.issubset({r['id'] for r in adj[core][n]})
        assert all(n in next(r for r in ext if r['id']==ident)['nodeIds'] for ident in ids)
    assert 'way/306360719' in [r['id'] for r in ext] and 'way/306360714' in [r['id'] for r in ext]
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.Import):assert all(v.name.split('.')[0] not in ['bpy','city_mesh'] for v in node.names)
        if isinstance(node,ast.ImportFrom):assert (node.module or '').split('.')[-1] not in ['bpy','city_mesh']
    assert spec['baseBuildingIdsToExclude']==[]
    report.update(checks={'nondegenerateTriangleFans':True,'finiteVertices':True,'scaleOnceAndGameDatum':True,'sourceShiftCompensation':True,
     'frameRestoredSuccessAndFailure':True,'cpuBudget':True,'sourceWaysAndNodeOrder':True,'sampleSpacingAndHeightLookup':True,
     'estimatedProfileOptIn':True,'railRoadSourceNodeSeparated':True,'sourceEndpointGameHeightNotRescaled':True,
     'sharedSameDeckNodeAgreement':True,'fixedOuterBoundaryContinuation':True,'noWaterRoadTopXixingBoaoGeometry':True,'noSceneImports':True},
     profileCount=11,railProfileCount=1,profileCountWithOuterContinuations=15,sourceSharedSameDeckCases=shared_cases,
     railRoadSameNode={'node':'3351280499','separationGame':delta,'observedDatum':False},
     sourceModuleSha256=sha(source),specSha256=sha(sp),boundsGameENU={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]},
     validationScope='CPU FakeB/projection/source-chain/budget/interpolation only; not triangulated GLB, GPU, named visual/PBR, measured deck/water/terrain, collision, real driving/night or FPS.')
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');(HERE/'source-road-profile-preview.json').write_text(json.dumps({'waterDisplayGameY':lm['y'],'datum':'arbitrary CPU-test datum ONLY, not site measurement','profiles':ext,'railways':rail},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'triangles':report['triangleCountBeforeExport'],'materials':report['materials'],'perBridge':report['bridges'],'profiles':len(profiles)},ensure_ascii=False))
if __name__=='__main__':main()

"""Pure CPU geometry/dry-mask/projection; no safe traversal or GLB claim."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import math
import sys
from shapely.geometry import shape,Polygon,Point
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city,project
class FakeB:
    def __init__(self,fail_at=None):self.frame=(47,32,.78);self.faces=[];self.fail_at=fail_at
    def face(self,mat,points,uv=None):
        if self.fail_at is not None and len(self.faces)>=self.fail_at:raise RuntimeError('deliberate failure')
        x,y,a=self.frame;c,s=math.cos(a),math.sin(a);self.faces.append((mat,[(x+u*c-v*s,y+u*s+v*c,z) for u,v,z in points]))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verts(b):return [p for mat,points in b.faces for p in points]
def area3(a,b,c):
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)];w=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];return math.sqrt(sum(x*x for x in w))
def module(p,name):
    ms=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(ms);ms.loader.exec_module(m);return m
def main():
    source=ROOT/'scripts/landmarks/leifeng_site.py';sp=HERE/'spec.json';spec=json.loads(sp.read_text());city=load_city('hangzhou');a=spec['anchor'];x,z=project(a['lon'],a['lat'],city);lm={'x':x,'z':z,'lon':a['lon'],'lat':a['lat'],'y':1.7}
    m=module(source,'leifeng_site_cpu');b=FakeB();old=b.frame;report=m.build(b,lm,spec);assert old==b.frame;points=verts(b)
    assert all(math.isfinite(v) for p in points for v in p)
    minimum=math.inf
    for mat,p in b.faces:
        for i in range(1,len(p)-1):
            area=area3(p[0],p[i],p[i+1]);minimum=min(minimum,area);assert area>1e-11,(mat,p,area)
    assert sum(len(p)-2 for mat,p in b.faces)==report['triangleCountBeforeExport']<=spec['budget']['maxTriangles']
    assert len(report['materials'])<=spec['budget']['maxMaterials'] and report['candidateWaterPlanes']==0 and report['lightCount']==0
    assert report['staticApproach']['staticBeltCount']==2 and not report['staticApproach']['animationImplemented']
    small=FakeB();m.build(small,lm,spec,.3)
    for p,q in zip(points,verts(small)):
        for k,base in enumerate([x,z,lm['y']]):assert math.isclose(p[k]-base,2*(q[k]-base),abs_tol=1e-7)
    shifted=dict(lm,lon=a['lon']+.001,lat=a['lat']-.001);shifted['x'],shifted['z']=project(shifted['lon'],shifted['lat'],city);bs=FakeB();m.build(bs,shifted,spec)
    assert all(math.isclose(a,b,abs_tol=1e-7) for p,q in zip(points,verts(bs)) for a,b in zip(p,q))
    fail=FakeB(7);before=fail.frame
    try:m.build(fail,lm,spec)
    except RuntimeError:pass
    else:raise AssertionError('Expected FakeB failure')
    assert fail.frame==before and m.ground_footprints(lm,spec)==[]
    dry=shape(spec['landMaskLocalMetres']);wet=shape(spec['wetMaskLocalMetres']);area=0
    for patch in spec['terrainPatches']:
        poly=Polygon([p[:2] for p in patch['verticesMetresENU']]);assert dry.buffer(1e-7).covers(poly) and poly.intersection(wet).area<1e-8
        if patch['part']=='ground-estimate':area+=poly.area
    # Candidate source-only query cannot admit a lake point or invent missing edge.
    assert m.walk_surface(120.145,30.25,lm,spec,allow_estimated=True) is None
    for f in [m.walk_surface,m.walk_surfaces]:
        try:f(*( [a['lon'],a['lat'],lm,spec] if f is m.walk_surface else [lm,spec]))
        except ValueError:pass
        else:raise AssertionError('Estimated surfaces need explicit opt-in')
    rows=m.walk_surfaces(lm,spec,allow_estimated=True);assert rows and all(not r['traversalAccepted'] for r in rows)
    for r in rows:
        p=r['verticesGameENU'];q=[sum(v[k] for v in p)/3 for k in range(3)];lon=city['geography']['originWGS84'][0]+q[0]/(city['geography']['eastMetresPerDegree']*.6);lat=city['geography']['originWGS84'][1]+q[1]/(city['geography']['northMetresPerDegree']*.6)
        way=r['sourcePart'][5:] if r['sourcePart'].startswith('path-') else None;h=m.walk_surface(lon,lat,lm,spec,allow_estimated=True,source_way_id=way)
        assert h is not None
        # Different overlaid candidate ribbons may share XY; sourceway selection
        # is required rather than treating the crossing as a new source junction.
        if way is not None:assert math.isclose(h['heightGame'],q[2],abs_tol=1e-5)
    place=m.tower_placement(lm,spec);assert math.isclose(place['y'],lm['y']+spec['towerPlacement']['groundEstimateEgm2008M']*.6,abs_tol=1e-8) and not place['entranceAccepted']
    assert spec['sourceEntranceGap']['distanceToMappedTowerM']>14 and spec['sourceEntranceGap']['upperOtherSourceRoadIds']==[]
    assert sha(ROOT/'scripts/landmarks/leifeng_pagoda.py')==spec['towerPlacement']['frozenModuleSha256'];assert sha(ROOT/spec['towerPlacement']['frozenSpecPath'])==spec['towerPlacement']['frozenSpecSha256']
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node,ast.Import):assert all(v.name.split('.')[0] not in ['bpy','city_mesh'] for v in node.names)
        if isinstance(node,ast.ImportFrom):assert (node.module or '').split('.')[-1] not in ['bpy','city_mesh']
    # Retain latest threebridge15road contract results without changing that task.
    bridge_path=ROOT/'scripts/landmarks/qiantang_bridges.py';bm=module(bridge_path,'bridges_readonly_recheck');bsp=ROOT/'docs/hangzhou/research/core/qiantang-bridges-round2/spec.json';bspec=json.loads(bsp.read_text());profiles=bm.source_road_profiles(bspec,1.7,allow_estimated=True)
    assert len(profiles)==15 and all(r['status']=='candidate-estimated' and not r['navigationAccepted'] for r in profiles)
    fixed={f['id']:f for f in json.loads((ROOT/'docs/hangzhou/research/core/qiantang-bridges-round2/fixed-bridge-features.geojson').read_text())['features']}
    for r in profiles:assert r['nodeIds']==fixed[r['id']]['properties']['nodeIds'] and r['coordinatesWGS84']==fixed[r['id']]['geometry']['coordinates']
    (HERE/'bridge-profile-recheck.json').write_text(json.dumps({'readOnly':True,'sourceModuleSha256':sha(bridge_path),'specSha256':sha(bsp),'roadCount':15,'roadIds':[r['id'] for r in profiles],
      'fourOuterContinuations':['way/306360714','way/306360716','way/306360719','way/589558020'],'sourceNodeOrderAndWGSMatch':True,'estimatedStatusPreserved':True,'railwayMixedIntoRoads':False,'drivingAccepted':False},ensure_ascii=False,indent=2)+'\n')
    report.update(checks={'cpuBudget':True,'nondegenerateFiniteGeometry':True,'onceScaleAndGameVerticalDatum':True,'sourceShiftCompensation':True,'frameRestoredSuccessAndFailure':True,
      'sourceLandWaterDryClipping':True,'sourceOnlyWalkQueryAndEstimatedOptIn':True,'sourceEntranceGapNotJoined':True,'towerModuleAndSpecUntouched':True,'bridge15ProfilesReadonlyRechecked':True,'noWaterAndNoSceneImports':True},
      sourceModuleSha256=sha(source),specSha256=sha(sp),minimumTriangleCrossAreaGame=minimum,sourceDryTerrainAreaM2=area,
      boundsGameENU={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]},
      validationScope='CPU geometry/source masks/counts/queries only; mathematical dry mask is not proof of no-waterfalls/entrance/collision/actors/Blender/GLB/browser/visual/performance acceptance.')
    (HERE/'cpu-geometry-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'triangles':report['triangleCountBeforeExport'],'materials':report['materials'],'towerYGame':place['y'],'entranceGapM':report['sourceEntranceGapM'],'bridgesRoadsRechecked':15},ensure_ascii=False))
if __name__=='__main__':main()

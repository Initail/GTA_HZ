"""CPU-only source/structure regression checks; no Blender, browser or fake GLB."""
import ast
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
MODULE=ROOT/'scripts/landmarks/alibaba_b.py';sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def area(r):return abs(sum(x*v-u*y for (x,y),(u,v) in zip(r,r[1:]+r[:1]))/2)
def inside(p,r):
    x,y=p;hit=False
    for (a,b),(c,d) in zip(r,r[1:]+r[:1]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:hit=not hit
    return hit


def boundary_intersections(r):
    """Independent segment-parameter audit of complete generated boundaries."""
    def cross(p,q):return p[0]*q[1]-p[1]*q[0]
    result=[]
    for i,(a,b) in enumerate(zip(r,r[1:]+r[:1])):
        u=(b[0]-a[0],b[1]-a[1]);length=math.hypot(*u)
        assert length>.01,('collapsed boundary edge',i,length)
        for j in range(i+1,len(r)):
            if j==i+1 or (i==0 and j==len(r)-1):continue
            c,d=r[j],r[(j+1)%len(r)];v=(d[0]-c[0],d[1]-c[1]);w=(c[0]-a[0],c[1]-a[1]);den=cross(u,v)
            if abs(den)>1e-10:
                t,s=cross(w,v)/den,cross(w,u)/den
                if -1e-7<=t<=1+1e-7 and -1e-7<=s<=1+1e-7:result.append((i,j))
            elif abs(cross(w,u))<1e-7:
                t0=(w[0]*u[0]+w[1]*u[1])/(length*length)
                t1=((d[0]-a[0])*u[0]+(d[1]-a[1])*u[1])/(length*length)
                if max(0,min(t0,t1))<=min(1,max(t0,t1))+1e-7:result.append((i,j))
    return result


class Collector:
    def __init__(self,fault_after=None):self.frame=(7,11,.2);self.initial=self.frame;self.faces=[];self.fault_after=fault_after
    def face(self,material,points,uv=None):
        if self.fault_after is not None and len(self.faces)==self.fault_after:raise RuntimeError('deliberate receiver failure')
        x0,y0,a=self.frame;c,s=math.cos(a),math.sin(a)
        self.faces.append((material,[(x*c-y*s+x0,x*s+y*c+y0,z) for x,y,z in points]))


def main():
    spec=json.loads((HERE/'spec.json').read_text());evidence=ROOT/spec['evidencePath']
    assert sha(evidence)==spec['evidenceSha256'] and sha(ROOT/spec['sourceFootprintsPath'])==spec['sourceFootprintsSha256']
    # The parent owns shared city configuration and has changed unrelated task
    # points since this object was frozen. Keep the historical spec hash, and
    # check every geometry-relevant projection field against its frozen job.
    frozen=json.loads((HERE/'task/alibaba-b/job.json').read_text())['coordinatePolicy']
    current_geo=load_city('hangzhou')['geography']
    assert frozen['cityConfigSha256']==spec['coordinateConfigSha256']
    for k in ('originWGS84','projection','eastMetresPerDegree','northMetresPerDegree'):
        assert current_geo[k]==frozen[k],('shared projection changed',k)
    assert current_geo['crs']==frozen['sourceCRS'] and current_geo['scale']==frozen['horizontalScale']==frozen['verticalScale']
    config_check={'frozenWholeFileSha256':spec['coordinateConfigSha256'],'currentWholeFileSha256':sha(ROOT/'config/cities/hangzhou.json'),
                  'geometryRelevantFieldsEqual':True,'policy':'historical spec retained; all projection/scaling fields individually compared'}
    manifest=json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    assert manifest['source']['sha256']==spec['sourceSnapshotSha256'] and sha(ROOT/'data/processed/hangzhou/buildings.geojson')==manifest['sha256']['buildings']
    fixed=json.loads((ROOT/spec['sourceFootprintsPath']).read_text());fixed={f['id']:f for f in fixed['features']}
    allids={'way/'+str(n) for n in range(1363020721,1363020744)};excluded={'way/1363020741','way/1363020742'}
    assert set(fixed)==allids and set(spec['baseBuildingIdsToExclude'])==allids-excluded
    assert len(spec['objects'])==21 and len(spec['excludedSubscopeBlockers'])==2
    groupmap=json.loads((HERE/'object-groups.json').read_text());assert groupmap['physicalBuildingCount'].startswith('unknown')
    assert all(not o['excludeBase'] for o in groupmap['groups'] if o['sourceId'] in excluded)
    for o in spec['objects']:assert o['ringsWGS84']==fixed[o['sourceId']]['geometry']['coordinates'][0]
    matches=json.loads((HERE/'footprint-correspondence.json').read_text());assert len(matches['matches'])==23 and all(m['fixedPolygonMatchesAuxiliary']['allCoordinatesExact'] for m in matches['matches'])
    for n in ast.walk(ast.parse(MODULE.read_text())):
        if isinstance(n,ast.Import):assert all(a.name not in ('bpy','city_mesh','scripts.city_mesh') for a in n.names)
        if isinstance(n,ast.ImportFrom):assert n.module not in ('bpy','city_mesh','scripts.city_mesh')
    ref=importlib.util.spec_from_file_location('b_candidate',MODULE);mod=importlib.util.module_from_spec(ref);ref.loader.exec_module(mod)
    geo=load_city('hangzhou')['geography'];lon,lat=spec['anchor']['lon'],spec['anchor']['lat'];lm={'lon':lon,'lat':lat,'x':125,'z':-75,'y':4}
    c=Collector();report=mod.build(c,lm,spec,.6)
    assert c.frame==c.initial and report['triangleCountBeforeExport']==sum(len(ps)-2 for _,ps in c.faces)
    assert report['triangleCountBeforeExport']<=spec['budget']['maxTriangles'] and len(report['materials'])<=spec['budget']['maxMaterials']
    assert report['modeledSourceObjectCount']==21 and report['mainOfficeClusterCount']==2 and report['visitorCount']==1 and report['gardenRoofCount']==2
    assert report['gardenCellCount']>=8 and report['newLights']==0 and report['photoTextures']==0
    assert all(math.isfinite(v) for _,ps in c.faces for p in ps for v in p)
    vertices={tuple(round(v,5) for v in p[:2]) for _,ps in c.faces for p in ps}
    for obj in spec['objects']:
        for r in obj['ringsWGS84']:
            for lo,la in r:
                p=(round(125+(lo-lon)*geo['eastMetresPerDegree']*.6,5),round(-75+(la-lat)*geo['northMetresPerDegree']*.6,5));assert p in vertices,('source corner lost',obj['label'],p)
    full=Collector();mod.build(full,lm,spec,1)
    assert len(c.faces)==len(full.faces)
    for (_,ps),(_,qs) in zip(c.faces,full.faces):
        for p,q in zip(ps,qs):
            for k,origin in enumerate((125,-75,4)):assert math.isclose(p[k]-origin,(q[k]-origin)*.6,rel_tol=1e-9,abs_tol=1e-8)
    shifted=dict(lm,lon=lon+.001,lat=lat-.001,x=125+geo['eastMetresPerDegree']*.001*.6,z=-75-geo['northMetresPerDegree']*.001*.6)
    moved=Collector();mod.build(moved,shifted,spec,.6)
    for (_,ps),(_,qs) in zip(c.faces,moved.faces):assert all(math.dist(p,q)<1e-6 for p,q in zip(ps,qs))
    failed=Collector(9)
    try:mod.build(failed,lm,spec,.6);raise AssertionError('Receiver fault swallowed')
    except RuntimeError:assert failed.frame==failed.initial
    ctx=mod._context(lm,spec);collisions=mod.ground_footprints(lm,spec,.6);areas=[];insets=[];probes=[];occluded=0;raw_regressions=[];expected_collision_area=0
    for i,r in enumerate(collisions):
        assert not boundary_intersections(r),('self-intersecting full collision ring',i)
        assert area(r)>.01,('tiny artificial collision fragment',i,area(r))
    def game(p):return 125+p[0]*.6,-75+p[1]*.6
    for obj,rs in ctx['objects']:
        exactarea=area(rs[0])-sum(area(r) for r in rs[1:]);bandarea=sum(area(r) for r in mod._bands(rs))
        assert math.isclose(exactarea,bandarea,rel_tol=1e-8,abs_tol=1e-6)
        areas.append({'sourceId':obj['sourceId'],'mappedAreaM2':exactarea,'candidateRoofFillAreaM2':bandarea})
        if obj['kind']=='office-arm':
            inner,effective=mod._inset_with_distance(rs[0],spec['facade']['groundInsetM'])
            assert not boundary_intersections(inner),('inset boundary crosses',obj['sourceId'])
            assert all(inside(p,rs[0]) for p in inner) and area(inner)<area(rs[0])
            assert math.isclose(sum(area(r) for r in mod._bands([inner])),area(inner),rel_tol=1e-8,abs_tol=1e-6)
            expected_collision_area+=area(inner)*.36
            raw=mod._miter(rs[0],spec['facade']['groundInsetM'])
            raw_hits=boundary_intersections(raw) if raw else []
            if raw_hits:
                raw_regressions.append({'sourceId':obj['sourceId'],'formerRequestedInsetM':spec['facade']['groundInsetM'],'formerCrossingEdges':raw_hits,
                    'effectiveEstimatedInsetM':effective,'correctedAreaM2':area(inner),'marginMethod':'feasible topology interval less4cm; no make_valid/delete-cells'})
            insets.append({'sourceId':obj['sourceId'],'sourceAreaM2':area(rs[0]),'estimatedGroundAreaM2':area(inner),
                           'requestedInsetM':spec['facade']['groundInsetM'],'effectiveInsetM':effective})
        if obj['kind'] in ('visitor','garden-roof'):expected_collision_area+=exactarea*.36
        expected_collision_area+=len(mod._supports(obj,rs[0],spec))*spec['facade']['columnSideM']**2*.36
        if obj['kind']=='junction':
            p=game(mod._center(rs[0]));assert not any(inside(p,r) for r in collisions),('elevated junction blocked at ground',obj['label'])
            probes.append({'kind':'junction-underpass','sourceId':obj['sourceId'],'game':p})
        if obj['kind']=='garden-roof':
            for hexagon,tri in mod._garden_cells(obj,rs[0],spec):
                assert all(inside(p,rs[0]) for p in hexagon)
                assert all(inside(p,hexagon) for p in tri)
                greenarea=sum(area(r) for r in mod._bands([hexagon,tri]))
                assert math.isclose(greenarea,area(hexagon)-area(tri),rel_tol=1e-8,abs_tol=1e-6)
        for p,q in mod._split_edges(rs[0],ctx):
            if obj['kind']=='garden-roof':continue
            intervals=mod._visible_intervals(obj,p,q,ctx)
            if sum(b-a for a,b in intervals)<obj['height']['value']-.7-obj['bodyBottomM']-.1:occluded+=1
    assert occluded>=4,'adjacent arms not suppressing coplanar internal facades'
    assert {r['sourceId'] for r in raw_regressions}=={'way/1363020727','way/1363020734'},'reported two original bow ties not reproduced'
    assert math.isclose(sum(area(r) for r in collisions),expected_collision_area,rel_tol=1e-8,abs_tol=1e-5),'collision area discarded or extra solid added'
    # Open northern west hexagonal courtyard is a source concavity, not one
    # giant office box. Its mapped centre is verified outside all occupied
    # source outlines, then checked against candidate roof and collision.
    obj,rs=next((o,rs) for o,rs in ctx['objects'] if o['label']=='west-north-folded-arm')
    courtyard=mod._center(rs[0]);assert not inside(courtyard,rs[0])
    assert not any(inside(game(courtyard),r) for r in collisions),'concave courtyard collision filled'
    roofs=[[(p[0],p[1]) for p in ps] for mat,ps in c.faces if mat=='roof' and len({round(p[2],5) for p in ps})==1]
    assert not any(inside(game(courtyard),r) for r in roofs),'concave courtyard roof filled'
    probes.append({'kind':'northwest-source-courtyard','game':game(courtyard)})
    assert max(o['height']['value'] for o in spec['objects'])<45 and len(set(o['height']['value'] for o in spec['objects']))>=5
    assert all(o['height']['basis']=='estimated' and o['height']['errorPlusMinusM']>=2 for o in spec['objects'])
    result={'checkedAt':'2026-10-14','scope':'CPU/source finite exterior only; no GLB, scene, browser, full navigation or visual/performance acceptance',
        'sourceModule':str(MODULE.relative_to(ROOT)),'sourceModuleSha256':sha(MODULE),'specSha256':sha(HERE/'spec.json'),'evidenceSha256':sha(evidence),
        'checks':{'exact23SourceAnd21ExclusionCorrespondence':True,'centralRoofAndHistoricalBlockersRetained':True,
            'finiteGeometryAndAllModeledCorners':True,'noSceneImportOrExport':True,'singleScaleGameHeightProjection':True,
            'frameRestorationOnSuccessAndError':True,'sourceConcaveRoofAreaAndCourtyardVoid':True,
            'estimatedGroundInsetContained':True,'elevatedJunctionGroundUnderpasses':True,'gardenHexesAndTriangleVoidContained':True,
            'coplanarInternalFacadeSuppression':True,'individualEstimatedHeightsNo80mCopy':True,'triangleMaterialBudget':True,
            'allCollisionBoundaryRingsSimpleAndNondegenerate':True,'reportedTwoInsetBowTiesReproducedAndCorrected':True,
            'completeCollisionAreaPreservedNoDeletedSlivers':True,'lowerBodyInsetAndCollisionShareSameValidBoundary':True,
            'frozenCoordinatePolicyStillMatchesSharedProjection':True},
        'report':report,'collisionPolygonCount':len(collisions),'roofAreaChecks':areas,'estimatedGroundInsetChecks':insets,
        'sourceConfigComparison':config_check,'sourceInsetRegressions':raw_regressions,
        'minCollisionAreaGameM2':min(area(r) for r in collisions),'totalCollisionAreaGameM2':sum(area(r) for r in collisions),
        'sharedOccludedEdgeFragments':occluded,'probes':probes,
        'limitations':['ground plans/pilotis/doors are bounded estimates, not surveyed footprints',
            'closed low green-roof rooms are exterior candidates; exact glazing/door access needs review',
            'gold shared material approximates orange shades; final PBR colour/night unverified',
            'central0741/0742 not replaced; complete B campus remains unfinished',
            'CPU painter images are not actual GLB/game screenshots, no measured FPS/bytes/memory']}
    (HERE/'cpu-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks':result['checks'],'triangles':report['triangleCountBeforeExport'],'materials':report['materials'],'gardenCells':report['gardenCellCount'],'suppressedFacadeFragments':occluded},ensure_ascii=False))


if __name__=='__main__':main()

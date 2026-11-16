"""Source/CPU checks for currentA finite candidate, not Blender/game acceptance."""
import ast
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];MODULE=ROOT/'scripts/landmarks/alibaba_a.py'
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def area(r):return abs(sum(x*v-u*y for (x,y),(u,v) in zip(r,r[1:]+r[:1]))/2)
def inside(p,r):
    x,y=p;hit=False
    for (a,b),(c,d) in zip(r,r[1:]+r[:1]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:hit=not hit
    return hit


class Collector:
    def __init__(self,fault_after=None):self.frame=(7,11,.2);self.initial=self.frame;self.faces=[];self.fault_after=fault_after
    def face(self,material,points,uv=None):
        if self.fault_after is not None and len(self.faces)==self.fault_after:raise RuntimeError('deliberate receiver failure')
        x0,y0,a=self.frame;c,s=math.cos(a),math.sin(a)
        self.faces.append((material,[(x*c-y*s+x0,x*s+y*c+y0,z) for x,y,z in points]))


def main():
    spec=json.loads((HERE/'spec.json').read_text());evidence=ROOT/spec['evidencePath']
    assert sha(evidence)==spec['evidenceSha256'] and sha(ROOT/spec['sourceFootprintsPath'])==spec['sourceFootprintsSha256']
    assert sha(ROOT/'config/cities/hangzhou.json')==spec['coordinateConfigSha256']
    manifest=json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    assert manifest['source']['sha256']==spec['sourceSnapshotSha256'] and sha(ROOT/'data/processed/hangzhou/buildings.geojson')==manifest['sha256']['buildings']
    source=json.loads((ROOT/spec['sourceFootprintsPath']).read_text());source={f['id']:f for f in source['features']}
    excluded={'way/456731145'};assert set(spec['baseBuildingIdsToExclude'])==set(source)-excluded and len(source)==13
    assert len(spec['objects'])==12 and len(spec['excludedSubscopeBlockers'])==3
    assert all(o['phase'] is None and o['historicalUnitNumber'] is None for o in spec['objects'])
    assert sorted(o['label'] for o in spec['objects'] if o['kind']=='office')==['A1','A2','A3','A4','A5','A6','A7','A8']
    for o in spec['objects']:assert o['ringsWGS84']==source[o['sourceId']]['geometry']['coordinates'][0]
    matches=json.loads((HERE/'footprint-correspondence.json').read_text());assert len(matches['matches'])==13 and all(m['allCoordinatesExact'] for obj in matches['matches'] for m in obj['outerAndInnerRingMatches'])
    for n in ast.walk(ast.parse(MODULE.read_text())):
        if isinstance(n,ast.Import):assert all(a.name not in ('bpy','city_mesh','scripts.city_mesh') for a in n.names)
        if isinstance(n,ast.ImportFrom):assert n.module not in ('bpy','city_mesh','scripts.city_mesh')
    ref=importlib.util.spec_from_file_location('a_candidate',MODULE);mod=importlib.util.module_from_spec(ref);ref.loader.exec_module(mod)
    geo=load_city('hangzhou')['geography'];lon,lat=spec['anchor']['lon'],spec['anchor']['lat'];lm={'lon':lon,'lat':lat,'x':125,'z':-75,'y':4}
    c=Collector();report=mod.build(c,lm,spec,.6);assert c.frame==c.initial
    assert report['triangleCountBeforeExport']==sum(len(ps)-2 for _,ps in c.faces)<=spec['budget']['maxTriangles']
    assert len(report['materials'])<=spec['budget']['maxMaterials'] and report['modeledSourceObjects']==12
    assert report['mappedOfficeObjects']==8 and report['mappedLinkObjects']==4 and report['sourceHoleCount']==11
    assert report['linkLatticeCrossStrandCount']>=1000 and report['linkTrussBayCount']>=100
    assert report['photoTextures']==0 and report['newLights']==0 and all(math.isfinite(v) for _,ps in c.faces for p in ps for v in p)
    vertices={tuple(round(v,5) for v in p[:2]) for _,ps in c.faces for p in ps}
    for obj in spec['objects']:
        for r in obj['ringsWGS84']:
            for lo,la in r:
                p=(round(125+(lo-lon)*geo['eastMetresPerDegree']*.6,5),round(-75+(la-lat)*geo['northMetresPerDegree']*.6,5));assert p in vertices,('sourcecornerlost',obj['sourceId'],p)
    full=Collector();mod.build(full,lm,spec,1);assert len(c.faces)==len(full.faces)
    for (_,ps),(_,qs) in zip(c.faces,full.faces):
        for p,q in zip(ps,qs):
            for k,origin in enumerate((125,-75,4)):assert math.isclose(p[k]-origin,(q[k]-origin)*.6,rel_tol=1e-9,abs_tol=1e-8)
    shifted=dict(lm,lon=lon+.001,lat=lat-.001,x=125+geo['eastMetresPerDegree']*.001*.6,z=-75-geo['northMetresPerDegree']*.001*.6)
    moved=Collector();mod.build(moved,shifted,spec,.6)
    for (_,ps),(_,qs) in zip(c.faces,moved.faces):assert all(math.dist(p,q)<1e-6 for p,q in zip(ps,qs))
    failed=Collector(9)
    try:mod.build(failed,lm,spec,.6);raise AssertionError('Receiverfaultswallowed')
    except RuntimeError:assert failed.frame==failed.initial
    ctx=mod._context(lm,spec);collisions=mod.ground_footprints(lm,spec,.6);probes=[];areas=[];stripes=[];suppressed=0
    def game(p):return 125+p[0]*.6,-75+p[1]*.6
    roofs=[[(p[0],p[1]) for p in ps] for mat,ps in c.faces if mat=='roof' and len({round(p[2],5) for p in ps})==1]
    for obj,rs in ctx['objects']:
        exact=area(rs[0])-sum(area(r) for r in rs[1:]);filled=sum(area(r) for r in mod._bands(rs));assert math.isclose(exact,filled,rel_tol=1e-8,abs_tol=1e-6)
        areas.append({'sourceId':obj['sourceId'],'sourceOccupiedAreaM2':exact,'candidateBandAreaM2':filled})
        for r in rs[1:]:
            p=mod._center(r);assert inside(p,r)
            assert not any(inside(game(p),f) for f in roofs),('opaque roofcapsourcehole',obj['label'])
            assert not any(inside(game(p),r) for r in collisions),('groundcollidersourcehole',obj['label'])
            probes.append({'kind':'mappedhole','sourceId':obj['sourceId'],'game':game(p)})
        if obj['kind']=='link':
            for a,b in zip(rs[0],rs[0][1:]+rs[0][:1]):
                if math.dist(a,b)>12:
                    p=mod._mix(a,b,.5);centre=mod._center(rs[0]);p=mod._mix(p,centre,.04)
                    if inside(p,rs[0]) and not any(inside(p,h) for h in rs[1:]) and not any(inside(game(p),c) for c in collisions):
                        probes.append({'kind':'link-underpass','sourceId':obj['sourceId'],'game':game(p)});break
        if obj['kind']=='office' and len(rs)==1:
            slit=mod._rooflight(obj,rs[0],spec)
            if slit:
                assert all(inside(p,rs[0]) for p in slit)
                p=mod._center(slit)
                assert any(inside(game(p),r) for r in collisions),'estimatedrooflight createsfictitiousgroundhole'
                assert not any(inside(game(p),f) for f in roofs),'estimatedglassstrip opaque-capped'
                stripes.append(obj['sourceId'])
        for a,b in mod._split_edges(rs[0],ctx):
            intervals=mod._visible_intervals(obj,a,b,ctx)
            if sum(hi-lo for lo,hi in intervals)<obj['height']['value']-.7-obj['bodyBottomM']-.1:suppressed+=1
    assert len([p for p in probes if p['kind']=='link-underpass'])==4
    assert len(stripes)>=2 and suppressed>=2
    assert all(o['height']['basis']=='estimated' and o['height']['errorPlusMinusM']>=4 for o in spec['objects'])
    assert max(o['height']['value'] for o in spec['objects'])<35
    result={'checkedAt':'2026-10-14','scope':'FiniteCPU/source candidate checks, noactualGLB/GPU/browser/navigation/visual/performanceacceptance',
        'sourceModule':str(MODULE.relative_to(ROOT)),'sourceModuleSha256':sha(MODULE),'specSha256':sha(HERE/'spec.json'),'evidenceSha256':sha(evidence),
        'checks':{'exact13SourceAnd12ExclusionCorrespondence':True,'A9HistoricalUnitsFullNetworkBlockersRetained':True,
            'finiteGeometryAllModeledCorners':True,'noSceneImportOrExport':True,'singleScaleGameHeightProjection':True,
            'frameRestoredOnSuccessAndError':True,'sourceHoleRoofAndGroundVoids':True,'concaveSourceFillArea':True,
            'estimatedGlassRoofStripeDoesNotCutGround':True,'fourLinkGroundUnderpassProbes':True,
            'sourceSharedFaceSuppression':True,'individualEstimatedHeightsNoUniform7FOr80m':True,'triangleMaterialBudget':True},
        'report':report,'collisionPolygonCount':len(collisions),'sourcePlanAreaChecks':areas,'probes':probes,
        'estimatedGlassRoofSourceIds':stripes,'sharedOccludedEdgeFragments':suppressed,
        'limitations':['A9/completehistoricalphase/currentnumber mapping/fullbridgefunctions remainblockers',
            'grounddoors/rooffacts/multilevelterrain/actualcolumnclearance unverified',
            'coarsewovenmesh isgeometrysampling, notfullyreproducedstranddensity orcolour',
            'referencephotocapturedateandexacteachfacegeolocationunknown; allsidePBR/nightnotaccepted',
            'CPUpreviews arepaintergraphics, not exportedGLB/game screenshots; noactualFPS/GLBbytes/memory']}
    (HERE/'cpu-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks':result['checks'],'triangles':report['triangleCountBeforeExport'],'materials':report['materials'],'holes':report['sourceHoleCount'],'collisionPolygons':len(collisions)},ensure_ascii=False))


if __name__=='__main__':main()

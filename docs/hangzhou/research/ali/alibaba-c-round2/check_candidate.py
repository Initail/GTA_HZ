"""Independent source/CPU checks; no GLB, Blender, browser or terrain acceptance."""
import ast
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
MODULE=ROOT/'scripts/landmarks/alibaba_c.py'
sys.path.insert(0,str(ROOT/'scripts'))
from city_config import load_city


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


class Collector:
    def __init__(self,fault_after=None):
        self.frame=(7,11,.2);self.initial=self.frame;self.faces=[];self.fault_after=fault_after
    def face(self,material,points,uv=None):
        if self.fault_after is not None and len(self.faces)==self.fault_after:raise RuntimeError('deliberate receiver failure')
        x0,y0,a=self.frame;c,s=math.cos(a),math.sin(a)
        self.faces.append((material,[(x*c-y*s+x0,x*s+y*c+y0,z) for x,y,z in points]))


def inside(p,r):
    x,y=p;hit=False
    for (a,b),(c,d) in zip(r,r[1:]+r[:1]):
        if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:hit=not hit
    return hit


def area(r):return abs(sum(x*v-u*y for (x,y),(u,v) in zip(r,r[1:]+r[:1]))/2)


def main():
    spec=json.loads((HERE/'spec.json').read_text());evidence=ROOT/spec['evidencePath']
    assert sha(evidence)==spec['evidenceSha256']
    assert sha(ROOT/spec['sourceFootprintsPath'])==spec['sourceFootprintsSha256']
    assert sha(ROOT/'config/cities/hangzhou.json')==spec['coordinateConfigSha256']
    manifest=json.loads((ROOT/'data/processed/hangzhou/extraction-manifest.json').read_text())
    assert manifest['source']['sha256']==spec['sourceSnapshotSha256']
    assert sha(ROOT/'data/processed/hangzhou/buildings.geojson')==manifest['sha256']['buildings']
    fixed=json.loads((ROOT/spec['sourceFootprintsPath']).read_text());source={f['id']:f for f in fixed['features']}
    expected={'relation/'+str(n) for n in range(18754982,18754988)}|{'way/1363020716','way/1363020718'}
    assert set(spec['baseBuildingIdsToExclude'])==expected==set(source)
    for obj in spec['buildings']+[spec['mediaRoof']]:
        assert obj['ringsWGS84']==source[obj['sourceId']]['geometry']['coordinates'][0]
    matches=json.loads((HERE/'footprint-correspondence.json').read_text())
    assert len(matches['matches'])==8 and all(r['allCoordinatesExact'] for f in matches['matches'] for r in f['outerAndInnerRingMatches'])
    tree=ast.parse(MODULE.read_text())
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):assert all(a.name not in ('bpy','city_mesh','scripts.city_mesh') for a in n.names)
        if isinstance(n,ast.ImportFrom):assert n.module not in ('bpy','city_mesh','scripts.city_mesh')
    ref=importlib.util.spec_from_file_location('c_candidate',MODULE);mod=importlib.util.module_from_spec(ref);ref.loader.exec_module(mod)
    geo=load_city('hangzhou')['geography'];lon,lat=spec['anchor']['lon'],spec['anchor']['lat']
    lm={'lon':lon,'lat':lat,'x':125,'z':-75,'y':4};c=Collector();report=mod.build(c,lm,spec,.6)
    assert c.frame==c.initial and report['triangleCountBeforeExport']==sum(len(p)-2 for _,p in c.faces)
    assert report['triangleCountBeforeExport']<=spec['budget']['maxTriangles']
    assert len(report['materials'])<=spec['budget']['maxMaterials']
    assert report['officeCount']==6 and report['visitorCount']==1 and report['sourceAtriumCount']==6 and report['bridgeCount']==6
    assert report['photoTextures']==0 and report['newLights']==0
    assert all(math.isfinite(v) for _,ps in c.faces for p in ps for v in p)
    vertices={tuple(round(v,5) for v in p[:2]) for _,ps in c.faces for p in ps}
    for obj in spec['buildings']+[spec['mediaRoof']]:
        for r in obj['ringsWGS84']:
            for lo,la in r:
                expectedp=(round(125+(lo-lon)*geo['eastMetresPerDegree']*.6,5),round(-75+(la-lat)*geo['northMetresPerDegree']*.6,5))
                assert expectedp in vertices,('source corner lost',obj['sourceId'],expectedp)
    full=Collector();mod.build(full,lm,spec,1)
    for (_,ps),(_,qs) in zip(c.faces,full.faces):
        for p,q in zip(ps,qs):
            for k,origin in enumerate((125,-75,4)):
                assert math.isclose(p[k]-origin,(q[k]-origin)*.6,rel_tol=1e-9,abs_tol=1e-8)
    shifted=dict(lm,lon=lon+.001,lat=lat-.001,x=125+geo['eastMetresPerDegree']*.001*.6,z=-75-geo['northMetresPerDegree']*.001*.6)
    moved=Collector();mod.build(moved,shifted,spec,.6)
    for (_,ps),(_,qs) in zip(c.faces,moved.faces):assert all(math.dist(p,q)<1e-6 for p,q in zip(ps,qs))
    failed=Collector(9)
    try:
        mod.build(failed,lm,spec,.6);raise AssertionError('Receiver failure swallowed')
    except RuntimeError:assert failed.frame==failed.initial
    ctx=mod._context(lm,spec);collisions=mod.ground_footprints(lm,spec,.6)
    probes=[];area_checks=[]
    def game(p):return 125+p[0]*.6,-75+p[1]*.6
    roof_faces=[[(p[0],p[1]) for p in ps] for mat,ps in c.faces if mat=='roof' and len({round(p[2],5) for p in ps})==1]
    for obj,rs in ctx['buildings']:
        plan_area=area(rs[0])-sum(area(r) for r in rs[1:]);bands=list(mod._bands(rs));filled=sum(area(r) for r in bands)
        assert math.isclose(plan_area,filled,rel_tol=1e-8,abs_tol=1e-6),('concave/holed fill area wrong',obj['label'])
        area_checks.append({'label':obj['label'],'sourcePlanAreaM2':plan_area,'collisionBandAreaM2':filled})
        for r in rs[1:]:
            p=game(mod._center(r));assert not any(inside(p,c) for c in collisions),'atrium blocked'
            assert not any(inside(p,f) for f in roof_faces),'opaque roof caps atrium'
            probes.append({'kind':'atrium-void','label':obj['label'],'game':p})
    garden=game((0,0));assert not any(inside(garden,r) for r in collisions),'whole campus collision proxy'
    # Source visitor shape is concave. Use a geometric notch probe where its
    # convex hull would be filled, independent of estimated portal accent.
    visitor=next(rs[0] for o,rs in ctx['buildings'] if o['label']=='访客中心')
    notch=mod._mix(visitor[1],visitor[2],.5)
    centre=mod._center(visitor);probe=mod._mix(notch,centre,.03)
    if inside(probe,visitor):probe=mod._mix(notch,centre,-.03)
    assert not inside(probe,visitor)
    assert not any(inside(game(probe),r) for r in collisions),'visitor mapped notch blocked'
    probes.append({'kind':'visitor-mapped-notch','game':game(probe)})
    # Elevated links are separated from the ground collision domain. At least
    # one midpoint per external span remains a true open underpass probe.
    for left,right,a,b,r in mod.bridge_segments(ctx,spec):
        p=game(mod._mix(a,b,.5));assert not any(inside(p,c) for c in collisions),('bridge ground blockage',left,right)
        probes.append({'kind':'bridge-underpass','link':left+'-'+right,'game':p})
    # Long roof is not a tall solid, and supports do not become a parcel bbox.
    roof=ctx['roof'][0];a,b=max(zip(roof,roof[1:]+roof[:1]),key=lambda e:math.dist(*e))
    roofprobes=[game(mod._mix(a,b,t)) for t in (.18,.37,.59,.77)]
    assert any(not any(inside(p,r) for r in collisions) for p in roofprobes),'Media Roof treated as ground wall'
    assert len(set(o['height']['value'] for o in spec['buildings'] if o['label']!='访客中心'))>3
    assert all(o['height']['basis']=='estimated' and o['height']['errorPlusMinusM']>=8 for o in spec['buildings'])
    result={'checkedAt':'2026-10-13','scope':'CPU/source candidate checks only; not actual GLB/GPU/terrain/driving/visual validation',
        'sourceModule':str(MODULE.relative_to(ROOT)),'sourceModuleSha256':sha(MODULE),'specSha256':sha(HERE/'spec.json'),'evidenceSha256':sha(evidence),
        'checks':{'eightExactExclusionFootprints':True,'allOuterInnerSourceCornersRetained':True,
            'fixedGeofabrikAndAuxiliaryHashes':True,'finiteGeometry':True,'triangleMaterialBudget':True,
            'singleScaleGameHeightAndOffsetProjection':True,'frameRestoredOnSuccessAndError':True,
            'sixAtriumCollisionAndOpaqueRoofVoids':True,'concaveVisitorNotchAndPlanArea':True,
            'elevatedBridgeAndMediaRoofUnderpasses':True,'noWholeCampusCollider':True,
            'individualEstimatedHeights':True,'noSceneImportExportOrPhotoTextures':True},
        'report':report,'collisionPolygonCount':len(collisions),'planAreaChecks':area_checks,'probes':probes,
        'limitations':['finite CPU probes do not prove all collision/door/navigation paths',
            'source OSM layer2 is not physical deck elevation','ground datum and multilevel podium remain unmeasured',
            'scheme roof/link/facade abstractions need actual GLB three-view visual checks','no FPS, GLB bytes or GPU material result']}
    (HERE/'cpu-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'checks':result['checks'],'triangles':report['triangleCountBeforeExport'],'materials':report['materials'],'colliderCount':len(collisions)},ensure_ascii=False))


if __name__=='__main__':main()

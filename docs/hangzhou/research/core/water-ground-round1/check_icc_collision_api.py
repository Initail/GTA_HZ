"""Check added ICC collision API without changing earlier evidence packages."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from shapely.geometry import Point,Polygon
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    helper=ROOT/'docs/hangzhou/research/core/international-conference-center-round2/validate_cpu.py'
    hs=importlib.util.spec_from_file_location('icc_cpu_readonly',helper);h=importlib.util.module_from_spec(hs);hs.loader.exec_module(h)
    spec,module,mod=h.load();b=h.BRecorder();mod.build(b,{'x':0,'z':0,'y':0},spec,.6)
    baseline=json.loads((OUT/'icc-before-api.json').read_text());stream=hashlib.sha256(json.dumps(b.faces,separators=(',',':')).encode()).hexdigest()
    assert stream==baseline['meshFaceStreamSha256'] and len(b.faces)==baseline['faces'],'ICC rendering geometry changed'
    assert digest(ROOT/'docs/hangzhou/research/core/international-conference-center-round2/spec.json')==baseline['specSha256'],'ICC scope/spec changed'
    lm={'x':123,'z':-456,'y':13.25};footprints=mod.ground_footprints(lm,spec,.6)
    minimum=math.inf;bykind={}
    for f in footprints:
        ring=f['polygonGame'];poly=Polygon(ring)
        assert poly.is_valid and poly.area>=.01,(f['kind'],poly.area)
        assert all(math.isfinite(v) for p in ring for v in p) and all(len(p)==2 for p in ring)
        assert f['maxYGame']>f['minYGame'] and f['minYGame']==lm['y']
        assert f['sourceFeatureIds'] and 'unconfirmed' in f['entryStatus']
        minimum=min(minimum,poly.area);bykind[f['kind']]=bykind.get(f['kind'],0)+1
    assert not any(Polygon(f['polygonGame']).covers(Point(lm['x'],lm['z'])) for f in footprints),'whole globe disk replaced interior'
    delta=(23,-45,7);moved=mod.ground_footprints({'x':lm['x']+delta[0],'z':lm['z']+delta[1],'y':lm['y']+delta[2]},spec,.6)
    for a,c in zip(footprints,moved):
        for p,q in zip(a['polygonGame'],c['polygonGame']):assert max(abs(q[i]-p[i]-delta[i]) for i in [0,1])<1e-8
        assert abs(c['minYGame']-a['minYGame']-7)<1e-8 and abs(c['maxYGame']-a['maxYGame']-7)<1e-8
    try:mod.ground_footprints(lm,spec,.36)
    except ValueError:pass
    else:raise AssertionError('collision double scaling accepted')
    a=spec['axisRadiansEastCCW'];ca,sa=math.cos(a),math.sin(a);front=spec['glazedFaceRelativeRadians']
    for theta in [front,front+math.pi]:
        r=mod.radial_boundary_metres(spec['outerPodiumUVMetres'],theta);u,v=r*math.cos(theta),r*math.sin(theta)
        p=Point(lm['x']+(u*ca-v*sa)*.6,lm['z']+(u*sa+v*ca)*.6)
        assert not any(Polygon(f['polygonGame']).covers(p) for f in footprints if f['kind']=='podium-outer-skin'),'podium entry gap was filled'
    result={'status':'passed-host-contract-only','sourceModuleBeforeSha256':baseline['sourceModuleBeforeSha256'],
      'sourceModuleAfterSha256':digest(module),'sourceSpecSha256':baseline['specSha256'],
      'renderingGeometryChanged':False,'meshFaceStreamSha256':stream,'faces':len(b.faces),
      'groundFootprints':len(footprints),'byKind':bykind,'minimumAreaGameUnits2':minimum,
      'checks':['all polygon rings implicitly closed/simple/finite; area>=.01 integration contract',
        'base gameY/explicit vertical bounds/translated coordinates','reject repeated .60 scale',
        'no whole globe ground disk or filled roof annulus','front/rear podium outer gaps retained',
        'prior spec/scope untouched','B rendering face stream exactly unchanged'],
      'limitations':['Real doors/entrance and site datum not verified. Current candidate lobby/entry glass walls have no actual door cutouts.',
        'Thin collision skins estimate. Sloping entry walls use conservative maximum endpoint bounds; not exact height-aware roof intersection.']}
    (OUT/'icc-collision-api-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()

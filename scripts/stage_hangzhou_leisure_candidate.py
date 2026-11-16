"""Freeze the v14 integration packet without publishing an unvalidated demo."""
import hashlib,json,shutil
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'artifacts/cities/hangzhou/city-leisure-v14'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    out=C/'integration-checkpoint-v1.json'
    if out.exists():raise SystemExit('Existing checkpoint is protected')
    tests={'phase-one-v2':210,'mode-camera-tests-v2':30,'actual-world-data-v3':7,'session-tests-v2':9,'leisure-rules-v1':13,'bus-tests-v3':7}
    checks={}
    for name,count in tests.items():
        path=C/(name+'.json');r=json.loads(path.read_text())
        assert r['exitCode']==0 and r['stopped'] is None and f'pass {count}' in r['output'] and 'fail 0' in r['output']
        checks[name]={'sha256':sha(path),'passedTests':count,'scope':'offline; bus tests cover uninstalled subsystem'}
    bundle=json.loads((C/'bundle-v2.json').read_text());assert bundle['exitCode']==0 and bundle['stopped'] is None
    # These are private staging copies, never the user's accepted v12/v13.
    archive=C/'pre-v14-shell';assert not archive.exists();shutil.copytree(C/'dist',archive)
    shutil.copytree(C/'public',C/'dist',dirs_exist_ok=True)
    for name in ['main.js','main.css']:shutil.copy2(C/'build-v2'/name,C/'dist/assets'/name)
    index=C/'dist/index.html';text=index.read_text().replace('v13 骑行试玩','v14 主城休闲候选').replace('杭州体验版 v12 · 西湖碰撞候选','杭州 v14 · 主城休闲集成候选');index.write_text(text)
    surface=C/'dist/cities/hangzhou/geography/site-surfaces.json';geo=C/'dist/cities/hangzhou/geography/manifest.json';detail=C/'dist/cities/hangzhou/landmark-detail.json'
    assert json.loads(geo.read_text())['siteSurfacesSha256']==sha(surface)
    assert json.loads(detail.read_text())['terrain']['manifestSha256']==sha(geo)
    landscape=C/'dist/cities/hangzhou/landscape';roots=json.loads((landscape/'canopy-root-heights.json').read_text());manifest=json.loads((landscape/'canopy/manifest.json').read_text())
    assert roots['plantingSha256']==sha(landscape/'canopy-trees.json')
    assert manifest['rootHeightOverrides']['sha256']==sha(landscape/'canopy-root-heights.json')
    sources={str(p.relative_to(C)):sha(p) for p in sorted((C/'src').rglob('*')) if p.is_file()}
    overlays={str(p.relative_to(C)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted((C/'dist').rglob('*')) if p.is_file()}
    result={'schemaVersion':1,'id':'demo-v14-main-city-leisure-candidate','createdAtUTC':datetime.now(timezone.utc).isoformat(),'parentCandidate':'westlake-bicycle-v1','fallbackAssets':'demo-v10/dist; same fallback as frozen v13; not copied or modified','sourceFiles':sources,'stagedOverlays':overlays,'checks':checks,'bundleReportSha256':sha(C/'bundle-v2.json'),'terrainAndCanopyBindings':True,'sourceImplemented':['main-city boat and fishing adapters','two prototype role-specific NPCs','dry source-node walking route to estimated game dock','Bai canopy v3 placements, root heights and triangle camera guard'],'notInstalled':['bus route/runtime rendering','west-lake-context-batched-v2','lingyin-context-batched-v1'],'releaseGate':{'formalNpmBuild':False,'fullRenderTypecheck':False,'browser':False,'visual':False,'resourceBudget':False,'publicPreviewReady':False},'blockers':['Full Babylon type graph exceeds fixed offline memory budget; partial pure modules passed. Alternate JSC attempts remain failures.','Previous whole-city loading exceeded browser resource gate. Current v14 has not been loaded in a browser.','Boat/fishing people and animations remain intermediate visual quality; no final landmark acceptance.'],'status':'staged integration checkpoint, not a released demo'}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'sources':len(sources),'overlays':len(overlays),'passedOfflineChecks':sum(tests.values()),'releaseReady':False,'sha256':sha(out)}))
if __name__=='__main__':main()

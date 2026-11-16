"""Hash this research-only package and validate provenance/unknown safeguards."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=json.loads((OUT/'integration-parameters.json').read_text());s=json.loads((OUT/'source-claims.json').read_text());dat=json.loads((OUT/'datum-check.json').read_text())
    assert p['WestLake']['datumOffsetToApplyM'] is None and p['WestLake']['reportedRoutineHeightM']==7.18
    assert p['CityBalcony']['lowerFloorAbsoluteHeightM'] is None and p['GrandTheatre']['poolOuterWGS84'] is None
    assert all(h is None for h in p['Lingyin']['hallGroundAbsoluteHeightsM'])
    assert dat['allowBallpark'] is False and dat['empiricalOffsetApplied'] is None
    assert len(p['blockers'])==7 and all(r['url'].startswith('https://') and r['publisher'] and r['accessedAt'] for r in s['sources'])
    original=ROOT/'docs/hangzhou/research/core/research-hashes.json';frozen=json.loads(original.read_text())['files']
    for name,r in frozen.items():assert digest(original.parent/name)==(r if isinstance(r,str) else r['sha256']),name
    icc=json.loads((OUT/'icc-collision-api-validation.json').read_text());assert not icc['renderingGeometryChanged']
    module=ROOT/'scripts/landmarks/international_conference_center.py';assert digest(module)==icc['sourceModuleAfterSha256']
    files={str(f.relative_to(OUT)):{'sha256':digest(f),'bytes':f.stat().st_size} for f in sorted(OUT.rglob('*')) if f.is_file() and f.name!='round1-hashes.json' and '__pycache__' not in f.parts}
    manifest={'schemaVersion':1,'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'stage':'research-completed-ground-water-acceptance-blocked',
      'files':files,'sourceCount':len(s['sources']),'blockerCount':len(p['blockers']),'originalResearchPreservedFiles':len(frozen),
      'iccAuthorizedAPIAddition':{'module':str(module.relative_to(ROOT)),'sourceSha256':digest(module),'renderingGeometryChanged':False},
      'sourcePhotosPDFBundled':False,'BlenderBrowserInvoked':False,'runtimeGroundWaterValidated':False}
    (OUT/'round1-hashes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'frozenFiles':len(files),'sources':len(s['sources']),'blockers':len(p['blockers']),'originalResearchPreserved':len(frozen),'runtimeAccepted':False}))
if __name__=='__main__':main()

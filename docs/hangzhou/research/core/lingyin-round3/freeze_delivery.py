"""Freeze only this new site package; verify old core and hall sources intact."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    old={
      'scripts/landmarks/lingyin_temple.py':'0c215b8a4deb1a36cdcf09eae68a17deef82f24b40aa0226fae15af537052011',
      'docs/hangzhou/research/core/lingyin-round2/spec.json':'5b614933b8ac9f2afee0f344831e389eec7d0bac23ddde1dcd221feb35b50a93'}
    for name,sha in old.items():assert digest(ROOT/name)==sha,name
    original=ROOT/'docs/hangzhou/research/core/research-hashes.json'
    records=json.loads(original.read_text())['files']
    for name,row in records.items():
        assert digest(original.parent/name)==(row if isinstance(row,str) else row['sha256']),name
    task=OUT/'task-bundles/lingyin-temple'
    job=json.loads((task/'job.json').read_text())
    assert job['stage']=='evidence-ready' and job['budget']['maxTriangles']==30000
    validation=json.loads((task/'validation.json').read_text())
    assert all(row['status']=='unknown' for row in validation['checks'].values())
    model=json.loads((task/'model.json').read_text())
    assert model['sha256'] is None and model['buildCommand'] is None
    spec=json.loads((OUT/'spec.json').read_text())
    assert all(v is None for v in spec['hallBaseYGame'].values())
    cpu=json.loads((OUT/'cpu-geometry-validation.json').read_text())
    assert cpu['trianglesBeforeBlenderExport']<=30000
    source=ROOT/'scripts/landmarks/lingyin_site.py'
    assert cpu['sourceModuleSha256']==digest(source) and cpu['sourceSpecSha256']==digest(OUT/'spec.json')
    files={str(p.relative_to(OUT)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*'))
      if p.is_file() and p.name!='round3-hashes.json' and '__pycache__' not in p.parts}
    result={'schemaVersion':1,'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'stage':'evidence-ready','stageScope':'per-hall adapter and limited estimated exterior/site details; full real ground/route remains pending',
      'files':files,'sourceModule':str(source.relative_to(ROOT)),'sourceModuleSha256':digest(source),
      'sourceSpecSha256':digest(OUT/'spec.json'),
      'preservedPriorSource':{'hallModuleAndSpec':old,'originalCoreFiles':len(records),'originalCoreManifestSha256':digest(original)},
      'formalEightChecks':'all unknown; no worker GLB/browser/Blender/performance','actualReferencePhotosBundled':0,
      'license':'Derived glyph geometry from Adobe SourceHanSerif under SIL OFL1.1, local license preserved; all other source photographs/PDF references only',
      'cpuPreviews':'4 actual-viewed original CPU drafts with visibly disclosed synthetic heights; not game screenshots',
      'integration':'Parent must supply provenance-bound5finite gameY bases, bind new module/spec/dependency hashes, replace priorLingyin object and verify ground/path/entry.'}
    (OUT/'round3-hashes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'frozenFiles':len(files),'moduleSha256':result['sourceModuleSha256'],'specSha256':result['sourceSpecSha256'],'preservedCoreFiles':len(records),'stage':result['stage']}))


if __name__=='__main__':main()

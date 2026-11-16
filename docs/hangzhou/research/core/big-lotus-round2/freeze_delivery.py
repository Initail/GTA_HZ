"""Freeze this worker delivery without touching earlier research packages."""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')


def main():
    attempts={'schemaVersion':1,'actualAttempts':[
      {'action':'primary official text and reference-photo review','result':'completed',
       'notes':'NBBJ/CCDI publication identity, operator, organizer and fixed OSM; no capture-date or photo-license invention'},
      {'action':'ARCHINA web-tool page open','result':'failed','reason':'web-tool redirect/internal error; same public page fetched/read successfully by curl'},
      {'action':'ARCHINA CDN HTTPS photo download','result':'failed','reason':'certificate hostname mismatch; no TLS verification bypass; photographs not viewed or bundled'},
      {'action':'OSM way626826731 coarse neighbourhood classification','result':'corrected',
       'notes':'Footprint is east of main stadium in tennis area, not the main bowl. Sent immediate parent correction, explicit do-not-exclude recorded.'},
      {'action':'first source freeze','result':'failed','reason':'list equality incorrectly required identical ring starting point/order; replaced with exact undirected edge-set comparison of cyclic/reversed rings'},
      {'action':'dependent task generation after initial failed freeze','result':'failed','reason':'no task-catalog existed yet; subsequent successful freeze generated catalog before task generation'},
      {'action':'limited core evidence-ready','result':'passed','scope':'main stadium shell/bowl, not site terraces/interiors'},
      {'action':'first CPU geometry draft','result':'passed-host-contract-only','triangles':26806,
       'notes':'No degenerate fan triangles; first draft preview exposed overly narrow roof tips/gaps. Revised curved broad canopy ends to match the visible annular roof.'},
      {'action':'current CPU geometry','result':'passed-host-contract-only','triangles':27854,
       'notes':'55 independent petals, three tiers, exact source vertex projection, open-core/roof and provisional base-slot rays; fixed28000/10material budget not raised'},
      {'action':'current CPU three-view projection','result':'generated and actually viewed',
       'notes':'Pillow front-face orthographic drawings, not game screenshots; geometry recognizability only, full visual acceptance pending'},
      {'action':'Blender export and browser validation','result':'not-run','reason':'serial main integration owns these operations'}]}
    write(OUT/'attempts.json',attempts)
    original=ROOT/'docs/hangzhou/research/core/research-hashes.json'
    frozen=json.loads(original.read_text())['files']
    differences=[]
    for name,record in frozen.items():
        expected=record if isinstance(record,str) else record['sha256']
        p=original.parent/name
        if digest(p)!=expected:differences.append(name)
    assert not differences,('original research changed',differences)
    previous={
      'scripts/landmarks/lingyin_temple.py':'0c215b8a4deb1a36cdcf09eae68a17deef82f24b40aa0226fae15af537052011',
      'docs/hangzhou/research/core/lingyin-round2/spec.json':'5b614933b8ac9f2afee0f344831e389eec7d0bac23ddde1dcd221feb35b50a93',
      'scripts/landmarks/broken_bridge.py':'eab2ac0c16d54d9b7b6a2ba93a454e83ecd5cc963cafda2ff9f3494f727b78b2',
      'docs/hangzhou/research/core/broken-bridge-round2/spec.json':'0b96b192a1011a5e217b98ace971bd04d5442228b51cad0193d2a9143a282eb4'}
    for name,sha in previous.items():assert digest(ROOT/name)==sha,('previous module/spec changed',name)
    files={str(p.relative_to(OUT)):{'sha256':digest(p),'bytes':p.stat().st_size}
      for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='round2-hashes.json' and '__pycache__' not in p.parts}
    module=ROOT/'scripts/landmarks/big_lotus.py'
    result={'schemaVersion':1,'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'stage':'evidence-ready','files':files,'sourceModule':str(module.relative_to(ROOT)),
      'sourceModuleSha256':digest(module),'sourceSpecSha256':digest(OUT/'spec.json'),
      'priorResearchPreserved':{'files':len(frozen),'sourceManifestSha256':digest(original),
        'priorIndependentModulesAndSpecs':previous},
      'releaseImages':'only original CPU candidate previews; no official photographs or reference pages bundled',
      'stageLimit':'no worker GLB export/browser/runtime/performance acceptance'}
    write(OUT/'round2-hashes.json',result)
    print(json.dumps({'frozenFiles':len(files),'moduleSha256':digest(module),
      'specSha256':digest(OUT/'spec.json'),'originalResearchPreserved':len(frozen)},ensure_ascii=False))


if __name__=='__main__':main()

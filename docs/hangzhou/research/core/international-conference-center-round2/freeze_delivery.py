"""Hash this worker package and confirm prior independent evidence is preserved."""
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
    write(OUT/'attempts.json',{'schemaVersion':1,'actualAttempts':[
      {'action':'official source/reference review','result':'completed','notes':'Actual PETROFF, engineer report, supplier, hotel and2017 interview;12 images actually viewed, not bundled'},
      {'action':'initial urllib public source fetch','result':'partially failed','reason':'bad file descriptor for several hosts; native curl fetched same valid public TLS sources successfully, no dependencies modified'},
      {'action':'CarlosOtt official direct page','result':'failed','reason':'web timeout and curl untrusted certificate chain; no TLS bypass; PETROFF primary project and engineer report supply attributable role evidence'},
      {'action':'government CUC page direct access','result':'failed','reason':'web cache miss for bothwww and bare domains; only search-index corroboration recorded, not dimension evidence'},
      {'action':'prior helper first call for area moments','result':'failed','reason':'temporary exec globals/locals separated, math not bound; read-only import helper then succeeded with no source changes'},
      {'action':'date verification for Tsinghua lighting source','result':'corrected','notes':'Actual page states2016-09-08, replacing preliminary unverified date before evidence-ready'},
      {'action':'limited exterior evidence-ready check','result':'passed','scope':'gold globe/podium exterior candidate, not current site/interiors'},
      {'action':'first CPU front ray','result':'failed','reason':'exact centre ray crossed a legitimate steel mullion; off-centre3m glass-area ray retained to check the actual facade, not a uniform gold wall'},
      {'action':'CPU geometry and draft review','result':'iterated','notes':'Source entry outer pieces left a gap toward central lobby. Added explicitly estimated connectors with exact source edge contacts and corrected roof normal/winding; estimates/pending retained.'},
      {'action':'current CPU geometry','result':'passed-host-contract-only','triangles':20073,'materials':4,
       'notes':'Source projection/scale/base/frame, sphere85m envelope, glazed wedge/cap, terraces, rounded podium, connector normal/rays and32specific exclusions; fixed26000 ceiling unchanged'},
      {'action':'CPU three-view preview','result':'generated and actually viewed','notes':'Pillow orthographic sketches, not real game screenshots or physical material acceptance'},
      {'action':'Blender/browser','result':'not-run','reason':'Serial main integration owns export and runtime checks'}]})
    original=ROOT/'docs/hangzhou/research/core/research-hashes.json'
    frozen=json.loads(original.read_text())['files']
    for name,record in frozen.items():
        expected=record if isinstance(record,str) else record['sha256']
        assert digest(original.parent/name)==expected,('original core changed',name)
    previous={
      'scripts/landmarks/lingyin_temple.py':'0c215b8a4deb1a36cdcf09eae68a17deef82f24b40aa0226fae15af537052011',
      'docs/hangzhou/research/core/lingyin-round2/spec.json':'5b614933b8ac9f2afee0f344831e389eec7d0bac23ddde1dcd221feb35b50a93',
      'scripts/landmarks/broken_bridge.py':'eab2ac0c16d54d9b7b6a2ba93a454e83ecd5cc963cafda2ff9f3494f727b78b2',
      'docs/hangzhou/research/core/broken-bridge-round2/spec.json':'0b96b192a1011a5e217b98ace971bd04d5442228b51cad0193d2a9143a282eb4',
      'scripts/landmarks/big_lotus.py':'faf3caf74bd5cc28dbcc632195fd052ab2f3029b62f7dec81a3960e7c8d4d368',
      'docs/hangzhou/research/core/big-lotus-round2/spec.json':'f3b5a535875fba14addf94cd2b285148fa48c98b4f537093d5f63f4299081a73'}
    for name,sha in previous.items():assert digest(ROOT/name)==sha,('previous module/spec changed',name)
    files={str(p.relative_to(OUT)):{'sha256':digest(p),'bytes':p.stat().st_size}
      for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='round2-hashes.json' and '__pycache__' not in p.parts}
    module=ROOT/'scripts/landmarks/international_conference_center.py'
    write(OUT/'round2-hashes.json',{'schemaVersion':1,'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
      'stage':'evidence-ready','files':files,'sourceModule':str(module.relative_to(ROOT)),
      'sourceModuleSha256':digest(module),'sourceSpecSha256':digest(OUT/'spec.json'),
      'priorResearchPreserved':{'files':len(frozen),'sourceManifestSha256':digest(original),
        'priorIndependentModulesAndSpecs':previous},
      'releaseImages':'only original CPU candidate previews; no official reference photos bundled',
      'stageLimit':'No worker GLB export, browser, collision/night/performance or full-site acceptance'})
    print(json.dumps({'frozenFiles':len(files),'moduleSha256':digest(module),
      'specSha256':digest(OUT/'spec.json'),'originalResearchPreserved':len(frozen)},ensure_ascii=False))


if __name__=='__main__':main()

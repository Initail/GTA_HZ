"""Freeze independent balcony package; preserve earlier research/source specs."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
    write(OUT/'attempts.json',{'schemaVersion':1,'actualAttempts':[
      {'action':'fixed Geofabrik main/parts/context','result':'completed','notes':'relation8718551 and3exacthole building parts. Geometry intersection search retained14nearbyroads/16green/river/wave culture context without deleting them.'},
      {'action':'source/public photograph review','result':'completed','actualImagesViewed':11,'notes':'9photographer opposing street directions and2official aerial context. No photos bundled.'},
      {'action':'government2015/2023 picture fetch','result':'failed','reason':'403/cachemiss; no approval bypass or fabricated photo claim'},
      {'action':'HangzhouNews2012 reference image fetch','result':'failed','reason':'anti-bot307 redirects loop; no bypass. Other original public photo references were available.'},
      {'action':'university direct source/image fetch','result':'failed','reason':'25s network timeout, no TLS bypass; actual web page text available and read'},
      {'action':'source footprint freeze first attempt','result':'failed-and-corrected','reason':'closed ring index off-by-one; exact18open vertices checked and two actual back fingers retained, no invented third entry'},
      {'action':'initial unconstrained triangulation','result':'failed-and-corrected','reason':'Delaunay filter did not cover source concave/holed polygon fully. ExistingShapely2.1.2constrained triangulation used with full-area assertion'},
      {'action':'first CPU triangle budget','result':'failed','triangles':28438,'ceiling':28000,'notes':'Removed only hidden internal top-rail caps at adjoining segments. Budget kept28000.'},
      {'action':'first Pillow helper import','result':'failed-and-corrected','reason':'BundledPillowruntime lacksShapely; CPUvalidation keepsShapely import inside its data-check main so pureB preview imports remain independent'},
      {'action':'CPU preview/normal review','result':'iterated','notes':'Source interior-ring roofs and constrained deck triangles initially faced downward. Producer now normalizes roofs/deck CCW and slab boundary winding; upward-normal assertions added.'},
      {'action':'clipped paving triangulation','result':'failed-and-corrected','reason':'Buffer boundary produced numerical collinear triangles. Producer removes zero-area construction triangles and retains strict coverage/nondegenerate output checks.'},
      {'action':'final CPU validation','result':'passed-host-contract-only','triangles':25192,'materials':5,'solidFootprints':136,'notes':'Source projection/base/scale, floor API, exact source geometry/area, bridge ground clearance, explicit collision strips, normals, budget; no actual runtime acceptance'},
      {'action':'final CPU three-view preview','result':'generated-and-actually-viewed','notes':'OrthographicPillowdrafts, not game screenshots/full visual acceptance'},
      {'action':'Blender/browser/shared writes','result':'not-run','reason':'Main integrator owns serial export/runtime/assets/config; this worker touched only its independent round2/module'}]})
    original=ROOT/'docs/hangzhou/research/core/research-hashes.json';frozen=json.loads(original.read_text())['files']
    for name,rec in frozen.items():assert digest(original.parent/name)==(rec if isinstance(rec,str) else rec['sha256']),name
    previous={
      'scripts/landmarks/lingyin_temple.py':'0c215b8a4deb1a36cdcf09eae68a17deef82f24b40aa0226fae15af537052011',
      'docs/hangzhou/research/core/lingyin-round2/spec.json':'5b614933b8ac9f2afee0f344831e389eec7d0bac23ddde1dcd221feb35b50a93',
      'scripts/landmarks/broken_bridge.py':'eab2ac0c16d54d9b7b6a2ba93a454e83ecd5cc963cafda2ff9f3494f727b78b2',
      'docs/hangzhou/research/core/broken-bridge-round2/spec.json':'0b96b192a1011a5e217b98ace971bd04d5442228b51cad0193d2a9143a282eb4',
      'scripts/landmarks/big_lotus.py':'faf3caf74bd5cc28dbcc632195fd052ab2f3029b62f7dec81a3960e7c8d4d368',
      'docs/hangzhou/research/core/big-lotus-round2/spec.json':'f3b5a535875fba14addf94cd2b285148fa48c98b4f537093d5f63f4299081a73',
      'scripts/landmarks/international_conference_center.py':'9c4c00a61709997328147965beea562995619f50d35bb12d91e00a99696cb77c',
      'docs/hangzhou/research/core/international-conference-center-round2/spec.json':'b8b454c8da4ece8ecfa88cad4770ac4b0c9d235335282072bbd03f9dbe6a1c20'}
    for name,sha in previous.items():assert digest(ROOT/name)==sha,name
    files={str(p.relative_to(OUT)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='round2-hashes.json' and '__pycache__' not in p.parts}
    module=ROOT/'scripts/landmarks/city_balcony.py'
    write(OUT/'round2-hashes.json',{'schemaVersion':1,'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'stage':'evidence-ready','files':files,
      'sourceModule':str(module.relative_to(ROOT)),'sourceModuleSha256':digest(module),'sourceSpecSha256':digest(OUT/'spec.json'),
      'priorResearchPreserved':{'files':len(frozen),'sourceManifestSha256':digest(original),'priorIndependentModulesAndSpecs':previous},
      'releaseImages':'only original CPU candidate previews, zero reference photos bundled','stageLimit':'limited exterior only; actual GLB/current entrances/elevations/8formalchecks pending'})
    print(json.dumps({'frozenFiles':len(files),'moduleSha256':digest(module),'specSha256':digest(OUT/'spec.json'),'originalResearchPreserved':len(frozen)}))
if __name__=='__main__':main()

from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;R=P.parents[5];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();d=json.loads((P/'model-delivery.json').read_text());g=json.loads((P/'glb-review.json').read_text());n=json.loads((P/'nullengine-review.json').read_text());assert g['failed']==n['failed']==0
(P/'README.md').write_text('''# Actual coastal bridges GLB v4 — source fidelity passed, actor/visual gates open

`coastal-bridges.glb`: 24916 triangles,9 bridge/material meshes,2,550,680 bytes. Original source objects/materials remain;48 semantic road shells belong to the source renderer; lower Qiantang railway remains in this asset. All three bridge placements use separate integer ENU origins and local float32 vertices, original GLB Y-up and original Babylon root identity correction. Model/spec hashes bind the unchanged frozen CPU candidate.

Independent direct GLB review65/65: all directed triangle multiplicities, exact UV after glTF V flip, exact node transforms, material tokens, nondegenerate geometry and UV, positive winding/normal dot. Actual maximum f64 source→GLB world position error1.67911e−5g. NullEngine20/20: exact directed triangles/UV and root-corrected world coordinates,73 representative finite face-normal rays hit; maximum expected decoded world error0. Default root negative control fails position as expected. This proves real mesh loader geometry, not browser rendering or continuous actor navigation.

The first actual export in `../actual-glb-v2/` lost180 faces because local deduplicated vertices exposed180 identical directed source triangles to Blender validation. The original source uses independent per-face vertices; v3 restored all original triangles and multiplicities. Independent v3 NORMAL checks found110 thin-member triangles with one or more bad corner normals (including a default [0,1,0] GLB normal). v4 computes normalized cross products from the exact final local float32 triangles, assigns the same explicit split normal to each triangle corner and enables custom normals. Geometry, UVs, material bindings and model parameters remain the same. This is a render-attribute repair, not removal of original members or a source-width change. Existing180 coincident original triangles are intentionally preserved, not new foundation overlays; visual impact remains a gate.

Regeneration uses isolated factory-startup Blender:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python docs/hangzhou/research/core/qiantang-bridges-integration-v2/actual-glb-v4/export.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/qiantang-bridges-integration-v2/actual-glb-v4/review.py
node docs/hangzhou/research/core/qiantang-bridges-integration-v2/actual-glb-v4/nullengine.mjs
```

Exporter refuses overwriting an existing GLB; use a new sibling candidate directory for regeneration. Frozen source package hashes are checked before exporting. The actual Blender batch is finished; live Blender scene and public assets were not changed.

Main integration must install `coastal-bridges.glb` via the existing coastal→landmarks mesh path, apply all82 source-height rows atomically, render the complete49 owned support domains without duplicate road shells, and keep7613 bounded structural collisions. No source actor blockers are resolved by this fidelity result: lower Fuxing and bank-end path/guardrail mismatches remain; Qiantang tank probes fail the original narrow corridor. Browser day/night, GPU performance, full continuous driving, arrivals and exact source-deck shell joins are not verified. No whole-project completion or Skill verified stage is claimed.
''')
files={str(f.relative_to(R)):sha(f) for f in sorted(P.iterdir()) if f.is_file() and f.name!='package-manifest.json'};report={'kind':'actual three-bridge GLB independent source fidelity review; actor/support/visual blockers retained','sourcePackageSha256':sha(P.parent/'package-manifest.json'),'artifactSha256':sha(P/'coastal-bridges.glb'),'sourceModuleSha256':d['sourceModuleSha256'],'specSha256':d['specSha256'],'actualGlbChecks':{'passed':g['passed'],'failed':g['failed']},'nullEngineChecks':{'passed':n['passed'],'failed':n['failed'],'faceRays':len(n['rays'])},'files':files};(P/'package-manifest.json').write_text(json.dumps(report,indent=2));print({'artifact':report['artifactSha256'],'package':sha(P/'package-manifest.json')})

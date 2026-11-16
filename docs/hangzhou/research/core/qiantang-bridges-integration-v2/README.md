# Three bridge integration v2: frozen CPU candidate, unresolved acceptance

This isolated candidate is **not an accepted playable bridge package**. Source meshes, source heights, collision probes and old failures are preserved separately. Main integrator owns all shared data, Blender export and world installation.

## Rebuild and placement

From repository root, run sequentially:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/qiantang-bridges-integration-v2/prepare.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/qiantang-bridges-integration-v2/validate-model.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/qiantang-bridges-integration-v2/validate-profiles.py
node --experimental-transform-types docs/hangzhou/research/core/qiantang-bridges-integration-v2/runtime-collision.mjs
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/qiantang-bridges-integration-v2/diagnose-contact.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python docs/hangzhou/research/core/qiantang-bridges-integration-v2/freeze.py
```

Node strip-only mode cannot compile existing constructor parameter properties. The transform-types mode above ran successfully on local Node24.13.0. No dependency versions changed. Source snapshots bind the runtime reviewed here; a changed runtime requires a new review rather than reusing this pass count.

Pure module `scripts/landmarks/qiantang_bridges_v2.py` exposes `build(B, spec.placementGame, spec, .6)`, `ground_footprints` and `deck_domains`. It does not import Blender or city_mesh. Positions are canonical ENU game coordinates; physical dimensions scale exactly once by .60. Preserve the existing Blender→GLB→Babylon root handling. CPU `candidate-mesh.npz` is not a GLB. `integration-contract.json` freezes exact role/ownership and atomic source-height application rules.

## Shape, source boundaries and elevations

Retained original primitive identities: Qiantang16 Warren trusses and lower railway; Fuxing2 large/9 small blue arches and double-deck members; Zhijiang2 red arch pylons/stays. Fuxing axis uses the previously reviewed paired-source correction, not a new arbitrary displacement. Semantic removal of48 road deck shell primitives leaves full road surfaces to the source renderer; materials are not used to delete fused GLB parts. One railway bed remains object-owned. Fuxing guardrails follow the original reported26.4/32m width transitions and retain original member sizes, instead of old constant26.4m rails cutting the widened interiors. Budget24916/25000 triangles;7613 conservative primitive bounds; no new lights or water planes.

Fuxing old upper22m and lower12m relative the legacy reference conflicted with the retained small arch rise12.15m/radius.85m. New upper26.25m =12+12.15+.85+deck1.25; actual roadway Y16.65g. Qiantang upper roadway increases from12.3g to12.45g, placing it .25physical m above the retained upper chord centre (radius.24m). Lower railway stays5.88g. Zhijiang target remains11.7g. These are **estimated constructibility adaptations, not measured heights**, and legacy referenceY.9 is not a surveyed contemporary river level. New primary source review is in `source-review-20261111.json`; original raw DSM-derived values and each failed intermediate candidate remain intact.

`source-height-proposal.json` has82 complete affected sourceRoadId rows,187 changed original nodes,41 unchanged graph-frontier nodes, exact original points/node IDs/widths and original/result heights. It uses connected source graph only, rigid core pins and bounded harmonic approach transitions; no new nodes/edges. Both endpoints of every source segment intersecting the core are pinned to ensure interpolation across the entire structural main interval. Core flat regions can extend to those existing source endpoints. Main-core5399 samples differ from target by ≤3.56e−15g; global shared-node height differences are exactly0. Maximum affected grade.106443618 gives source height changes.28208g at original maximum car timestep and.02236g at maximum running timestep; these numerical checks are not real driving acceptance. The inherited OSM horizontal road widths remain estimates and are **not validated lane/deck envelopes**.

## Actual CPU failures retained

Model identity/UV/triangle checks11/11 and source-node/height checks90/90 pass. Full support checks and actual actor checks are separate. Core collision probes (~5g spacing) use unchanged CityCollision1.15g margin, CityWalk and tankFootprintClear; no unrelated props or water are simulated. They are source-path tests, not continuous driving or exact moving-body mesh tests.

| Source road | Deck | Probes | Car blocked | Walk blocked | Tank blocked |
| --- | --- | ---: | ---: | ---: | ---: |
| way/4348186#0 | upper | 130 | 0 | 0 | 130 |
| way/29169666#0 | upper | 160 | 6 | 7 | 16 |
| way/154135283#0 | upper | 6 | 0 | 0 | 0 |
| way/29170042#0 | upper | 7 | 0 | 0 | 0 |
| way/154135290#0 | upper | 160 | 0 | 0 | 0 |
| way/336983476#0 | lower | 168 | 63 | 85 | 168 |
| way/340648409#0 | lower | 166 | 1 | 1 | 68 |
| way/589429905#0 | lower | 168 | 85 | 102 | 168 |
| way/306360721#0 | single | 58 | 0 | 0 | 0 |
| way/589558021#0 | single | 57 | 0 | 0 | 0 |

Fuxing lower way336983476 has267/839 ≤1g source-centre samples outside the reported support, maximum2.65473g; upper29169666 has2/802 outside by.06547g. All source-strip width overhangs are listed in validation-profiles. Original1.15g structural collision margin encounters guardrail bars/posts and some arch members at the retained paths. Do not resolve this by deleting guardrails, reducing actor dimensions, changing source graph coordinates or silently declaring all modes pass. The next research step is lower-deck cross-section, source mapping semantics and finite bank geometry. Source numerical width, centreline accuracy and reported structural edge remain distinct evidence.

## Unfinished gates and licensing

No Blender/actual GLB, browser screenshot, actual driving, day/night, memory/FPS, full arrival or global render integration gate is passed here. Keep Skill stage planned; evidence and model contracts bind the CPU sources but no artifact hash is invented. The original source has no verified luminaire geometry; original materials remain, while the2024 supplier report newly supports qualitative night lighting only. Do not claim a recreated lighting installation.

MIT project/model code and OSM ODbL attribution are retained. The private ignored reference cache contains the re-read Fuzhou University paper solely for audit. Public photos/papers are references, not redistribution licenses or release textures. No reference image is baked into models. Historical pre-fix failures remain in `before-*` and `trial-uniform-radius-390/`. Source snapshots plus package-manifest bind this review; later exports and further Fuxing research belong in new subdirectories.

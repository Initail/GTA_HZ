# Actual local terrain GLB v1 review

Asset SHA256: `359c528b67724c3bdf703d877df17bac758eebd4c4250a8efcedc7c2c26dfc75`.

All 43,622 directed world triangles match the prepared float32 geometry exactly. There are no degenerate faces, nonmanifold edges or reversed shared edges. Open edges are explicitly owned by the shoreline (492) and local crop (390). Maximum source vertex error is 5.0317e-6 game units.

**UV gate failed: nine actual UV triangles collapse** (six land, three park). Values remain finite. Correctly reproducing both float32 roundings and the glTF V flip removes the reviewer's initial mapping-comparison false positives; it does not remove these nine real degeneracies. The root exported v2 separately.

Babylon NullEngine retains all directed faces and UV values. The existing root quaternion correction gives zero world-position difference; the default root negative control differs by 7,749 game units. All 42 representative vertical rays hit. No browser, GPU materials or actor simulation was used.

Actual floor/terrain comparison: lower slab clearance is .009999871g with no penetration. Upper slab has 648 narrow perimeter overlap pairs, totaling .00354503g2; after eroding its actual footprint by 1mm, interior penetration is zero. These remain real join failures.

The first shoreline classification used positive normal.z and accidentally counted 159 nearly vertical Boolean side faces as tops. Those raw reports remain under `raw-side-classification-*`. The actual GLB has two separated normal clusters: 159 faces have normalized z below .001, while 1,164 true tops have z above .99. Corrected top overlap is 25.527216g2, including 23.319348g2 nearly coplanar terrain/shore sheets. Outside the source-discontinuity 1mm band, height differences are -.007714 to +.001371g; multi-metre differences remain inside that band. Side faces were not removed from the asset or their raw evidence.

This report does not accept global crop joins, exclusive surface ownership, full soil closure, body collision or visual appearance.

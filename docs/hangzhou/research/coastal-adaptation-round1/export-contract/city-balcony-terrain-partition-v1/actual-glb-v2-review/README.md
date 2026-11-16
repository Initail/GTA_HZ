# Actual local terrain GLB v2 review

Asset SHA256: `49fee2ba93052f67e732c647d2edacc72c45718901d9ff692f4669ca252782a1`.

**Geometry, UV and NullEngine checks pass; physical/render joins remain pending.** All 43,622 directed world triangles equal v1 exactly. There are no degenerate faces, nonmanifold edges or reversed shared edges.

UV uses one integer period translation per projection: period 8g, integer origin `[414,-248,0]`. Each triangle retains the original XY or dominant wall-axis projection. Independent source calculations reproduce the actual two float32 roundings and V flip: serialized UV values match exactly, with zero collapsed UV triangles and zero nonfinite values. The integer translation preserves repeating-texture phase, scale and direction.

NullEngine retains all 43,622 local directed faces and UV values. Existing root quaternion correction gives zero world-position error; the default-root negative control differs by 7,749g. All 42 representative rays hit. Materials were skipped; this is not a browser/GPU result.

World geometry is byte-for-value equivalent to v1, so v1's actual floor and shoreline join failures still apply. See sibling `actual-glb-v1-review/relative-position-summary.json` and `join-repair-proposal-v1/`. The UV repair does not resolve the 648 upper-slab perimeter overlap pairs or 23.319g2 of nearly coplanar shore/terrain coverage. The crop has not been joined to the global terrain, and no final closed-soil claim is made.

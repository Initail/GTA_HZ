# City Balcony road height options — not activated

The fixed OSM snapshot identifies two short, one-way `tunnel=yes`, `layer=-1` primary roads: 157967583 and 157967585. Each joins two original, non-tunnel approach roads. Treating only those two short ways as below grade would leave endpoint steps. `fixed-osm-road-and-nearby-tags.json` preserves the 16 potentially affected ways' exact snapshot tags, versions and node lineage; no updated OSM was fetched. The PBF is `zhejiang-261011.osm.pbf`, SHA `4eb65f64925498408faeee7eb04b60d7eb8a01c49ddb239f73070d4d282c75a9`.

## Confirmed tunnel geometry option

`confirmed-tunnel-only-profiles.json` affects exactly six roads: the two tunnels plus 557050557, 157967584, 605330157 and 157967586. It retains every original XY, source node, width, name, kind, direction and grade tag. Height profiles are estimated game adaptations, not surveyed road elevations. Raw DSM-derived estimates remain in every profile sample.

Using the city's existing default six-real-metre tier clearance at scale 0.60 gives a conservative 3.6g ceiling clearance target. Source samples cover full-width road cross sections at <=0.5g intervals and all original nodes, against actual linked GLB slab-bottom triangles. Their original minimum clearance is negative (about −0.61g), proving the old profile intersects the slab. Lowering constraints propagate continuously through original shared nodes with a 0.04 lowering-gradient transition. Maximum lowering is 4.221929g; final sampled longitudinal grade is at most 4.71399%; all shared source-node heights remain continuous. The three-and-a-half-metre game-space clearance is a modelling choice, not evidence of real tunnel headroom.

The source-node topology is sufficient to make this a connected proposal. It does not certify physical road support, terrain excavation, retaining walls, piers, source pavement joins, actual vehicle bodies or browser driving. In particular, open sunken approaches require corridor excavation instead of a grass surface remaining over the lowered road.

## The service road has two unresolved interpretations

336828925 is 86.405249g long. Its first source node 3439149586 is shared with approach 557050557; its other endpoint is a source dead end. Only `highway=service` is tagged: no entrance, access, tunnel, level or service subtype. There are no tagged source nodes within 50g of this line in the fixed snapshot. This absence does not prove an entrance is absent.

The under-floor hypothesis is `service-under-lower-floor-hypothesis-profiles.json`. Taking the current lower slab literally would require a road near −2.0321g for 3.6g clearance. That lowers the road by up to 7.687407g and propagates into 16 original roads, including crossing links, to avoid shared-node steps. The maximum sampled grade is 8.98996%. This is an explicit **estimated game adaptation**, not a confirmed underground parking entry. Foundation/pier body conflicts and the actual service use remain to be resolved.

The upper interpretation cannot be rejected merely because the lower cap is low. `service-upper-comparison.json` checks all 4.5g of road width against the single-valued upper walk envelope. The source centerline occupies 28.027368g of upper deck; partial-width support starts at station 57.75g and full-width at 59.25g. Original road estimates differ from the upper plane by −0.611212 to +0.097407g. A modest rising supported road from the unchanged source junction could therefore reach the upper plane without changing the six-road tunnel proposal or filling the lower public space.

The upper option has a concrete model obstacle: the source route crosses outer edges 0 and 1 at source node 10935463454 (station 58.377881g), and its full-width end grazes edge 17. All three currently have upper railings. Actual GLB clipping above the upper plane, in a 3g-tall body band, finds 103 obstructing faces (20 glass, 83 steel). Those are real current-model obstacles, not lower piers misclassified by footprint alone. Removing or opening only a source-bound access-width railing section would be a new explicit model adaptation requiring a defined endpoint edge treatment; it cannot be assumed already built.

## Evidence and limits

The fixed OSM source is primary evidence of geometry, shared nodes and tunnel tags. The existing [owner project evidence](https://www.hzyjfz.cn/index.php?a=detail&id=45&m=project) and [project-engineer interview](https://news.sohu.com/20070126/n247846969.shtml) establish the main balcony / lower and upper levels and wider sunken-road context. The owner URL returned 404 in this run; the prior hashed project evidence remains in `docs/hangzhou/research/core/city-balcony-round2/evidence.json`. Neither gives the current level or operation of this exact service way. Search results for later, different Zhijiang tunnels and the two side balconies were not substituted for this source road.

No proposal changes rewards, speeds, vehicle dimensions or road topology. Both service interpretations remain explicit alternatives; a coherent geometry fit is not evidence of actual use. The primary tunnel package is independently usable for the next physical candidate, while the service identity/entry and body clearance stay visible blockers.

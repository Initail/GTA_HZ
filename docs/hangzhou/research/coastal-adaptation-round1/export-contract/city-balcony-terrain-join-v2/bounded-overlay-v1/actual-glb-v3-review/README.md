# Actual GLB v3: finite geometry gate

`finite-geometry-acceptance.json` is the acceptance boundary. The actual GLB has 36,504 directed faces, all mapped once to source faces; zero degenerate/nonmanifold/reversed shared edges and zero exact serialized UV mismatches. Source/actual paired edge endpoints bound every linear edge displacement by 0.0000431047g, below the adopted 0.001g serialization budget. The actual node rotation differs from its intended angle matrix by at most 4.49e-10.

The original root quaternion correction is retained. NullEngine imports all faces and UVs correctly; the corrected world error is 0.0000159636g and 36 ray probes hit. Default root orientation is a negative control, not used for delivery. Materials were skipped in NullEngine, so this is not visual, GPU or performance acceptance.

Actual serialization reintroduces microscopic projected overlap and gaps: bank upward-top overlap 0.00123769g², combined closed-bank dry gap 0.00411914g², 134 normalized microscopic holes. Maximum checked gap distance to source dry/owner boundaries is 0.0000394212g; distance to actual support is 0.0000334201g. These are accepted bounded rendering approximation strips, not relabeled zero-area topology. The raw combined boundary Hausdorff 0.120038g is retained: narrow seams can separate a bank strip into a component, causing its inward edge to enter the set-boundary metric despite paired source vertices moving only 0.0000431g.

Actual upper/lower floor penetrations remain zero; bottom clearances are at least 0.00741449g / 0.00999999g. Smooth sampled physical height error is at most 0.00594954g. Large height differences at the existing discontinuity band remain separately reported. Near-coplanar microscopic bank overlap will still need browser antialiasing/appearance inspection.

`coverage-report.json` retains an additional hypothetical re-serialization preflight of decoded world points; its angle-zero reversed-face entry is not the actual imported GLB. The actual asset passed using the source contract's one-degree frame. `actual-report.json` is the authoritative actual triangle/UV audit.

No global crop insertion, collision, road height, lower-floor access, browser or appearance/performance acceptance is claimed.

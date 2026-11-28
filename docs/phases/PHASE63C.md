# Phase 63C — Contact anchors and automatic alignment

In Paired Preview, choose a contact label, click a point on each unmirrored source frame or enter signed offsets relative to its pivot. The overlay displays both transformed anchors and their separation in scene pixels. Align B to A moves B using its current scale and mirror, preserving A and both source clips. Render again after alignment. Both actors must be active at the playhead. Pair JSON retains optional contact metadata; older bundles default to zero offsets. Anchors are fixed over the clip, not tracked anatomical landmarks; this is translation-only alignment, no IK, limb deformation or per-frame contact correction. Fractional scaling and renderer rounding can leave small residual errors.

Manual acceptance: select hands/face on two clips, verify guide and mismatch, align at unequal scales and mirrored facing, test inactive frames and out-of-range positions, reload pair and older bundle. Desktop and CI validation pending.

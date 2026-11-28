# Phase 61S-E — Character consistency and flicker correction

Analyze local foreground bounds, bottom-center position and median RGB outliers. Corrections are opt-in: bounded color offsets, bounded integer translation (no clipping), partial-alpha smoothing and edge-only chroma despill. Preview selected original/corrected frames, then accept with undo or discard. Scale is diagnostic only; intentional motion may be flagged. This is a conservative raster heuristic, not semantic identity detection or optical flow. Synthetic CPU tests added; desktop acceptance pending.

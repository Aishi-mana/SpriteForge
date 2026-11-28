# Phase 61S-F — Frame interpolation and smooth motion

Choose nearest-frame, alpha-aware blend or translation-assisted blend, factor 2–4, bounded motion strength and maximum shift. Preserve duration by multiplying FPS (non-loop clips hold the final frame); otherwise retain FPS for slow motion. Looping clips interpolate across the seam. Preview separately, scrub/play, accept with undo or discard. Original frames are retained exactly. CPU motion estimation uses foreground bounds, not optical flow or neural pose interpolation; complex movement may ghost. Desktop acceptance pending.

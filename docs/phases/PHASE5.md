# Phase 5 - AI joint cleanup
Unzip over your spriteforge folder. New: engine/refine.py. Changed: engine/rig.py, engine/generate.py, engine/main.py, ui/index.html.
No new packages. No Rust rebuild.

Animate tab -> tick "AI joint cleanup", describe the character, press Preview.
- Only small discs around moving joints (shoulders, elbows, hips, knees, neck, pelvis) are repainted; everything else is untouched.
- SDXL inpaint + your pixel LoRA at low strength (default 0.45), same seed for every frame, then snapped to the sprite's own palette.
- Safety net: if the AI changes too much in a frame, that frame silently keeps the rig-only version (reported in the status line).
- "Show before cleanup" toggles the preview; the strip shows before/after rows.
- Export right after Preview reuses the cleaned frames (no second AI pass).
Limits: frames must be <= 256 px (sprite + padding). Expect roughly 20-60 s per frame on 8 GB.

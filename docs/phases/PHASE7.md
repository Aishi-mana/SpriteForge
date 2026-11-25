# Phase 7 - review & reuse AI cleanup results
Unzip over your spriteforge folder. Changed: engine/refine.py, engine/rig.py, engine/projects.py, engine/main.py, ui/index.html. No packages, no rebuild.

Animate tab, after a Preview with "AI joint cleanup":
- Under every frame is an "AI" tick. Untick it to keep that frame's rig-only version (red outline). "AI all" / "Rig all" flip everything.
- Frames the AI changed too much are pre-unticked automatically.
- "Redo unticked frames (new seed)" re-runs the AI only for those frames and merges the results back (needs the live result, i.e. same session).
- "Highlight what the AI changed" paints changed pixels magenta on the preview. "Show before cleanup" plays the rig-only version.
- Onion skin (works for any animation) shows the previous/next frame faintly. Click a frame to pause and inspect it.
- Export writes exactly the frames you chose (AI + rig-only mix) through /api/rig/export_frames, with no second AI pass.
- Cleaned results are saved inside the project (per animation) and come back when you load it, ready to review and export.

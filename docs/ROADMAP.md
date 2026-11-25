# Roadmap and known limits

## Candidate next features
- **Animate: start and end reference** (Phase 26 initial implementation; validation pending): the Animate tab already takes a reference sprite; let it also take an optional **start** and **end** reference (first and last pose of the clip).
  Ideas to evaluate: derive start/end poses from the two sprites (auto-placed rigs) and have the rig interpolate between them (extends *Custom clips*); and/or use both as references for AI in-betweens (IP-Adapter + skeleton per frame).
  Needs a design pass first (loop vs one-shot, how the two rigs map onto each other, palette lock).
- **Tiles follow-ups (remaining)**: collision / navigation polygons derived from the art and for terrain tiles; hand-drawn-looking borders (AI inpaint along the mask edge); transitions with different border widths per terrain pair; verify the Godot multi-terrain painting rules and adjust the export if needed.
- **First-run setup wizard / model manager**: download IP-Adapter / ControlNet with progress, check models, pick the assistant model, optional installer.
- **Custom clips**: pose keyframes yourself, interpolate (and save/share clips); per-clip secondary-motion presets.
- **Softer joints**: soft deformation (skinning) instead of rigid parts; better elbows/knees.
- **Better multi-view consistency**: line-art / depth conditioning for the view generator; multi-view reference sheets; per-view regen with the first view as extra reference.
- **Pixel editor extras**: layers, tile mode, selection copy/paste, outline/shade tools, palette ramps inside the editor.
- **Aseprite `.aseprite` export**, Godot `AnimationPlayer` scenes, Unity prefab generation.
- **Auto-tune rig weights** from AI cleanup results (not done: mapping cleaned pixels back to sprite pixels is unreliable).

## Known limits
- Only **SDXL**. Flux / HiDream / Qwen files are detected and blocked. No SD 1.5 path.
- 8 GB VRAM: skeleton (ControlNet) mode uses sequential offload (1-3 min per image); video models are out of scope.
- The AI cannot keep a character identical across poses; the **rig** is the consistent path. Reference/skeleton is for exploring.
- Rig motion is rigid cut-outs: the walk/run/attack clips are generic; side views look best. Front/back walks are a step-and-bob. Three-quarter views are approximations.
- AI joint cleanup needs frames <= 256 px and is slow (20-60 s per frame).
- Template/direction generation: the AI sees only the dummy's silhouette and shading (no pose-control model), so limb placement can wander; lower *Redraw strength*, or Regen/Edit a view.
- Not verified on real hardware as of phase 19 (the queue/history tab included): pixel editor in a real browser, palette tab UI, secondary motion, templates, directions, Godot/Unity import of exports, AI cleanup quality, `.tres`/importer script in the engines.

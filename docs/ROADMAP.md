# Roadmap and known limits

This is a **candidate backlog**, not a release promise. The repository currently includes Phase 22 features; see [the handoff](../HANDOFF.md) and [phase notes](phases/) for implementation history. Functional correctness and hardware validation are separate.

## First: verify the newest delivered features

The previous handoff recorded user testing through Phase 18, but **Phases 19-22 were not confirmed on the target laptop** at that point. Use the [manual testing checklist](TESTING_CHECKLIST.md), especially steps 15-22, before treating the following as production-ready:

- **Phase 19 — queue and history:** multi-job queue, pause/cancel, restart persistence, fork/re-run/compare.
- **Phase 20 — tiles and props:** seamless tiles, workbench, packed atlas and tileset exports.
- **Phase 21 — terrain sets:** 47-blob / 16-edge auto-tiles and Godot 4 / Tiled import and painting.
- **Phase 22 — corner/multi-terrain sets, animated tiles, solid flags and AI seam repair:** visual seams, exported collision and animation, and especially Godot multi-terrain painting semantics.

Automated tests exercise internal logic and fake SDXL calls; they do not establish real GPU quality, VRAM behaviour, Tauri/browser rendering or Godot/Tiled import compatibility. Track observed failures before adding more export formats.

## Candidate next features

1. **Animate: start and end reference frames (requested):** accept optional sprites for the first and final poses, align their rigs and palettes, then interpolate or use guided in-betweens. First decide how one-shot versus looping clips behave and how to handle differing silhouettes.
2. **Art-derived tile collision/navigation:** generate polygons from tile art instead of only the current full-square solid flag; add collision for terrain sets.
3. **Tile styling and transitions:** AI-painted/hand-drawn terrain edges, per-pair border widths, and corrected Godot multi-terrain metadata after testing.
4. **First-run setup wizard / model manager:** check required SDXL files and dependencies, show optional IP-Adapter/ControlNet download progress, and configure llama.cpp.
5. **Custom keyframed clips:** edit pose keyframes, interpolate, save/share animation clips and tune secondary motion per clip.
6. **Animation/graphics improvements:** soft joint deformation, higher consistency across generated views, and editor layers/copy-paste/tile mode.
7. **More exports:** Aseprite `.aseprite`, Godot `AnimationPlayer` scenes, Unity prefab generation.
8. **Automatic rig-weight tuning from AI cleanup:** experimental because mapping edited pixels back to the rig is unreliable.

## Known limits

- **SDXL only.** Flux / HiDream / Qwen / SD1.5 checkpoints are not supported by this pipeline.
- On an **8 GB GPU**, ControlNet/skeleton mode uses CPU/sequential offload and may take minutes per image; large generation settings can still cause OOM.
- Reference-pose and view generation may drift from the character's original identity or silhouette. The rig produces the most repeatable animation frames.
- Rig movement uses rigid parts; front/back walking is a simplified step-and-bob, three-quarter views are approximate, and elbows/knees can look stiff.
- AI joint cleanup is slow and most useful for small frames; its output must be reviewed.
- Current tile collision is a full square for manually marked solid tiles; **art-derived polygons and terrain collisions are not implemented**.
- Godot/Tiled outputs are format-tested, but **import/painting must be verified in the actual target editors**. Multi-terrain Godot painting is explicitly best effort.
- The desktop shell targets Windows; real inference, memory use and renderer behaviour are not established by the headless unit tests.

## Maintenance follow-ups

Clean up already-tracked runtime files (local configuration, logs, history) and duplicate root phase notes *separately* after confirming any needed user data is backed up. See [Repository workflow](REPOSITORY_WORKFLOW.md).

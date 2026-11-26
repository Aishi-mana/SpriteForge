# Roadmap and known limits

This is a **candidate backlog**, not a release promise. The repository now includes implementations through Phase 48 (validation pending); see [the handoff](../HANDOFF.md) and [phase notes](phases/) for implementation history. Functional correctness and hardware validation are separate.

## First: verify the newest delivered features

The previous handoff recorded user testing through Phase 18, but **Phases 19-22 were not confirmed on the target laptop** at that point. Use the [manual testing checklist](TESTING_CHECKLIST.md), especially steps 15-22, before treating the following as production-ready:

- **Phase 19 — queue and history:** multi-job queue, pause/cancel, restart persistence, fork/re-run/compare.
- **Phase 20 — tiles and props:** seamless tiles, workbench, packed atlas and tileset exports.
- **Phase 21 — terrain sets:** 47-blob / 16-edge auto-tiles and Godot 4 / Tiled import and painting.
- **Phase 22 — corner/multi-terrain sets, animated tiles, solid flags and AI seam repair:** visual seams, exported collision and animation, and especially Godot multi-terrain painting semantics.

Automated tests exercise internal logic and fake SDXL calls; they do not establish real GPU quality, VRAM behaviour, Tauri/browser rendering or Godot/Tiled import compatibility. Track observed failures before adding more export formats.

## Implemented since Phase 22 (live verification pending)

- Phase 23: multi-style pixel and HD character generation.
- Phase 24: HD rig animation and exports.
- Pose preset library: editable and reusable Reference Pose presets.
- Phase 25: custom rig keyframes.
- Phase 26: actual first/final reference images and AI or crossfade in-betweens.
- Phase 27: optional soft elbow/knee deformation.
- Phase 28: multi-model text generation and LoRA family checks; standalone NetaYume and Qwen Rapid routes using shared local model files and native image references. SDXL-only ControlNet/inpaint remain.
- Phase 29: master-reference directional character generation, shared framing, palette and approved-view locks.
- Phase 30: feature-level reference guidance and separate appearance candidates.
- Phase 31: modular layer compositor and reusable recipes.
- Phase 32: AI-assisted isolated modular assets, approximate fitting and explicit approval.

See the corresponding [phase notes](phases/) for scope and limitations. Regression tests have been added but the full suite and live hardware workflows have not been verified.

## Candidate next features

1. **Phase 33 implemented (validation pending):** modular bone attachments, body-only saved rig and standard clip previews/export. Phase 34 adds opt-in soft elbow/knee garment meshes and independent spring-chain motion for flexible layers (validation pending). Phase 35 adds synchronized independent animation sheets and an engine-neutral manifest with optional hidden alternatives (validation pending). Phase 36 bundles Godot 4 and Unity desktop runtime components for synchronized clip playback, equipment choices and loadout persistence (engine validation pending). Phase 37 adds optional manual two-bone weight painting, explicit depth overrides and selected body-part occlusion baked into exported layers (validation pending). Phase 38 adds a cross-project character/asset/rig snapshot library and local model/LoRA readiness manager (validation pending). Phase 39 begins integration testing and stability fixes; full validation is a release gate before new character features.
2. **Character improvements:** precise masked editing, semantic asset extraction, garment fitting, improved multiview conditioning and per-clip secondary motion presets.
3. **First-run setup wizard:** extend Phase 38 model readiness inspection with dependency version validation and optional IP-Adapter/ControlNet setup.
4. **Pixel editor extras:** layers, copy/paste, tile mode, outline/shade tools and palette ramps.
5. **More exports:** Aseprite `.aseprite`, Godot `AnimationPlayer` scenes, Unity prefab generation.
6. **Automatic rig-weight tuning from AI cleanup:** experimental because mapping edited pixels back to the rig is unreliable.
7. **Deferred tiles/terrain:** art-derived collision/navigation polygons, AI-painted terrain edges, per-pair border widths and Godot multi-terrain verification. Resume after character work.


## Known limits

- **Model support is architecture and layout dependent.** SDXL retains reference, skeleton and inpainting; the specific standalone NetaYume and Qwen Rapid routes add native image references. SD1.5 and supported Diffusers-format Lumina 2, FLUX.1, SD3 and Qwen-Image text-generation routes are experimental. Check exact model/LoRA compatibility and installed runtime components.
- On an **8 GB GPU**, ControlNet/skeleton mode uses CPU/sequential offload and may take minutes per image; large generation settings can still cause OOM.
- Reference-pose and view generation may drift from the character's original identity or silhouette. The rig produces the most repeatable animation frames.
- Rigid movement remains available; optional soft mesh elbows/knees can stretch or fold. Front/back walking is simplified and three-quarter views approximate. AI reference guidance does not guarantee identity or exact feature locks.
- AI joint cleanup is slow and most useful for small frames; its output must be reviewed. Modular asset generation is not semantic extraction or exact garment fitting. Modular animation supports independent baked layer sheets; the runtime is not a live skeletal system.
- Current tile collision is a full square for manually marked solid tiles; **art-derived polygons and terrain collisions are not implemented**.
- Godot/Tiled outputs are format-tested, but **import/painting must be verified in the actual target editors**. Multi-terrain Godot painting is explicitly best effort.
- The desktop shell targets Windows; real inference, memory use and renderer behaviour are not established by the headless unit tests.

## Maintenance follow-ups

Clean up already-tracked runtime files (local configuration, logs, history) and duplicate root phase notes *separately* after confirming any needed user data is backed up. See [Repository workflow](REPOSITORY_WORKFLOW.md).

Phase 40: independent custom skeleton hierarchy editor and rigid CPU pose preview; Phase 41 adds normalized multi-bone mesh binding and weight painting. Phase 42 adds custom rig rotation tracks, interpolation, onion skins, playback and baked clip export. Phase 43 adds analytical two-bone IK, target tracks and authored canvas-space foot contacts. Phase 44 adds selective masked SDXL cleanup and non-destructive accepted custom timeline frames. Phase 45 adds editable bone mappings, reusable motion bundles and proportional IK/contact retargeting. Phase 46 adds multi-actor scene composition, independent timing and flattened scene export. Phase 47 adds deterministic procedural VFX, actor attachments and transparent effect export. Phase 48 adds persistent generation batches and sequential project animation exports. Next Phase 49 performance and integration validation.

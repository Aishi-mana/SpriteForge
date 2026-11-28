# SpriteForge — maintainer handoff

> **Required for all contributors and AI agents:** read [AGENTS.md — mandatory user-first UX policy](AGENTS.md#mandatory-user-first-ux-policy--read-before-every-change) before making changes. Essential actions must be visible, discoverable, and easy to repeat.

**Snapshot:** GitHub implementation baseline `0f3df14f4224`, Phase 61Q-F, merged 2026-11-27T11:40:01Z.  
**Repository:** [Aishi-mana/SpriteForge](https://github.com/Aishi-mana/SpriteForge) (public, verified 2026-11-27).  
**Source of truth:** this repository, not the historical phase ZIP files.

**VFX implementation:** 61P-A through H merged and CPU-validated on their PRs; final main validation passed (45976217804); desktop/GPU/native engine import acceptance pending. Main automatic CPU triggers restored with public-only job condition; public visibility confirmed; standard runners eligible for free execution. See the living diary for current status.

**World Studio:** 61Q-A–F merged and CPU/JS-validated on their PRs. Initial World Studio scope integrated; final main CI passed, desktop/GPU acceptance pending. Phase 61R-A System Asset Studio foundation implemented on feature branch; CPU/JS validation pending. Next B shared game style profiles and AI kits. Raster-first quarter-view maps, shared-layout AI plates and props, style profiles, effective masks, polish and session-only character movement/actions/VFX preview.

Start with the [living implementation diary](docs/IMPLEMENTATION_DIARY.md), [README.md](README.md), [Architecture](docs/ARCHITECTURE.md), [Development](docs/DEVELOPMENT.md), and [Repository workflow](docs/REPOSITORY_WORKFLOW.md).

## Current animation milestone (2026-11-28)

62K-A AnimateDiff backend merged via PR #142 (CPU #348 passed, merge daa53d1). 62K-B guided local setup merged via #143 (CPU #354 passed, merge 78cf0a9). C and D merged via #146 (CPU #357 passed, merge ca429a9). Desktop detection revealed legacy UNet/VAE .bin weights; verified conversion hotfix #147 passed CPU #360 and merged at fcb609c. User now has Safetensors files and both models are detected; runtime VAE slicing API hotfix and BiRefNet default merged via #148 (CPU #362 passed, merge 0bb359b). User reports AnimateDiff runs but motion quality is disappointing. See [AnimateDiff setup](docs/ANIMATEDIFF.md). Desktop GPU and visual acceptance remain open. [Phase 62L roadmap](docs/PHASE62L_ANIMATION_ROADMAP.md) parked at user request; proposed order D neural interpolation, then C AI keyframes. General text-to-video and other Wan motion guidance improvements remain deferred. Visible Wan ending pose hotfix #150 passed CPU #369 and merged at 33b4d84. User confirmed Standard retained 20 sampling steps after switching from Native; fast-default hotfix implemented on feature branch, validation pending. See [Wan ending poses](docs/WAN_ENDING_POSES.md).

## What this project does

A Windows-local pixel-art sprite studio built around **SDXL + pixel-art LoRA**. Python/FastAPI in `engine/` serves the single-file vanilla-JS `ui/index.html`; a Tauri v2 desktop window in `src-tauri/` starts and stops the local engine. Optional local chat uses a `llama.cpp` server and a GGUF model.

Users can generate/pixelize sprites, make reference-guided poses and expressions, rig and animate characters (11 procedural clips, secondary motion and optional inpaint cleanup), edit palettes/pixels, use mannequins and directional sheets, queue generations, and build/export tilesets, terrain sets and animated tiles. Exports target PNG/GIF, Godot 4, Unity and Tiled depending on feature. See [User guide](docs/USER_GUIDE.md).

Primary deployment target was a Windows laptop with an NVIDIA GPU with **8 GB VRAM**, so SDXL pipeline memory/offload tradeoffs matter. Required model weights live in a configured external models directory; models are **not** bundled with the repo.

## Read, run, test

```bat
rem From the repo root on Windows
spriteforge.bat           rem Tauri if installed; otherwise browser fallback
run.bat                   rem engine/browser-only
python tests/run_all.py   rem model calls faked; Node.js needed for JS tests
```

- Engine: `python -m engine.main`, bound to `127.0.0.1` (default port 8765).
- UI edits take effect on reload; Python edits require restart. Rust/Tauri changes require `spriteforge.bat rebuild`.
- With no models or GPU, many algorithm/API tests can run, but a full GPU acceptance test cannot.
- GitHub Actions CPU validation runs the Python/Node suite on Windows and Ubuntu. Latest merged implementation PR #80 passed [CPU validation](https://github.com/Aishi-mana/SpriteForge/actions/runs/45922429701). This does not establish GPU or desktop acceptance.
- Run [Manual testing checklist](docs/TESTING_CHECKLIST.md) for hardware and Godot/Tiled validation.

## Features and confidence as recorded in previous phase notes

| Phase | Scope | Historical verification status |
|---|---|---|
| 1-11 | Core generation, reference/pose, rig, projects, exports, assistant, portrait | Previously confirmed for major workflows; game-engine importer verification remained open |
| 12-13, 15.1 | Pixel quality, diagnostics and model-classifier hotfix | Installed; the 15.1 fix addressed a real generation-blocking regression |
| 14-18 | Pixel editor, palettes, secondary motion, templates, 4/8 directions | Previous handoff reports these were user-tested and working |
| 19 | Queue/history | Delivered; real-laptop testing not recorded |
| 20 | Tiles/props, workbench and tileset export | Delivered; real-laptop and editor-import testing not recorded |
| 21 | Blob/edge terrain sets | Delivered; Godot/Tiled painting not confirmed |
| 22 | Corner/multi-terrain, animated tiles, solid collision, AI seam repair | Delivered; real SDXL and Godot/Tiled behaviour not confirmed |

These are **historical reports**, not new test results. Details: [Changelog](CHANGELOG.md) and [phase notes](docs/phases/). Later phases through 61K-G are documented in the living diary.

## Implementation map and pitfalls

- `engine/main.py`: FastAPI routes and request validation. `generate.py`: cached SDXL, IP-Adapter, ControlNet and inpaint. `pixelize.py`: crisp conversion.
- `rig.py`, `refine.py`, `directions.py`, `templates.py`: animation, cleanup, view and mannequin pipelines.
- `tiles.py`, `terrain.py`: tile workbench, seam repair, animation, autotile exports. `jobs.py`: persistent queue/history.
- `projects.py`, `palettes.py`, `exporter.py`, `portrait.py`, `diag.py`, `llm.py`: supporting subsystems.
- `ui/index.html`: all sidebar controls, tab content, state restoration, editor and JS helpers in one file. Test all UI changes with `tests/test_ui.py` and Node.js.
- Rigs use **continuous coordinates** (a pixel occupies `[i, i+1)`), not pixel centres. Mirroring and joint transforms are sensitive to this.
- Model classification must not mislabel real SDXL models; the `<option>` display label and its `value` must stay separate.
- Keep tests realistic; fake model functions must preserve current signatures. Do not claim successful GPU/engine integration from mocked tests.

## Project data and Git caution

Runtime data goes into `config.json`, `projects/`, `history/`, `exports/`, `palettes/`, and logs. **This initial Git snapshot includes a tracked configuration file, diagnostics and log/history entries.** Do not accidentally recommit local changes to them, paste their contents into issues or remove them without a backup. `.gitignore` does not retroactively remove files already in Git history.

See [Repository workflow](docs/REPOSITORY_WORKFLOW.md) for a follow-up cleanup plan. Keep code/documentation PRs separate from any data/history rewrite.

## What's next

1. Phase 61L-A through G merged; perform manual acceptance. Phase 61M-A–F merged; 61M-G stabilization pending validation and real-model acceptance. 61M exact-fit modular assets follow. Continue manual reference-editing acceptance and measure GPU resource usage.
2. Target Windows GPU and desktop acceptance; native engine import checks remain outstanding.
3. Phase 62 packaging is on hold.
4. Review tracked runtime data separately, after backups.

**Working agreement:** use focused branches and PRs, update tests and phase notes, append timestamped entries to the [living diary](docs/IMPLEMENTATION_DIARY.md) for implementations, fixes, validation and merges. Update current status in the README and roadmap; never claim unverified hardware results.

## Direct Animation Editor milestone (2026-11-29 PHT)

64A–H merged; #168 CPU run 46167123563 passed and merged at 0716b2f4. 64I integration changes and desktop checklist on feature branch; CPU and actual desktop/GPU acceptance pending. See [64I acceptance](docs/phases/PHASE64I.md). Phase 65 unified asset library next.

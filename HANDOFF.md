# SpriteForge — maintainer handoff

**Snapshot:** GitHub `main`, Phase 22 codebase, reviewed for documentation on 2026-11-26.  
**Repository:** [Aishi-mana/SpriteForge](https://github.com/Aishi-mana/SpriteForge) (private).  
**Source of truth:** this repository, not the historical phase ZIP files.

Start with [README.md](README.md), [Architecture](docs/ARCHITECTURE.md), [Development](docs/DEVELOPMENT.md), and [Repository workflow](docs/REPOSITORY_WORKFLOW.md).

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
- The existing code has a standalone test runner, not a declared GitHub Actions workflow. **This documentation refresh has not run the suite against a full checkout or verified hardware.**
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

These are **historical reports**, not new test results. Details: [Changelog](CHANGELOG.md) and [phase notes](docs/phases/). Phase 22 is the last documented feature phase.

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

1. Confirm target-laptop results for Phases **19-22**, particularly multi-terrain painting in Godot and animated/collision tile imports in Godot/Tiled; attach errors/screenshots without exposing local configuration.
2. Fix observed issues with a regression test, update docs and include a clear manual-verification note in the PR.
3. Choose a next feature from [Roadmap](docs/ROADMAP.md), prioritizing the previously requested **Animate start/end reference sprites**.
4. Clean up tracked runtime files and duplicate top-level `PHASE*.md` files after a deliberate review and backup.

**Working agreement:** prefer a short-lived GitHub branch and PR, update tests/docs with changes, state what was actually verified, and avoid ZIP-as-source-of-truth instructions.

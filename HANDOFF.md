# SpriteForge - handoff (state: end of phase 22)

Read this first, then `README.md` and `docs/ARCHITECTURE.md`. Everything here is current as of the zip it ships in.

## 1. What this project is
A local, offline **AI pixel-art sprite studio** for the user's Windows laptop: SDXL + the pixel-art LoRA generate sprites; a bone **rig** animates them (11 procedural clips, secondary motion, optional AI joint cleanup);
export gives sprite sheets + Godot 4 / Unity data. Extra tabs: Reference pose (IP-Adapter + OpenPose ControlNet), Pixelize, Portrait (+ expressions), Palette tools, Template (mannequin + reference), Directions (4/8-way),
a pixel editor, projects, a local llama.cpp assistant, and Diagnostics. Stack: Python (FastAPI/uvicorn, diffusers, numpy/scipy/Pillow) backend `engine/`, one-file vanilla-JS UI `ui/index.html`, Tauri v2 window `src-tauri/`.

## 2. Bootstrap in a new chat (do this first)
The project arrives as `spriteforge_FULL_phase22.zip` (plus this file). In the sandbox:
```bash
mkdir -p /home/claude && cd /home/claude && unzip -oq /mnt/user-data/uploads/spriteforge_FULL_phase22.zip
cd spriteforge && python3 tests/run_all.py        # expect: 435+ checks, ALL TEST FILES PASSED (~1 min; numpy/pillow/scipy present, node present)
```
Sandbox facts: **no GPU, no network** (cannot run SDXL / download models), no fastapi/pydantic/torch (tests stub FastAPI; model calls are faked). The sandbox **can reset** between turns (it happened twice in the last session: working files vanished,
only delivered zips survived and the tree was rebuilt by unzipping every phase zip in order). So: always deliver work as zips, and save checkpoint zips into `/mnt/user-data/outputs` while working.

## 3. The user and how to work with them
- Windows laptop, **RTX 5070 Laptop (8 GB VRAM), 32 GB RAM**. Models in `C:\Users\Admin\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models` (ComfyUI shared folder: checkpoints include sd_xl_base_1.0, animagine-xl-4.0, juggernautXL, plus Flux/HiDream files that **cannot** be used;
  LoRAs include pixel-art-xl-v1.1, Line_Art_SDXL, Qwen/Wan/Flux LoRAs that cannot be used). llama.cpp at `C:/AI/llama-cpp/llama-server.exe`, assistant model `gemma-3-4b-it-Q4_K_M.gguf` (2.3 GB) - works.
- Launch: `spriteforge.bat` (Tauri window; works). The user tests on the laptop **later**, sends **screenshots** and error text, then asks for the next thing. Casual, short messages (often ending with "~"), expects progress without lots of questions.
- **Delivery format (keep doing this)**: after each phase deliver a zip with **only the changed/new files** + a `PHASEn.md` note, named `spriteforge_phaseN_topic.zip` (hotfix: `phaseN.1_HOTFIX-...`), call `present_files`, then a clear summary:
  what changed, what was verified here vs not, what to expect, limits, and 1 question about what's next. Never ship `config.json` (user's paths). Tell them when a Tauri rebuild is needed (`spriteforge.bat rebuild`; Rust files only).
- Be honest about what cannot be verified in the sandbox (real SDXL, VRAM, browser rendering, Godot/Unity import). When a bug is reported from a screenshot, find the **root cause**, fix it, and add a test that would have caught it.
- Tests are part of delivery: extend `tests/`, run `python tests/run_all.py` before zipping. Update `docs/` and `CHANGELOG.md` (add `docs/phases/PHASEn.md`) with each phase.

## 4. Phase history and status
"Confirmed" = the user ran it on the laptop and reported it working (their words at phase 11: "everything up to portrait is working"; screenshots of generation, reference pose, rig, portraits, expressions, assistant).
| phase | what | status |
|---|---|---|
| 1 | engine + browser UI, SDXL txt2img, pixelize | confirmed |
| 2 / 2.1 | Reference pose (IP-Adapter), Tauri shell + bat; fix `enable_vae_tiling` | confirmed |
| 3 / 3.1 | skeleton editor + ControlNet, fixed canvas; OOM fix (sequential offload, generation size) | confirmed (identity/pose adherence is a known limit) |
| 4 | rig animation (clips, preview, export sheet/GIF) | confirmed |
| 5 | AI joint cleanup (inpaint around moving joints) | reported working with phase 11 |
| 6 / 7 | projects (save/load/autosave/gallery); review, redo, diff, onion, results saved | confirmed |
| 8 | 6 more clips (hurt, death, cast, climb, block, cheer) | confirmed |
| 9 | export layouts: Godot 4 `.tres/.tscn`, Unity json + importer, Aseprite-style JSON | files confirmed; **engine import not confirmed** |
| 10 | local assistant (llama.cpp via llama-server, Apply buttons) | confirmed |
| 11 | portrait + expressions (inpaint only the face area) | confirmed |
| 12 | quality pass: crisp converter, grid snap, OKLab palette, outline, sampler | installed (UI shows its controls); no explicit feedback |
| 13 | Diagnostics (+ model tagging) | installed; **introduced the "cannot generate" bug** |
| 14 | pixel editor | delivered, **untested by user** |
| 15 | palette tools | delivered, untested |
| 15.1 | HOTFIX: option value corruption + classifier flagged real SDXL as non-SDXL | delivered (the user's reported "cannot generate") |
| 16 | secondary motion (cape/hair/tail springs) | delivered, untested |
| 17 | sprite templates + reference (mannequin dummies, inpaint in silhouette) | delivered, untested |
| 18 | 4/8-direction sheets (5 views + mirrors, view-aware walk, aligned export) | confirmed by the user ("everything tested and working", before phase 19) |
| 19 | generation queue + history (engine/jobs.py, Queue tab, re-run/fork/compare) | delivered, untested on hardware |
| 20 | tiles and props (engine/tiles.py, Tiles & props tab: seamless tiles, workbench, tileset export Godot .tres / Tiled .tsx / atlas) | delivered, untested on hardware |
| 21 | autotile / terrain sets (engine/terrain.py: 47-blob + 16-edge, lookup, Godot terrain .tres, Tiled wang set) | delivered, untested on hardware |
| 22 | tile follow-ups: corner16 + multi-terrain sets (81/256 tiles), animated tiles (scroll/ripple/shimmer), solid/collision export, AI seam repair | delivered, untested on hardware (Godot multi-terrain painting rules are best effort) |
Delivery order was 13, 14, 15, 15.1, 16, 17, 18, 19, 20, 21, 22. The user reported phases 14-18 tested and working.

## 5. Cheat sheet (details in docs/ARCHITECTURE.md)
- Engine modules: `main` (all HTTP endpoints, 65 routes), `jobs` (queue + history), `tiles` (tiles/props, tileset export), `terrain` (autotile sets), `generate` (SDXL pipelines, one cached; txt2img / IP-Adapter / ControlNet / inpaint), `pixelize` (crisp converter), `rig` (bones, clips, secondary motion, render),
  `refine` (AI joint cleanup), `portrait`, `templates` (mannequins + generate from template), `directions`, `palettes`, `exporter`, `projects`, `diag`, `llm`.
- **Coordinates are continuous** (pixel i spans [i, i+1)). Joints: 15 names, `l_`/`r_` = screen sides. Bone labels 0-9 (+10 cape, 11 hair, 12 tail). Rotation clockwise-positive; `F=-1` facing right.
- Only **SDXL** works. `diag.inspect_file` classifies model files from tensor names (check SDXL markers FIRST; block only positively-identified incompatible families).
- UI: everything in `ui/index.html`; sidebar controls with ids are **auto-saved** in projects; non-input state needs explicit save/load (see DEVELOPMENT.md "A tab").
- Patch `ui/index.html` with small Python replace scripts that `assert old in text`; always `node --check` the script and re-run `tests/test_ui.py`.
- Pitfalls already hit: see `docs/DEVELOPMENT.md` "Lessons learned" (realistic test data; option `value`; continuous coords; never drop pixels; perceptual colour maths; VRAM limits).

## 6. Verified vs not verified (as of this handoff)
- **Verified in the sandbox (435 automated checks, 14 files)**: pixel conversion accuracy, palettes, rig clips and secondary motion, all 970 mannequin variants, template/direction generation logic with a fake model, exports (layouts, pivots, Godot/Unity data structure),
  projects, endpoints (called directly), diagnostics, assistant manager against a fake server, pixel-editor logic and interactions on a fake DOM.
- **Not verifiable here**: real SDXL/IP-Adapter/ControlNet/inpaint runs and image quality, VRAM/speed, the real browser/Tauri rendering, the pixel editor and the Palette/Template/Directions tabs in a real browser, importing exports into Godot 4 / Unity
  (the C# importer was never compiled), llama.cpp with other models.
- Expect first-run errors in untested-on-hardware features; Diagnostics + `engine.log` + screenshots are the debugging loop.

## 7. Open items and what the user was about to choose
The remaining menu: **first-run setup wizard / model manager**, remaining tile follow-ups (collision from art, AI hand-drawn borders), custom clips; the user also asked (roadmap) for **Animate start + end reference frames** (also: custom keyframed clips, soft joint deformation, better multi-view consistency, pixel-editor extras - see `docs/ROADMAP.md`).
Before building the next feature, ask the user for test results of phases 14-18 (use `docs/TESTING_CHECKLIST.md`), and fix what they report first.

## 8. First actions for the new chat
1. Bootstrap (section 2) and run the tests. 2. Skim `README.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`. 3. Greet the user briefly, say the project is loaded and all tests pass, and ask for **laptop test results / screenshots** of the newest phases (or what feature they want next).
4. Keep the delivery format of section 3. 5. If the sandbox ever resets again: re-unzip the full zip (and any later phase zips in order).

## 9. File map
```
spriteforge.bat run.bat requirements.txt config.example.json README.md CHANGELOG.md HANDOFF.md
engine/*.py (17)   ui/index.html   shell/index.html   src-tauri/{Cargo.toml,build.rs,tauri.conf.json,src/main.rs,icons/}
tests/_common.py test_*.py (14) js/*.js run_all.py        docs/{USER_GUIDE,ARCHITECTURE,DEVELOPMENT,TESTING_CHECKLIST,ROADMAP}.md  docs/phases/PHASE*.md
```

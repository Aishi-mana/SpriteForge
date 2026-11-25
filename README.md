# SpriteForge

A **local, offline AI pixel-art sprite studio** for Windows: generate character sprites, give them poses, animate them
with a bone rig, and export sprite sheets with ready-made Godot 4 / Unity data. Everything runs on your own machine
(SDXL via `diffusers`, plus an optional local chat assistant through `llama.cpp`).

Built for an 8 GB laptop GPU (RTX 5070 Laptop, 32 GB RAM): SDXL runs with CPU offload; the assistant runs on the CPU.

## What it does

| Tab | Purpose |
|---|---|
| **Generate** | Text to sprite: SDXL + the pixel-art LoRA, then a *crisp* pixel conversion (grid snap, perceptual palette, no blended colours). |
| **Reference pose** | Take a sprite as reference (IP-Adapter) and make new poses, optionally steered by an OpenPose **skeleton editor** (ControlNet). |
| **Pixelize** | Convert any image to real pixel art (fixed size or auto-detected grid), palette presets, outline, clean-up. |
| **Animate** | The core: a 10-bone **rig** over your sprite, 11 procedural clips (idle, walk, run, climb, cheer, attack, cast, block, jump, hurt, death), **secondary motion** for capes/hair/tails, optional **AI joint cleanup**, frame review, export. |
| **Portrait** | Base portrait (text or from a sprite) + a set of **expressions** that repaint only the face area. |
| **Palette** | Import/export palettes (.hex .gpl .pal, swatch PNG), your own library, remap with dithering, merge/reduce, hue variants, shading ramps. |
| **Template** | A neutral **mannequin** (with a ready rig) + a **reference image** produce a sprite with the template's exact size and silhouette. |
| **Directions** | 4/8-direction characters (5 views + mirrors), view-aware walk cycles, one aligned sprite sheet per animation. |

Also: a **pixel editor** (Edit buttons everywhere), **projects** (save/load/autosave), a **local assistant chat**
(proposes prompts/settings as "Apply" buttons), and a **Diagnostics** panel (GPU, models, downloads, self-tests).

## Install and run (Windows)

1. Install **Python 3.10-3.12**. For the desktop window also install **Rust** (rustup.rs), the VS C++ Build Tools and WebView2 (built into Windows 11).
2. Copy `config.example.json` to `config.json` and set `models_dir` (the folder containing `checkpoints/` and `loras/`),
   **or** just start the app and set it in the sidebar. Use forward slashes.
3. Double-click **`spriteforge.bat`**. First run creates `.venv`, installs PyTorch (CUDA 12.8 build, required for RTX 50-series) and
   the requirements, builds the Tauri window once, and launches. Without Rust it opens in your browser at http://127.0.0.1:8765.
   `run.bat` = browser-only mode. `spriteforge.bat rebuild` rebuilds the Tauri shell.
4. Needed models (SDXL only): `sd_xl_base_1.0.safetensors` in `checkpoints/` and `pixel-art-xl-v1.1.safetensors` (nerijs/pixel-art-xl) in `loras/`.
   Reference/skeleton/template features download the SDXL IP-Adapter (~3 GB) and OpenPose ControlNet (~2.5 GB) from Hugging Face **once**.
5. Optional assistant: put llama.cpp's `llama-server.exe` and a chat `.gguf` (3-4B, Q4) under `C:/AI`, open the assistant's settings, press Scan.

**First thing to do after installing: press 🩺 Diagnostics.** It checks Python packages, the GPU (including whether your PyTorch build supports an RTX 50-series), model files,
downloads, the assistant, and runs the app's own self-tests.

## Folder layout

```
spriteforge/
  spriteforge.bat  run.bat  requirements.txt  config.example.json   launch + setup
  engine/        Python backend (FastAPI + all the image/rig/export logic)  -> docs/ARCHITECTURE.md
  ui/index.html  the entire web UI (one file, vanilla JS)
  src-tauri/     Tauri v2 desktop shell (starts/stops the engine)   shell/ = its loading page
  tests/         435-check test suite, no GPU needed:  python tests/run_all.py
  docs/          USER_GUIDE, ARCHITECTURE, DEVELOPMENT, TESTING_CHECKLIST, ROADMAP, phases/ (per-phase notes)
  projects/ exports/ palettes/   created at runtime (your data)
  engine.log  llm.log  diagnostics.txt   created at runtime
```

## Documentation

- `docs/USER_GUIDE.md`  step-by-step workflows for every tab
- `docs/ARCHITECTURE.md`  modules, data formats, conventions, full API table
- `docs/DEVELOPMENT.md`  how to work on the code, test it, and add features
- `docs/TESTING_CHECKLIST.md`  ordered manual test plan for a real GPU
- `docs/ROADMAP.md`  ideas and known limits
- `CHANGELOG.md`  what each phase added;  `HANDOFF.md`  state of the project for a new maintainer/chat

## Troubleshooting (top 8)

| Symptom | Fix |
|---|---|
| Dropdowns empty | Models folder not set/found: set it in the sidebar. Check `engine.log`. |
| "checkpoint not found ... ⚠" | You have an old build (< 15.1). Update; the dropdown tagging bug is fixed there. |
| Checkpoint is tagged `⚠ not SDXL` | Flux / HiDream / SD1.5 files cannot be used. `? not recognised` files are allowed but may fail. |
| CUDA out of memory | Skeleton mode: lower *Generation size* (640), Variations 1, close GPU apps. Run 🩺 GPU test. |
| RTX 50-series "no kernel image" | PyTorch must be the cu128 build; Diagnostics tells you. `pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu128` |
| First reference/skeleton run is slow | It downloads the IP-Adapter / ControlNet once. |
| Assistant can't load | Diagnostics > Assistant; see `llm.log`. Only a file named `llama-server` and a `.gguf` are accepted. |
| Tauri build fails | Install Rust + VS C++ Build Tools, or use browser mode (it falls back automatically). |

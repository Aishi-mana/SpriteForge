# Phase 62E — Desktop and GPU acceptance

Status: acceptance tooling implemented; execution pending. PRs #117 and #118 merged after CPU validation.

## Local evidence

Launch SpriteForge using spriteforge.bat. From a second terminal in the repository root run:

    .venv\Scripts\python.exe tests\live_acceptance.py

For an explicitly selected installed SDXL checkpoint, while the queue is idle:

    .venv\Scripts\python.exe tests\live_acceptance.py --checkpoint "YOUR_CHECKPOINT.safetensors" --output gpu-acceptance.json

The probe checks live HTTP UI delivery, state, queue, built-in diagnostics, resource snapshots and optionally the existing real SDXL benchmark. It does not start the engine, install models, release resources, or exercise desktop interactions. Diagnostics writes its normal local report. GPU inference can load models and may download dependencies if uncached; run only when ready. A failed or timed-out request is not proof inference stopped. Do not rerun until the engine is idle. GPU peak is the benchmark's PyTorch allocator measurement, not whole-device peak or model-load peak. Do not commit reports or logs. Run tests/browser_smoke.py separately following PHASE62B.md.

## Manual release gate

Record commit, Windows/WebView2 version, GPU/driver, model and settings, pass/fail/blocked/not run, and evidence for each row. Use a disposable project and back up existing projects.

| Workflow | Required evidence |
|---|---|
| Desktop startup/shutdown | Tauri window renders; restart and verify engine shuts down cleanly |
| Navigation and queue | All workspaces accessible; rig/full-frame and More actions work on real result |
| Generation and exact-reference editing | One real output per installed supported backend, preserve reference and record failures |
| Rig and full-frame | Preview, edit, playback, save and export; include video route if installed |
| Persistence | Save/reopen disposable project; verify gallery, markers, directional frames and layers |
| World and system assets | Playtest collision and animation; verify layer and UI asset exports |
| Export | Open PNG/WebP and animation pack; inspect alpha, dimensions, timing and metadata; target engine import |
| Resource recovery | Record resource status before/after inference and explicit UI release; compare allocator and device memory separately |
| Responsiveness | Navigate during queued inference, cancel, recover and retry; record observable freezes |

An API pass or CPU CI pass does not complete this gate. Missing model or hardware stays blocked/not run. Follow TESTING_CHECKLIST.md for detailed workflows.

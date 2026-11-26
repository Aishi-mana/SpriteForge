# Phase 39 — Integration testing, performance and stability

No new generation features. Phase 39 is a stabilization branch based on Phase 38.

## Changes
- Isolate sampler selection, queued progress and cancellation by worker thread; check cancellation before launch and between images. SDXL folder ControlNet uses from_pretrained.
- Local Comfy worker: 30-minute guard, bounded termination, delete successful scratch jobs and remove request/image files on failure; keep failure logs. Existing older job folders are untouched. Shutdown marks queued worker cancellation. A forcibly terminated parent can still leave worker files/processes behind.
- Cache safetensors family classification by file identity and modification time (bounded 256 entries); do not reload model weights to scan.
- Bound rig source dimensions/frame count/padding/supersampling/retained surface pixels and raw image batch allocation. Return actionable 400 for unsupported AI endpoint transitions; blend remains model-independent.
- Stage project image inputs before replacing existing files, and atomically replace each PNG. This is not a transaction covering the whole project directory.
- Test runner uses explicit UTF-8, offline model flags and 180-second timeout per file. Existing queue tests updated for thread-local progress; streaming endpoint test supports real FastAPI and stubs.

## Verification actually performed
- Phase 38 full UI JavaScript parsed; no missing literal element IDs or duplicate IDs.
- Actual pixel editor and model dropdown JavaScript unit-test source executed in a JS harness with repository HTML and filesystem/console stubs: 19 + 14 = 33 assertions passed.
- Phase 39 UI syntax checked.
- Full Python suite, GPU execution, actual browser/Tauri interaction and engine compilation are not verified in the chat environment. Do not treat added tests as passed. A CPU-only Linux/Windows CI workflow is included, plus validate.bat for installed Windows environments. CI does not download models or install torch.

## Windows validation
Run validate.bat in the repo after setup. It compiles Python sources and runs all tests; install Node if needed for JavaScript checks. Use a disposable project for manual testing. Do not overwrite existing production projects during validation.

### Manual acceptance checklist (RTX 5070 laptop, 8 GB VRAM / 32 GB RAM)
1. In Library, rescan models, verify NetaYume and both registered Qwen checkpoints resolve to the existing model folder and Qwen encoder/VAE; select matching LoRA or none.
2. Generate one non-explicit full-body character using each checkpoint. Start with Qwen 768 / 4 steps / CFG 1 and Neta 1024 / 20 steps / CFG 4. Record wall time, peak system RAM, peak VRAM, output dimensions and job log if failure. These are starting settings, not guaranteed memory/performance figures.
3. Use a master reference for a second angle and one appearance variation. Verify original master and locked views survive. Test cancel queued work and then generate again. Check no successful worker scratch remains.
4. Build a body + outfit + hair modular recipe, save rig, swap layer, test rigid/soft/spring/weighted motion and occlusion. Save project, reopen, confirm layer order, joints, paint and attachments. Save to Library and copy into a disposable project. Reject mismatched rig preset.
5. Export idle/walk/attack with all alternatives and same recipe. Check matching frame cells/pivots, manifest ordering, exported PNG transparency and reconstructed assembly. Open Godot 4 and Unity desktop, compile runtime scripts, load each clip, switch outfit, save/load equipment, test one-shot completion and invalid/incompatible manifests.
6. Validate legacy pixel generation, reference pose, custom keyframes, endpoint blend, templates, directions, palette/portrait/tile/terrain workflows before merging. No new tile/terrain features.

Do not mark the release stable until CPU tests and relevant device/engine checks pass. CI failure must be investigated, not ignored. No measured speedup or RAM reduction is claimed.

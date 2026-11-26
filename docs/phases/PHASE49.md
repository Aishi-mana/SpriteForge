# Phase 49 — Performance & integration validation

Status: initial CPU integration benchmark added; execution and broader validation pending.

Run from the repository root in the existing Python environment:

```
python tests/test_phase49_integration.py
python tests/run_all.py
```

The new test exercises eight animated actors, twelve effects, mixed sampling, attachment, transforms, 24 frames, JSON roundtrip, out-of-order scrubbing and rejection of oversized scenes. Three full renders report median wall time and rendered frames per second. No fixed timing assertion: host performance varies. Compare identical workloads on identical hardware and retain raw results. This is offline compositor throughput, not interactive playback FPS.

## Release gates

- CPU suite passes with Node.js present; record output and environment.
- Compare batch generation/retry/cancellation and project/export preservation using existing regression tests.
- On Windows, launch spriteforge.bat, run Diagnostics, verify GPU recognition and local model paths. Record cold/warm inference latency, peak dedicated GPU memory and peak process RAM; test one job before a 24-character batch.
- In Scenes, preview and export a representative multi-actor scene with attached effects; scrub, save, reload and compare output. Observe UI responsiveness and cached playback separately from render throughput.
- Exercise a sustained session with repeated generate, cancel, animate and export operations; record errors and memory trends. Verify Godot/Unity imports where applicable.
- No production performance claims or release sign-off until measured evidence is attached. Do not commit local configs, model weights, logs or user projects.

See DEVELOPMENT.md and TESTING_CHECKLIST.md for existing procedures.

# Phase 66D — GPU, VRAM and RAM optimization

## Changes
- Cache identity distinguishes active LoRA and ControlNet directories and generation versus inpaint. Unused directories do not trigger reload. Clear stale ControlNet metadata when evicting a pipeline. Existing single-pipeline cache and offload strategy unchanged.
- GPU/RAM resource panel reports device-wide free/total, engine allocator allocated/reserved/unused reserve, system available RAM, engine RSS and best-effort recursive child RSS. Child RSS may double count shared memory; external unrelated processes and WebView RAM are not included. Missing psutil or inaccessible metrics do not block generation. Install updated requirements for RAM reporting.
- Interpolation keeps a rolling pair of decoded input frames instead of all frames; hold skips artwork decoding within interpolation (validation still runs). Temporal inspection retains only per-frame metrics, not all decoded arrays. Correction algorithm unchanged.
- Explicit release/unload remains guarded by existing GPU lock. No new automatic unloading or quality/steps/resolution changes.

## Acceptance
CPU regressions for cache identity, RAM probe failure/worker exit, allocator reporting and interpolation decode behavior. JavaScript syntax preflight passed; Python execution and GPU/desktop acceptance pending. Record cold/warm generation time, GPU free/allocated/reserved, available RAM and process/child RSS before and after repeated Generate, Wan, AnimateDiff, interpolation and manual release/unload on target Windows machine. No measured memory reduction or speedup claimed.

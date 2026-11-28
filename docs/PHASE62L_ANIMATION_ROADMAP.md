# Phase 62L — Deferred anime sprite animation roadmap

Status: planning only, parked at user request on 2026-11-28 PHT. No runtime implementation authorized in this phase yet.

## Context

Phase 62K delivered the AnimateDiff backend, local model setup, motion profiles, benchmarking and runtime compatibility. User reports actual AnimateDiff motion quality is disappointing after desktop testing. Retain AnimateDiff as an optional backend; do not claim visual acceptance. The current preference is anime/stylized game artwork, not photorealistic video.

## Proposed order when resumed

1. **62L-D — Neural frame interpolation first.** Investigate a local RIFE or FILM implementation compatible with the Windows laptop and 8 GB GPU. Use existing manual/imported/generated keyframes. Preview interpolation before applying, retain exact anchor frames, support repeatable loop timing and transparent sprite extraction/export. Compare against existing CPU interpolation; do not claim improved quality until desktop tests. Preserve existing CPU option and original frames.
2. **62L-C — AI keyframe animation second.** Use compatible reference-conditioned image generation to propose 2–4 deliberate anchor poses for idle, blinking, walking, attacks, casting and custom motion. Provide visible preview, regenerate individual anchors, review and accept, then interpolate. Preserve character appearance and art style where feasible; no hard identity guarantee.
3. **62L-A — Anime image model compatibility** remains a related backlog item. Audit existing support for Illustrious XL, Pony XL and SD1.5 anime checkpoints before adding anything.
4. **62L-B — General-purpose text-to-video** remains deferred, including game effects and environment assets.
5. **62L-E — Reference consistency and animation benchmarking** remains a future comparative acceptance milestone.

## Acceptance and boundaries

Reuse the Full-frame Animation Studio, BiRefNet transparency default, timeline, preview, PNG/WebP export and benchmarking rather than creating disconnected tools. Make essential actions visible. Evaluate intentional motion, identity, lighting, silhouette, loop seams, alpha quality, speed and repeat generation on actual hardware. Model selection, licenses, local runtime dependencies and VRAM behavior require investigation when work resumes. No implementation, download, or CI dispatch for this planning record.

Deferred Wan improvements remain separately recorded in the living diary: typed motion precedence, lighting stability, balanced sampling, reusable seeds and spatial conditioning.

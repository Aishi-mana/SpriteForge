# Phase 66A — Full-system functional audit

Baseline: PR #178 merged e76907c6; CPU workflow 46177515167 success, Windows 2258 checks and Ubuntu 2267 checks. UI source inventory: 20 workspace tabs, 1066 literal event handlers, 1152 declared function names; literal function targets resolved with helper allowlist. This is not a click-through or GPU benchmark.

## Findings and fixes

- Queue input decoding outside exception boundary could terminate worker; now bad/missing input records error and next job can proceed.
- FileReader failure could leave queue promise unsettled; reject on error/abort.
- Out-of-order queue refresh and history detail could show stale state; request guards.
- Background job completion could replace another workspace's results; render only in originating workspace, history remains accessible.
- History failures and note/delete errors surfaced.
- Regression checks cover literal action targets, tabs, queue recovery, stale responses.

## Desktop audit matrix (pending)

| Workspace | Acceptance path |
|---|---|
| Generate, Reference, Template, Portrait | Generate twice, cancel/retry, result actions and saved settings |
| Character, Directions, Modular | Identity, edit, layer reuse, save/load |
| Pixelize, Palette | Import, edit, export and repeat |
| Rig, Custom rig, Full-frame | Source transfer, preview, edit, loop, export |
| Scenes, World | Paired actor clips, maps, collision/playtest |
| Tiles, VFX, System | Import, preview, render, export |
| Library, Production, Queue | Search, reuse, backup, batch and job recovery |

Record hardware, model, dimensions, seed, steps, cold/warm wall time, peak VRAM/RAM and failure recovery. No performance numbers claimed until measured. Existing standard Wan settings unchanged. Prioritize UX and native confirmation behavior in 66B; cross-studio result transfer in 66C; GPU and timing in 66D/E; previews in 66F; unified jobs in 66G; storage in 66H; diagnostics in 66I; desktop stress in 66J. Packaging on hold.

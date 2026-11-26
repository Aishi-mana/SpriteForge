# SpriteForge — living implementation diary

An append-only engineering record of implemented changes, fixes, decisions and verification. The repository is the source of truth; this diary complements the detailed [phase notes](phases/) and [roadmap](ROADMAP.md).

## Maintenance contract

- Every implementation or bug-fix PR must add a dated diary entry in the same branch, alongside tests and relevant phase documentation. Record actual date/time in ISO 8601 with offset (prefer UTC; Manila is UTC+08:00).
- Record phase/feature, purpose, changed modules/files, implementation decisions, compatibility and migration effects, tests and observed results, outstanding limitations, PR/commit references, and next action.
- When validation fails, record the failure and correction; when validation or merge succeeds, append a status update with actual timestamps and links. Never claim GPU, desktop or game-engine verification from CPU mocks.
- Keep previous entries intact; correct errors with a dated follow-up. Do not include secrets, local paths, prompts containing private data, logs or user assets.
- Status terms: implemented = code committed; validated = specific checks passed; merged = confirmed on main; hardware-verified = actually tested on target equipment.

## Backfill from GitHub history

The following entries are reconstructed from actual PR creation/merge metadata and PR descriptions, ordered by PR number (submission sequence, not merge sequence). Historical descriptions report confidence at submission, not current test status. Earlier Phases 1–22 predate this PR history; see [CHANGELOG.md](../CHANGELOG.md) and [phase notes](phases/) for their undated historical records. No dates have been invented.

### docs: refresh Phase 22 status and GitHub maintenance workflow

- Opened: 2026-11-25T18:02:02Z; merged: 2026-11-26T00:56:06Z (UTC).
- [PR #1](https://github.com/Aishi-mana/SpriteForge/pull/1); merge commit `28ff0c5f3b8e`.
- Recorded scope and verification at submission:

## Summary
- Bring README up to Phase 22: document queue/history, tiles/terrain/animation features, and real-device validation status.
- Replace obsolete ZIP-only maintainer instructions in HANDOFF with the GitHub source of truth and historical feature confidence.
- Update development/release workflow to branches, PRs, source/docs/tests together, and accurate Node.js test caveats.
- Prioritize Phases 19-22 hardware/editor validation in the roadmap while preserving the requested Animate start/end-reference feature.
- Add `docs/REPOSITORY_WORKFLOW.md` with a GitHub process, docs index, and careful follow-up plan for tracked runtime/user data.

## Checks
- Reviewed existing README, user guide, architecture, development guide, phase 20-22 notes, scripts, test runner and repository tree.
- Verified commit diff contains exactly 5 documentation files and all relative Markdown file links in changed docs resolve within the branch.
- **Not run:** `python tests/run_all.py` (this connector-based docs edit did not create a local full checkout).
- **Not verified:** GPU inference, Windows Tauri rendering, and Godot/Tiled imports.

## Follow-up (not done in this PR)
- Audit and untrack already-committed `config.json`, logs, diagnostics and `history/` in a separate reviewed housekeeping PR after backups. Adding `.gitignore` patterns alone is insufficient for tracked files.
- Review duplicate root `PHASE*.md` notes separately.
- Run Phase 19-22 manual checks on the target Windows machine / game editors.

Documentation-only change; no code or user data modified.

### Phase 23: multi-style HD character generation

- Opened: 2026-11-25T18:10:56Z; merged: 2026-11-26T00:56:26Z (UTC).
- [PR #2](https://github.com/Aishi-mana/SpriteForge/pull/2); merge commit `2731734bab14`.
- Recorded scope and verification at submission:

Initial implementation of retro pixel, anime, four chibi presets and custom illustration. Adds HD full-colour processing, optional background keying, style-aware Generate/Reference pose requests, queue and project settings, result-card safeguards and regression tests. No new model dependencies. Explicit sexual-generation controls and HD animation are outside this change. Tests added but not executed in a full checkout; Windows/GPU verification pending. Draft for review; do not merge before running tests. PR #1 may overlap README documentation.

### Phase 24: HD sprite animation

- Opened: 2026-11-25T19:38:11Z; merged: 2026-11-26T00:56:48Z (UTC).
- [PR #3](https://github.com/Aishi-mana/SpriteForge/pull/3); merge commit `f4dd646906a5`.
- Recorded scope and verification at submission:

Initial resolution-aware rigid-bone animation, alpha preservation, bicubic rendering, memory budgets, fitted previews, HD result animation and smooth Godot/Unity exports. Regression tests added, not executed. Stacked on Phase 23. Soft skinning and start/end references remain follow-ons.

### QoL: persistent skeleton pose presets

- Opened: 2026-11-25T19:47:12Z; merged: 2026-11-26T00:57:30Z (UTC).
- [PR #4](https://github.com/Aishi-mana/SpriteForge/pull/4); merge commit `d2bf32fafd22`.
- Recorded scope and verification at submission:

Reference pose editor: save overrides, create named poses, reset saved or factory poses, clear/delete saved presets. Local browser/webview storage, no repo user data. Adds JS regression coverage; not yet executed. Stacked on Phase 24. Template-tab mannequin rig overrides are separate and not modified by this patch.

### Phase 25: custom keyframes and reference-guided animation

- Opened: 2026-11-25T19:50:22Z; merged: 2026-11-26T00:58:16Z (UTC).
- [PR #5](https://github.com/Aishi-mana/SpriteForge/pull/5); merge commit `1ff6498bfca1`.
- Recorded scope and verification at submission:

Initial custom keyframe timeline with start/end and intermediate poses, reference image bounding-box joint estimates, eased rigid-bone interpolation, single-clip preview/export and project persistence. Tests added but not executed. No AI morphing or pose detector. Stacked on pose presets.

### Phase 26: actual start and end reference images

- Opened: 2026-11-25T19:55:33Z; merged: 2026-11-26T00:59:56Z (UTC).
- [PR #6](https://github.com/Aishi-mana/SpriteForge/pull/6); merge commit `e2e955ec3653`.
- Recorded scope and verification at submission:

Adds a separate Start → end images animation mode. Keeps Phase 25 custom keyframes intact. Exact RGBA first/final frames, SDXL redraw of intermediate frames, crossfade fallback, project persistence, one-shot preview and canvas-preserving export. Tests written, runtime/GPU validation pending.

### Phase 27: soft joint deformation

- Opened: 2026-11-25T20:00:18Z; merged: 2026-11-26T00:59:25Z (UTC).
- [PR #7](https://github.com/Aishi-mana/SpriteForge/pull/7); merge commit `5d68572c2b73`.
- Recorded scope and verification at submission:

Optional two-bone textured mesh skinning for elbows/knees, 0–100 softness, pixel and HD sampling, custom keyframe compatibility, preview/export/directions and project settings. Rigid remains default. Phase 26 untouched. Tests added; full runtime validation pending.

### Phase 28: character model support and LoRA compatibility

- Opened: 2026-11-25T20:05:21Z; merged: 2026-11-26T00:59:19Z (UTC).
- [PR #8](https://github.com/Aishi-mana/SpriteForge/pull/8); merge commit `a22aed0f90e7`.
- Recorded scope and verification at submission:

Adds experimental architecture-specific text-to-image loaders for SD1.5 and local Diffusers Lumina2/FLUX/SD3/Qwen pipelines, plus optional Lumina transformer single-file route with base components. Checkpoint-specific family match/unverified/incompatible LoRA labels, diagnostics and tests. Existing SDXL conditioning remains. Actual local files and GPU unverified; tests added, not executed.

### Phase 29: reference-led character consistency

- Opened: 2026-11-25T20:33:03Z; merged: 2026-11-26T00:59:12Z (UTC).
- [PR #9](https://github.com/Aishi-mana/SpriteForge/pull/9); merge commit `f3de9d3cc156`.
- Recorded scope and verification at submission:

Separate reference-led multi-view mode for Qwen, NetaYume and SDXL. Project master reference, view prompts, shared framing/palette, sequential rendering, per-view locks and regeneration, 256px HD direction output and aggregate memory limit. Existing template mode retained. GPU/browser verification pending.

### Phase 30: character identity and appearance locking

- Opened: 2026-11-25T20:36:35Z; merged: 2026-11-26T00:59:06Z (UTC).
- [PR #10](https://github.com/Aishi-mana/SpriteForge/pull/10); merge commit `623af75b40f3`.
- Recorded scope and verification at submission:

Adds per-feature reference-guidance locks, independent variation target and candidate generation, master/candidate comparison, gallery/reference/Animate actions and project persistence. Uses existing Qwen/NetaYume/SDXL reference routes and one-image memory policy; preserves Phase 29 template mode and locked views. Prompt-level guidance, not pixel-exact masks. GPU/browser validation pending.

### Phase 31: modular character customization

- Opened: 2026-11-25T20:51:50Z; merged: 2026-11-26T00:58:59Z (UTC).
- [PR #11](https://github.com/Aishi-mana/SpriteForge/pull/11); merge commit `7717910ff09f`.
- Recorded scope and verification at submission:

Separate CPU-only Modular tab: non-destructive transparent layer stack, reusable outfit/hair/body alternatives, offsets, scaling, opacity, mirroring and ordering, project persistence, portable ZIP recipe and composite PNG, Reference/Animate handoff. No AI segmentation or independent layer rigging. Tests added; live browser verification pending.

### Phase 32: AI-assisted modular asset generation

- Opened: 2026-11-26T00:53:32Z; merged: 2026-11-26T00:58:52Z (UTC).
- [PR #12](https://github.com/Aishi-mana/SpriteForge/pull/12); merge commit `a8e63d84df0d`.
- Recorded scope and verification at submission:

Generate isolated clothing/hair/footwear/accessory candidates from a body or composite reference with existing Qwen/NetaYume/SDXL pipelines. Border keying, approximate fitting, raw/asset/composite review, explicit non-destructive layer acceptance and stale-recipe protection. One image per job, existing memory policy. No semantic segmentation or independent rigging. JavaScript parse checked; GPU and browser verification pending.

### Phase 33: modular layer rigging and bone attachment

- Opened: 2026-11-26T01:05:32Z; merged: 2026-11-26T01:49:44Z (UTC).
- [PR #13](https://github.com/Aishi-mana/SpriteForge/pull/13); merge commit `35764e751e80`.
- Recorded scope and verification at submission:

Independent rigid and auto-split attachments driven by the existing skeleton, reusable body-only joint profile, modular standard-clip preview and export, CPU memory limits, recipe/project persistence. Original flattened animation retained. JS parse checked; tests added but not run. No weighted garment skinning or independent cloth physics yet.

### Phase 34: modular soft deformation and secondary motion

- Opened: 2026-11-26T01:13:38Z; merged: 2026-11-26T01:49:38Z (UTC).
- [PR #14](https://github.com/Aishi-mana/SpriteForge/pull/14); merge commit `c5354f76884c`.
- Recorded scope and verification at submission:

Opt-in soft garment elbow/knee meshes and per-layer independent spring chains, adjustable anchor/segments/flutter/stiffness/damping, presets and recipe persistence. Existing rigid defaults and CPU memory limits retained. Standard modular preview/export use the same renderer. JS syntax checked; regression tests added but not executed. No collision simulation or independent animated layer export.

### Phase 35: independent animated layer export

- Opened: 2026-11-26T01:16:47Z; merged: 2026-11-26T01:49:30Z (UTC).
- [PR #15](https://github.com/Aishi-mana/SpriteForge/pull/15); merge commit `65a2b1fec665`.
- Recorded scope and verification at submission:

Synchronized transparent modular body/equipment sheets, optional hidden non-body alternatives and individual frames. Shared untrimmed grid, pivot, FPS, loop, draw order and visibility manifest; exact reconstructed assembled sheet from exported layers. Existing rig deformation and CPU budgets reused. Standard flattened export unchanged. JS syntax checked, CPU tests added but not executed. Engine-neutral baked PNG export, not runtime skeletal rig.


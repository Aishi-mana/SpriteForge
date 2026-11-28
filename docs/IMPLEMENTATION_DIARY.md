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

### Phase 36: runtime character assembly and equipment system

- Opened: 2026-11-26T01:19:58Z; merged: 2026-11-26T01:49:23Z (UTC).
- [PR #16](https://github.com/Aishi-mana/SpriteForge/pull/16); merge commit `903d33a24d33`.
- Recorded scope and verification at submission:

Godot 4 and Unity desktop components bundled with modular sheet exports. Shared clock, clip switching, category equipment and layer visibility, loadout persistence, recipe and layer-set compatibility checks. Documentation and fingerprint/bundle regression tests included. JS parse passed; Python suite and actual engine compile/playback not verified. Baked frames, not live skeletal rig.

### Phase 37: advanced layer occlusion and manual bone weight editing

- Opened: 2026-11-26T01:23:31Z; merged: 2026-11-26T01:49:14Z (UTC).
- [PR #17](https://github.com/Aishi-mana/SpriteForge/pull/17); merge commit `eba8893334d1`.
- Recorded scope and verification at submission:

Opt-in two-bone weighted meshes with bounded canvas brush stamps, undo/reset, per-layer explicit depth and animated body-bone alpha occlusion. Persistent recipes and synchronized independent sheets use matching order and baked masks. Existing rigid, soft and spring modes preserved. JS syntax checked; CPU regression tests added but not executed. No general multi-bone weight maps or dynamic inter-layer collisions.

### Phase 38: character model and asset library manager

- Opened: 2026-11-26T01:26:25Z; merged: 2026-11-26T01:49:06Z (UTC).
- [PR #18](https://github.com/Aishi-mana/SpriteForge/pull/18); merge commit `397a65be554e`.
- Recorded scope and verification at submission:

Shared local searchable character recipe, individual layer and exact-body rig snapshots, tags/thumbnail previews, copy/apply/delete, validated bounded persistence. Installed model and LoRA manager shows file-presence readiness and filters compatibility without loading weights. Both Qwen checkpoints retained. JS parse checked; CPU regression tests added but not run. No installer or GPU benchmark.

### Phase 39: integration testing, performance and stability

- Opened: 2026-11-26T01:36:36Z; merged: 2026-11-26T01:48:59Z (UTC).
- [PR #19](https://github.com/Aishi-mana/SpriteForge/pull/19); merge commit `d8ba565cd473`.
- Recorded scope and verification at submission:

Stabilization fixes: thread-isolated sampler/progress, cancellation, local worker cleanup and timeout, bounded model-header cache and render allocations, project input staging, SDXL folder ControlNet loading. CPU validation CI and Windows validate.bat, manual GPU/Godot/Unity acceptance checklist. 33 JavaScript assertions passed in an isolated harness; full Python and device tests not yet verified. Keep draft until validated.

### Phase 40: custom skeleton and bone hierarchy editor

- Opened: 2026-11-26T01:55:28Z; merged: 2026-11-26T03:56:59Z (UTC).
- [PR #20](https://github.com/Aishi-mana/SpriteForge/pull/20); merge commit `4ea20cc8e616`.
- Recorded scope and verification at submission:

Independent custom rig tab with connected editable bone hierarchy, four starters, parent-child forward kinematics, CPU rigid pose preview/export, portable JSON presets and project persistence. Existing humanoid and modular rigs preserved. JS parse and literal ID checks passed; CPU CI pending. Multi-bone skinning, custom animation timeline and IK remain future phases.

### Phase 41: multi-bone skinning and weight painting

- Opened: 2026-11-26T02:06:23Z; merged: 2026-11-26T03:56:52Z (UTC).
- [PR #21](https://github.com/Aishi-mana/SpriteForge/pull/21); merge commit `c5897c0d9812`.
- Recorded scope and verification at submission:

Optional custom-rig linear blend mesh with normalized nearest-four auto weights, manual radial stamps for any bone, selected-bone heatmap, undo/clear/reset, and preset/project persistence. Shared textured triangle rasterizer, rigid fallback, bounded mesh/stamps. Feature branch CPU CI enabled. JS syntax and IDs checked; regression tests added, CPU run pending. No timeline or IK.

### Phase 42: advanced animation timeline

- Opened: 2026-11-26T02:59:14Z; merged: 2026-11-26T03:56:44Z (UTC).
- [PR #22](https://github.com/Aishi-mana/SpriteForge/pull/22); merge commit `65221fd4aa5d`.
- Recorded scope and verification at submission:

Custom rig bone-specific rotation tracks, linear/ease/step interpolation, key capture/duplicate/delete, scrub and playback with adjacent onion skins, reused weighted mesh binding and standard spritesheet export. One clip per profile; normalized rig and timeline persisted in project/JSON. Existing manual pose, standard animation and modular workflows preserved. JS syntax and literal IDs checked; CPU CI pending. No IK, multi-clip collection or position/scale tracks.

### Phase 43: inverse kinematics and foot locking

- Opened: 2026-11-26T03:05:36Z; merged: 2026-11-26T03:56:36Z (UTC).
- [PR #23](https://github.com/Aishi-mana/SpriteForge/pull/23); merge commit `8e1805ec70d8`.
- Recorded scope and verification at submission:

Analytic two-bone IK, adjustable constraints, target drag geometry preview and residual, frame-indexed target keys and fixed contact ranges. Shared solver for rigid/weighted custom rig and baked timeline preview/export; project/preset persistence. Manual angles and existing modular/humanoid rigs retained. JS syntax and literal IDs checked; regression tests added and CI pending. Canvas-space contacts, not automatic root motion or ground detection.

### Phase 44: AI-assisted animation cleanup

- Opened: 2026-11-26T03:21:40Z; merged: 2026-11-26T03:56:29Z (UTC).
- [PR #24](https://github.com/Aishi-mana/SpriteForge/pull/24); merge commit `2b4266834a23`.
- Recorded scope and verification at submission:

Selective SDXL inpainting of custom timeline frames, posed-joint/brush masks, exact outside-mask RGBA and default alpha lock, pixel palette lock, original/candidate/accepted comparison, persistent accepted frame overlays with source/profile/pad provenance checks, accepted playback and export. Existing Qwen/Neta reference runtimes are not true mask inpainting; excluded. CPU mock regressions and JS syntax/ID checks; CI and live GPU/browser tests pending.

### Phase 45: animation retargeting between characters

- Opened: 2026-11-26T03:29:49Z; merged: 2026-11-26T03:56:22Z (UTC).
- [PR #25](https://github.com/Aishi-mana/SpriteForge/pull/25); merge commit `d69e33df3c0b`.
- Recorded scope and verification at submission:

Motion bundle export/import, stable ID/name suggestions and editable one-to-one mappings, rotation track and timing transfer, optional limb-length/orientation-scaled IK targets and fixed contacts, paired solved geometry preview and reachability report. Destination source pixels, rest skeleton, manual pose and weights preserved; apply replaces timeline and IK chains. CPU regression tests and JS syntax/ID checks; CI pending. No automatic root motion or guarantee of identical world-space poses.

### Phase 46: multi-character animation scenes

- Opened: 2026-11-26T03:43:26Z; merged: 2026-11-26T03:56:15Z (UTC).
- [PR #26](https://github.com/Aishi-mana/SpriteForge/pull/26); merge commit `c3a150e51e55`.
- Recorded scope and verification at submission:

New Scenes tab: independent baked custom-rig actors from current or saved projects, PNG props, portable actor/scene bundles, position tween, facing, scale, opacity, depth, independent source FPS/speed/start/end/offset/loop-hold-hide. Shared frame scrub, cached playback, fixed untrimmed flattened scene export and project persistence. CPU budget guards and regression tests; JS syntax/IDs checked. CI pending. No live rig interaction, physics or collision logic.

### Phase 47: visual effects, magic and particles

- Opened: 2026-11-26T03:46:22Z; merged: 2026-11-26T03:56:07Z (UTC).
- [PR #27](https://github.com/Aishi-mana/SpriteForge/pull/27); merge commit `3844cbf6a9f7`.
- Recorded scope and verification at submission:

Eight CPU procedural effect presets, deterministic seeded emitters, editable timing/color/radius/opacity/depth/rotation/speed, actor-pivot attachment or free position, shared scene timing, effect-only scenes, project/JSON persistence and standalone transparent VFX exports. Bounded effect work; regression tests added; JS syntax/IDs checked. CI pending. No additive shaders, automatic combat, live bone attachments or GPU inference.

### Phase 48: batch character production

- Opened: 2026-11-26T03:55:26Z; merged: 2026-11-26T03:57:52Z (UTC).
- [PR #28](https://github.com/Aishi-mana/SpriteForge/pull/28); merge commit `a5085ee6d86d`.
- Recorded scope and verification at submission:

Production tab with shared generation settings, named character rows and reusable recipes, grouped persistent single-worker GPU queue, resolved seeds, per-row retry and new project creation, sequential saved custom rig animation exports with optional automatic retargeting and warning review. No automatic skeleton fitting; projects preserved; export status session-only. CPU regression tests and JS syntax/IDs checked. CI pending.

### Phase 49 — initial performance and integration validation

- Opened: 2026-11-26T04:01:57Z; merged: 2026-11-26T04:06:13Z (UTC).
- [PR #29](https://github.com/Aishi-mana/SpriteForge/pull/29); merge commit `85d26a59913b`.
- Recorded scope and verification at submission:

Adds a maximum-layer CPU scene integration regression with repeat timing, deterministic JSON roundtrip and scrub checks, plus validation gates. Execution is pending; no benchmark results or hardware sign-off claimed.

### Phase 50 — UI cleanup and workspace navigation

- Opened: 2026-11-26T04:10:05Z; merged: 2026-11-26T04:14:32Z (UTC).
- [PR #30](https://github.com/Aishi-mana/SpriteForge/pull/30); merge commit `d865ae8912da`.
- Recorded scope and verification at submission:

Fix hidden panel CSS, group navigation, add contextual workspace headings, collapsible setup, connection feedback and responsive styling. Preserve existing control IDs. Desktop visual verification remains pending.

### Phase 51 — Advanced pixel editor tools

- Opened: 2026-11-26T04:45:23Z; merged: 2026-11-26T04:48:08Z (UTC).
- [PR #31](https://github.com/Aishi-mana/SpriteForge/pull/31); merge commit `57e8f4db2f1a`.
- Recorded scope and verification at submission:

Adds selection clipboard, rotation, shading, outline, vertical symmetry, wrapped brush and bounded undo. Layered editing is deferred. Desktop validation pending.

### Phase 52 — selected-region AI character editing and extraction

- Opened: 2026-11-26T04:48:57Z; merged: 2026-11-26T04:58:38Z (UTC).
- [PR #32](https://github.com/Aishi-mana/SpriteForge/pull/32); merge commit `51f0fbda2217`.
- Recorded scope and verification at submission:

Adds SDXL masked region edits with alpha lock, explicit candidate acceptance and undo, and manual rectangular asset PNG extraction. Semantic segmentation and real GPU verification remain outstanding.

### Phase 53 — reusable character identity profiles and consistency review

- Opened: 2026-11-26T04:59:31Z; merged: 2026-11-26T05:06:53Z (UTC).
- [PR #33](https://github.com/Aishi-mana/SpriteForge/pull/33); merge commit `534053a9b65d`.
- Recorded scope and verification at submission:

Adds device-local named character profiles for master, identity text, appearance locks and style, plus visual consistency review. No new model dependencies. Desktop validation pending.

### Phase 54 — persistent animation clips and eased transitions

- Opened: 2026-11-26T05:07:15Z; merged: Not merged (UTC).
- [PR #34](https://github.com/Aishi-mana/SpriteForge/pull/34); superseded/unmerged.
- Recorded scope and verification at submission:

Superseded by reconciled PR #36; original branch retained.

### Phase 55 — tile map painter and collision-cell export

- Opened: 2026-11-26T05:14:44Z; merged: Not merged (UTC).
- [PR #35](https://github.com/Aishi-mana/SpriteForge/pull/35); superseded/unmerged.
- Recorded scope and verification at submission:

Superseded by corrected PR #38; original branch retained.

### Phase 54 — reconciled animation clips and transitions

- Opened: 2026-11-26T05:16:16Z; merged: 2026-11-26T06:43:29Z (UTC).
- [PR #36](https://github.com/Aishi-mana/SpriteForge/pull/36); merge commit `e65c8d98f4f9`.
- Recorded scope and verification at submission:

Supersedes conflicted PR #34. Reapplies Phase 54 on the merged Phase 53 base, preserving identity profiles.

### Phase 56 — interactive character behavior preview

- Opened: 2026-11-26T05:16:57Z; merged: 2026-11-26T08:53:39Z (UTC).
- [PR #37](https://github.com/Aishi-mana/SpriteForge/pull/37); merge commit `3c2b669230dc`.
- Recorded scope and verification at submission:

Adds baked clip idle/walk/attack sandbox, movement controls and illustrative collision boxes. No scene mutation. Full state graph and collision authoring deferred.

### Phase 55 — corrected map editor integration

- Opened: 2026-11-26T07:54:52Z; merged: 2026-11-26T07:59:36Z (UTC).
- [PR #38](https://github.com/Aishi-mana/SpriteForge/pull/38); merge commit `a5594addf822`.
- Recorded scope and verification at submission:

Supersedes #35. Isolates map-specific DOM code from queue test extraction and preserves merged Phase 54.

### Phase 57 — project duplication and portable backups

- Opened: 2026-11-26T08:55:46Z; merged: 2026-11-26T09:14:41Z (UTC).
- [PR #39](https://github.com/Aishi-mana/SpriteForge/pull/39); merge commit `de435205956a`.
- Recorded scope and verification at submission:

Adds project copy, ZIP export/import, bounded archive validation, non-overwriting restore and regression checks. Manual snapshots via ZIP; automatic version history and desktop verification remain outstanding.

### Phase 58 — workspace productivity controls

- Opened: 2026-11-26T09:15:13Z; merged: 2026-11-26T09:20:18Z (UTC).
- [PR #40](https://github.com/Aishi-mana/SpriteForge/pull/40); merge commit `86fee971c3e1`.
- Recorded scope and verification at submission:

Resizable persistent sidebar, accessible command search, keyboard shortcuts, focus mode and fullscreen API integration. Desktop verification pending.

### Phase 59 — game engine export integration

- Opened: 2026-11-26T09:20:22Z; merged: 2026-11-26T10:04:50Z (UTC).
- [PR #41](https://github.com/Aishi-mana/SpriteForge/pull/41); merge commit `f35e53169c24`.
- Recorded scope and verification at submission:

Adds Aseprite-style array JSON, atlas validation, checksum manifest, portable asset ZIP and Unity controller/prefab generation. Native engine import verification remains outstanding.

### Phase 60 — GPU resource management

- Opened: 2026-11-26T10:12:40Z; merged: 2026-11-26T10:19:20Z (UTC).
- [PR #42](https://github.com/Aishi-mana/SpriteForge/pull/42); merge commit `3825c63a0806`.
- Recorded scope and verification at submission:

GPU resource status, lock-protected cache release, conservative presets and GPU-free regression tests.

### Phase 61 — integration safeguards and regression coverage

- Opened: 2026-11-26T10:20:46Z; merged: 2026-11-26T10:48:44Z (UTC).
- [PR #43](https://github.com/Aishi-mana/SpriteForge/pull/43); merge commit `61aa7e945c95`.
- Recorded scope and verification at submission:

Fixes project map isolation, protects clips on skeleton hierarchy changes, cancels stale behavior previews, preserves worker-specific settings and adds UI regression tests. Phase 62 packaging remains deferred; real GPU and native engine verification outstanding.

### Phase 61A — Full-body character artwork

- Opened: 2026-11-26T11:39:40Z; merged: 2026-11-26T11:51:47Z (UTC).
- [PR #44](https://github.com/Aishi-mana/SpriteForge/pull/44); merge commit `dc43712d820d`.
- Recorded scope and verification at submission:

Dedicated full-length artwork generation, view selection, master approval and project persistence, optional reference conditioning and CPU regression tests. Existing portrait expressions unchanged.

### Phase 61B — Multi-framing portraits

- Opened: 2026-11-26T17:17:17Z; merged: 2026-11-26T17:29:21Z (UTC).
- [PR #45](https://github.com/Aishi-mana/SpriteForge/pull/45); merge commit `0cf13e256fc1`.
- Recorded scope and verification at submission:

Four portrait framings with master reference, padded aspect ratios, pixel/HD output, asset saving and compatible pixel expression handoff. CPU regression tests and documentation included.

### Phase 61C — Emotional portraits and gestures

- Opened: 2026-11-26T17:19:57Z; merged: 2026-11-26T17:29:31Z (UTC).
- [PR #46](https://github.com/Aishi-mana/SpriteForge/pull/46); merge commit `4cb4ac9ae795`.
- Recorded scope and verification at submission:

Adds 13 emotional states, eight gesture presets and custom description, using approved master reference and framing controls. Preserves existing masked expression workflow. Stacked on 61B; retarget to main after 61B merges.

### Phase 61D — Shared character identity and outfit profiles

- Opened: 2026-11-26T17:30:30Z; merged: 2026-11-26T17:34:45Z (UTC).
- [PR #47](https://github.com/Aishi-mana/SpriteForge/pull/47); merge commit `82bcc3cd5a21`.
- Recorded scope and verification at submission:

Validated project-scoped identity, eight named outfits, descriptive locks and shared prompt conditioning for artwork, portraits and gestures. Includes regression tests and documentation.

### Phase 61E — Artwork-to-sprite conversion

- Opened: 2026-11-26T17:32:28Z; merged: 2026-11-26T17:38:32Z (UTC).
- [PR #48](https://github.com/Aishi-mana/SpriteForge/pull/48); merge commit `a601ed98a7ad`.
- Recorded scope and verification at submission:

Direct CPU and reference-conditioned AI conversion, pixel/HD output, extracted palette locking, approved sprite persistence and animation handoff. Stacked on Phase 61D.

### Phase 61F — Character pose and animation workflow

- Opened: 2026-11-26T17:34:26Z; merged: 2026-11-26T17:38:39Z (UTC).
- [PR #49](https://github.com/Aishi-mana/SpriteForge/pull/49); merge commit `159ba68f6f2f`.
- Recorded scope and verification at submission:

Approved sprite handoff into standard/custom rig, reference pose presets, action clip selection and starter export pack. Confirmed source replacement clears stale clips; stale auto-placement responses ignored. Includes UI regression tests. Stacked on 61E.

### Phase 61G — Unified Character Studio dashboard

- Opened: 2026-11-26T17:39:30Z; merged: 2026-11-26T17:43:47Z (UTC).
- [PR #50](https://github.com/Aishi-mana/SpriteForge/pull/50); merge commit `b9d5814636c4`.
- Recorded scope and verification at submission:

Dedicated workspace with identity and pipeline status, stage shortcuts, linked image previews, project gallery filtering and PNG downloads. Includes UI regression tests and docs. No new asset database; existing tools remain available.

### Phase 61H — Character Studio integration and resource safeguards

- Opened: 2026-11-26T17:48:33Z; merged: 2026-11-26T17:56:29Z (UTC).
- [PR #51](https://github.com/Aishi-mana/SpriteForge/pull/51); merge commit `84eca7dfc988`.
- Recorded scope and verification at submission:

Bounded reference decoding and generation parameters, native worker routing, exact portrait aspect and alpha handling, conservative defaults, shared job controls and asset guards. Synthetic lifecycle regression tests and limitations documented. Windows packaging unchanged.

### Phase 61I — Dedicated body base and modular dressing

- Opened: 2026-11-26T18:05:36Z; merged: 2026-11-26T18:09:24Z (UTC).
- [PR #52](https://github.com/Aishi-mana/SpriteForge/pull/52); merge commit `e4e37dfb8d50`.
- Recorded scope and verification at submission:

CPU-only featureless mannequin generator with body build, proportions, approximate views, pose, resolution and color controls. Independent project persistence, transparent PNG download, Modular body layer handoff and Character Studio shortcut. Regression tests and documented limits.

### Phase 61J — Enclosed background removal and alpha repair

- Opened: 2026-11-26T18:13:35Z; merged: 2026-11-26T18:17:15Z (UTC).
- [PR #53](https://github.com/Aishi-mana/SpriteForge/pull/53); merge commit `3302a40225da`.
- Recorded scope and verification at submission:

Shared color-key pocket detection, selected HD background key, result-card alpha preview with manual selection, regression coverage and documentation.

### Phase 61K-A — Multi-model reference instruction editing

- Opened: 2026-11-26T18:24:35Z; merged: 2026-11-26T18:40:01Z (UTC).
- [PR #54](https://github.com/Aishi-mana/SpriteForge/pull/54); merge commit `aa8c44adc23a`.
- Recorded scope and verification at submission:

Native Qwen instruction route, Neta image-to-image and SDXL full-canvas inpaint adapters. Shared validated endpoint, alpha cleanup, source canvas control and non-destructive preview/accept/discard interface. Mocked routing and API regression tests. Real GPU evaluation and protected-region compositing remain outstanding.

### Phase 61K-B — Regional masking and protected pixels

- Opened: 2026-11-26T18:41:05Z; merged: 2026-11-26T18:45:42Z (UTC).
- [PR #55](https://github.com/Aishi-mana/SpriteForge/pull/55); merge commit `ca0052fadfef`.
- Recorded scope and verification at submission:

Source-resolution mask painting, protection, inversion and exact RGBA compositing across supported editors. SDXL native mask forwarding, validated mask input, protected pixel regression tests and documented limitations.

### Phase 61K-C — Character identity preservation controls

- Opened: 2026-11-26T18:47:14Z; merged: 2026-11-26T18:56:33Z (UTC).
- [PR #56](https://github.com/Aishi-mana/SpriteForge/pull/56); merge commit `4839b4053fdc`.
- Recorded scope and verification at submission:

Configurable identity guidance keys and UI presets across Qwen, Neta and SDXL instruction editing. Explicit unlock semantics, validation, metadata and regression tests. Existing exact regional compositing retained. GPU and desktop verification outstanding.

### Phase 61K-D — Quick character editing presets

- Opened: 2026-11-26T18:49:13Z; merged: 2026-11-26T18:56:45Z (UTC).
- [PR #57](https://github.com/Aishi-mana/SpriteForge/pull/57); merge commit `931cddaab591`.
- Recorded scope and verification at submission:

Ten editable instruction templates, suggested identity locks, masking hints and conditional canvas expansion. Regression tests registered. Stacked on 61K-C pending validation; retarget to main after PR #56 merges.

### Phase 61K-E — Edit history, undo redo and comparison

- Opened: 2026-11-26T18:50:37Z; merged: 2026-11-26T18:56:55Z (UTC).
- [PR #58](https://github.com/Aishi-mana/SpriteForge/pull/58); merge commit `83454a6c0080`.
- Recorded scope and verification at submission:

Session-local bounded revision snapshots, original restore, undo/redo, comparison and revision PNG export. New edits discard redo branch and invalidate stale template rig data. Regression tests registered. Stacked on 61K-D pending dependency validation.

### Phase 61K-F — Character Studio and Modular editing integration

- Opened: 2026-11-26T18:59:33Z; merged: 2026-11-26T19:03:23Z (UTC).
- [PR #59](https://github.com/Aishi-mana/SpriteForge/pull/59); merge commit `351d4a132543`.
- Recorded scope and verification at submission:

Integrate approved artwork, sprite, body base, modular layer and composite editing through staged candidates. Reuse revision history, explicit approvals, modular layer import and PNG export. Source identity and project reload guards; registered regression tests. Real desktop and GPU validation outstanding.

## Validation and correction events

- 2026-11-26T18:49:35Z — 61K-C Ubuntu CPU validation failed in `test_instruction_identity.py`: the test expected the word hairstyle to be absent from the entire prompt, although it was part of the requested edit. 61K-D inherited the same failure; preset tests passed.
- 2026-11-26T18:52:38Z to 18:52:44Z — Corrected assertion on all three dependent branches (61K-C, D, E): distinguish requested changes from preservation guidance, verify exact forwarded prompt; commits `a286e07`, `0353193`, `5d7161c`. No production feature removed. CPU validation runs [124](https://github.com/Aishi-mana/SpriteForge/actions/runs/45879368318), [125](https://github.com/Aishi-mana/SpriteForge/actions/runs/45879373753), [126](https://github.com/Aishi-mana/SpriteForge/actions/runs/45879377540) succeeded before merging.
- 2026-11-26T19:03:23Z (2026-11-27 03:03:23 Manila) — 61K-F merged after [CPU validation 130](https://github.com/Aishi-mana/SpriteForge/actions/runs/45880211164) succeeded. Latest implementation merge: `351d4a132543`. 61K-G integration testing and optimization is next. Phase 62 packaging remains on hold. Real GPU editing, desktop interactions and native engine imports are not certified by CPU validation.

## New entries

Use the following template for each future change (replace placeholders with actual values).

### YYYY-MM-DDTHH:MM:SS+00:00 — Phase / feature

- Purpose:
- Implementation and affected files:
- Design decisions / compatibility:
- Tests and observed results:
- Failures / fixes:
- PR and commit:
- Status and remaining limitations:
- Next action:


### 2026-11-26T19:10:27Z (2026-11-27 03:10:27 Manila) — Phase 61K-G: integration and resource safeguards

- Purpose: stabilize reference editing before hardware acceptance; permit regional equipment removal even when an intermediate model result is empty.
- Implementation: `engine/instruction_edit.py` bounds candidate dimensions, composites before checking final visibility, rejects overlapping instruction requests and reports elapsed duration. `engine/main.py` routes API through the guard and returns actionable OOM guidance. `ui/index.html` reuses the brush overlay, coalesces redraws, rejects oversized source images, freezes controls during requests and uses the resource recommendation when known.
- Decisions: retain existing generation lock, local workers and model-specific settings; no new dependencies or claimed VRAM savings. The edit guard covers instruction requests, not the entire job queue.
- Tests: added `tests/test_instruction_integration.py` for Qwen/Neta/SDXL mocked removal and protected pixels, timing, output bounds, overlap rejection and lock recovery. CPU CI pending; no hardware verification performed.
- References: commits `be0cd568`, `b83bcccf`, `c05e30b2`, `471b6280`, `210e00f6`, `cf24488d`; [phase notes](phases/PHASE61KG.md), [manual acceptance](TESTING_CHECKLIST.md).
- Status: implemented, validation pending. Documentation branch dependency PR #60 is still being validated. Next: submit 61K-G PR, validate, merge dependencies in order, then record actual outcomes. Real GPU quality, peak VRAM, desktop interaction and native engine imports remain outstanding. Phase 62 stays on hold.

### 2026-11-26T19:15:41Z (2026-11-27 03:15:41 Manila) — Phase 61K final integration

- Documentation PR [#60](https://github.com/Aishi-mana/SpriteForge/pull/60) passed [CPU validation](https://github.com/Aishi-mana/SpriteForge/actions/runs/45881403350) and merged at 2026-11-26T19:15:29Z (`4da12e6bd533`).
- Phase 61K-G PR [#61](https://github.com/Aishi-mana/SpriteForge/pull/61) passed [CPU validation](https://github.com/Aishi-mana/SpriteForge/actions/runs/45881683504); retargeted to main after #60, confirmed mergeable, merged at 2026-11-26T19:15:41Z (`6ab3ade814fc`).
- All seven reference-editing implementation phases are merged. Updated README, HANDOFF, roadmap and phase notes to reflect the verified milestone. Documentation-only closure; no production changes or new hardware test results.
- Continue pushing implementations and maintaining documentation and dated diary entries. Next: manual GPU/desktop and native engine acceptance; measure actual latency and VRAM. Phase 62 Windows packaging stays on hold until explicitly resumed.

### 2026-11-27 (Manila) — Phase 61L-A: magic background eraser

- Adds optional CPU-only exterior segmentation in engine/alpha_cleanup.py and the existing Alpha Cleanup preview dialog in ui/index.html. Existing modes and callers retain behavior. Auto uses supported nearby border shades; hard alpha removal preserves retained RGBA and guards against erasing the entire image. No semantic or cast-shadow guarantee.
- Regression cases added to tests/test_alpha_cleanup.py; CI and desktop verification pending. Implementation commit `291852b2571c`. Next: 61L-B shadow removal after validation. Roadmap adds 61M exact-fit modular layers after 61L; packaging remains on hold.

### 2026-11-27 (Manila) — Phase 61L-B: ground shadow removal

- Engine `engine/alpha_cleanup.py`: CPU-only shallow component detection near foreground feet, exterior contact, optional background pass, transparent-source bypass and hard RGBA preservation. Commit `fadeb61586cf`.
- API `engine/main.py` validates independent 0–100 sensitivity; UI `ui/index.html` offers Ground shadow removal and reports pixel counts. Tests `tests/test_alpha_cleanup.py` cover opaque/translucent shadows, clothing/boots, zero strength and API integration. Commits `d8274286c38d`, `98f705c3770c`, `31a0d23ceb3e`.
- [Phase notes](phases/PHASE61LB.md) describe heuristic limits. No semantic guarantee or measured hardware result. CI pending; stacked on 61L-A. Next: 61L-C manual erase/restore. 61M remains queued, Phase 62 packaging on hold.

### 2026-11-26T19:26:07Z — 61L-A integration

- PR #62 passed [CPU validation](https://github.com/Aishi-mana/SpriteForge/actions/runs/45883175799) and merged into main at `44ce9936e7e7`. PR #63 retargeted to main; validation pending at observation.

### 2026-11-27 (Manila) — Phase 61L-C: manual alpha tools

- `ui/index.html` adds source-resolution canvas preview, RGBA connected wand, sampled and unrestricted circular erasers, original restore, interpolated strokes, eight snapshots and fully transparent apply guard. Commit `15b6ca05d810`.
- JS buffer regression tests registered in `tests/test_ui.py` (`62518afb107d`, `ba3a3a939b9e`). CI and desktop verification pending. Canvas premultiplied alpha round trips may round partial-alpha RGB. Automatic previews replace manual edits; undo retains the preceding preview. No new model dependency.
- [Phase notes](phases/PHASE61LC.md). Stacked on 61L-B; next 61L-D. 61M queued after 61L. Phase 62 packaging on hold.

### 2026-11-26T19:40:07Z — 61L-B integration and 61L-C correction

- PR #63 passed CPU validation run 45883522786 and merged at `681cef153466`. PR #64 failed Windows and Ubuntu run 45883789688 in the new JS regression; the wand test omitted the y coordinate. Corrected test call; rerun pending. No production feature removed.

### 2026-11-27 (Manila) — Phase 61L-D: edge and alpha refinement

- `engine/alpha_cleanup.py` adds boundary-only partial alpha cutoff, optional estimated matte reversal with bounded gain, hard-color default and full-erasure guard (`a3e1c7267bd9`). API settings (`02e0308b5edd`), current-preview refinement button and counts (`d42519d7e75d`), regression tests (`f0af1b6fe944`).
- Decisions: no opaque recoloring or resampling, no automatic matte inference, no model dependency; estimated matte correction can miscorrect already-unmatted pixels. Existing manual preview retained and undo supported.
- [Phase notes](phases/PHASE61LD.md); CI and desktop acceptance pending. Stacked on corrected 61L-C. Next: 61L-E protected areas and pixel preservation. 61M queued; Phase 62 packaging on hold.

### 2026-11-27 (Manila) — Phase 61L-E: protected regions

- `engine/alpha_cleanup.py` restores exact operation-input RGBA under a same-size binary mask (`176b3cd3acf6`); API accepts optional protection PNG (`29817f3af7e5`). `ui/index.html` adds paint/unpaint, cyan overlay, mask-aware manual tools and mask-inclusive undo (`f34ad76fbb37`). Python/JS regressions added (`8f6746262c9a`, `66dbaedfd6c6`).
- Protection is session-local, automatic compositing is post-process (not a segmentation barrier), and locks preserve current operation input rather than recovering earlier erasures. Browser partial-alpha rounding remains. [Phase notes](phases/PHASE61LE.md). CI and desktop acceptance pending, stacked on 61L-D. Next 61L-F workspace integration. 61M queued; Windows packaging on hold.

### 2026-11-26T19:44:47Z — 61L-C integration

- PR #64 passed CPU validation run 45885410471 and merged at `58dda3f6b0e9`.

### 2026-11-26T19:44:55Z — 61L-D integration

- PR #65 passed CPU validation run 45885510358 and merged at `e59c77c54a7a`.

### 2026-11-27 (Manila) — Phase 61L-F: workspace integration

- `ui/index.html`: direct cleanup entry points for approved assets and generated artwork/sprite candidates, staged review and revision history, source-change guard (`034d2479b7e6`); explicit same-size modular layer replacement preserving settings and validating size/budget (`1f69a0dab954`). Existing project and source guards retained. Tests extended (`95a3a75f6eb2`).
- Composite output remains flattened; replacement is explicit and rig weights must be reviewed. Canvas rounding and desktop acceptance remain outstanding. [Phase notes](phases/PHASE61LF.md). CI pending, stacked on 61L-E. Next 61L-G. Phase 61M queued; Phase 62 on hold.

### 2026-11-26T19:52:17Z — 61L-E integration

- PR #66 passed CPU validation run 45885757512 and merged at `20d28ff2821d`.

### 2026-11-26T19:52:27Z — 61L-F integration

- PR #67 passed CPU validation run 45886106091 and merged at `4035422dc642`.

### 2026-11-27 (Manila) — Phase 61L-G: integration and resource safeguards

- Engine component lookup and reduced redundant buffers, accurate protected halo count (`08ce3b1ab921`); API validates mask dimensions early and guards empty output (`f33459bdf68c`). UI reuses buffers, bounds history and canvas size, coalesces brush redraws and reports preview duration (`9b0daf09e614`).
- Pipeline/max-canvas and JS history regressions added (`07dc75fb5d07`, `007b800f045a`). CI pending. No measured performance improvements or desktop verification; browser partial-alpha RGB rounding remains. [Phase notes](phases/PHASE61LG.md); manual checklist expanded. Next 61M after validation and merge. Phase 62 on hold.

### 2026-11-26T20:04:57Z — 61L-G integration

- PR #68 passed [CPU validation](https://github.com/Aishi-mana/SpriteForge/actions/runs/45887047432) and merged at `26c3a6d3454f`. All 61L implementations merged. Desktop acceptance, measured memory/time and partial-alpha canvas rounding remain outstanding.

### 2026-11-27 (Manila) — Phase 61M-A: fixed-canvas registration

- `engine/modular_assets.py` adds body-conditioned prompt and full-canvas placement of fitted RGBA (`9714f33ab2c0`); API opt-in (`fe1b3e0ad296`); Modular UI default fixed-canvas with legacy fallback (`3eafd1574be7`); regression tests (`cac871abd780`). Source body and recipe not mutated. Existing approximate anatomical fitting remains; no semantic extraction or real inference verified. CI pending. [Phase notes and planned B–G](phases/PHASE61MA.md). Windows packaging stays on hold.

### 2026-11-26T20:13:17Z — 61M-A integration

- PR #69 passed [CPU validation](https://github.com/Aishi-mana/SpriteForge/actions/runs/45888560402) and merged at `5b7d9b219292`.

### 2026-11-27 (Manila) — Phase 61M-B: silhouette landmarks and placement guides

- `engine/modular_assets.py` adds body-alpha band estimates, category region and row-envelope guide, non-destructive spill review (`c604889e61da`). API fixed-canvas path uses derived region and returns mask and metadata (`cfe7487e3fee`). UI shows mask and spill warning (`36839353c71f`); regressions (`3a86818afe65`).
- Design: CPU geometry only, no pose model or diffusion mask conditioning yet; no clipping. Fixed vertical fractions can misidentify unusual poses and proportions. Legacy path unchanged. [Phase notes](phases/PHASE61MB.md). CI, real model and desktop verification pending. Next 61M-C. Phase 62 stays on hold.

### 2026-11-27 (Manila) — 61M-B test correction

- CPU run 45889558860 failed on both platforms in the asymmetric silhouette fixture: shoulder pixels started at row 29, inside the estimated head band ending at row 30 exclusive. Moved synthetic shoulder boundary to row 30; production heuristic unchanged. Revalidation pending.

### 2026-11-27 (Manila) — Phase 61M-C: experimental Qwen extraction

- `engine/modular_assets.py` adds fixed-coordinate difference extraction and guarded Qwen instruction route (`16c50e127e90`); API opt-in (`c4c4786c9781`), Modular controls (`38d411b3a112`), mocked extraction regressions (`3c311c59d647`).
- Design: preserve input body, no post-extraction scaling, advisory guide, explicit candidate approval. Pixel differencing is not semantic extraction; model drift and same-color regions remain risks. CI, real inference and desktop testing pending. Stacked on corrected PR #70. [Phase notes](phases/PHASE61MC.md). Next 61M-D; packaging on hold.

### 2026-11-26T20:33:59Z — 61M-B integration

- PR #70 passed CPU validation run 45890421263 and merged at `05349829fac9`.

### 2026-11-26T20:34:06Z — 61M-C integration

- PR #71 passed CPU validation run 45890532322 and merged at `45adf7fac76d`.

### 2026-11-27 (Manila) — Phase 61M-D: multi-backend extraction

- Shared adapter for Qwen, NetaYume, SDXL with SDXL guide masking (`330b8d3c88fb`); API capability routing and strength mapping (`8c1af8f40b2f`); Modular UI (`3100d78e8fce`); mocked regressions (`b515fe7624bd`).
- SDXL uses a restrictive guide, Qwen/Neta use advisory guides. Explicit legacy fitting fallback, no automatic retry. Difference extraction remains nonsemantic; actual inference quality and desktop behavior unverified. CI pending. [Phase notes](phases/PHASE61MD.md). Next 61M-E; packaging on hold.

### 2026-11-27 (Manila) — Phase 61M-E: asset specialization

- `engine/modular_assets.py` adds optional profile prompts, depth, attachment and expanded placement guides (`c1388fad9431`); API integration (`aa9702ec64c1`), Modular profile selection and attachment retention (`04762ce1814e`), CPU regressions (`1e88f6518c0c`).
- Existing recipe categories retained; category replacement still hides all matching layers. Expanded masks remain bounded by canvas, hand placement is heuristic, occluded rear surfaces are not reconstructed. CI and hardware acceptance pending; stacked on 61M-D. [Phase notes](phases/PHASE61ME.md). Next 61M-F. Packaging on hold.

### 2026-11-27 (Manila) — Phase 61M-F: candidate cleanup and alignment

- `engine/modular_assets.py` adds validated non-destructive candidate review, transformed placement metrics and registered export (`9b8af0418657`); API endpoint (`2c168ea8d0cb`); Modular UI cleanup, manual transforms, reset, preview and export (`e07c574b540c`, `acda8336e988`); CPU regressions (`405dddede84a`).
- Decisions: explicit review before accepting, reuse existing Alpha Cleanup, numeric transforms, no recipe mutation during review. Partial clipping and browser alpha rounding remain possible. CI and hardware acceptance pending; stacked on 61M-E. [Phase notes](phases/PHASE61MF.md). Next 61M-G. Windows packaging remains on hold.

### 2026-11-26T22:20:53Z — 61M-D integration

- PR #72 passed CPU validation run 45903481248 and merged at `c0abab5e357a`.

### 2026-11-26T22:21:01Z — 61M-E integration

- PR #73 passed CPU validation run 45903693075 and merged at `4fd7393bac35`.

### 2026-11-26T22:21:10Z — 61M-F integration

- PR #74 passed CPU validation run 45903911050 and merged at `99a04d0480f7`.

### 2026-11-27 (Manila) — Phase 61M-G: stabilization

- `engine/modular_assets.py` reduces extraction temporary arrays, avoids duplicate validation and adds conservative clipping warning (`168e42f312aa`); API preflight and error handling (`a7dd075f3d0c`); UI freshness checks, image release and review timing (`55e0e34a7310`); regression tests (`7fe38d0eeddd`).
- No measured speedup or GPU/desktop acceptance. Heuristic fit and nonsemantic extraction limitations remain. CPU CI pending. [Phase notes](phases/PHASE61MG.md); manual checklist updated. Phase 62 packaging remains on hold.

### 2026-11-26T22:36:09Z — 61M-G integration

- PR #75 passed CPU validation run 45904396866 and merged at `054c55806cd3`.

### 2026-11-27 (Manila) — Phase 61N-A: Generate prompt audit and body-base fix

- Confirmed actual knight/blue armor/red cape input defaults and hidden costume phrases in three style presets. Neutral style phrases (`1decf8eec220`), dedicated mannequin prompt and anti-clothing negatives (`adfbe7e23310`), Generate API flag (`dca0d8f5df8b`), UI neutral defaults and project setting (`8bfc51958217`), prompt tests (`a1632d385a8c`) and API routing regressions added.
- Existing saved prompts are preserved; no model policies changed. Model output quality not verified; CI pending. [Phase notes](phases/PHASE61NA.md). Next 61N-B final prompt visibility, C existing Art Style selector additions, D integration checks. Packaging on hold.

### 2026-11-26T23:26:29Z — 61N-A integration

- PR #76 passed CPU validation run 45910461870 and merged at `7b76e807df84`.

### 2026-11-27 (Manila) — Phase 61N-B: prompt transparency

- Shared engine positive/negative assembly (`017c082d194e`), CPU preview endpoint and shared mode resolution (`eb90446070c5`), Generate inspection/copy UI (`b4150cd35c23`), CPU prompt and endpoint regressions (`e531239660f6`, `d9861a32a21f`).
- Style remains independent of subject content. Snapshot preview is engine text before model tokenization; no GPU or desktop acceptance verified. CI pending. [Phase notes](phases/PHASE61NB.md). Next 61N-C existing Style selector; packaging on hold.

### 2026-11-27 (Manila) — 61N-B validation correction

- CPU run 45911091109 failed on Windows and Ubuntu in the isolated queue JavaScript harness; API and styles passed. Prompt preview listener registration was inside the extracted queue block; moved DOM listener setup outside it to avoid executing browser-only initialization in the fake DOM. Revalidation pending.

### 2026-11-27 (Manila) — Phase 61N-C: head-height style presets

- Six neutral style mappings (`afc4d5ed2374`) and existing Art Style selector group (`5c6595d04b16`); CPU prompt, API preview and queue UI tests (`548c25f7054b`, `e559fce50d61`, `ffd172f0b2d2`).
- All legacy style IDs preserved. New styles use existing HD finishing and shared style settings; no independent proportion dropdown or automatic anatomy enforcement. No model inference or desktop verification; CI pending. Stacked on corrected PR #77. [Phase notes](phases/PHASE61NC.md). Next 61N-D; packaging on hold.

### 2026-11-26T23:48:00Z — 61N-B integration

- PR #77 passed CPU validation run 45911491222 and merged at `b63d6ce7f184`.

### 2026-11-26T23:48:08Z — 61N-C integration

- PR #78 passed CPU validation run 45911598462 and merged at `9a6605f5e106`.

### 2026-11-27 (Manila) — Phase 61N-D: Generate integration

- Prompt snapshot invalidation, history restores actual generation parameters and saved HD control refresh (`c6f2173ae6c2`); mocked native and local runtime parity tests (`052b01e6455d`); queue UI history/preview regressions (`7d7552d88f0b`); batch recipe propagation test (`6957b1fdbdee`).
- Tests added, CI pending. No actual model inference, desktop acceptance or head-height enforcement claimed. Existing model policies unchanged. [Phase notes](phases/PHASE61ND.md); manual checklist updated. Packaging on hold.

### 2026-11-27T00:21:58Z — 61N-D integration

- PR #79 passed CPU validation run 45913273985 and merged at `29b4437f72da`. All 61N phases merged and CPU validated. Real model inference, desktop acceptance and head-height quality remain unverified. Phase 62 remains on hold.

### 2026-11-27 (Manila) — Phase 61O: lightweight WebP export

- Added lossless exact-RGBA Pillow encoder and bounded scale (`8292593f1bfb`), CPU API (`a0c28373cc89`), shared image download selector and routing (`545a5fef6c3c`), CPU roundtrip tests (`f847dba40639`) and JS download format/error tests (`0bf917d77c80`, `70da2e8d8295`).
- PNG remains default; standalone static WebP only, project data and engine export packs unchanged. No measured size savings or desktop acceptance. CPU CI pending. [Phase notes](phases/PHASE61O.md). Packaging on hold.

### 2026-11-27T03:19:26Z — 61O integration

- PR #80 passed CPU validation run 45922429701 and merged at `b8885badac71`. Standalone lossless WebP exports CPU-validated; desktop download acceptance and representative file-size savings remain unverified. Existing PNG/game-engine packs unchanged. Phase 62 on hold.

### 2026-11-27 (Manila) — Actions usage pause and Phase 61P-A

- User requested manual-only CI to conserve remaining Actions minutes; push/PR triggers removed on main (`3db2b22e6105`), manual dispatch retained. No CI started for this phase.
- Dedicated standalone procedural VFX recipes (`d8aa648b1eac`), API endpoints (`0358f5421681`), VFX workspace, browser-local library, transparent playback, recipe import/export and scene insertion (`3ffe0819a76d`), CPU regression file (`6830b07437c0`).
- Reuses existing Phase 47 renderer and PNG/GIF atlas exporter; current-frame PNG/WebP, no projectile motion, explosion chaining or AI yet. Saved library is browser-local, portable via JSON. Tests added but not executed here; desktop and export acceptance pending. [Phase notes](phases/PHASE61PA.md). Packaging on hold.

### 2026-11-27 (Manila) — Phase 61P-B: advanced slash and weapon trails

- Shared renderer seven advanced kinds, tapered ribbon/echo/glow/spark controls (`c4bc6b149e11`), preset schema (`815a311e249d`), Studio/Scenes preset UI (`1cb429a4358d`), short active-range correction (`625bb052e6e2`), CPU regressions (`681c8f55748a`).
- Original slash preserved. Procedural trails are not sampled weapon-bone motion; glow baked, no additive shader. Tests added but not executed; no Actions dispatch, desktop acceptance pending. Stacked on PR #81. [Phase notes](phases/PHASE61PB.md). Next 61P-C; packaging on hold.

### 2026-11-27 (Manila) — Phase 61P-C: projectile motion paths

- Added four projectile presets, exact endpoint displacement, straight/arc/ease-in/ease-out trajectories, tangent-oriented procedural artwork, fixed path-enclosing standalone canvas, Studio and Scene controls, standalone scene effect export and CPU regressions. Files: `engine/vfx.py`, `engine/vfx_studio.py`, `engine/scenes.py`, `engine/main.py`, `ui/index.html`, `tests/test_vfx_studio.py`.
- User approved resuming CI following reported public visibility; connected metadata still reported private. Restored automatic push/PR triggers with public-only automatic job condition (manual dispatch retained). No test success claimed; CPU and desktop validation pending. Stacked on #82; explosion chaining, actual weapon attachment, AI art and packaging remain future work. [Phase notes](phases/PHASE61PC.md).

### 2026-11-27T04:37:16Z — 61P-C validation status

- PR #83 opened at `6da666e8cafa`. [CPU validation run 45941010590](https://github.com/Aishi-mana/SpriteForge/actions/runs/45941010590) completed with skipped conclusion, not a pass. Repository metadata still reported private; public-only condition prevented automatic CPU jobs. PRs #81–83 remain open. Manual dispatch or confirmed public visibility and another PR event are needed for actual validation.

### 2026-11-27 (Manila) — Phase 61P-D: explosion and impact chaining

- Three standalone burst presets (explosion, shockwave, frost burst), optional impact flash or burst on projectile arrival, independent impact duration/color/scale, deterministic flight/impact stage timing, fixed canvas and shared scene/standalone export. Updated `engine/vfx.py`, `engine/vfx_studio.py`, `engine/scenes.py`, `ui/index.html`, `tests/test_vfx_studio.py`. Corrected 61P-C misplaced Scene trajectory controls and added a regression assertion. Old recipes default to no impact; no arbitrary recursive chains or collision detection. Actor-attached effects retain current anchor semantics. CPU tests added, not run locally; desktop pending.
- User approved public auto CI. Restored push/main and PR triggers directly on main (`1146a683f037`), retaining public-only automatic execution because connected metadata still reports private. Stacked on #83. [Phase notes](phases/PHASE61PD.md). Next 61P-E AI effect artwork; packaging on hold.

### 2026-11-27T04:51:09Z — 61P-D validation status

- PR #84 opened at `066e1d1cb3e5`. Automatic main push run [45942246404](https://github.com/Aishi-mana/SpriteForge/actions/runs/45942246404) and 61P-D pull request run [45942323715](https://github.com/Aishi-mana/SpriteForge/actions/runs/45942323715) both completed as skipped, not passed. Connected repository metadata still private. Public-only condition prevented hosted CPU jobs. PRs #81–84 remain open; no merge or desktop acceptance claimed.

### 2026-11-27 (Manila) — Phase 61P-E: AI effect artwork

- Added VFX-specific prompt assembly, existing model/runtime generation endpoint and CPU image import/flat-background keying, portable bounded PNG artwork in recipes, optional opacity-controlled overlay with procedural rotation/scale/fade, Studio generation/import/clear/preview controls, regression tests. Files: `engine/generate.py`, `engine/main.py`, `engine/vfx_art.py`, `engine/vfx.py`, `engine/vfx_studio.py`, `ui/index.html`, `tests/test_vfx_studio.py`, `tests/test_vfx_art_prompt.py`. Saved artwork replays without a model; effects preserve their procedural motion and impact. No model inference or desktop validation performed; single-image artwork, not AI video or frame-by-frame generation. Impact stage remains procedural. Stacked on #84; earlier PRs remain open; repo metadata still private. [Phase notes](phases/PHASE61PE.md). Next timeline/keyframes, packaging on hold.

### 2026-11-27 (Manila) — 61P-E PR status

- PR #85 opened at `aeb49b7b5574`. [CPU run 45942676416](https://github.com/Aishi-mana/SpriteForge/actions/runs/45942676416) reported completed/skipped; no test pass claimed unless completed successfully. Repository metadata still private, automatic CPU jobs remain public-only. PRs #81–85 remain open; #81 mergeability needs rechecking after the main CI update. No real model inference or desktop acceptance claimed.

### 2026-11-27 (Manila) — Phase 61P-F: VFX timeline and keyframes

- Added bounded relative-frame keyframe tracks with linear/smooth/hold interpolation, additive position and rotation, multiplicative size/opacity/RGB tint, Studio and Scene editors, deterministic shared compositor and path-aware canvas sizing, recipe persistence, and CPU regressions. Files: `engine/vfx_keyframes.py`, `engine/vfx.py`, `engine/vfx_art.py`, `engine/vfx_studio.py`, `engine/scenes.py`, `ui/index.html`, `tests/test_vfx_studio.py`. No-key recipes preserve prior behavior. Keyframes apply across flight and impact; relative frame indexing preserves timing when inserted into a scene. Max radius stays 128; no per-property independent key lists or curve handles yet. CPU tests added, desktop not exercised.
- Repository confirmed public, existing connector read/write access and branch creation succeeded with active repository rules. Automatic public CI enabled; prior phases still stacked/unmerged. [Phase notes](phases/PHASE61PF.md). Next combat integration; packaging on hold.

### 2026-11-27 (Manila) — 61P stack CI policy reconciliation

- PR #81 conflicted with the updated `AGENTS.md` on main (`09818c02f0c0`). Preserved main's public-only automatic CPU workflow and current repository instructions using ordinary merge commits rather than rewriting history. Previous cumulative CPU run [45947967990](https://github.com/Aishi-mana/SpriteForge/actions/runs/45947967990) passed on Ubuntu and Windows for PR #86 at `945d9135c1a5` (2026-11-27T05:51:17Z). Reconciliation checks and final integration remain pending; no desktop or GPU acceptance claimed.

### 2026-11-27T08:12:42Z — 61P-A–F integration

- All six reconciled PRs passed automatic CPU validation and merged into main in dependency order. 61P-A: PR #81, [run 45962863576](https://github.com/Aishi-mana/SpriteForge/actions/runs/45962863576), merge `91c62c56cf93`; 61P-B: PR #82, [run 45962907263](https://github.com/Aishi-mana/SpriteForge/actions/runs/45962907263), merge `a01a2eebc3d2`; 61P-C: PR #83, [run 45962920525](https://github.com/Aishi-mana/SpriteForge/actions/runs/45962920525), merge `bdc062e2c6cd`; 61P-D: PR #84, [run 45962950898](https://github.com/Aishi-mana/SpriteForge/actions/runs/45962950898), merge `feed6ec27c53`; 61P-E: PR #85, [run 45962966727](https://github.com/Aishi-mana/SpriteForge/actions/runs/45962966727), merge `2906aa9ad5e3`; 61P-F: PR #86, [run 45962998966](https://github.com/Aishi-mana/SpriteForge/actions/runs/45962998966), merge `8c8be370f45c`. Public CI remains enabled; no repository rules changed or force pushes used. Fresh main-branch validation pending at integration. Real model inference and desktop acceptance remain outstanding. Next 61P-G combat integration; Phase 62 packaging on hold.

### 2026-11-27 (Manila) — Phase 61P-G: combat integration

- Main post-merge CPU validation [45963984250](https://github.com/Aishi-mana/SpriteForge/actions/runs/45963984250) passed on baseline `3b0282e00ab3`. Added combat cue scheduling by reachable source clip frame and delay, mirrored actor-follow attachment, frozen launch/target placement, exact sampled projectile arrival, attack VFX playback in behavior sandbox and CPU regressions. Files: `engine/combat_vfx.py`, `engine/vfx.py`, `engine/scenes.py`, `engine/main.py`, `ui/index.html`, `tests/test_combat_vfx.py`. Cues bake ordinary scene effects; reapply after actor changes. Anchor offsets are user-defined relative to actor pivot; no skeletal weapon sampling, dynamic collision, gameplay damage, or target simulation in behavior preview. CPU tests added, not yet executed; desktop pending. [Phase notes](phases/PHASE61PG.md). Next export/stabilization; packaging on hold.

- Pre-PR correction: frozen left-facing launch stores a separate world mirror flag rather than mutating the authored direction or keys; reapplying the same cue is idempotent. Standalone export accounts for mirrored path bounds, behavior preview uses unmirrored local artwork and its own launch facing. Added regression assertion; CI pending.

### 2026-11-27T08:49:29Z — 61P-G integration

- PR #87 passed CPU run [45965257424](https://github.com/Aishi-mana/SpriteForge/actions/runs/45965257424) at `ba257a87714f`, merged to main `e9719b541a02`. Desktop/GPU acceptance not claimed.

### 2026-11-27 (Manila) — Phase 61P-H: VFX export and stabilization

- Corrected moving and keyframed effect origin metadata, conservative origin-inclusive bounds, mirrored attached effect exports; added optional full-alpha APNG and lossless animated WebP, correct GIF loop setting and cumulative duration rounding, configurable Studio atlas columns/engine targets, versioned effect recipe/scene cue JSON in ZIP manifest. Stabilized impact range clamping and stale recipe import handling. Files: `engine/vfx.py`, `engine/vfx_studio.py`, `engine/vfx_export.py`, `engine/exporter.py`, `engine/main.py`, `ui/index.html`, `tests/test_vfx_export.py`. PNG atlas remains authoritative for exact frame identity; preview encoders can merge identical frames, GIF is binary alpha. Engine import, GPU and desktop acceptance remain pending. CPU regressions added; CI pending. Phase 62 packaging remains on hold. [Phase notes](phases/PHASE61PH.md).

### 2026-11-27T09:43:54Z — Phase 61P-H integration and 61P milestone

- PR #88 passed [CPU validation 45969155296](https://github.com/Aishi-mana/SpriteForge/actions/runs/45969155296) on Windows and Ubuntu at `eb4be331427e` (completed 2026-11-27T08:55:46Z); merged to main at `69a2b4684452`. Phase 61P-A–H is fully implemented, merged and CPU-validated on PRs. 61P-G post-merge CPU run [45968674565](https://github.com/Aishi-mana/SpriteForge/actions/runs/45968674565) also passed. Final main post-merge validation pending at integration; real desktop, GPU inference and native engine import acceptance remain outstanding. No Phase 62 packaging started; repository rules unchanged.

### 2026-11-27T09:47:27Z — 61P main validation

- Final main CPU run [45976217804](https://github.com/Aishi-mana/SpriteForge/actions/runs/45976217804) passed at `a215cb9358cb`. Desktop, real GPU and native engine acceptance remain outstanding.

### 2026-11-27 (Manila) — Phase 61Q-A: World Studio foundation

- User approved modern anime/HD-2D quarter-view AI environment blockouts with separated ground, rocks, trees, foreground and gameplay masks, manual polish and character playtest. Implemented independent World Studio tab with raster layer import, ordered compositing, offsets/drag, visibility, lock, opacity, zoom/scroll viewport, spawn coordinates, undo, PNG composite and portable JSON, character project save/load and ZIP restoration. Files: `engine/world.py`, `engine/main.py`, `engine/projects.py`, `ui/index.html`, `tests/test_world.py`; implementation commit `dc2e096c3c5c`. Default quarter view 1280x720, modern anime, smooth sampling. Limits: 3072 px per side, six million canvas pixels, 24 layers/24 million source pixels/48 MB encoded. Masks are imported map-sized alpha coverage; display is separate from art, no collision enforcement yet. Existing tile painter unchanged. AI generation, style extraction, mask painting and playable actors deferred to B–F. CPU tests added, CI pending; desktop and GPU acceptance not performed. [Phase notes](phases/PHASE61QA.md). Phase 62 held; 61R system assets planned.

### 2026-11-27T10:12:14Z — 61Q-A integration

- PR #89 CPU run [45979376737](https://github.com/Aishi-mana/SpriteForge/actions/runs/45979376737) passed (completed 10:10:09Z), merged to main `592e3e6e1b7a`. Desktop acceptance pending.

### 2026-11-27 (Manila) — Phase 61Q-B: shared-layout AI world blockout

- Added deterministic quarter-view winding/straight/clearing layout, adjustable object counts, seeded placement and spawn, model-agnostic AI passes for distant scenery, ground and trail materials, isolated rock/tree/foreground objects, flat-key alpha cleanup, independent editable prop instances and atomic assembly. Layout preview and sequential per-pass progress with cancellation between passes. Uses the selected checkpoint/LoRA and global settings; no pixel quantization for HD art. Files: `engine/world_blockout.py`, `engine/world.py`, `engine/generate.py`, `engine/main.py`, `ui/index.html`, `tests/test_world_blockout.py`. Initial implementation `1d631c21c665`. Persistent layout settings, map JSON and project roundtrip. AI blockout max 3M canvas pixels; no semantic image decomposition or guarantee that perspective/lighting agree; repeated asset artwork per role, masks/character style/playtest pending. Synthetic CPU regression tests added; real GPU and desktop untested. Next 61Q-C style matching; Phase 62 held.

- Pre-PR review: retained a transparent rim after cropping isolated props, including rectangular cutouts; fixed synthetic test spawn for smaller map and simplified button state. No model execution performed.

### 2026-11-27T10:24:30Z — 61Q-B integration

- PR #90 passed [CPU validation 45980557941](https://github.com/Aishi-mana/SpriteForge/actions/runs/45980557941) at `2b7e104e925e` (completed 10:18:01Z), merged into main `5e5208a2ce13`. Real model/desktop acceptance pending.

### 2026-11-27 (Manila) — Phase 61Q-C: environment style matching

- Added portable editable style profile to world schema, deterministic visible-pixel analysis (palette suggestions, saturation, percentile tonal range and neighboring-pixel edge-change proxy), bounded reference thumbnail, manual shading/linework/style notes, current or saved character source/PNG import, optional palette accent suggestions, shared text guidance in all six AI passes, optional explicit model-supported image conditioning and strength. Profile defaults to text guidance without palette lock; no inferred semantic style or character proportions. Files: `engine/world_style.py`, `engine/world.py`, `engine/world_blockout.py`, `engine/main.py`, `ui/index.html`, `tests/test_world_style.py`; backend commit `b06086d3f8f1`. Existing world JSON and project save/restore preserve profile; standalone profile JSON reusable between maps. Metrics are heuristic, opaque backgrounds affect analysis unless removed, conditioning can transfer unwanted character features; model-specific behavior and GPU quality unverified. CPU tests added, CI pending; desktop acceptance pending. Next 61Q-D gameplay masks/depth hints. Phase 62 packaging held.

### 2026-11-27T10:41:08Z — 61Q-C integration

- PR #91 passed [CPU validation 45982154637](https://github.com/Aishi-mana/SpriteForge/actions/runs/45982154637) at `91627ed7c158` (completed 10:29:48Z); merged to main `9e00e5985dd0`. 61Q-B main run 45981851133 also passed. Desktop/GPU acceptance pending.

### 2026-11-27 (Manila) — Phase 61Q-D: gameplay masks and depth hints

- Added deterministic alpha-derived walkable masks from ground-detail/trail or ground, bottom-silhouette contact ellipses for rocks/foliage, separate occlusion coverage, editable local anchors, solid/occlusion flags and ground/sorted/foreground depth modes. Blockout optionally builds three map-sized suggested masks (default on in UI). Rebuild preserves manual masks and respects locked generated masks; collision takes priority over walkable; mask visibility/opacity debug-only. Added source signature/stale check, spawn validation, coverage counts, mask filters and depth/footprint overlay. Files `engine/world_masks.py`, `engine/world.py`, `engine/main.py`, `ui/index.html`, `tests/test_world_masks.py`; implementation `61e1ea88b65b`. Heuristic footprints and masks require review; raster snapshots must be rebuilt after source changes, no semantic segmentation or actual character movement yet. Fixed CPU tests added, CI pending; GPU/desktop acceptance pending. Phase 62 held. Next 61Q-E manual polish.

### 2026-11-27T10:46:47Z — 61Q-D integration

- PR #92 passed [CPU validation 45984507095](https://github.com/Aishi-mana/SpriteForge/actions/runs/45984507095) at `582847be407f` (completed 10:46:34Z), merged to main `b51bb010d145`. 61Q-C main run 45984176778 passed. Desktop/GPU acceptance pending.

### 2026-11-27 (Manila) — Phase 61Q-E: manual polish and regional regeneration

- Implemented persistent tri-state mask corrections (add, erase, restore suggestions) as separate map-sized RGBA correction layers, effective coverage preview, brush radius and continuous strokes; correction survives automatic rebuild, collision still wins. Generated walkable base now retains raw path coverage before collision subtraction, enabling erase collision to restore path (rebuild older generated masks). Added duplicate/mirror/scale around saved ground-contact anchor, rectangle selection, local PNG/AI artwork replacement with optional interior edge feather and unchanged surface alpha/other layers. Files `engine/world_polish.py`, `engine/world_masks.py`, `engine/world.py`, `engine/main.py`, `ui/index.html`, `tests/test_world_polish.py`; initial backend `e7d3464bc5fe`. Branch based on 61Q-D head during CI, parent PR then passed and merged. AI patch is fresh generation/fitted art, not contextual inpainting; review seams, prop contact and stale masks. CPU regressions added, validation pending, desktop/GPU unverified. Next 61Q-F interactive playtest; Phase 62 held.

### 2026-11-27T10:57:41Z — 61Q-E integration

- PR #93 passed [CPU validation 45985180212](https://github.com/Aishi-mana/SpriteForge/actions/runs/45985180212) at `f437a39c0918` (completed 10:51:17Z); merged to main `50be84a87949`. 61Q-D main run 45984971810 passed. Desktop/GPU acceptance pending.

### 2026-11-27 (Manila) — Phase 61Q-F: interactive character playtest

- Added separate session-only World Studio playtest canvas; current standard/approved sprite, scene actor, saved standard animation project and imported actor JSON clip assignment, idle/walk/run/attack/cast, four/eight-direction movement with normalized diagonal, swept circular feet occupancy and sliding, effective corrected masks and stale/spawn validation, camera follow/zoom, local pivot, horizontal facing mirror, depth sorting, foreground, optional scene or saved VFX on action frame, keyboard and held pointer buttons, reset/stop. Files `engine/world_playtest.py`, `engine/main.py`, `ui/index.html`, `tests/test_world_playtest.py`, `tests/js/world_playtest_test.js`, `tests/test_ui.py`; backend commit `0dbca9e8c8f7`. Map is not mutated. No navmesh, NPC, hit damage or transitions; 4/8-way movement uses side-facing clips not directional art, occlusion mask is debug hint while actual visual occlusion follows layer depth, no walkable mask means bounds/collision-only. CPU and JS regressions added; CI pending, actual desktop/GPU/engine acceptance pending. Initial 61Q scope implemented; Phase 62 held; Phase 61R system assets planned.

- Pre-PR review: bounded aggregate saved-project clip retrieval, cleared unmatched slots when loading a different character to avoid mixing animations, skipped stationary collision scans, added stale check before sending prepared clips. No desktop acceptance performed.

### 2026-11-27T11:40:01Z — 61Q-F integration and initial World Studio milestone

- PR #94 passed [CPU/JavaScript validation 45987012092](https://github.com/Aishi-mana/SpriteForge/actions/runs/45987012092) on Windows and Ubuntu at `35694d24ae4e` (completed 2026-11-27T11:04:15Z). Merged into main `0f3df14f4224`. 61Q-E main run 45986466322 also passed. All six initial 61Q subphases now merged and CPU-validated on their PRs; final main validation, actual desktop/GPU acceptance remain pending. Future extensions (NPCs, transitions, directional animation selection, native map export) remain separate. Phase 61R System Asset Studio planned, not started; Phase 62 packaging held.

### 2026-11-27T11:43:07Z — World Studio final main validation

- Main CPU/JS runs 45992411970 (docs baseline `af26215e7773`, completed 11:43:05Z) and 45992345405 (merge `0f3df14f4224`, completed 11:43:07Z) passed. Desktop/GPU acceptance pending.

### 2026-11-27 (Manila) — Phase 61R-A: System Asset Studio foundation

- Approved 61R A–J roadmap. Added versioned theme, unique reusable artwork library, independently positioned image/text/rectangle instances, category labels, optional palette and art direction, alpha PNG import/export, editable labels/fonts/geometry/opacity/visibility/lock, stacking/drag/duplicate/undo, zoom, procedural starter layout, preview PNG and portable theme JSON. Integrated optional `system_theme` in project save/load and archive validation. Files `engine/system_assets.py`, `engine/projects.py`, `engine/main.py`, `ui/index.html`, `tests/test_system_assets.py`, `tests/js/system_assets_test.js`, `tests/test_ui.py`; backend commit `27f7e13c0d2f`. Max 32 assets, 64 components, 24 MB encoded art, 12M source pixels, 6M preview pixels. No AI kits, shared profile extraction, nine-slice, functional controls or native export yet. Generic local font families only; preview PNG is client-rendered. CPU/JS tests added, CI pending. Desktop/GPU acceptance not performed; Phase 62 held. Next 61R-B.


## 2026-11-27 20:41 PHT — Phase 61R-B: Shared style profiles and AI UI kits

- Reuse validated World/character style profiles in system themes, including project and portable JSON persistence.
- Add starter, menu and HUD six-role kits, separate selected-model generation passes, transparent artwork normalization and atomic append preserving layouts.
- Add CPU coverage for style guidance, kit validation, append and persistence. CI and desktop/GPU acceptance not yet verified. No manual workflow dispatch.


## 2026-11-27 PHT — Phase 61R-C: Panels, frames and nine-slice

- Add per-instance source margins and nine-slice rendering for reusable image panels and frames, including transparent centers, integer destination cuts and proportional border compression for small layouts.
- Add editor toggle, editable margins and quarter-margin suggestion; preview/export use the same renderer. Legacy image instances retain stretch rendering.
- Add CPU validation, archive roundtrip and JS geometry coverage. Stacked on 61R-B while its validation is running; no manual CI dispatch. Desktop visual acceptance pending.


## 2026-11-27 20:58 PHT — Phase 61R-D: Controls and interaction states

- PR #96 and #97 passed CPU validation and merged. Add button, toggle, tab and slider visual-state configuration, alternate image or rectangle-color variants, normal fallback, pointer preview and forced-state inspection. Preview changes are transient; PNG export uses normal artwork.
- Validate state asset references and nine-slice compatibility; prevent referenced artwork deletion. CPU and JS tests added. Slider value mechanics, keyboard navigation, game actions and desktop acceptance remain pending. No manual CI dispatch.


## 2026-11-28 06:25 PHT — Phase 61R-E: Item, equipment and skill icons

- PR #98 passed CPU validation and merged. Added eight icon categories, shared style and selected-model generation, transparent square output at six sizes, categorized artwork filtering and persistent icon metadata. Added CPU tests and project roundtrip. Generation is single-icon; batch atlases and engine metadata export deferred. No manual CI dispatch; GPU acceptance pending.


## 2026-11-28 07:30 PHT — Phase 61R-F: HUDs and resource bars

- PR #99 passed CPU validation and merged. Add per-component HP, MP, stamina, XP, cooldown and custom resource bindings, four fill directions, numeric labels, transient value preview and damage/healing simulation. Persist default values and use defaults in clean PNG export. CPU and JS tests added. Live gameplay binding, timed cooldowns and floating damage effects deferred. No manual CI dispatch.
- User requested a follow-up full-frame animation pipeline inspired by Sorceress Auto-Sprite: character image to motion video or redrawn frames, aligned transparent sprite sheets, no mandatory cutout rig. Plan after 61R; backend feasibility and GPU requirements to be evaluated.


- 61R-F validation #239: Windows passed; Ubuntu HUD tests passed but queue FIFO/history checks failed. Fix job ID timestamp sampling and sort queue/history by creation timestamp with ID tie-breaker; add clock rollback regression. Awaiting fresh validation.


## 2026-11-28 PHT — Phase 61R-G: Inventory, dialogue and menus

- Added four editable layout recipes, proportional canvas sizing, optional role-based artwork reuse and nine-slice, interactive slots and buttons, independent labels, inventory icon placement, atomic append/replace with component budget and locked-layout protection. JS regression coverage added. Stacked on 61R-F queue fix pending validation. Runtime inventory data, dialogue branching, and actual menu actions are deferred. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61R-H: Animated UI effects

- PR #100 and #101 passed CPU validation and merged. Add per-component fade, slide, scale, pulse, highlight glow and resource sweep recipes with delay, easing, duration, intensity, looping and reverse; non-destructive requestAnimationFrame preview, static PNG export and persisted validated motion metadata. CPU and JS tests added. Timed gameplay cooldowns, floating damage text, event-driven transitions and animated export deferred. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61R-I: Interactive testing and World integration

- Reuse the System Studio renderer in the World playtest as a viewport-fixed aspect-fit overlay; preserve nine-slice, text, controls, HUD fills and motion recipes. Add pointer testing, role-wide resource simulation, reset and independent runtime image cache. Map/theme authoring and static export remain unchanged. JS regression tests added. Stacked on 61R-H pending validation. Runtime inventory/dialogue scripts, game-event bindings and keyboard UI navigation deferred. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61R-J: Exports and stabilization

- PR #102 and #103 passed CPU validation and merged. Added validated UI ZIP export with RGBA PNGs, categorized icons, external-path manifest, editable theme roundtrip, Godot and Unity layout hints and integration README. Added archive integrity, metadata, coordinate/border mapping, empty theme and invalid-reference tests. Native engine scenes/importers and desktop acceptance deferred. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61S-A: Full-frame Animation Studio foundation

- PR #104 passed CPU validation and merged. Add independent full-frame workspace, approved character or imported PNG reference, motion description, same-canvas PNG frame imports, ordering/removal/undo, FPS/loop playback, pivot guide, validated bounded document and project/archive persistence. No skeletal dependency. CPU regression tests added; AI generation backend, automatic alignment, video import and export deferred. No manual CI dispatch.


## 2026-11-28 08:36 PHT — Phase 61S-B: Local AI video backend

- PR #105 passed CPU validation and merged. Add optional local Diffusers LTX image-to-video adapter, model discovery via video_models/model_index.json, reference letterboxing, bounded settings, shared GPU lock and image pipeline release, CPU offload, MP4 preview/download and discard-result handling. Fake runner tests cover routing and validation. No model download, actual GPU acceptance, server-side cancellation or frame extraction yet. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61S-C: Reference-guided character animation

- Add persisted motion presets, optional identity/camera/in-place/loop guidance, view selection, matching neutral/chroma reference backgrounds, safe framing margin and server-generated prompt preview. Existing reference pixels are preserved apart from fit/compositing. Tests cover prompt construction, background, validation and persistence. Stacked on 61S-B pending validation. Identity consistency and seamless loops are guidance only; extraction and actual GPU acceptance pending. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61S-D: Video-to-sprite extraction

- PR #107 passed CPU validation and merged. Added optional imageio/FFmpeg video sampling, start/end range, FPS, chroma key tolerance and soft alpha, shared union crop, common pivot, atomic validated timeline replacement with undo, synthetic CPU regression tests. Actual decoder and desktop acceptance pending; no semantic segmentation, despill or per-frame anatomical alignment yet. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61S-E: Character consistency and flicker correction

- PR #108 passed CPU validation and merged. Added local temporal bounds/color diagnostics, opt-in bounded position and color corrections, partial-alpha edge smoothing, chroma despill, selected-frame original/corrected preview and undoable acceptance. Zero strengths preserve exact source data; scale is diagnostic only. Synthetic regression tests added. No semantic identity detection, optical flow or GPU acceptance yet. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61S-F: Frame interpolation and smooth motion

- Added CPU nearest-frame, premultiplied-alpha blend and bounded translation-assisted interpolation, 2–4x frame multipliers, optional duration preservation, loop seam and non-loop terminal holds, exact original frames, bounded output and separate preview playback/scrub/accept/undo. Tests cover motion, alpha, timing and budgets. Stacked on 61S-E pending validation. Optical flow, neural interpolation and desktop acceptance deferred. No manual CI dispatch.

- Included 61S-E boundary correction: preserve first and last frames during temporal color and position correction.


## 2026-11-28 PHT — Phase 61S-G: Keyframe editing and regeneration

- Persist keyframe markers and locks; remap on reorder/removal/interpolation, preserve locked frames during consistency correction, block extraction replacement until unlocked. Stage imported PNG or existing image editor output as a candidate, compare and accept a single frame with undo. Added CPU tests. AI editing uses existing editor capabilities, no direct neighboring-frame conditioning. Stacked on 61S-F; desktop/GPU acceptance pending. No manual CI dispatch.

- 61S-E validation #259 failed on Windows and Ubuntu: two-sample endpoint median changed stable boundary frames. Restrict temporal color and position corrections to interior frames; endpoint alpha/despill behavior unchanged. Revalidate automatically.


## 2026-11-28 PHT — Phase 61S-H: Seamless loops and directions

- Reconciled E–G, CPU runs #261/#264/#265 passed and all merged. Add independent directional snapshots with shared canvas/pivot/FPS, four/eight direction selection, aggregate validation, direction switching, seam difference analysis, ping-pong and alpha bridge append operations. Original frames and locks retained. CPU tests added; desktop acceptance pending. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61S-I: Combat and complex motion

- PR #112 CPU #268 passed and merged. Added combat presets and validated per-frame phase, event/label, hitbox, VFX anchor and root displacement. Directional snapshots retain metadata; reorder/remove/interpolation remap events; extraction clears metadata. Canvas overlay and undoable editing. CPU tests added. Runtime collision, combo execution, multi-clip orchestration and root application deferred. No manual CI dispatch.


## 2026-11-28 PHT — Phase 61S-J: World integration and export

- PR #113 CPU #270 passed and merged. Added full-frame directional World Studio source and saved-project loading, bounded clip validation, per-direction playback and current event display, image decode reuse, paged PNG atlas/sequence and lossless animated WebP ZIP exports with portable timing/pivot/combat metadata and Godot/Unity import notes. Native engine files, runtime damage/root motion and desktop/GPU acceptance deferred. No manual CI dispatch.


## 2026-11-28 09:40 PHT — Phase 62A: Initial UI audit and queue handoff

- User reported confusing layout and queue Animate buttons not working. Static review of UI found 20 workspaces, generic Animate routing to rig workflow, missing source image error handling, history response races, and missing full-frame result handoff. Added explicit rig/full-frame actions, immediate rig navigation, decode error reporting, full-frame reference transfer, project-load busy guard and history ticket checks. Added static UI contract regression. Actual desktop issue not reproduced; full browser and GPU acceptance remain pending. No manual CI dispatch.


## 2026-11-28 PHT — Phase 62B: Browser workflow smoke coverage

- Added explicit opt-in Playwright Chromium smoke script using real page, queue/history fixture, both animation handoffs, rig API error, invalid image and all navigation buttons. No live GPU or project mutations. Harden rig source failure and stale overlay response handling, full-frame busy checks and queue result metadata. Browser test not executed in this connector environment; manual opt-in avoids extra CI minutes. Stacked on 62A pending validation.


## 2026-11-28 PHT — Phase 62C: UI/UX consolidation

- PRs #115 and #116 passed CPU validation and merged. Reorganized the existing 20 workspace buttons into six expandable categories plus always-visible Queue, automatically opening the active category on direct navigation. Result cards now prioritize AI editing, full-frame animation, rig animation and save; all remaining actions are retained in expandable More actions. Corrected misleading directional reference label and clarified animation methods. Updated browser smoke for categorized navigation and expandable result actions. Browser/desktop acceptance pending; no manual CI dispatch.


## 2026-11-28 PHT — Phase 62D: Integration and data integrity

- Found saved-gallery edit deleted original before replacement; added validated atomic PUT replacement, unique IDs and project-scoped gallery callbacks. Serialize UI save/load, retain dirty state for edits during save, cancel stale load before application. Preflight secondary assets before modifying project files; serialize reads against writes. Correct directional reference src field; clear transient full-frame candidates on project load; guard shared FPS/canvas and world clip contracts; export keyframe/lock metadata. Regression tests added. Full crash-atomic multi-file saves and desktop/model acceptance remain pending. No manual CI dispatch.


## 2026-11-28 10:04 PHT — Phase 62E: Live acceptance tooling

- PRs #117 and #118 passed CPU validation and merged. Added opt-in live API/SDXL benchmark probe, resource snapshots, non-overwriting JSON report, mocked contract regression and manual release gate. No desktop/GPU execution in connector environment. No manual CI dispatch.


## 2026-11-28 PHT — Phase 62F: Queue result action hotfix

- User desktop screenshot confirms all primary Queue history result buttons remain inert despite CPU validation. Root cause: hOpen renders result cards, then assigns toolbar onclick handlers to every descendant button[data-a], overwriting render's callbacks. Exclude #hres descendants from toolbar binding; add static contract regression and expand opt-in browser smoke to check individual action dispatch. Browser and desktop execution still pending. No manual CI dispatch.


## 2026-11-28 PHT — Phase 62G: Animation workflow usability

- Desktop screenshot confirmed Queue-to-full-frame handoff now works. User found generation hidden behind collapsed sections. Promoted character, motion preset/prompt, local LTX model selector/readiness, frame count/FPS and Generate animation to visible two-column workflow; 25-frame conservative default, optional automatic extraction and playback, explicit timeline replacement, locked-frame and revision guards, advanced controls retained, timeline thumbnails compact. Added layout regression and browser smoke coverage for visible controls and missing model. Live browser/GPU execution pending; no manual CI dispatch.


## 2026-11-28 11:04 PHT — Phase 62H: Shared Wan video runtime

- Reused MVManaAtelier Wan image-to-video workflow and shared ComfyUI model/runtime discovery. Exact Q3_K_M high/low pair, acceleration LoRAs, UMT5 and VAE readiness; optional LTX retained. Owned temporary headless server, GGUF whitelist, node check, model-path mapping, GPU lock and cache release, bounded output, stage polling, 480x480/33/16/4 defaults. Other applications must be closed manually; no cross-app GPU lock or cancellation guarantee. CPU regression added; real ComfyUI/Wan execution pending. No manual CI dispatch.


## 2026-11-28 PHT — Phase 62H Windows cleanup hotfix

- User supplied real ComfyUI log: RTX 5070 Laptop GPU, 8151 MB VRAM, both Wan sampling stages completed, prompt executed in 80.40 seconds. UI reported WinError 32 on temporary engine.log. Replaced strict temporary directory cleanup with bounded retry and nonfatal cleanup, preserved last engine log outside job folder, explicitly waited for owned child exit. Added mocked locked-file regression. MP4 delivery and extraction still need live retest. No manual CI dispatch.


## 2026-11-28 PHT — 62H-C: Foreground protection and restrained idle

- User confirmed Wan MP4 delivery and 33 extracted frames after manually installing imageio dependencies. Neutral color key damaged face and white armor; requested smaller idle movement. Added border-connected chroma mask, conservative tolerance/softness, minimal idle and prompt intensity, re-extraction with current tolerances, requirements and existing-venv launcher repair. Added synthetic regression. Foreground matching colors connected to border remain a limitation; semantic BiRefNet/SAM planned. Actual desktop retest pending; no manual CI dispatch.


## 2026-11-28 PHT — 62J-A semantic animation alpha

- Reused Atelier's core BiRefNet graph and existing shared background_removal checkpoint via isolated offline ComfyUI runtime. Added explicit AI/chroma/keep-background selection, detection, re-extraction, optional RGB-gated three-frame mask stabilization, tests. Actual mask polarity, interior gaps, hair quality and GPU compatibility require desktop acceptance. SAM2 interactive tracking and manual paint/restore are not implemented here. No manual CI dispatch.


## 2026-11-28 PHT — 62J-B manual transparency correction

- Added selected-frame erase/restore brush, radius and strength, stroke overlay, explicit apply/discard, undo and validated server endpoint. Restore uses an explicitly imported, aligned original PNG; it does not reconstruct missing RGB or automatically recover source video frames. Locked frames and unedited frames protected; no SAM tracking or persistent foreground mask yet. Synthetic regression added; browser and desktop acceptance pending.


## 2026-11-28 12:08 PHT — Animation acceptance checkpoint and roadmap reprioritization

- #124, #125, #126 and #128 merged after CPU validation. User confirms video and 33-frame extraction; latest desktop test reports visible flicker, excessive idle movement and residual background despite improved character detail. Screenshot shows custom preset and Minimal intensity, but not the selected transparency method in full. No claim of verified BiRefNet inference from detection alone. User requests roadmap persistence and animation polish before global transparency rollout or other models. Next 62J-C, then SAM if needed and compatible. This entry records plans, not implementation of new algorithms.


## 2026-11-28 PHT — 62J-C animation polish (initial implementation)

- Added CPU-only controlled breathing from transparent reference, 0–4 px amplitude, periodic torso-band warp, exact unwarped head/feet regions, explicit timeline replacement/locks/undo. Approximate anatomy band is not a semantic body rig. Added conservative BiRefNet residual cleanup and stronger RGB-gated edge correction above 50%; UI defaults 80% temporal and 70% cleanup, method visible in extraction result. Re-extraction retains source MP4. Server now receives actual document for lock enforcement. Regression tests added. Desktop quality, quantitative flicker diagnostics, SAM tracking and broader cleanup remain pending. No manual CI dispatch.


## 2026-11-28 PHT — 62J-C1 controlled idle storage/UX hotfix

- User desktop reported 'Idle exceeds artwork budget' with 33 frames, 16 FPS and 1 px amplitude. Fit reference copy to selected output maximum (480 px default), account for original reference in pixel and encoded limits, bounded automatic downscale retry, reuse symmetric phase renders, retain frame count/FPS and original reference. Hide video-only generation controls in controlled mode; report actual output dimensions and actionable errors. Directional canvases stay fixed. Regression added; real reference desktop retest pending. No manual CI dispatch.


## 2026-11-28 PHT — 62J-C2 playback flicker hotfix

- User confirms 33 controlled frames at 480x480/16 FPS but reports flicker and no visible idle motion. Found preview resets canvas dimensions and clears it before each asynchronous PNG decode, potentially displaying blank frames. Predecode frame images before playback, cache by current frame array, paint synchronously once ready, preserve last displayed frame during loading, guard stale playback. Increase recommended breathing amplitude to 3 px (max 8), still approximate torso-only warp. Added static UI and synthetic motion regression; actual flicker source and visual quality require desktop retest. No manual CI dispatch.


## 2026-11-28 PHT — 62J-C3 guided AI animation

- User confirmed playback flicker fixed by #132; controlled deformation remains visually unsatisfactory. Reused MVManaAtelier Wan first/last graph with existing GGUF pair and runtime. Added explicit first/last conditioning selector and optional aligned end PNG; default same reference at both endpoints for loop guidance. Standard I2V, controlled idle, MP4 preview and alpha extraction retained. Graph regression added. Endpoint conditioning does not lock intermediate poses or expressions; motion templates and stronger control backend remain future work. Actual GPU acceptance pending. No manual CI dispatch.

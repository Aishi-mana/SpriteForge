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

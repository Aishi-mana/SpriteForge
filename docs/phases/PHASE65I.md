# Phase 65I — Unified Asset Library integration and desktop acceptance

## Integration fixes

Picker keeps errors visible after failed Modular, World, System or VFX imports; blocks closing during active import; checks workspace and direct editor session; confirms replacement references. Saved MP4 sets advanced extraction range. Non-loop playback retains last frame duration. WeakMap provenance preserves source across supported settings, directional changes, direct editor Apply, undo and library save; unrelated documents remain unlinked. This is not universal provenance across all generation/edit paths.

## Desktop acceptance (not yet executed)

Use a disposable test project and spare library capacity. Pull main after PR validation/merge. No new model downloads needed for CPU checks. Record OS, WebView, engine and Git revision. Keep a backup before testing.

| Check | Expected result |
|---|---|
| Save a generated PNG and a modular snapshot | Visible independent entries with full-resolution payloads |
| Edit collection/tags/favorite, restart app | Metadata persists; filter/search correct |
| Save a full-frame animation, view and scrub | Correct transparency, FPS, direction, final-frame hold |
| Save current or imported MP4, restart, play/seek/download | Original bytes preserved; WebView codec supported |
| Choose saved MP4 in Full-frame Studio | Preview loads and extraction duration is populated |
| Extract sprites, save animation, open history | Source video shown; no overwrite |
| Reuse image in Modular, World, System and VFX | Valid imports work, rejected imports keep picker open |
| Reuse animation in Scenes and paired actors | Select direction; original unchanged |
| Load animation, edit settings or apply direct edit, save | Revision link retained; undo works |
| Cancel picker during list loading; repeat use | Stale responses ignored, no app restart |
| Export asset/full backup and import in spare library | Copies retained, internal links remapped, no overwrite |
| Reject invalid ZIP and retry | Error displayed, no partial published assets |

Actual Windows desktop, GPU generation and native engine import results remain unverified. CPU regression is separate. No manual CI dispatch or packaging change.

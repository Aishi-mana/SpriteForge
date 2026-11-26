# Phase 61 — Final integration pass

- Project loading warns before clearing a session-only map and resets map state after successful fetch.
- Skeleton topology changes require confirmation before clearing stored clips. Back up the saved project first if needed.
- Scene changes and workspace exits cancel behavior playback and pending asynchronous starts, releasing preview frame references.
- Resource presets preserve architecture-specific local worker settings.
- CPU regression includes map reset, clip confirmation and behavior cancellation checks.

Remaining verification: real Windows desktop interaction, GPU generation on target hardware, and native Godot/Unity imports. Deferred features recorded in previous phase notes remain deferred. Phase 62 packaging is explicitly outside this pass.

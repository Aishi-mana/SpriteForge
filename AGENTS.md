# SpriteForge repository instructions

- Read `docs/IMPLEMENTATION_DIARY.md`, `HANDOFF.md` and the relevant phase notes before making changes.
- For every implementation or bug-fix PR, append a timestamped entry to `docs/IMPLEMENTATION_DIARY.md` in the same branch. Include scope, files, design decisions, actual verification, failures/corrections, limitations and PR/commit references. Append actual validation and merge outcomes when known; never invent timestamps or results.
- Keep historical entries intact. Update phase notes and current README/roadmap/handoff status at milestones. Treat CPU mocked tests, GPU inference, desktop interactions and native game-engine imports as separate verification categories.
- Use focused branches and PRs. Keep generated assets, local config, model weights and logs out of source changes. Phase 62 packaging remains on hold until explicitly requested.

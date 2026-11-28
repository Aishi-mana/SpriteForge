# SpriteForge repository instructions

## Mandatory user-first UX policy — read before every change

Usability is an acceptance requirement, not optional polish. Every contributor and AI agent must follow these rules across all studios, including when resuming in a new chat:

- Keep essential actions (create, preview, play, save, download, export, retry, cancel, undo) directly visible beside the result or workflow they affect. Never bury core actions in advanced settings or nested accordions.
- Use a simple default workflow, plain-language labels, helpful defaults, and progressive disclosure only for genuinely optional technical settings. Clearly distinguish saving an editable project from exporting usable assets.
- Show prerequisites, actionable errors, progress, and recovery options at the point of use; disable unavailable actions with an explanation. Do not silently fail or require an app restart for ordinary repeat operations.
- Keep layouts compact and responsive; avoid full-width timeline thumbnails, excessive scrolling, duplicate controls, and unexplained jargon. Preserve access to advanced capabilities without making them mandatory.
- Do not substitute a different technology or workflow for the user's requested output without disclosure and agreement (e.g. deformation is not full-frame AI animation).
- Before opening a PR, review the complete user journey from input through result, export, and repeat use. Add regression coverage for placement and behavior; record desktop visual verification separately from CPU checks. If not visually verified, say so.
- At each handoff, read this policy and the living diary, verify live PR/check status, and explicitly report what is implemented, validated, merged, and ready to pull. Merge validated approved work rather than stopping at a passing check; do not manually dispatch CI without approval.

- Read `docs/IMPLEMENTATION_DIARY.md`, `HANDOFF.md` and the relevant phase notes before making changes.
- For every implementation or bug-fix PR, append a timestamped entry to `docs/IMPLEMENTATION_DIARY.md` in the same branch. Include scope, files, design decisions, actual verification, failures/corrections, limitations and PR/commit references. Append actual validation and merge outcomes when known; never invent timestamps or results.
- Keep historical entries intact. Update phase notes and current README/roadmap/handoff status at milestones. Treat CPU mocked tests, GPU inference, desktop interactions and native game-engine imports as separate verification categories.
- Use focused branches and PRs. Keep generated assets, local config, model weights and logs out of source changes. Phase 62 packaging remains on hold until explicitly requested.

- User approved resuming CPU validation on public repositories. Automatic runs are public-only to conserve private Actions allowance; manual dispatch is retained. Explicitly distinguish untested changes from validated ones.

# Phase 62B — Browser workflow smoke coverage

Run `python -m pip install playwright`, `python -m playwright install chromium`, then `python tests/browser_smoke.py`. Real Chromium against the actual UI with deterministic mocked API responses. Tests queue history to rig/full-frame, backend/decode error visibility and 20 navigation buttons. This optional suite is not added to automatic CI to conserve minutes. Browser execution, real engine and desktop acceptance remain pending. Hardened stale rig overlay responses and source decode failures.

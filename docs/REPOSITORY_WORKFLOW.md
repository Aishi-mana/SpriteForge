# Repository workflow and maintenance

**Project:** [Aishi-mana/SpriteForge](https://github.com/Aishi-mana/SpriteForge)  
**Default branch:** `main`. This repository supersedes the older phase-by-phase ZIP handoffs.

## Making a change

1. Fetch/pull the latest `main` and make a focused branch (for example `docs/update-install-guide` or `fix/terrain-export`).
2. Change source files and add/adjust tests and documentation. The historical `docs/phases/PHASE*.md` files explain earlier deliveries; don't copy them back to the root.
3. Run `python tests/run_all.py` from the root. Install NumPy/Pillow/SciPy for the offline tests; install **Node.js** to exercise the embedded UI JS tests. Without Node.js, JS tests are skipped, not proved passing.
4. If changing model loading, renderer behaviour or engine exports, also perform applicable checks from [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) on the Windows GPU and/or in Godot 4 / Tiled. Record what remains untested.
5. Review `git status --short` and `git diff --stat`; commit only intended files; open a pull request for review before merging to `main`. Mention test results and any Tauri rebuild requirement.

## Tracked runtime files & cleanup

**Important finding (initial repo snapshot):** the repository tracks `config.json`, `engine.log`, `llm.log`, `diagnostics.txt` and entries under `history/`. The current `.gitignore` excludes build/cache directories but does **not** exclude these runtime files. These files can contain local paths, prompts, generation settings, error output or images. Treat them as **user data**; do not share raw contents casually.

Recommended **separate, reviewed** housekeeping task:

1. Back up any runtime files and confirm they are not supposed to be version-controlled. Keep `config.example.json` as the safe template.
2. Add appropriate ignore patterns for local config, logs, diagnostics and generated `projects/`, `exports/`, `palettes/`, `history/` data.
3. Remove *only the tracked copies* from the Git index using `git rm --cached` on the reviewed paths; this leaves the local files in place. Verify the staged diff carefully to avoid data loss.
4. Open a distinct PR for this cleanup. Existing Git history still contains prior versions: if sensitive material was committed, decide separately whether history rewriting or credential rotation is warranted. Do not force-push or rewrite history as part of routine documentation updates.

The root `PHASE*.md` notes also duplicate `docs/phases/` for earlier phases. After confirming no external links require them, choose whether to preserve aliases or remove duplicates in another maintenance PR.

## Build and runtime boundaries

- `spriteforge.bat`: Windows setup/launcher; builds Tauri when Rust tooling is available. `spriteforge.bat rebuild` refreshes the shell after Rust changes.
- `run.bat`: starts the browser-mode local engine; open `http://127.0.0.1:8765` if it does not open automatically.
- `config.example.json`: intended configuration template; **do not overwrite a user's existing `config.json`**.
- Model files are external, not vendored. Initial online downloads may be needed for optional IP-Adapter/ControlNet, although the application can subsequently run locally.
- In this snapshot there is no `.github/workflows/` CI configuration. Do not equate a PR existing with automated tests having run.

## Documentation map

- [README](../README.md): overview, installation, troubleshooting and current status.
- [User guide](USER_GUIDE.md): step-by-step feature workflows through Phase 22.
- [Architecture](ARCHITECTURE.md): modules, persistence, API routes and conventions.
- [Development](DEVELOPMENT.md): source-level changes and tests.
- [Testing checklist](TESTING_CHECKLIST.md): hardware and import acceptance.
- [Roadmap](ROADMAP.md): pending verification, possible next features and known limits.
- [Handoff](../HANDOFF.md): concise maintainer overview and feature confidence.
- [Phase notes](phases/): historical details; [Changelog](../CHANGELOG.md): chronological summaries.

# Phase 19 - generation queue + history
Unzip over your spriteforge folder. New: engine/jobs.py, tests/test_queue.py, tests/js/queue_test.js. Changed: engine/main.py, engine/generate.py, ui/index.html, tests/test_ui.py, docs.
No packages, no rebuild (Python + UI only): restart the engine / relaunch spriteforge.bat.

## What you get
- **Generate** (and **Generate poses** on Reference pose) now runs through a queue. Same button, same result display, but the job is also stored in the history.
- **＋ Add to queue** (under the Generate button, tabs Generate / Reference pose): puts the job in line and returns immediately, so you can change the prompt, queue another, or switch tabs.
  Jobs run one at a time, oldest first (one GPU). A strip under the button shows "Queue: 1 running · 2 waiting"; click it to open the **Queue** tab.
- **Queue tab**: waiting/running jobs with progress ("image 2 of 3"), Cancel (waiting) / Discard (running: the current image finishes, then its results are thrown away),
  **Pause / Resume** (a running job finishes first), **Cancel waiting**.
- **History** (same tab): every finished job as a card (thumbnail, seed, prompt, time). Search prompt/model/note, filter by kind, ★ only. Click a card:
  - **Use these settings**: puts every sidebar control back (and, for Reference jobs, the reference image, the skeleton pose and Use skeleton) and opens the right tab.
  - **Show in Generate / Reference pose**: puts the results back in the normal results area (Edit, Use as reference, Animate, Save, PNG all work on them).
  - **Re-run (same seed)**: queues the same settings again (same pictures). **Fork (new seed)**: same settings, random seed (a new variation).
  - **★ Favourite**, a searchable **note**, **Delete** (click twice). Settings used, and the input images (reference, skeleton).
  - Tick **compare** on 2-4 cards and press **Compare ticked**: results side by side and a list of exactly which settings differ.
- History is global (not per project), saved in `history/<job>/` (job.json + PNGs), survives restarts, keeps the newest 300 jobs (favourites are never deleted). **Clear history** keeps favourites.
- Jobs that were waiting or running when the app closed come back as "interrupted" (use Re-run).
- Errors (for example out of GPU memory) are stored with the job; the queue carries on with the next one.

## Limits
- A running image cannot be interrupted mid-way (the pipeline has no stop hook): Discard waits for the current image. With the skeleton on 8 GB that can be 1-3 minutes.
- Only Generate and Reference pose are queued. Pixelize is instant (runs directly); Portrait, Template, Directions and AI cleanup still run directly, but they now share the GPU lock with the queue (they wait their turn instead of colliding).
- The sampler is a global setting applied when a job starts; starting a Portrait/Template action while a queued job starts in the same second could use the other's sampler (cosmetic).

## Technical
- `engine/jobs.py`: `Manager` (worker thread, atomic job.json, in-memory index, pruning, recovery) with an injected executor, so it is tested with a fake one.
- `main.py`: `_do_generate` / `_do_reference` (the old endpoints now call them, behaviour unchanged), `_exec_job`, `_coerce_ref` (job params are plain JSON), 11 new routes.
- `generate.PROGRESS`: optional callback(done, total) after each image (no signature changes).
- Tests: `tests/test_queue.py` (36 checks: order, pause, cancel, errors, restart, pruning, endpoints with a fake SDXL) and `tests/js/queue_test.js` (21 checks on the real UI code with a fake DOM/API). 246 checks in total.
- Not verified here (no GPU / browser): the real queue with SDXL, how the new tab looks, progress during a real generation.

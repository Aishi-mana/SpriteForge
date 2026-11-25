# Phase 13 - diagnostics
Unzip over your spriteforge folder. New: engine/diag.py. Changed: engine/generate.py, engine/llm.py, engine/portrait.py, engine/main.py, ui/index.html. No packages, no rebuild.

Press "🩺 Diagnostics" (next to the title). "Run checks" gives a report with OK / WARN / FAIL / INFO rows and a fix line for every problem:
- System: Python and packages (missing ones listed), RAM, disk space, app folder writable, config.json.
- GPU: PyTorch build, CUDA device, VRAM free, whether this PyTorch build contains your GPU's architecture (RTX 50-series needs cu128), a real fp16 math test.
- Models: every checkpoint / LoRA header is read: broken or truncated downloads are caught, and files are classified (SDXL / SD1.5 / Flux-or-other).
- Downloads: IP-Adapter, OpenPose ControlNet, internet reachability.
- Assistant: llama-server version (CUDA / Vulkan), model, size vs. settings.
- Self-tests (CPU, ~1 s): pixelize, rig animation, export, projects, portrait pipeline - proves the app's own code works on your machine.
- Recent API errors and the last lines of engine.log / llm.log.
Buttons: "GPU test" loads SDXL and renders 4 steps (reports load time, speed, peak VRAM); "Assistant test" loads the model and asks for one word (speed in tokens/s);
"Copy report" puts the whole report on the clipboard (also saved as diagnostics.txt).
Also new: checkpoints that cannot work (Flux, SD1.5, HiDream, broken files) and LoRAs for other model families (Qwen, Wan, Flux) are now tagged in the dropdowns, and Generate / Portrait / cleanup refuse them with a clear message instead of a cryptic error. The first SDXL checkpoint is preselected if sd_xl_base is missing.

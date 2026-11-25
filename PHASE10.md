# Phase 10 - local assistant chat (GGUF via llama.cpp)
Unzip over your spriteforge folder. New: engine/llm.py. Changed: engine/main.py, ui/index.html. No packages, no rebuild.

Needs llama.cpp's llama-server (llama-server.exe) and a chat .gguf somewhere under C:/AI (the folder is scanned 4 levels deep).
1. Press "✦ Assistant" (bottom-right), open the gear, press Scan, pick a model, Save.
2. First message starts llama-server on port 8766 (CPU by default, so SDXL keeps all the VRAM); it unloads itself after 10 idle minutes.
3. The assistant answers with prompts and settings; each proposed change is an "Apply" button. It never generates or exports by itself.
Fields it can set: prompt, negative, character, pose, anim, reference / skeleton / cleanup strength.
It sees your current tab, prompt, character, pose text, animation and checkpoint/LoRA names.
Settings (server path, model, GPU layers, context, idle minutes, scan folder) are stored in config.json. Log: llm.log.
Safety: only a file named llama-server and a .gguf model can be configured.
Suggested models: any 3-4B instruct model at Q4 (e.g. Qwen2.5-3B-Instruct, Llama-3.2-3B-Instruct, Phi-3.5-mini).

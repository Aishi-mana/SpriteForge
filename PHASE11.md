# Phase 11 - portrait maker + expressions
Unzip over your spriteforge folder. New: engine/portrait.py. Changed: engine/generate.py, engine/main.py, engine/projects.py, engine/llm.py, ui/index.html. No packages, no rebuild.

New "Portrait" tab:
1. Base portrait: describe the face / hair / eyes / collar. "Start from" = Text only, or your Reference sprite via IP-Adapter
   (set it in the Reference tab first). Pick size (64-256), colours and background, press Generate base portrait, then "Use as base".
2. Face area: pick a preset (whole face / eyes + brows / mouth) or drag on the portrait to draw your own area. Only this area is repainted.
3. Tick expressions (happy, sad, angry, surprised, embarrassed, smug, sleepy, pain, scared, determined, laughing, serious) and/or type your own,
   press Generate expressions. They appear one by one as they finish (SDXL inpaint, same seed for all, with your pixel LoRA).
   - Everything outside the face area stays pixel-identical to the base.
   - Results snap to the base palette; "Extra colors allowed" (default 4) lets blush, tears, sweat drops keep their own colours.
   - "Change strength" (default 0.82): higher = bigger expression change, lower = closer to the base face.
4. "Base" button on any expression continues from it; "x" removes it; PNG downloads one.
5. Export portrait set: individual PNGs + one sheet + Aseprite-style JSON + Godot 4 .tres/.tscn (one animation per expression, e.g. play("happy"))
   + Unity json + importer script, into <app>/exports/<name>_portraits_pack/.
The base portrait, face area and all expressions are saved in the project. The assistant can also fill the portrait prompt and a custom expression.

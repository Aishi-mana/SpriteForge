# Phase 15.1 - HOTFIX: "checkpoint not found ... not SDXL" / cannot generate
Cause (introduced in phase 13): the model tagger changed the option TEXT, and because the options had no separate value, the tag became part of the file name.
Also the classifier treated 'transformer_blocks' (present in real SDXL files) as a non-SDXL sign, so sd_xl_base_1.0 and the pixel-art LoRA were wrongly flagged.
Fixed: options now carry the exact file name as their value; classification checks real SDXL markers first; only positively identified Flux/DiT, SD 1.5, Qwen/Wan LoRAs and broken files are blocked; anything unrecognised is labelled "? not recognised" but still allowed.
Unzip over your spriteforge folder (ui/index.html, engine/diag.py), then press Ctrl+R / relaunch.

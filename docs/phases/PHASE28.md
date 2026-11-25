# Phase 28 — character model compatibility

Checkpoint selector shows architecture and readiness. LoRA options are labelled Family match, Unverified or Incompatible for the selected checkpoint. Incompatible choices are disabled and cleared when switching model; backend also rejects known mismatches. Header metadata and tensor signatures are heuristics, not proof of shape/training compatibility.

Text-to-image routes: SDXL and SD 1.5 single-file checkpoints; complete local Diffusers pipeline folders for SDXL, SD 1.5, Lumina 2 (NetaYume), FLUX.1, SD3/3.5 and Qwen-Image. New architectures are experimental until GPU-tested. Flow architectures keep native scheduler. Sequential CPU offload reduces VRAM, but large models may still exceed RAM/VRAM. Existing reference, ControlNet and inpaint workflows require SDXL.

NetaYume: put a complete Diffusers version (with model_index.json, transformer, tokenizer, scheduler, VAE and text encoder) under models/checkpoints/NetaYume. A recognized Lumina single-file checkpoint can also be attempted with a complete local Lumina 2 base pipeline in checkpoints/Lumina2-base; this loads the transformer using Diffusers single-file conversion and uses the base's other components. Comfy all-in-one files may not convert; use a compatible Diffusers folder instead. No automatic model download. FLUX/Qwen/SD3 raw single files are not supported by this implementation. Use the local folder version.

Update dependencies (diffusers>=0.36; newer may be necessary for particular model versions) before relaunch. Start with one variation, 512–768 pixels, then raise resolution if memory permits. No verified GPU generation yet. No changes to earlier phases. Tile and terrain follow-ups deferred.

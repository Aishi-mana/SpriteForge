# Phase 23 — multi-style character generation (initial implementation)

Generate and Reference pose expose Retro pixel art, Modern anime, RPG chibi, Super chibi, Soft chibi, Premium chibi, and Custom illustration. Existing jobs without art_style retain pixel behavior. HD output keeps the full palette, uses Lanczos resizing and border-connected background keying with a soft edge. It is not a semantic background remover; inspect the edges and use a contrasting flat background. The canvas is not cropped, preserving alignment.

Choose an SDXL-compatible anime checkpoint and optional matching LoRA yourself; switching to HD clears a selected pixel-art LoRA by filename. No new model dependencies. HD output is 256–1024 px; Generate inference can be reduced to 640 or 768 to save memory. Reference pose keeps its existing generation-size control and always keys the background. Pixel-only palette/cleanup settings do not apply in HD.

Queue requests carry style and output size, and sidebar fields are saved with projects. Old projects default to pixel art. HD results can be downloaded, saved and used as references. Pixel editor, tileset, upscaled PNG and rig buttons are disabled on HD result cards; portraits, templates, directions and tile generation retain the existing pixel workflow. No explicit sexual-generation controls are added.

Validation: regression tests added for prompt defaults, HD gradients, alpha, output size and JS queue parameters. Run python tests/run_all.py with Node.js installed. Real GPU, Windows UI and output quality must be checked on the target machine before merging.

Phase 24 follow-up enables HD rig animation; see [Phase 24](PHASE24.md).

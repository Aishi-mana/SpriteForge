# Phase 61M-A — Fixed-canvas modular asset foundation

Opt-in API fixed_canvas (default false for existing clients; enabled by default in Modular UI) uses visible body reference, category-specific prompt and existing approximate region fit. Embed fitted RGBA into full recipe canvas at its original placement, then return layer offset 0,0 and scale 100. Body and recipe unchanged until explicit acceptance. Asset PNG and combined preview remain separate. Registration is exact relative to the fitted region, not anatomical fit: model output still uses existing square reference preparation, crop and approximate fit. No semantic extraction or guarantee of outfit alignment. Existing legacy fit available. Tests cover dimensions, origin, RGBA, preview equivalence and invalid placement; CI/GPU/desktop acceptance pending.

## Planned sequence

- A: fixed canvas and origin contract, isolated output foundation.
- B: pose-aware body landmarks and category placement masks.
- C: Qwen body-conditioned edit and isolated layer extraction.
- D: NetaYume and SDXL backend adapters, fallback and capability checks.
- E: hair front/back, clothing, footwear and accessories with occlusion and alignment review.
- F: candidate cleanup, manual alignment, modular approval and export integration.
- G: regression, resource safeguards and real-model acceptance checklist.

Phase 62 packaging remains on hold.

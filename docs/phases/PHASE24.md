# Phase 24 — HD sprite animation

Initial HD rigid-bone renderer for sources larger than 160 px (up to 1024 px). Existing pixel sources retain nearest-neighbour/palette behavior. HD layers keep fractional alpha and use bicubic affine transforms without 4x supersampling. Overlap scales with source size. Existing procedural clips and painted secondary chains remain available. Preview and rig canvas fit the viewport. HD cards can open Animate. Godot and Unity animation pack exports select linear filtering for HD sources. GIF previews avoid 4x scaling for large frames; PNG preserves alpha.

Limits: 48 million frame pixels per HD clip/pack; atlas 64 million pixels and 32768 px per axis. Large death clips may need fewer frames or a smaller source. Use grid export when row exceeds limits. GIF cannot preserve partial alpha. AI cleanup and pixel editor are not HD-enabled. This is rigid cutout animation, not mesh skinning or AI in-between generation; manually adjust joints and inspect seams. Start/end references and soft deformation remain follow-ons. Automatic resolution threshold may classify unusually large pixel art as HD.

Tests added for fractional alpha, full-colour output, pixel compatibility, oversized clips and export filtering. Full Python/Node suite and real browser/GPU/engine import validation pending.

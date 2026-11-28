# Phase 63F — Independent sprite and game interaction exports

Paired Preview > Export independent game assets (ZIP). Choose PNG or lossless WebP. Each character has a separate untrimmed, unmirrored atlas with source frame rectangles, pivot, FPS and sampling. Sheets are paged to 4096px maximum dimensions. interaction.json records shared FPS/canvas, per-frame source indices, visibility, positions and depth, actor scale/mirroring/opacity, contact offsets and optional enter/loop/exit ranges. Indices are zero-based and stage ends exclusive. Source images remain independent. README explains runtime integration. Existing scene validation and budgets apply. This is a generic engine-neutral package, not a ready-made Godot/Unity controller. No combined preview GIF is included yet.

CPU regression cases cover separate artwork, timing, overrides, stage validation and WebP. Tests and desktop validation not executed at authoring.

# Phase 63D — Per-frame positioning, depth and occlusion

Paired Preview includes an exact scene-frame editor for actor X/Y and depth. Select a timeline cell or frame number, choose A/B, apply or remove an override, or align B to A's fixed contact anchor on that frame. Timeline dots mark overrides. Re-render after edits; the selected frame is retained. Higher depth draws in front, with existing alpha compositing and stable tie order. Adjacent frames retain the base transform unless separately overridden. Pair JSON preserves overrides in validated scene actor data; older bundles remain supported. Replacing an actor clears its overrides. Out-of-range overrides are omitted from pair saves and renders. No limb-level masks, automatic occlusion reconstruction or interpolated keys in this phase.

Added CPU regression cases for exact-frame placement, depth switching, scrub parity, validation and project roundtrip. Tests and desktop validation have not been executed at authoring.

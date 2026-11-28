# Wan 2.2 — ending pose reference

In Full-frame Animation Studio select **Wan AI — native quality (slower)**, **Wan AI — fast preview**, or **Standard AI animation**. The **Ending pose (Wan)** control is directly visible when the Wan 2.2 A14B model is selected, including in advanced mode. No new models are required.

| Ending pose | Behavior |
| --- | --- |
| Automatic | Idle / minimal idle / alert / floating / weapon-ready presets reuse the starting reference; other presets use start-only generation. |
| Same as start | Always supply the same start and end reference via Wan first/last conditioning, including for combat recovery loops. |
| Different ending pose | Choose a final PNG (up to 8 MB). Both references condition generation; return-to-start prompt guidance is disabled. |
| No ending reference | Original start-only Wan image-to-video generation. |

The ending preview shows the starting image in same-reference mode, or the imported target in custom mode. Custom mode requires an image before generation. Switching quality or refreshing models does not reset the choice or file. The selection is session-only and clears when loading another animation document. The start image and target should use consistent framing and character scale; the existing reference preparation fits each to the requested canvas.

## Desktop acceptance

1. Select minimal idle and Automatic; verify the ending preview matches the start. Generate and compare the first and last frames, and review unwanted middle-frame motion.
2. Choose a combat preset such as slash, and select Different ending pose. Supply an aligned recovery or strike pose. Verify both endpoints guide the generated clip; use the same image as the next clip's starting artwork for a manual combo chain. The engine does not automatically splice clips.
3. Switch quality and refresh models; confirm the custom image remains selected. Clear the ending image and verify generation is disabled until a new image is chosen or another ending mode selected.
4. Choose No ending reference and verify ordinary start-only generation remains available. Test repeated generation, extraction and export.

First/last conditioning is guidance, not a guaranteed exact pixel lock or seamless transition. Existing motion prompt constraints and model capabilities still affect results. No new GPU acceptance claim is made until tested on the desktop. Wan Fun Control 5B and AnimateDiff are unaffected.

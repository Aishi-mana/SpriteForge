# Phase 3 - skeleton pose editor + ControlNet + fixed canvas
Unzip over your spriteforge folder (no Rust changes, no rebuild needed). Keep your config.json.

Reference pose tab -> "Use skeleton pose" (on by default):
- Pick a preset, drag joints (Shift+drag moves everything), Mirror flips left/right.
- Use the "Stand" preset to line the skeleton up over your reference (shown faintly), then keep the scale for all poses.
- Output is a fixed square canvas (default 128 px) at one constant scale, so frames line up.
- Local ControlNet: put an SDXL OpenPose file with "openpose" and "xl" in its name in <models>/controlnet.
  Otherwise xinsir/controlnet-openpose-sdxl-1.0 downloads once from Hugging Face.
- "Remove ground shadow" strips the grey blob under feet (untick it if it eats real boots).

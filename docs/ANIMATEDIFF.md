# AnimateDiff — experimental short AI animation (62K-A)

This backend uses SpriteForge's existing Diffusers environment, not a separate ComfyUI installation or manual node graph. It generates new frames using AnimateDiff's video-to-video denoiser, conditioned on repeated copies of the current reference image. No deformation is applied. Reference identity, subtle motion, lighting consistency and loop seamlessness are not guaranteed.

## Model setup

Select **AnimateDiff — short AI animation** in Full-frame Animation Studio. Click **Create model folders** to create the two directories inside the configured models directory. The screen displays their exact paths, links to example model repositories, and missing components for each detected folder. Copy or download the complete local Diffusers-format folders into those paths, then click **Refresh models**. Generation remains unavailable until a pair passes the file checklist.

Example baseline repositories: [SD1.5 image model](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/tree/main) and [AnimateDiff v1.5-2 motion adapter](https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2/tree/main). These are compatibility starting points, not a recommendation for a particular artistic style. Preserve the subdirectories and filenames. The initial loader expects standard (unsharded, non-variant) safetensors files, not just the standalone checkpoint at the repository root.

Expected layout:

    animatediff/
      base/
        my-sd15-model/
          model_index.json
          unet/
          vae/
          text_encoder/
          tokenizer/
          scheduler/
      motion/
        my-motion-adapter/
          config.json
          diffusion_pytorch_model.safetensors

Use a compatible SD1.5 base (not SDXL, Qwen or Wan) and an SD1.5 Diffusers MotionAdapter. The base needs the complete pipeline components and safetensors weights; the adapter needs its matching config and weights. Raw ComfyUI checkpoint files and original AnimateDiff .ckpt files are not accepted in this initial implementation. No automatic downloads or conversion are performed. See the [Diffusers AnimateDiff documentation](https://huggingface.co/docs/diffusers/en/api/pipelines/animatediff). Check model licenses for your project's intended use.

## Desktop test

1. Restart SpriteForge after updating. Open Full-frame Animation Studio.
2. Choose artwork and a motion preset such as Idle — minimal breathing.
3. Select AnimateDiff — short AI animation and refresh models. Select a detected base/adapter pair.
4. Start with 512 x 512, 16 frames, 8 FPS, 12 nominal sampling steps. The video-to-video strength is 0.5, so the actual denoising step count can be lower.
5. Generate and compare the raw MP4. Use the existing extraction, timeline and sprite export controls.
6. Generate a second time in the same session. Record speed, visual motion, identity drift and memory errors.

Detection checks metadata and nonempty required component files, not their tensor contents, licenses, or GPU runtime compatibility. The setup screen does not automatically download, convert, or relocate weights. CPU offload and chunking reduce memory pressure but do not guarantee operation on an 8 GB GPU. Desktop/GPU acceptance is pending. The initial reference conditioning is not a hard first/last-frame or facial lock.

## Character preservation and motion (62K-C)

The visible movement profile changes video-to-video denoising strength and prompt guidance: Preserve artwork (0.35 / CFG 4), Balanced (0.50 / CFG 5), More movement (0.65 / CFG 6). These are experimental starting points; lower strength can reduce motion, higher strength can change character details. No frame blending, deformation or hard facial lock is performed. With identity preservation enabled, lighting, palette, costume and shading consistency are included in the prompt. A nonempty typed motion description replaces the preset-specific motion text and restrictions (including the default idle blink restriction); general framing, identity, intensity and loop guidance remain active. Clear the text to use the preset alone. For example, type “Blink once, keep the mouth still” or “Gentle hair sway, steady head and feet.” Use the visible Reuse last successful seed option to compare settings on the same noise seed. The last successful seed is session-only; reproducibility is not guaranteed across different runtime versions and model configurations. CPU regression tests cover prompt construction and parameter selection, not animation quality.

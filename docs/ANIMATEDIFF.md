# AnimateDiff — experimental short AI animation (62K-A)

This backend uses SpriteForge's existing Diffusers environment, not a separate ComfyUI installation or manual node graph. It generates new frames using AnimateDiff's video-to-video denoiser, conditioned on repeated copies of the current reference image. No deformation is applied. Reference identity, subtle motion, lighting consistency and loop seamlessness are not guaranteed.

## Model setup

Select **AnimateDiff — short AI animation** in Full-frame Animation Studio. Click **Create model folders** to create the two directories inside the configured models directory. The screen displays their exact paths, links to example model repositories, and missing components for each detected folder. Copy or download the complete local Diffusers-format folders into those paths, then click **Refresh models**. Generation remains unavailable until a pair passes the file checklist.

Example baseline repositories: [SD1.5 image model](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/tree/main) and [AnimateDiff v1.5-2 motion adapter](https://huggingface.co/guoyww/animatediff-motion-adapter-v1-5-2/tree/main). These are compatibility starting points, not a recommendation for a particular artistic style. Preserve the subdirectories and filenames. The loader prefers standard (unsharded, non-variant) Safetensors files. The exact published SD1.5 legacy UNet/VAE .bin component files can also be converted on the first generation; standalone checkpoints are not supported.

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

Use a compatible SD1.5 base (not SDXL, Qwen or Wan) and an SD1.5 Diffusers MotionAdapter. The base needs the complete pipeline components and safetensors weights; the adapter needs its matching config and weights. Raw ComfyUI checkpoint files and original AnimateDiff .ckpt files are not accepted in this initial implementation. No automatic downloads are performed. The narrow legacy conversion exception is described below. See the [Diffusers AnimateDiff documentation](https://huggingface.co/docs/diffusers/en/api/pipelines/animatediff). Check model licenses for your project's intended use.

## Desktop test

1. Restart SpriteForge after updating. Open Full-frame Animation Studio.
2. Choose artwork and a motion preset such as Idle — minimal breathing.
3. Select AnimateDiff — short AI animation and refresh models. Select a detected base/adapter pair.
4. Start with 512 x 512, 16 frames, 8 FPS, 12 nominal sampling steps. The video-to-video strength is 0.5, so the actual denoising step count can be lower.
5. Generate and compare the raw MP4. Use the existing extraction, timeline and sprite export controls.
6. Generate a second time in the same session. Record speed, visual motion, identity drift and memory errors.

Detection checks metadata and nonempty required component files, not their tensor contents, licenses, or GPU runtime compatibility. The setup screen does not download or relocate weights; first generation can perform the verified legacy conversion below. CPU offload and chunking reduce memory pressure but do not guarantee operation on an 8 GB GPU. Desktop/GPU acceptance is pending. The initial reference conditioning is not a hard first/last-frame or facial lock.

## Character preservation and motion (62K-C)

The visible movement profile changes video-to-video denoising strength and prompt guidance: Preserve artwork (0.35 / CFG 4), Balanced (0.50 / CFG 5), More movement (0.65 / CFG 6). These are experimental starting points; lower strength can reduce motion, higher strength can change character details. No frame blending, deformation or hard facial lock is performed. With identity preservation enabled, lighting, palette, costume and shading consistency are included in the prompt. A nonempty typed motion description replaces the preset-specific motion text and restrictions (including the default idle blink restriction); general framing, identity, intensity and loop guidance remain active. Clear the text to use the preset alone. For example, type “Blink once, keep the mouth still” or “Gentle hair sway, steady head and feet.” Use the visible Reuse last successful seed option to compare settings on the same noise seed. The last successful seed is session-only; reproducibility is not guaranteed across different runtime versions and model configurations. CPU regression tests cover prompt construction and parameter selection, not animation quality.


## Speed and quality comparison (62K-D)

Use the visible sampling speed selector (8 quick, 12 standard, 20 quality-comparison nominal steps). Keep the same model, reference, profile, resolution, frame count, FPS, prompt, extraction options and reused seed. Generate and extract the first candidate, click Compare speed and quality beside the video, enter visual rating/notes if desired and capture. Allow timeline replacement for the next generation, select the next speed preset, and repeat. Play both captured sequences together. Four candidates fit in the existing session comparison; export JSON v2 with measurements, settings and notes (no artwork).

Generation timing is client request wall time through MP4 receipt, including model load, inference, encoding and transfer; extraction timing is separate. Neither is GPU-only profiling. Automatic provenance is bound to the exact extracted document and source reference; edited/imported frames require manual metadata. Unknown random seeds are not represented as fixed seeds. Matching output and pixel metrics do not prove identity or artistic quality; visually review motion, facial detail, lighting, silhouette, seam and alpha quality. No actual desktop speed results are claimed until measured on hardware.


## 62K desktop acceptance checklist (RTX 5070 Laptop, 8 GB VRAM)

After the integrated CPU check passes and the PR is merged, pull main and restart SpriteForge. Close other GPU-heavy applications. In Full-frame Animation Studio, select AnimateDiff, create model folders if needed, install the complete SD1.5 image and MotionAdapter directories and refresh. Confirm both are detected before attempting generation.

- Smoke test: one transparent reference, minimal idle preset, empty typed prompt, Balanced profile, 512 x 512, 16 frames, 8 FPS, Quick preview (8 steps). If VRAM runs out, retry at 384 x 384 and 8 frames using advanced generation settings, recording the error and changed settings.
- Repeat test: retain reference and seed, allow replacing the timeline, generate again without restarting. Confirm playable MP4, extracted frames, timeline playback and PNG/WebP export.
- Motion intent: type “Blink once, keep the mouth still.” Check whether the movement actually appears and whether lighting, face, costume and framing stay stable.
- Benchmark: capture Quick, Standard and Quality candidates with the same settings and seed; compare actual request/extraction durations and visual quality. Export the comparison JSON if useful.

Acceptance requires real desktop generation and repeat use, not just model detection or CPU CI. Record success/failure, elapsed seconds, visual defects and any exact error. No fixed performance target or successful GPU result is assumed.


## 62K hotfix — existing SD1.5 .bin component weights

If the UNet and VAE contain diffusion_pytorch_model.bin instead of diffusion_pytorch_model.safetensors, do not rename or redownload them. Refresh models after updating SpriteForge. The pair can be selected; a visible note explains the one-time conversion. On generation, SpriteForge verifies each legacy file against the SHA-256 published by the example SD1.5 repository ([UNet](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/main/unet/diffusion_pytorch_model.bin), [VAE](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/main/vae/diffusion_pytorch_model.bin)). Only these exact known files are accepted, using PyTorch 2.6+ restricted weights-only CPU loading, never unrestricted pickle. The new standard-name Safetensors file is published beside the original without overwriting existing files. Allow approximately 4 GB free disk space for both conversions and sufficient system RAM. Conversion uses the local filesystem's hard-link support (NTFS supported). Subsequent runs reuse the converted file. Other .bin checkpoints, variants or corrupted files are not supported by this hotfix. Safetensors remain preferred; model detection does not guarantee successful conversion or inference. Actual full-weight conversion on Windows remains unverified.


## Desktop runtime and transparency hotfix

If both models are detected but generation reports that AnimateDiffVideoToVideoPipeline has no attribute enable_vae_slicing, update SpriteForge. The memory configuration now uses VAE component-level enable_slicing when present, with the older pipeline method as a fallback. CPU offload and explicit video decode chunking remain enabled. BiRefNet AI is now the initial transparency selection in Full-frame Animation Studio; conservative color key and keep background remain selectable. BiRefNet requires its existing local model and runtime; if extraction fails, the video preview is retained and another transparency method can be selected for retry. No model downloads are required by this code fix. Desktop inference remains pending.

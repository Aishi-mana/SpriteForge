# Phase 61S-D — Video-to-sprite extraction

Import video or use current generated MP4. Select sample range in milliseconds, FPS, background key, tolerance, edge softness and optional shared trim. Requires imageio and imageio-ffmpeg. Shared union crop preserves relative frame motion and assigns a bottom-center pivot; no automatic anatomical alignment. Timeline replacement is validated and undoable. Chroma key may remove matching subject colors; semantic segmentation and despill deferred. Synthetic tests cover alpha and shared crop; actual decoding and desktop acceptance pending.

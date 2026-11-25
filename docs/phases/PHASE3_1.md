# Phase 3.1 - fix OOM in skeleton mode
Skeleton mode now uses sequential CPU offload (UNet + ControlNet don't fit together in 8 GB).
New "Generation size" option (default 768). Failed runs reset the pipeline so retries start clean.

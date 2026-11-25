@echo off
cd /d %~dp0
if not exist .venv (
  python -m venv .venv
  call .venv\Scripts\activate
  python -m pip install -q --upgrade pip
  rem RTX 50-series (Blackwell) needs PyTorch built for CUDA 12.8+
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate
)
python -m engine.main
pause

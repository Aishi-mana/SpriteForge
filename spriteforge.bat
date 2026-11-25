@echo off
setlocal
cd /d %~dp0
title SpriteForge

rem --- 1. Python env (first run only) ---
if not exist .venv\Scripts\python.exe (
  echo Setting up Python environment, this takes a while the first time...
  python -m venv .venv || (echo Python not found. Install Python 3.10-3.12 and re-run. & pause & exit /b 1)
  call .venv\Scripts\activate
  python -m pip install -q --upgrade pip
  rem RTX 50-series (Blackwell) needs PyTorch built for CUDA 12.8+
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
  pip install -r requirements.txt
)

rem --- 2. Rust toolchain? If missing, fall back to browser mode ---
where cargo >nul 2>nul
if errorlevel 1 (
  echo.
  echo Rust not found - opening in your browser instead.
  echo For the desktop window install: Rust ^(rustup.rs^), VS C++ Build Tools, and WebView2 ^(already in Win 11^).
  echo.
  start "" http://127.0.0.1:8765
  call .venv\Scripts\activate
  python -m engine.main
  pause
  exit /b
)

rem --- 3. Build the desktop shell once (or when you pass "rebuild") ---
if /i "%1"=="rebuild" if exist src-tauri\target\release\spriteforge.exe del src-tauri\target\release\spriteforge.exe
if not exist src-tauri\target\release\spriteforge.exe (
  cargo tauri --version >nul 2>nul || (
    echo Installing Tauri CLI, one time, takes several minutes...
    cargo install tauri-cli --version "^2" --locked
  )
  pushd src-tauri
  cargo tauri build --no-bundle
  popd
)
if not exist src-tauri\target\release\spriteforge.exe (
  echo Build failed - see messages above.
  pause
  exit /b 1
)

rem --- 4. Launch (the app starts and stops the engine itself; log: engine.log) ---
start "" src-tauri\target\release\spriteforge.exe
endlocal

@echo off
cd /d "%~dp0"
set PYTHONUTF8=1
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
if not exist ".venv\Scripts\python.exe" (
  echo SpriteForge virtual environment missing. Run spriteforge.bat first.
  exit /b 1
)
".venv\Scripts\python.exe" -m compileall -q engine tests
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" tests\run_all.py
exit /b %errorlevel%

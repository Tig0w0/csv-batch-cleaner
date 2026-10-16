@echo off
cd /d "%~dp0"
python gui.py
if errorlevel 1 (
  echo Python 3.10+ is required. Open README.md for instructions.
  pause
)

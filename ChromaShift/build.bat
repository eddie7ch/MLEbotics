@echo off
echo ChromaShift — Building standalone executable...
uv run pyinstaller ^
  --onefile ^
  --windowed ^
  --name ChromaShift ^
  --add-data "*.py;." ^
  main.py
echo.
echo Build complete! Executable is in dist\ChromaShift.exe
pause

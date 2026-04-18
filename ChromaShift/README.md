# ChromaShift

**System-wide color accessibility overlay for Windows.**

ChromaShift remaps colors across your entire screen in real-time — any app, browser, game, or embedded site — helping people with color vision deficiency (CVD) see more clearly without any per-app configuration.

## Features

- **7 CVD types**: Deuteranopia, Deuteranomaly, Protanopia, Protanomaly, Tritanopia, Tritanomaly, Achromatopsia
- **3 correction modes**:
  - **Correct** — Daltonize algorithm: shifts confused colors so they're distinguishable
  - **High Contrast** — Stronger 1.5× daltonization for maximum color separation
  - **Simulate** — Shows what content looks like to a CVD viewer (useful for designers/developers)
- **Intensity slider** — 0–100% blend for subtle or strong correction
- **Live color preview** — Applies correction to common confusion color pairs before you enable
- **Global hotkey** — Toggle the overlay from any app (default: Ctrl+Shift+C)
- **System tray** — Always accessible; left-click to open, right-click to toggle
- **Auto-start with Windows** — Optional via in-app toggle
- **Settings persistence** — Remembers preferences across restarts

## How It Works

ChromaShift uses the Windows Magnification API (`MagSetFullscreenColorEffect`) to apply a 5×5 color transformation matrix to every pixel on screen. Same API as Windows' built-in Magnifier accessibility tool. No screen capture, no drivers, no admin rights required.

The **Daltonize** correction algorithm (Fidaner et al., 2008) computes a single-pass linear transform:

```
Correction = Identity + ErrorShift × (Identity − Simulation) × strength
```

The simulation matrix models what a CVD viewer sees; the error shift redistributes "lost" color information into channels the viewer can still perceive.

## Getting Started

```bat
install.bat    # installs dependencies via uv
run.bat        # launches ChromaShift
```

Or manually:

```
uv sync
uv run python main.py
```

### Build standalone .exe

```bat
build.bat
```

Produces `dist\ChromaShift.exe` — no Python required on the target machine.

## Requirements

- Windows 8 or later (Windows 10/11 recommended)
- Python 3.12+ with `uv` (for running from source)

## Tech Stack

- **Windows Magnification API** — system-wide color matrix overlay via ctypes
- **CustomTkinter** — modern dark-theme UI
- **pystray + Pillow** — system tray icon (generated programmatically)
- **keyboard** — global hotkey listener
- **winreg** — Windows startup registry

## Part of MLEbotics

https://mlebotics.com

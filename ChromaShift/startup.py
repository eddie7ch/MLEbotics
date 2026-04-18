"""Manage Windows auto-start via the HKCU Run registry key."""

import logging
import sys
import winreg

logger = logging.getLogger(__name__)

_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "ChromaShift"


def _exe_path() -> str:
    """Return the path to the running executable."""
    if getattr(sys, "frozen", False):
        return sys.executable
    # Running as a script — point to main.py via pythonw so no console window
    import os
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    script = os.path.abspath(sys.argv[0])
    return f'"{pythonw}" "{script}"'


def enable() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _KEY_PATH,
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _exe_path())
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        logger.error("Could not enable startup: %s", exc)
        return False


def disable() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _KEY_PATH,
            0, winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, _APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as exc:
        logger.error("Could not disable startup: %s", exc)
        return False


def is_enabled() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _KEY_PATH,
            0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, _APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False

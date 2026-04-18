"""Persistent settings stored as JSON in the user's AppData folder."""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "cvd_type": "deuteranopia",
    "mode": "correct",
    "intensity": 1.0,
    "hotkey": "ctrl+shift+c",
    "start_with_windows": False,
    "start_minimized": True,
    "theme": "dark",
}

def _settings_path() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home()))
    p = Path(appdata) / "ChromaShift"
    p.mkdir(parents=True, exist_ok=True)
    return p / "settings.json"


class Settings:
    def __init__(self):
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self.load()

    def load(self):
        path = _settings_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for key, default in _DEFAULTS.items():
                    self._data[key] = saved.get(key, default)
            except Exception as exc:
                logger.warning("Could not load settings: %s", exc)

    def save(self):
        path = _settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as exc:
            logger.error("Could not save settings: %s", exc)

    def get(self, key: str) -> Any:
        return self._data.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    # Convenience properties
    @property
    def enabled(self) -> bool: return bool(self._data["enabled"])
    @enabled.setter
    def enabled(self, v: bool): self.set("enabled", v)

    @property
    def cvd_type(self) -> str: return str(self._data["cvd_type"])
    @cvd_type.setter
    def cvd_type(self, v: str): self.set("cvd_type", v)

    @property
    def mode(self) -> str: return str(self._data["mode"])
    @mode.setter
    def mode(self, v: str): self.set("mode", v)

    @property
    def intensity(self) -> float: return float(self._data["intensity"])
    @intensity.setter
    def intensity(self, v: float): self.set("intensity", max(0.0, min(1.0, v)))

    @property
    def hotkey(self) -> str: return str(self._data["hotkey"])
    @hotkey.setter
    def hotkey(self, v: str): self.set("hotkey", v)

    @property
    def start_with_windows(self) -> bool: return bool(self._data["start_with_windows"])
    @start_with_windows.setter
    def start_with_windows(self, v: bool): self.set("start_with_windows", v)

    @property
    def start_minimized(self) -> bool: return bool(self._data["start_minimized"])
    @start_minimized.setter
    def start_minimized(self, v: bool): self.set("start_minimized", v)

    @property
    def theme(self) -> str: return str(self._data["theme"])
    @theme.setter
    def theme(self, v: str): self.set("theme", v)

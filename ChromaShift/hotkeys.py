"""Global hotkey management using the keyboard library."""

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import keyboard as _kb
    _KB_AVAILABLE = True
except Exception:
    _KB_AVAILABLE = False
    logger.warning("keyboard library unavailable — hotkeys disabled")


class HotkeyManager:
    def __init__(self):
        self._hotkey: Optional[str] = None
        self._callback: Optional[Callable] = None
        self._hook_id = None

    def register(self, hotkey: str, callback: Callable) -> bool:
        if not _KB_AVAILABLE:
            return False
        self.unregister()
        try:
            _kb.add_hotkey(hotkey, callback, suppress=False)
            self._hotkey = hotkey
            self._callback = callback
            logger.info("Registered hotkey: %s", hotkey)
            return True
        except Exception as exc:
            logger.error("Could not register hotkey %r: %s", hotkey, exc)
            return False

    def unregister(self):
        if not _KB_AVAILABLE or self._hotkey is None:
            return
        try:
            _kb.remove_hotkey(self._hotkey)
        except Exception:
            pass
        self._hotkey = None

    def is_valid(self, hotkey: str) -> bool:
        if not _KB_AVAILABLE:
            return False
        try:
            _kb.parse_hotkey(hotkey)
            return True
        except Exception:
            return False

    @property
    def available(self) -> bool:
        return _KB_AVAILABLE

    @property
    def current(self) -> Optional[str]:
        return self._hotkey

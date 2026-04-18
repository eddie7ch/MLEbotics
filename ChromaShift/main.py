"""ChromaShift — entry point and application orchestrator.

Wires together the overlay, settings, hotkeys, tray, and UI.
"""

from __future__ import annotations

import ctypes
import logging
import sys

# ── DPI awareness (must happen before any window is created) ──────────────────
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor v2
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("chromashift")

from hotkeys import HotkeyManager
from overlay import ColorOverlay
from profiles import get_matrix
from settings_manager import Settings
from startup import disable as startup_disable, enable as startup_enable, is_enabled as startup_is_enabled
from tray import SystemTray
from ui import ChromaShiftWindow


class ChromaShiftApp:
    def __init__(self):
        self.settings = Settings()
        self.overlay = ColorOverlay()
        self.hotkeys = HotkeyManager()
        self.tray = SystemTray()
        self.window: ChromaShiftWindow | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def run(self):
        if not self.overlay.initialize():
            logger.warning("Magnification API unavailable — color effects disabled")

        # Sync startup registry to settings
        if self.settings.start_with_windows and not startup_is_enabled():
            startup_enable()
        elif not self.settings.start_with_windows and startup_is_enabled():
            self.settings.start_with_windows = True

        # Re-apply previous state
        if self.settings.enabled:
            self._apply_current()

        # Build UI (must be on main thread)
        self.window = ChromaShiftWindow(
            settings=self.settings,
            on_toggle=self.toggle,
            on_cvd_change=self._on_cvd_change,
            on_mode_change=self._on_mode_change,
            on_intensity_change=self._on_intensity_change,
            on_hotkey_change=self._on_hotkey_change,
            on_startup_change=self._on_startup_change,
            on_minimize_change=self._on_minimize_change,
            on_quit=self.quit,
        )

        # Start system tray in background thread
        self.tray.start(
            on_open=self._show_window,
            on_toggle=self.toggle,
            on_quit=self.quit,
            active=self.settings.enabled,
        )

        # Register hotkey
        self._register_hotkey(self.settings.hotkey)

        # Show or hide window based on start_minimized
        if self.settings.start_minimized:
            self.window.withdraw()
        else:
            self.window.show()

        # Enter tkinter main loop
        self.window.mainloop()

        # Cleanup on exit
        self._shutdown()

    def _shutdown(self):
        self.hotkeys.unregister()
        self.overlay.uninitialize()
        self.tray.stop()

    def quit(self):
        self.overlay.reset()
        if self.window:
            self.window.after(0, self.window.quit_app)

    # ── Toggle ────────────────────────────────────────────────────────────────

    def toggle(self):
        if self.settings.enabled:
            self.disable()
        else:
            self.enable()

    def enable(self):
        self.settings.enabled = True
        ok = self._apply_current()
        if not ok:
            logger.warning("Overlay apply failed (Magnification API unavailable?)")
        self._sync_ui_and_tray()

    def disable(self):
        self.settings.enabled = False
        self.overlay.reset()
        self._sync_ui_and_tray()

    def _apply_current(self) -> bool:
        matrix = get_matrix(
            self.settings.cvd_type,
            self.settings.mode,
            self.settings.intensity,
        )
        return self.overlay.apply(matrix)

    def _sync_ui_and_tray(self):
        enabled = self.settings.enabled
        cvd_label = self.settings.cvd_type
        tooltip = (
            f"ChromaShift — {cvd_label} ({self.settings.mode})"
            if enabled else "ChromaShift — Off"
        )
        self.tray.update(enabled, tooltip)
        if self.window:
            self.window.after(0, self.window.notify_toggle)

    # ── Settings callbacks ────────────────────────────────────────────────────

    def _on_cvd_change(self, cvd_type: str):
        if self.settings.enabled:
            self._apply_current()
        self._sync_ui_and_tray()

    def _on_mode_change(self, mode: str):
        if self.settings.enabled:
            self._apply_current()

    def _on_intensity_change(self, intensity: float):
        if self.settings.enabled:
            self._apply_current()

    def _on_hotkey_change(self, hotkey: str):
        self._register_hotkey(hotkey)

    def _on_startup_change(self, enabled: bool):
        if enabled:
            startup_enable()
        else:
            startup_disable()

    def _on_minimize_change(self, minimized: bool):
        pass  # saved automatically by settings manager

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _register_hotkey(self, hotkey: str):
        self.hotkeys.register(hotkey, self._hotkey_pressed)

    def _hotkey_pressed(self):
        if self.window:
            self.window.after(0, self.toggle)

    def _show_window(self):
        if self.window:
            self.window.after(0, self.window.show)


def main():
    app = ChromaShiftApp()
    app.run()


if __name__ == "__main__":
    main()

"""System tray icon using pystray + Pillow-generated icon."""

import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    _TRAY_AVAILABLE = True
except ImportError:
    _TRAY_AVAILABLE = False
    logger.warning("pystray/Pillow not available — system tray disabled")


def _make_icon(active: bool = False) -> "Image.Image":
    """Generate a 64x64 ChromaShift tray icon programmatically."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle
    bg = (30, 30, 30, 230) if not active else (20, 130, 220, 230)
    draw.ellipse([2, 2, size - 2, size - 2], fill=bg)

    # Colour ring (4 quadrant arcs: red, green, blue, yellow)
    ring_colors = [
        ((220, 50, 50), (0, -90)),
        ((50, 200, 80), (-90, -180)),
        ((50, 120, 240), (-180, -270)),
        ((240, 200, 40), (-270, -360)),
    ]
    for color, (start, end) in ring_colors:
        draw.arc([8, 8, size - 8, size - 8], start=start, end=end,
                 fill=color, width=6)

    # White "C" in the centre
    cx, cy = size // 2, size // 2
    r = 10
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=45, end=315,
             fill=(255, 255, 255, 240), width=4)

    # Active indicator dot (bottom-right)
    if active:
        draw.ellipse([size - 16, size - 16, size - 6, size - 6],
                     fill=(60, 230, 100, 255))
    else:
        draw.ellipse([size - 16, size - 16, size - 6, size - 6],
                     fill=(120, 120, 120, 200))

    return img


class SystemTray:
    def __init__(self):
        self._icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None
        self._on_open: Optional[Callable] = None
        self._on_toggle: Optional[Callable] = None
        self._on_quit: Optional[Callable] = None
        self._active = False

    def start(
        self,
        on_open: Callable,
        on_toggle: Callable,
        on_quit: Callable,
        active: bool = False,
    ):
        if not _TRAY_AVAILABLE:
            return
        self._on_open = on_open
        self._on_toggle = on_toggle
        self._on_quit = on_quit
        self._active = active
        self._icon = self._build_icon()
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def _build_icon(self) -> "pystray.Icon":
        img = _make_icon(self._active)
        menu = pystray.Menu(
            pystray.MenuItem("Open ChromaShift", self._cb_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: "Disable" if self._active else "Enable",
                self._cb_toggle,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._cb_quit),
        )
        return pystray.Icon("ChromaShift", img, "ChromaShift", menu)

    def update(self, active: bool, tooltip: str = "ChromaShift"):
        self._active = active
        if self._icon:
            self._icon.icon = _make_icon(active)
            self._icon.title = tooltip

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    # ── callbacks (run on pystray thread) ──────────────────────────────────

    def _cb_open(self, icon, item):
        if self._on_open:
            self._on_open()

    def _cb_toggle(self, icon, item):
        if self._on_toggle:
            self._on_toggle()

    def _cb_quit(self, icon, item):
        self.stop()
        if self._on_quit:
            self._on_quit()

    @property
    def available(self) -> bool:
        return _TRAY_AVAILABLE

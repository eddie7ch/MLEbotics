"""Windows Magnification API wrapper for system-wide color effects.

Uses MagSetFullscreenColorEffect (Windows 8+) to apply a 5x5 color
transformation matrix across the entire display without per-app setup.
"""

import ctypes
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    _mag = ctypes.WinDLL("Magnification.dll")
    _MAG_AVAILABLE = True
except OSError:
    _MAG_AVAILABLE = False
    logger.warning("Magnification.dll not found — color overlay unavailable")


class MAGCOLOREFFECT(ctypes.Structure):
    _fields_ = [("transform", (ctypes.c_float * 5) * 5)]


_IDENTITY_3X3 = [
    [1.0, 0.0, 0.0],
    [0.0, 1.0, 0.0],
    [0.0, 0.0, 1.0],
]


def _build_mag_effect(rgb3x3: list[list[float]]) -> MAGCOLOREFFECT:
    """Convert output-row 3x3 matrix to Windows MAGCOLOREFFECT (5x5, transposed).

    Windows uses input-to-output convention: output = input_row @ M
    so M[i][j] = fraction of input_i going to output_j.
    Our rgb3x3 uses output-row convention: rgb[i][j] = weight of input_j for output_i.
    Therefore M = transpose(rgb3x3).
    """
    effect = MAGCOLOREFFECT()
    # Initialize to identity
    for r in range(5):
        for c in range(5):
            effect.transform[r][c] = 1.0 if r == c else 0.0
    # Embed transposed 3x3
    for i in range(3):
        for j in range(3):
            effect.transform[i][j] = rgb3x3[j][i]
    return effect


class ColorOverlay:
    """Manages the system-wide color overlay via Windows Magnification API."""

    def __init__(self):
        self._initialized = False
        self._active = False

    def initialize(self) -> bool:
        if not _MAG_AVAILABLE:
            return False
        try:
            self._initialized = bool(_mag.MagInitialize())
            if not self._initialized:
                logger.error("MagInitialize() failed")
            return self._initialized
        except Exception as exc:
            logger.error("MagInitialize error: %s", exc)
            return False

    def apply(self, rgb3x3: list[list[float]]) -> bool:
        """Apply a 3x3 RGB color matrix system-wide. Returns True on success."""
        if not self._initialized:
            return False
        try:
            effect = _build_mag_effect(rgb3x3)
            ok = bool(_mag.MagSetFullscreenColorEffect(ctypes.byref(effect)))
            self._active = ok
            return ok
        except Exception as exc:
            logger.error("MagSetFullscreenColorEffect error: %s", exc)
            return False

    def reset(self) -> bool:
        """Restore normal colors (identity matrix)."""
        ok = self.apply(_IDENTITY_3X3)
        if ok:
            self._active = False
        return ok

    def uninitialize(self):
        if self._initialized:
            try:
                self.reset()
                _mag.MagUninitialize()
            except Exception as exc:
                logger.error("MagUninitialize error: %s", exc)
            self._initialized = False

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def available(self) -> bool:
        return _MAG_AVAILABLE and self._initialized

"""Color Vision Deficiency (CVD) profiles and transformation matrices.

Simulation matrices: what a CVD user sees from a normal image.
  Sources: Brettel (1997), Viénot (1999)

Correction matrices: derived via the Daltonize algorithm (Fidaner et al. 2008)
  adapted to single-pass linear transforms: C = I + E*(I-S)*strength
  where S = simulation matrix, E = error redistribution matrix.

All 3x3 matrices use output-row convention:
  output_R = row0 · [R, G, B]
  output_G = row1 · [R, G, B]
  output_B = row2 · [R, G, B]
"""

from __future__ import annotations

# ── Matrix helpers ────────────────────────────────────────────────────────────

def _I() -> list[list[float]]:
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]

def _mul(A: list, B: list) -> list:
    """3x3 matrix multiply."""
    C = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                C[i][j] += A[i][k] * B[k][j]
    return C

def _add(A: list, B: list) -> list:
    return [[A[i][j] + B[i][j] for j in range(3)] for i in range(3)]

def _scale(A: list, s: float) -> list:
    return [[A[i][j] * s for j in range(3)] for i in range(3)]

def blend(A: list, B: list, t: float) -> list:
    """t=0 → A, t=1 → B."""
    u = 1.0 - t
    return [[A[i][j] * u + B[i][j] * t for j in range(3)] for i in range(3)]

def apply_matrix(m: list, rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Apply 3x3 matrix to an (R,G,B) tuple with values in [0,1]."""
    r, g, b = rgb
    return (
        max(0.0, min(1.0, m[0][0]*r + m[0][1]*g + m[0][2]*b)),
        max(0.0, min(1.0, m[1][0]*r + m[1][1]*g + m[1][2]*b)),
        max(0.0, min(1.0, m[2][0]*r + m[2][1]*g + m[2][2]*b)),
    )

# ── Base simulation matrices ──────────────────────────────────────────────────

_SIM = {
    "protanopia": [
        [0.56667, 0.43333, 0.00000],
        [0.55833, 0.44167, 0.00000],
        [0.00000, 0.24167, 0.75833],
    ],
    "deuteranopia": [
        [0.62500, 0.37500, 0.00000],
        [0.70000, 0.30000, 0.00000],
        [0.00000, 0.30000, 0.70000],
    ],
    "tritanopia": [
        [0.95000, 0.05000, 0.00000],
        [0.00000, 0.43333, 0.56667],
        [0.00000, 0.47500, 0.52500],
    ],
    "achromatopsia": [
        [0.2126, 0.7152, 0.0722],
        [0.2126, 0.7152, 0.0722],
        [0.2126, 0.7152, 0.0722],
    ],
}

# ── Error redistribution matrices ─────────────────────────────────────────────
# E[i][j] = fraction of error from input channel j redistributed to output channel i

_ERR = {
    # Shift lost-red info into green and blue
    "protanopia": [
        [0.0, 0.0, 0.0],
        [0.7, 0.0, 0.0],
        [0.7, 0.0, 0.0],
    ],
    # Shift lost-green info into red and blue
    "deuteranopia": [
        [0.0, 0.7, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 0.7, 0.0],
    ],
    # Shift lost-blue info into red and green
    "tritanopia": [
        [0.0, 0.0, 0.7],
        [0.0, 0.0, 0.7],
        [0.0, 0.0, 0.0],
    ],
}

def _daltonize(cvd_base: str, strength: float = 1.0) -> list:
    """C = I + E * (I - S) * strength"""
    I = _I()
    S = _SIM[cvd_base]
    E = _ERR[cvd_base]
    I_minus_S = _add(I, _scale(S, -1.0))
    correction = _add(I, _scale(_mul(E, I_minus_S), strength))
    return correction

# ── Precomputed correction matrices ──────────────────────────────────────────

_CORRECT    = {k: _daltonize(k, 1.0) for k in _ERR}
_CORRECT_HC  = {k: _daltonize(k, 2.5) for k in _ERR}
_CORRECT_MAX = {k: _daltonize(k, 4.0) for k in _ERR}

# ── CVD profile registry ──────────────────────────────────────────────────────

CVD_TYPES: dict[str, dict] = {
    "deuteranopia": {
        "label": "Deuteranopia",
        "subtitle": "Green-blind  (~6% of males, most common)",
        "base": "deuteranopia",
        "severity": 1.0,
    },
    "deuteranomaly": {
        "label": "Deuteranomaly",
        "subtitle": "Green-weak (reduced green sensitivity)",
        "base": "deuteranopia",
        "severity": 0.6,
    },
    "protanopia": {
        "label": "Protanopia",
        "subtitle": "Red-blind (~1% of males)",
        "base": "protanopia",
        "severity": 1.0,
    },
    "protanomaly": {
        "label": "Protanomaly",
        "subtitle": "Red-weak (reduced red sensitivity)",
        "base": "protanopia",
        "severity": 0.6,
    },
    "tritanopia": {
        "label": "Tritanopia",
        "subtitle": "Blue-blind (rare, ~0.01%)",
        "base": "tritanopia",
        "severity": 1.0,
    },
    "tritanomaly": {
        "label": "Tritanomaly",
        "subtitle": "Blue-weak (reduced blue sensitivity)",
        "base": "tritanopia",
        "severity": 0.6,
    },
    "achromatopsia": {
        "label": "Achromatopsia",
        "subtitle": "Complete color blindness (monochromacy)",
        "base": "achromatopsia",
        "severity": 1.0,
    },
    "achromatomaly": {
        "label": "Achromatomaly",
        "subtitle": "Partial color blindness (blue-cone monochromacy)",
        "base": "achromatopsia",
        "severity": 0.5,
    },
}

MODES = ["correct", "high_contrast", "maximum", "simulate"]
MODE_LABELS = {
    "correct":       "Correct",
    "high_contrast": "High Contrast",
    "maximum":       "Maximum",
    "simulate":      "Simulate",
}

# ── Public matrix resolver ────────────────────────────────────────────────────

def get_matrix(cvd_type: str, mode: str, intensity: float) -> list:
    """Return the 3x3 color matrix for the given CVD type, mode and intensity (0–1).

    intensity=0 → identity (no effect), intensity=1 → full effect.
    """
    profile = CVD_TYPES.get(cvd_type)
    if profile is None:
        return _I()

    base = profile["base"]
    severity = profile["severity"]
    t = intensity * severity  # effective blend factor

    if mode == "simulate":
        target = _SIM.get(base, _I())
    elif mode == "maximum":
        target = _CORRECT_MAX.get(base, _CORRECT_HC.get(base, _I()))
    elif mode == "high_contrast":
        target = _CORRECT_HC.get(base, _CORRECT.get(base, _I()))
    else:  # "correct"
        target = _CORRECT.get(base, _I())

    return blend(_I(), target, t)

# ── Sample colors for preview swatches ───────────────────────────────────────

# Common red-green confusion pairs (R,G,B in 0–255)
PREVIEW_PAIRS: list[tuple[tuple, tuple, str]] = [
    ((220,  50,  50), ( 50, 180,  50), "Red / Green"),
    ((200, 150,   0), ( 80, 140,  80), "Orange / Olive"),
    ((180,  80, 180), ( 80, 100, 180), "Purple / Blue"),
    ((  0, 160, 160), (160,  80,  80), "Teal / Brown"),
    ((240, 100,  30), (100, 160,  30), "Orange / Lime"),
    ((100,  50, 200), ( 50, 150,  50), "Violet / Green"),
]

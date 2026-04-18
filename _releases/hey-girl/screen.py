"""
Screen capture module.
Takes a screenshot of the primary monitor and returns it as a base64 PNG string.
"""

import base64
import io
import mss
import mss.tools
from PIL import Image


def capture_screenshot(monitor_index: int = 1, resize_to: tuple = None) -> str:
    """
    Capture a screenshot of the specified monitor.

    Args:
        monitor_index: Monitor to capture (1 = primary).
        resize_to: Optional (width, height) tuple to resize the screenshot.

    Returns:
        Base64-encoded PNG string.
    """
    with mss.mss() as sct:
        monitor = sct.monitors[monitor_index]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if resize_to:
        img = img.resize(resize_to, Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def capture_region(left: int, top: int, width: int, height: int) -> str:
    """
    Capture a specific rectangular region of the screen.
    Returns base64-encoded PNG string.
    """
    with mss.mss() as sct:
        region = {"left": left, "top": top, "width": width, "height": height}
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


if __name__ == "__main__":
    # Quick test: save a screenshot to disk
    data = capture_screenshot()
    with open("test_screenshot.png", "wb") as f:
        f.write(__import__("base64").b64decode(data))
    print("Screenshot saved to test_screenshot.png")

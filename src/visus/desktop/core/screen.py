"""Visus Desktop - Screen utilities.

Helpers for querying the display size and capturing screenshots. Capture prefers
``mss`` (fast, multi-monitor) and transparently falls back to ``pyautogui`` if
``mss`` is unavailable or fails. Heavy imports are done lazily so the module
imports cleanly even in headless environments.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_display_size() -> tuple[int, int]:
    """Return the primary display size as ``(width, height)`` in pixels."""
    import pyautogui

    return tuple(pyautogui.size())


def _capture_with_mss(region: tuple[int, int, int, int] | None):
    """Capture via ``mss`` and return a PIL image. Raises if mss is unavailable."""
    import mss
    from PIL import Image

    with mss.mss() as sct:
        if region is not None:
            x, y, width, height = region
            monitor = {
                "left": int(x),
                "top": int(y),
                "width": int(width),
                "height": int(height),
            }
        else:
            # monitors[1] is the primary monitor; monitors[0] is the full virtual screen.
            monitor = sct.monitors[1]
        shot = sct.grab(monitor)

    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def capture_screen(region: tuple[int, int, int, int] | None = None):
    """Capture the screen (or a region) and return it as a PIL image.

    Uses ``mss`` for speed and multi-monitor support, falling back to
    ``pyautogui`` on any failure (e.g. mss not installed).

    Args:
        region: Optional capture region as ``(x, y, width, height)``. When
            ``None`` (the default) the primary screen is captured.

    Returns:
        PIL.Image.Image: The captured screenshot.
    """
    try:
        return _capture_with_mss(region)
    except Exception as exc:
        logger.debug("mss capture failed (%s); falling back to pyautogui", exc)
        import pyautogui

        return pyautogui.screenshot(region=region)


def save_screenshot(path: str, region: tuple[int, int, int, int] | None = None) -> str:
    """Capture a screenshot and save it to ``path``; return ``path``."""
    image = capture_screen(region=region)
    image.save(path)
    return path

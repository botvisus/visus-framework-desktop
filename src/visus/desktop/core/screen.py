"""Visus Desktop - Screen utilities.

Thin, well-documented helpers for querying the display size and capturing
screenshots. ``pyautogui`` is imported lazily inside each function so this
module can still be imported in headless environments where ``pyautogui``
cannot initialize a display.
"""

from __future__ import annotations


def get_display_size() -> tuple[int, int]:
    """Return the primary display size as ``(width, height)`` in pixels.

    Returns:
        tuple[int, int]: The display size as ``(width, height)``.
    """
    import pyautogui

    return tuple(pyautogui.size())


def capture_screen(region: tuple[int, int, int, int] | None = None):
    """Capture a screenshot of the screen (or a region of it).

    Args:
        region: Optional capture region as ``(x, y, width, height)``. When
            ``None`` (the default) the whole screen is captured.

    Returns:
        PIL.Image.Image: The captured screenshot as a PIL image.
    """
    import pyautogui

    return pyautogui.screenshot(region=region)


def save_screenshot(path: str, region: tuple[int, int, int, int] | None = None) -> str:
    """Capture a screenshot and save it to ``path``.

    Args:
        path: Destination file path for the saved image.
        region: Optional capture region as ``(x, y, width, height)``. When
            ``None`` (the default) the whole screen is captured.

    Returns:
        str: The ``path`` the screenshot was saved to.
    """
    image = capture_screen(region=region)
    image.save(path)
    return path

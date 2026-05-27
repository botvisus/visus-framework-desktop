"""Visus Desktop - Extra mouse helpers.

Thin, well-documented wrappers over ``pyautogui`` for mouse actions that are
not covered by the core virtual mouse: scrolling, dragging, triple-clicking and
a lightly "human" jittered move.

``pyautogui`` is imported lazily inside each function so this module can still
be imported in headless environments where ``pyautogui`` cannot initialize a
display.
"""

from __future__ import annotations

import random


def scroll(amount: int, x: int | None = None, y: int | None = None) -> None:
    """Scroll the mouse wheel.

    Args:
        amount: Number of "clicks" to scroll. Positive values scroll up,
            negative values scroll down.
        x: Optional x coordinate to move to before scrolling.
        y: Optional y coordinate to move to before scrolling.
    """
    import pyautogui

    pyautogui.scroll(amount, x=x, y=y)


def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.5,
    button: str = "left",
) -> None:
    """Drag from a start point to an end point.

    The cursor is first moved to ``(start_x, start_y)`` and then dragged to
    ``(end_x, end_y)`` while holding ``button``.

    Args:
        start_x: X coordinate where the drag begins.
        start_y: Y coordinate where the drag begins.
        end_x: X coordinate where the drag ends.
        end_y: Y coordinate where the drag ends.
        duration: Time in seconds the drag should take.
        button: Mouse button to hold during the drag (``"left"``, ``"middle"``
            or ``"right"``).
    """
    import pyautogui

    pyautogui.moveTo(start_x, start_y)
    pyautogui.dragTo(end_x, end_y, duration, button=button)


def triple_click(
    x: int | None = None, y: int | None = None, interval: float = 0.05
) -> None:
    """Perform a triple click.

    Args:
        x: Optional x coordinate to click at. When ``None`` the click happens
            at the current cursor position.
        y: Optional y coordinate to click at. When ``None`` the click happens
            at the current cursor position.
        interval: Seconds to wait between each of the three clicks.
    """
    import pyautogui

    pyautogui.click(x, y, clicks=3, interval=interval)


def move_random(x: int, y: int, max_offset: int = 3, duration: float = 0.2) -> None:
    """Move the cursor to ``(x, y)`` with a light "human" jitter.

    The cursor first moves to a point randomly offset from the target (within
    ``max_offset`` pixels on each axis), then settles exactly on ``(x, y)``.

    Args:
        x: Target x coordinate to settle on.
        y: Target y coordinate to settle on.
        max_offset: Maximum jitter offset (in pixels) applied to each axis
            before settling on the exact target.
        duration: Time in seconds the initial jittered move should take.
    """
    import pyautogui

    offset_x = random.randint(-max_offset, max_offset)
    offset_y = random.randint(-max_offset, max_offset)
    pyautogui.moveTo(x + offset_x, y + offset_y, duration=duration)
    # Settle exactly on the requested target.
    pyautogui.moveTo(x, y)

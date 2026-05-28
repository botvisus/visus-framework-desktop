"""Visus Desktop - Screen utilities.

Helpers for querying the display size and capturing screenshots. Capture prefers
``mss`` (fast, multi-monitor) and transparently falls back to ``pyautogui`` if
``mss`` is unavailable or fails. Heavy imports are done lazily so the module
imports cleanly even in headless environments.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)


# Optional alternative screen source -- when set, ``capture_screen`` reads
# frames from disk instead of grabbing the live display. Supports
# ``'disk:<dir>'`` for now (Phase 2 / TS3). Thread-local so concurrent
# tests don't step on each other.
_source_state = threading.local()


def set_screen_source(source: str | None) -> None:
    """Configure where ``capture_screen`` reads from.

    Args:
        source: ``None`` for live capture (default), or
            ``'disk:<directory>'`` to cycle through PNG files in the
            directory (sorted alphabetically) instead of touching the
            display. Used by the executor when
            ``config['screen_source']`` is set, and directly by tests.
    """
    _source_state.source = source
    _source_state.index = 0


def get_screen_source() -> str | None:
    return getattr(_source_state, "source", None)


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


def _capture_from_disk_source(source: str, region):
    """Read the next PNG from a ``disk:<dir>`` source, looping when empty.

    Returns the captured PIL image, or ``None`` if the source is empty /
    missing so the caller can fall back to live capture.
    """
    from PIL import Image

    directory = source[len("disk:"):]
    if not os.path.isdir(directory):
        return None
    files = sorted(
        f for f in os.listdir(directory) if f.lower().endswith(".png")
    )
    if not files:
        return None
    index = getattr(_source_state, "index", 0) % len(files)
    _source_state.index = index + 1
    image = Image.open(os.path.join(directory, files[index])).convert("RGB")
    if region is not None:
        x, y, w, h = region
        image = image.crop((x, y, x + w, y + h))
    return image


def capture_screen(region: tuple[int, int, int, int] | None = None):
    """Capture the screen (or a region) and return it as a PIL image.

    When ``set_screen_source('disk:<dir>')`` has been called, frames come
    from disk instead of the live display (Phase 2 / TS3). Otherwise
    uses ``mss`` for speed and multi-monitor support, falling back to
    ``pyautogui`` on any failure (e.g. mss not installed).

    Args:
        region: Optional capture region as ``(x, y, width, height)``. When
            ``None`` (the default) the primary screen is captured.

    Returns:
        PIL.Image.Image: The captured screenshot.
    """
    source = get_screen_source()
    if source and source.startswith("disk:"):
        from_disk = _capture_from_disk_source(source, region)
        if from_disk is not None:
            return from_disk
        # Fall through to live capture so a misconfigured source does
        # not silently break the bot.
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


def _frame_signature(image) -> bytes:
    """Return a cheap content hash for a captured frame.

    ``tobytes()`` is faster than a real hash for the small regions
    typically passed to ``wait_for_stable_screen`` and is sufficient for
    equality comparison.
    """
    return image.tobytes()


def wait_for_stable_screen(
    region: tuple[int, int, int, int] | None = None,
    stable_for: float = 0.5,
    timeout: float = 15.0,
    poll_interval: float = 0.1,
) -> bool:
    """Wait until the screen stops changing (Phase 2, S1).

    Polls ``capture_screen(region)`` every ``poll_interval`` seconds.
    Returns True as soon as the same frame has been observed for at
    least ``stable_for`` seconds; returns False if ``timeout`` elapses
    first. Classic SPA / Oracle Forms "wait until the redraw finishes"
    primitive.

    Args:
        region: Optional ``(x, y, w, h)`` to monitor a subset of the
            screen; ``None`` watches the full primary monitor.
        stable_for: Seconds of unchanged frames required to declare
            stability.
        timeout: Maximum total time to wait before giving up.
        poll_interval: Time between consecutive captures.

    Returns:
        True if the screen stabilised, False on timeout.
    """
    import time as _time

    deadline = _time.monotonic() + timeout
    last_sig: bytes | None = None
    stable_since: float | None = None
    while _time.monotonic() < deadline:
        # Import inside the loop so test patches of ``capture_screen``
        # in the ``visus.desktop.core.screen`` namespace take effect.
        from . import screen as _screen

        frame = _screen.capture_screen(region=region)
        sig = _frame_signature(frame)
        now = _time.monotonic()
        if sig == last_sig:
            if stable_since is None:
                stable_since = now
            if (now - stable_since) >= stable_for:
                return True
        else:
            last_sig = sig
            stable_since = now
        _time.sleep(poll_interval)
    return False

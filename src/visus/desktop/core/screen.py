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
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Monitor:
    """One physical display, returned by :func:`get_monitors`.

    ``index`` is 1-based; mss reserves index 0 for the virtual screen
    spanning every monitor, which the public helpers hide. ``is_primary``
    follows mss's convention -- the first physical monitor it lists.
    """

    index: int
    x: int
    y: int
    width: int
    height: int
    is_primary: bool


# Optional alternative screen source -- when set, ``capture_screen`` reads
# frames from disk instead of grabbing the live display. Supports
# ``'disk:<dir>'`` for now (Phase 2 / TS3). Thread-local so concurrent
# tests don't step on each other.
_source_state = threading.local()


# Per-region screenshot cache (Phase 3 / E3). TTL stays 0 (disabled) by
# default; users opt in via ``set_screen_cache_ms`` or
# ``config['screen_cache_ms']``. Cache key is ``(region, monitor)`` so
# different regions don't collide.
_cache_state = threading.local()


def set_screen_cache_ms(ms: int) -> None:
    """Configure the TTL of the per-region screenshot cache in milliseconds.

    ``0`` (default) disables caching. Non-zero values let back-to-back
    ``capture_screen`` calls on the same region reuse the previous PIL
    image, useful when several finds run sequentially on the same area.

    No-op when the value matches the current TTL — preserves a long-
    running MCP server's cache across ``configure`` rebuilds (N3).
    """
    new_ttl = max(0, int(ms))
    if new_ttl == getattr(_cache_state, "ttl_ms", 0):
        return
    _cache_state.ttl_ms = new_ttl
    _cache_state.entries = {}


def _get_cache_ttl_ms() -> int:
    return int(getattr(_cache_state, "ttl_ms", 0))


def invalidate_screen_cache() -> None:
    """Clear every cached region (call after a click / typed input)."""
    _cache_state.entries = {}


def _cache_lookup(key):
    entries = getattr(_cache_state, "entries", None)
    if not entries:
        return None
    entry = entries.get(key)
    if entry is None:
        return None
    ts, image = entry
    if (_monotonic_ms() - ts) > _get_cache_ttl_ms():
        return None
    return image


def _cache_store(key, image):
    entries = getattr(_cache_state, "entries", None)
    if entries is None:
        entries = {}
        _cache_state.entries = entries
    entries[key] = (_monotonic_ms(), image)


def _monotonic_ms() -> int:
    import time as _time

    return int(_time.monotonic() * 1000)


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


def _capture_with_mss(
    region: tuple[int, int, int, int] | None,
    monitor_index: int | None = None,
):
    """Capture via ``mss`` and return a PIL image. Raises if mss is unavailable."""
    import mss
    from PIL import Image

    # ``mss.mss`` is the legacy alias; ``mss.MSS`` is the canonical class
    # name in mss>=10. Use whichever is available so we work across
    # versions without the DeprecationWarning.
    _MSS = getattr(mss, "MSS", None) or mss.mss

    with _MSS() as sct:
        if region is not None:
            x, y, width, height = region
            monitor = {
                "left": int(x),
                "top": int(y),
                "width": int(width),
                "height": int(height),
            }
        elif monitor_index is not None:
            if monitor_index < 1 or monitor_index >= len(sct.monitors):
                raise ValueError(
                    f"monitor index {monitor_index} out of range "
                    f"(have {len(sct.monitors) - 1} physical monitor(s))"
                )
            monitor = sct.monitors[monitor_index]
        else:
            # monitors[1] is the primary monitor; monitors[0] is the full virtual screen.
            monitor = sct.monitors[1]
        shot = sct.grab(monitor)

    return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def get_monitors() -> list[Monitor]:
    """Return the list of physical monitors (Phase 3 / E4).

    mss reserves index 0 for the virtual screen spanning every monitor;
    this helper hides it and returns just the physical ones starting at
    index 1. The first physical monitor is marked ``is_primary``.
    """
    import mss

    _MSS = getattr(mss, "MSS", None) or mss.mss
    with _MSS() as sct:
        raw = list(sct.monitors)
    physical: list[Monitor] = []
    for idx, m in enumerate(raw):
        if idx == 0:
            continue  # the virtual-screen entry
        physical.append(
            Monitor(
                index=idx,
                x=int(m["left"]),
                y=int(m["top"]),
                width=int(m["width"]),
                height=int(m["height"]),
                is_primary=(idx == 1),
            )
        )
    return physical


def take_screenshot(
    region: tuple[int, int, int, int] | None = None,
    monitor: int | None = None,
):
    """Capture either a region or a whole monitor (Phase 3 / E4).

    Convenience wrapper over :func:`capture_screen` exposed at the
    top-level so users do not need to construct a ``VisusBot`` for a
    one-shot screenshot.
    """
    return capture_screen(region=region, monitor=monitor)


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


def capture_screen(
    region: tuple[int, int, int, int] | None = None,
    monitor: int | None = None,
):
    """Capture the screen (or a region) and return it as a PIL image.

    When ``set_screen_source('disk:<dir>')`` has been called, frames come
    from disk instead of the live display (Phase 2 / TS3). Otherwise
    uses ``mss`` for speed and multi-monitor support, falling back to
    ``pyautogui`` on any failure (e.g. mss not installed).

    Args:
        region: Optional capture region as ``(x, y, width, height)``. When
            ``None`` (the default) the primary screen is captured.
        monitor: Optional 1-based monitor index. ``None`` keeps the
            historical behaviour (primary monitor); ``1`` is also the
            primary, ``2`` the secondary, etc. Mutually exclusive with
            ``region`` -- if both are given ``region`` wins.

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
    ttl_ms = _get_cache_ttl_ms()
    cache_key = None
    if ttl_ms > 0:
        cache_key = (region, monitor)
        cached = _cache_lookup(cache_key)
        if cached is not None:
            return cached
    try:
        captured = _capture_with_mss(region, monitor_index=monitor)
        if cache_key is not None:
            _cache_store(cache_key, captured)
        return captured
    except ValueError:
        # Re-raise programmer errors (e.g. invalid monitor index) so they
        # are not silently swallowed by the pyautogui fallback below.
        raise
    except Exception as exc:
        # The pyautogui fallback cannot honour a specific monitor index;
        # refuse to silently downgrade to the primary monitor instead
        # of what the caller asked for.
        if monitor is not None:
            raise RuntimeError(
                f"mss capture for monitor={monitor} failed ({exc}); "
                "pyautogui fallback only captures the primary monitor."
            ) from exc
        logger.debug("mss capture failed (%s); falling back to pyautogui", exc)
        import pyautogui

        return pyautogui.screenshot(region=region)


def save_screenshot(
    path: str,
    region: tuple[int, int, int, int] | None = None,
    monitor: int | None = None,
) -> str:
    """Capture a screenshot and save it to ``path``; return ``path``.

    Mirrors :func:`capture_screen` -- pass ``region=(x, y, w, h)`` to crop
    or ``monitor=N`` (1-based) to target a specific physical monitor.
    Parent directories are created if missing so callers don't have to
    pre-make the output folder.
    """
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    image = capture_screen(region=region, monitor=monitor)
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

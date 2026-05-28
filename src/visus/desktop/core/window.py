"""Visus Desktop - Top-level window management.

Cross-platform window helpers. The public surface (``focus_window``,
``maximize_window``, ``minimize_window``, ``close_window``) dispatches
by OS:

  * Windows -> ``pywin32`` (``win32gui`` / ``win32con``).
  * Linux   -> ``xdotool`` + ``wmctrl`` via
    :mod:`visus.desktop.core.window_linux` (Phase 4 / X1).

On unsupported platforms the public helpers raise
:class:`~visus.desktop.exceptions.NotSupportedOnThisOS`.
"""

from __future__ import annotations

import sys

from ..exceptions import NotSupportedOnThisOS


def _require_windows() -> None:
    if sys.platform != "win32":
        raise NotSupportedOnThisOS(
            "Direct win32 API requires Windows."
        )


def find_window(title_substring: str) -> int | None:
    """Find the first visible top-level window matching a title substring.

    Returns the hwnd of the first *visible* window whose title contains
    ``title_substring`` (case-insensitive), or ``None`` if none matched.
    """
    _require_windows()
    import win32gui

    needle = title_substring.lower()
    matches: list[int] = []

    def _callback(hwnd: int, _extra: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd) or ""
        if needle in title.lower():
            matches.append(hwnd)
            return False  # stop enumeration early
        return True

    win32gui.EnumWindows(_callback, None)
    return matches[0] if matches else None


def _dispatch_or_raise(win_impl, linux_fn, *args):
    """Pick the OS backend; raise NotSupportedOnThisOS otherwise."""
    if sys.platform == "win32":
        return win_impl(*args)
    if sys.platform.startswith("linux"):
        return linux_fn(*args)
    raise NotSupportedOnThisOS(
        f"Window management is not implemented on {sys.platform!r}."
    )


def _win_focus(title_substring: str) -> bool:
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.SetForegroundWindow(hwnd)
    return True


def _win_maximize(title_substring: str) -> bool:
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    return True


def _win_minimize(title_substring: str) -> bool:
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return True


def _win_close(title_substring: str) -> bool:
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    return True


def focus_window(title_substring: str) -> bool:
    """Bring a window matching ``title_substring`` to the foreground."""
    from . import window_linux as _linux

    return _dispatch_or_raise(_win_focus, _linux.focus_window_linux, title_substring)


def maximize_window(title_substring: str) -> bool:
    """Maximize a window matching ``title_substring``."""
    from . import window_linux as _linux

    return _dispatch_or_raise(
        _win_maximize, _linux.maximize_window_linux, title_substring
    )


def minimize_window(title_substring: str) -> bool:
    """Minimize a window matching ``title_substring``."""
    from . import window_linux as _linux

    return _dispatch_or_raise(
        _win_minimize, _linux.minimize_window_linux, title_substring
    )


def close_window(title_substring: str) -> bool:
    """Request that a window matching ``title_substring`` close (posts WM_CLOSE on Win)."""
    from . import window_linux as _linux

    return _dispatch_or_raise(_win_close, _linux.close_window_linux, title_substring)

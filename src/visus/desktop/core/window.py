"""Visus Desktop - Top-level window management (Windows).

Helpers for locating and manipulating top-level windows on Windows by a
case-insensitive substring of their title. Win32 functionality comes from
:mod:`pywin32` (``win32gui``/``win32con``), imported lazily so this module can
be imported on any platform. On non-Windows systems the functions raise
:class:`~visus.desktop.exceptions.NotSupportedOnThisOS` (a Linux backend via
xdotool/wmctrl is planned).
"""

from __future__ import annotations

import sys

from ..exceptions import NotSupportedOnThisOS


def _require_windows() -> None:
    if sys.platform != "win32":
        raise NotSupportedOnThisOS(
            "Window management is only available on Windows for now "
            "(a Linux backend via xdotool/wmctrl is planned)."
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


def focus_window(title_substring: str) -> bool:
    """Bring a window matching ``title_substring`` to the foreground."""
    _require_windows()
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.SetForegroundWindow(hwnd)
    return True


def maximize_window(title_substring: str) -> bool:
    """Maximize a window matching ``title_substring``."""
    _require_windows()
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    return True


def minimize_window(title_substring: str) -> bool:
    """Minimize a window matching ``title_substring``."""
    _require_windows()
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return True


def close_window(title_substring: str) -> bool:
    """Request that a window matching ``title_substring`` close (posts WM_CLOSE)."""
    _require_windows()
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    return True

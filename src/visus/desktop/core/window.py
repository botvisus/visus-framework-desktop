"""Visus Desktop - Top-level window management (Windows).

Helpers for locating and manipulating top-level windows on Windows by a
case-insensitive substring of their title. All Win32 functionality is
provided by :mod:`pywin32` (``win32gui``/``win32con``), which is imported
lazily inside each function so this module can be imported on any platform.
"""

from __future__ import annotations


def find_window(title_substring: str) -> int | None:
    """Find the first visible top-level window matching a title substring.

    Enumerates all top-level windows via :func:`win32gui.EnumWindows` and
    returns the handle (hwnd) of the first *visible* window whose title
    contains ``title_substring`` (case-insensitive).

    Args:
        title_substring: Substring to match against window titles
            (case-insensitive).

    Returns:
        int | None: The hwnd of the first matching visible window, or ``None``
        if no window matched.
    """
    import win32gui

    needle = title_substring.lower()
    matches: list[int] = []

    def _callback(hwnd: int, _extra: object) -> bool:
        # Only consider visible windows.
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd) or ""
        if needle in title.lower():
            matches.append(hwnd)
            # Stop enumeration early once we found a match.
            return False
        return True

    win32gui.EnumWindows(_callback, None)

    return matches[0] if matches else None


def focus_window(title_substring: str) -> bool:
    """Bring a window matching ``title_substring`` to the foreground.

    Args:
        title_substring: Substring to match against window titles
            (case-insensitive).

    Returns:
        bool: ``True`` if a matching window was found and focused, ``False``
        otherwise.
    """
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False

    win32gui.SetForegroundWindow(hwnd)
    return True


def maximize_window(title_substring: str) -> bool:
    """Maximize a window matching ``title_substring``.

    Args:
        title_substring: Substring to match against window titles
            (case-insensitive).

    Returns:
        bool: ``True`` if a matching window was found and maximized, ``False``
        otherwise.
    """
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False

    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    return True


def minimize_window(title_substring: str) -> bool:
    """Minimize a window matching ``title_substring``.

    Args:
        title_substring: Substring to match against window titles
            (case-insensitive).

    Returns:
        bool: ``True`` if a matching window was found and minimized, ``False``
        otherwise.
    """
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False

    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return True


def close_window(title_substring: str) -> bool:
    """Request that a window matching ``title_substring`` close.

    Posts a ``WM_CLOSE`` message to the window, which lets the application
    handle the close gracefully (e.g. prompting to save).

    Args:
        title_substring: Substring to match against window titles
            (case-insensitive).

    Returns:
        bool: ``True`` if a matching window was found and sent a close
        request, ``False`` otherwise.
    """
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False

    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    return True

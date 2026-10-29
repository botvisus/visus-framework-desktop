"""Typing without the keyboard: text and a few keys posted as window messages
straight to one control -- the companion of the virtual mouse.

The person's keyboard focus, keystrokes and clipboard stay theirs. Characters go
as ``WM_CHAR`` (any Unicode text, no keyboard-layout guessing); ``{enter}``,
``{tab}``, ``{del}``, ``{escape}`` as ``WM_KEYDOWN``/``WM_KEYUP``; ``{ctrl}a``
(select all) as ``EM_SETSEL``. Works where the control reads its message queue
(classic Win32 edits and dialogs). Apps that read the raw keyboard ignore posted
messages -- like the virtual mouse, check the result. Chords such as Ctrl+S
cannot be posted (the modifier state is read from the real keyboard).
"""

from __future__ import annotations

import logging
import re
import struct
import sys

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"(\{ctrl\}a|\{enter\}|\{tab\}|\{del\}|\{escape\})", re.IGNORECASE)
_EM_SETSEL = 0x00B1


def focused_control(hwnd: int) -> int:
    """The control holding keyboard focus inside ``hwnd``'s GUI thread -- where
    the text would go if that window were in front -- else ``hwnd`` itself."""
    import ctypes
    from ctypes import wintypes

    import win32process

    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
            ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
            ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
            ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
            ("rcCaret", wintypes.RECT),
        ]

    thread_id, _pid = win32process.GetWindowThreadProcessId(hwnd)
    info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
    if ctypes.windll.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)) and info.hwndFocus:
        return int(info.hwndFocus)
    return int(hwnd)


def _post_key(hwnd: int, vk: int) -> None:
    import win32api
    import win32con
    import win32gui

    scan = win32api.MapVirtualKey(vk, 0)
    down = 1 | (scan << 16)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, down)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, down | 0xC0000000)


def send_text(hwnd: int, text: str) -> bool:
    """Post ``text`` (with inline ``{enter}``/``{tab}``/``{del}``/``{escape}``/
    ``{ctrl}a`` tokens) to ``hwnd``. True once every message is queued."""
    if sys.platform != "win32" or not hwnd:
        return False
    import win32con
    import win32gui

    keys = {
        "{enter}": win32con.VK_RETURN, "{tab}": win32con.VK_TAB,
        "{del}": win32con.VK_DELETE, "{escape}": win32con.VK_ESCAPE,
    }
    try:
        for part in _TOKEN.split(text):
            if not part:
                continue
            token = part.lower()
            if token == "{ctrl}a":
                win32gui.PostMessage(hwnd, _EM_SETSEL, 0, -1)
            elif token in keys:
                _post_key(hwnd, keys[token])
            else:
                raw = part.encode("utf-16-le")
                # one WM_CHAR per UTF-16 code unit (emoji go as surrogate pairs)
                for code in struct.unpack(f"<{len(raw) // 2}H", raw):
                    win32gui.PostMessage(hwnd, win32con.WM_CHAR, code, 1)
    except Exception as exc:  # noqa: BLE001 -- a dead window, a bad handle
        logger.warning("virtual typing into %s failed: %s", hwnd, exc)
        return False
    return True

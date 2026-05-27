"""Tests for :mod:`visus.desktop.core.window`.

The Win32 layer is fully monkeypatched: ``EnumWindows`` is replaced with a
fake that feeds a fixed set of ``(hwnd, title)`` pairs, and the
state-changing calls (``SetForegroundWindow``, ``ShowWindow``,
``PostMessage``) are replaced with recorders. No real window is ever
focused, resized, or closed.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Window management is Windows-only (pywin32)"
)

# Fake top-level windows: (hwnd, title, is_visible).
_FAKE_WINDOWS = [
    (1001, "Untitled - Notepad", True),
    (1002, "Calculator", True),
    (1003, "Hidden Notepad", False),
]


@pytest.fixture
def fake_win32(monkeypatch):
    """Monkeypatch ``win32gui`` enumeration and lookup helpers."""
    import win32gui

    titles = {hwnd: title for hwnd, title, _ in _FAKE_WINDOWS}
    visible = {hwnd: vis for hwnd, _, vis in _FAKE_WINDOWS}

    def fake_enum_windows(callback, extra):
        for hwnd, _title, _vis in _FAKE_WINDOWS:
            # The callback returns False to stop enumeration early.
            if callback(hwnd, extra) is False:
                break

    monkeypatch.setattr(win32gui, "EnumWindows", fake_enum_windows)
    monkeypatch.setattr(win32gui, "GetWindowText", lambda hwnd: titles.get(hwnd, ""))
    monkeypatch.setattr(
        win32gui, "IsWindowVisible", lambda hwnd: visible.get(hwnd, False)
    )
    return win32gui


def test_find_window_matches_substring_case_insensitive(fake_win32) -> None:
    from visus.desktop.core.window import find_window

    # Case-insensitive substring match against a visible window.
    assert find_window("notepad") == 1001
    assert find_window("Calculator") == 1002


def test_find_window_returns_none_when_no_match(fake_win32) -> None:
    from visus.desktop.core.window import find_window

    assert find_window("no_such_window_title") is None


def test_find_window_ignores_invisible_windows(fake_win32) -> None:
    from visus.desktop.core.window import find_window

    # "Hidden Notepad" (hwnd 1003) is not visible, so "notepad" must resolve
    # to the visible Notepad window (1001) instead.
    assert find_window("hidden") is None


def test_focus_window_calls_set_foreground_with_resolved_hwnd(
    monkeypatch, fake_win32
) -> None:
    from visus.desktop.core.window import focus_window

    calls: list[int] = []
    monkeypatch.setattr(
        fake_win32, "SetForegroundWindow", lambda hwnd: calls.append(hwnd)
    )

    assert focus_window("calculator") is True
    assert calls == [1002]


def test_focus_window_false_when_no_match(monkeypatch, fake_win32) -> None:
    from visus.desktop.core.window import focus_window

    monkeypatch.setattr(
        fake_win32,
        "SetForegroundWindow",
        lambda hwnd: pytest.fail("should not be called"),
    )

    assert focus_window("no_such_window_title") is False


def test_maximize_window_calls_show_window_with_resolved_hwnd(
    monkeypatch, fake_win32
) -> None:
    import win32con

    from visus.desktop.core.window import maximize_window

    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        fake_win32, "ShowWindow", lambda hwnd, cmd: calls.append((hwnd, cmd))
    )

    assert maximize_window("notepad") is True
    assert calls == [(1001, win32con.SW_MAXIMIZE)]


def test_minimize_window_calls_show_window_with_resolved_hwnd(
    monkeypatch, fake_win32
) -> None:
    import win32con

    from visus.desktop.core.window import minimize_window

    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        fake_win32, "ShowWindow", lambda hwnd, cmd: calls.append((hwnd, cmd))
    )

    assert minimize_window("calculator") is True
    assert calls == [(1002, win32con.SW_MINIMIZE)]


def test_close_window_posts_wm_close_with_resolved_hwnd(
    monkeypatch, fake_win32
) -> None:
    import win32con

    from visus.desktop.core.window import close_window

    calls: list[tuple[int, int, int, int]] = []
    monkeypatch.setattr(
        fake_win32,
        "PostMessage",
        lambda hwnd, msg, wparam, lparam: calls.append((hwnd, msg, wparam, lparam)),
    )

    assert close_window("notepad") is True
    assert calls == [(1001, win32con.WM_CLOSE, 0, 0)]


def test_close_window_false_when_no_match(monkeypatch, fake_win32) -> None:
    from visus.desktop.core.window import close_window

    monkeypatch.setattr(
        fake_win32,
        "PostMessage",
        lambda *args: pytest.fail("should not be called"),
    )

    assert close_window("no_such_window_title") is False

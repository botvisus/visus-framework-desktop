"""Behavioural tests for ``visus.desktop.core.virtual_mouse.VirtualMouse``.

Nothing here clicks or moves a real mouse: ``pyautogui`` calls are
monkeypatched, and the Windows virtual-click path patches the win32 API
entry points (WindowFromPoint / ScreenToClient / PostMessage / MAKELONG).

This complements ``test_virtual_mouse.py`` (the DPI coordinate regression)
without duplicating it.
"""

from __future__ import annotations

import collections
import sys

import pyautogui
import pytest

import visus.desktop.core.virtual_mouse as vm_module
from visus.desktop.core.virtual_mouse import VirtualMouse
from visus.desktop.utils.config import BotVisionConfig

try:
    import win32api  # noqa: F401
    import win32con  # noqa: F401
    import win32gui  # noqa: F401

    _WIN32 = True
except Exception:
    _WIN32 = False

_IS_WINDOWS = sys.platform == "win32"

Point = collections.namedtuple("Point", "x y")


def _mouse(use_virtual=False):
    """Build a VirtualMouse with an explicit config."""
    return VirtualMouse(BotVisionConfig({"use_virtual_mouse": use_virtual}))


# --------------------------------------------------------------------------- #
# Physical click path (no virtual mouse)
# --------------------------------------------------------------------------- #
def test_left_click_uses_pyautogui_click(monkeypatch):
    """A left click with use_virtual=False calls pyautogui.click."""
    calls = []
    monkeypatch.setattr(pyautogui, "click", lambda *a, **k: calls.append(("click", a, k)))
    vm = _mouse(use_virtual=False)

    assert vm.click(100, 200, button="left", use_virtual=False) is True
    assert calls and calls[0][0] == "click"
    assert calls[0][1] == (100, 200)


def test_right_click_uses_pyautogui_right_click(monkeypatch):
    """A right click routes to pyautogui.rightClick."""
    calls = []
    monkeypatch.setattr(pyautogui, "rightClick", lambda *a, **k: calls.append(a))
    vm = _mouse(use_virtual=False)

    assert vm.click(10, 20, button="right", use_virtual=False) is True
    assert calls == [(10, 20)]


def test_double_click_uses_pyautogui_double_click(monkeypatch):
    """A double click routes to pyautogui.doubleClick."""
    calls = []
    monkeypatch.setattr(pyautogui, "doubleClick", lambda *a, **k: calls.append(a))
    vm = _mouse(use_virtual=False)

    assert vm.click(7, 8, button="double", use_virtual=False) is True
    assert calls == [(7, 8)]


def test_move_to_button_only_moves(monkeypatch):
    """button='move_to' moves the cursor and never clicks."""
    moves = []
    clicks = []
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: moves.append(a))
    monkeypatch.setattr(pyautogui, "click", lambda *a, **k: clicks.append(a))
    vm = _mouse(use_virtual=False)

    assert vm.click(50, 60, button="move_to") is True
    assert moves == [(50, 60)]
    assert clicks == []


def test_physical_click_returns_false_on_error(monkeypatch):
    """If pyautogui.click raises, _click_physical returns False (caught)."""

    def boom(*a, **k):
        raise RuntimeError("display gone")

    monkeypatch.setattr(pyautogui, "click", boom)
    vm = _mouse(use_virtual=False)

    assert vm.click(1, 2, button="left", use_virtual=False) is False


# --------------------------------------------------------------------------- #
# location_info recompute (virtual path)
# --------------------------------------------------------------------------- #
def test_location_info_recomputes_center(monkeypatch):
    """With use_virtual + location_info, the click targets the region centre."""
    seen = {}

    # Force the virtual path to be "taken" so the recompute happens, but make the
    # virtual click capture the coordinates instead of really posting messages.
    vm = _mouse(use_virtual=True)
    monkeypatch.setattr(vm, "virtual_available", True)
    monkeypatch.setattr(vm, "system", "windows")

    def fake_virtual(x, y, button="left"):
        seen["xy"] = (x, y)
        return True

    monkeypatch.setattr(vm, "_click_virtual_windows", fake_virtual)

    # region (200, 100, w=40, h=20) -> centre (220, 110).
    assert vm.click(0, 0, use_virtual=True, location_info=(200, 100, 40, 20)) is True
    assert seen["xy"] == (220, 110)


# --------------------------------------------------------------------------- #
# Virtual Windows path (skipped off Windows / without pywin32)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    not (_IS_WINDOWS and _WIN32), reason="Requires Windows + pywin32"
)
def test_virtual_windows_click_success(monkeypatch):
    """A successful Windows virtual click posts messages and returns True."""
    import win32api
    import win32gui

    posted = []

    monkeypatch.setattr(win32gui, "WindowFromPoint", lambda pt: 4242)
    monkeypatch.setattr(
        win32gui, "ScreenToClient", lambda hwnd, pt: (pt[0] - 10, pt[1] - 10)
    )
    monkeypatch.setattr(win32gui, "GetWindowText", lambda hwnd: "Target Window")
    monkeypatch.setattr(
        win32gui, "PostMessage", lambda *a, **k: posted.append(a)
    )
    monkeypatch.setattr(win32api, "MAKELONG", lambda lo, hi: (lo << 0) | (hi << 16))
    # Avoid the 50ms sleeps in the click sequence.
    monkeypatch.setattr(vm_module.time, "sleep", lambda *a, **k: None)

    vm = _mouse(use_virtual=True)
    assert vm._click_virtual_windows(300, 200, button="left") is True
    # A WM_MOUSEMOVE plus down/up were posted.
    assert len(posted) >= 3


@pytest.mark.skipif(
    not (_IS_WINDOWS and _WIN32), reason="Requires Windows + pywin32"
)
def test_virtual_windows_click_no_window_returns_false(monkeypatch):
    """When no window is under the point, the virtual click returns False."""
    import win32gui

    monkeypatch.setattr(win32gui, "WindowFromPoint", lambda pt: 0)

    vm = _mouse(use_virtual=True)
    assert vm._click_virtual_windows(10, 10, button="left") is False


@pytest.mark.skipif(
    not (_IS_WINDOWS and _WIN32), reason="Requires Windows + pywin32"
)
def test_virtual_failure_falls_back_to_physical(monkeypatch):
    """If the virtual click fails, click() falls back to the physical path."""
    physical = []
    monkeypatch.setattr(pyautogui, "click", lambda *a, **k: physical.append(a))
    # Cursor save/restore happen in the physical path when virtual is configured.
    monkeypatch.setattr(pyautogui, "position", lambda: Point(1, 1))
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: None)

    vm = _mouse(use_virtual=True)
    monkeypatch.setattr(vm, "virtual_available", True)
    monkeypatch.setattr(vm, "system", "windows")
    monkeypatch.setattr(vm, "_click_virtual_windows", lambda x, y, button="left": False)

    assert vm.click(40, 50, button="left", use_virtual=True) is True
    assert physical == [(40, 50)]


# --------------------------------------------------------------------------- #
# Cursor save / restore
# --------------------------------------------------------------------------- #
def test_save_and_restore_cursor_position(monkeypatch):
    """save_cursor_position records position; restore moves back to it."""
    moves = []
    monkeypatch.setattr(pyautogui, "position", lambda: Point(321, 654))
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: moves.append(a))

    vm = _mouse(use_virtual=False)
    vm.save_cursor_position()
    assert vm.original_cursor_pos == Point(321, 654)

    vm.restore_cursor_position()
    assert moves == [(321, 654)]


def test_restore_without_saved_position_is_noop(monkeypatch):
    """restore_cursor_position does nothing if no position was saved."""
    moves = []
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: moves.append(a))

    vm = _mouse(use_virtual=False)
    vm.original_cursor_pos = None
    vm.restore_cursor_position()

    assert moves == []


# --------------------------------------------------------------------------- #
# Misc accessors
# --------------------------------------------------------------------------- #
def test_get_cursor_position(monkeypatch):
    """get_cursor_position returns a plain (x, y) tuple."""
    monkeypatch.setattr(pyautogui, "position", lambda: Point(11, 22))
    vm = _mouse(use_virtual=False)

    assert vm.get_cursor_position() == (11, 22)


def test_get_cursor_position_returns_none_on_error(monkeypatch):
    """get_cursor_position returns None when pyautogui raises."""

    def boom():
        raise RuntimeError("no cursor")

    monkeypatch.setattr(pyautogui, "position", boom)
    vm = _mouse(use_virtual=False)

    assert vm.get_cursor_position() is None


def test_is_virtual_available_reflects_attribute():
    """is_virtual_available mirrors the detected availability flag."""
    vm = _mouse(use_virtual=False)
    vm.virtual_available = True
    assert vm.is_virtual_available() is True
    vm.virtual_available = False
    assert vm.is_virtual_available() is False

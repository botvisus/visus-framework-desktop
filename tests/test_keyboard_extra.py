"""Tests for ``visus.desktop.core.keyboard_extra``.

Every test monkeypatches the relevant ``pyautogui`` entry points
(``press``, ``hotkey``, ``keyDown``, ``keyUp``) so no real keystrokes are ever
sent to the host system.
"""

from __future__ import annotations

import pyautogui
import pytest

from visus.desktop.core.keyboard_extra import KeyboardMixin


class _Bot(KeyboardMixin):
    """Minimal concrete class used to exercise the mixin."""


@pytest.fixture
def recorder(monkeypatch):
    """Patch ``pyautogui`` key functions and record their calls.

    Returns a dict with ``press``, ``hotkey``, ``keyDown`` and ``keyUp`` keys,
    each holding the list of argument tuples captured for that function.
    """
    calls: dict[str, list] = {
        "press": [],
        "hotkey": [],
        "keyDown": [],
        "keyUp": [],
    }
    monkeypatch.setattr(pyautogui, "press", lambda *a, **k: calls["press"].append(a))
    monkeypatch.setattr(pyautogui, "hotkey", lambda *a, **k: calls["hotkey"].append(a))
    monkeypatch.setattr(pyautogui, "keyDown", lambda *a, **k: calls["keyDown"].append(a))
    monkeypatch.setattr(pyautogui, "keyUp", lambda *a, **k: calls["keyUp"].append(a))
    return calls


# ----------------------------------------------------------------------
# Generic helpers
# ----------------------------------------------------------------------
def test_type_key(recorder):
    """``type_key`` forwards the key name to ``pyautogui.press``."""
    _Bot().type_key("a")
    assert recorder["press"] == [("a",)]
    assert recorder["hotkey"] == []


def test_key_combo(recorder):
    """``key_combo`` forwards every key to ``pyautogui.hotkey``."""
    _Bot().key_combo("ctrl", "alt", "del")
    assert recorder["hotkey"] == [("ctrl", "alt", "del")]
    assert recorder["press"] == []


# ----------------------------------------------------------------------
# Navigation and editing
# ----------------------------------------------------------------------
def test_enter(recorder):
    """``enter`` presses ``"enter"``."""
    _Bot().enter()
    assert recorder["press"] == [("enter",)]


def test_shift_tab(recorder):
    """``shift_tab`` fires the Shift+Tab hotkey."""
    _Bot().shift_tab()
    assert recorder["hotkey"] == [("shift", "tab")]


def test_arrow_keys(recorder):
    """The four arrow helpers map to their ``pyautogui`` names."""
    bot = _Bot()
    bot.key_up()
    bot.key_down()
    bot.key_left()
    bot.key_right()
    assert recorder["press"] == [("up",), ("down",), ("left",), ("right",)]


def test_page_up(recorder):
    """``page_up`` presses ``"pageup"``."""
    _Bot().page_up()
    assert recorder["press"] == [("pageup",)]


def test_page_down(recorder):
    """``page_down`` presses ``"pagedown"``."""
    _Bot().page_down()
    assert recorder["press"] == [("pagedown",)]


# ----------------------------------------------------------------------
# Function keys
# ----------------------------------------------------------------------
def test_key_f5(recorder):
    """``key_f5`` presses ``"f5"``."""
    _Bot().key_f5()
    assert recorder["press"] == [("f5",)]


def test_key_f1_and_f12(recorder):
    """The first and last function keys press their respective names."""
    bot = _Bot()
    bot.key_f1()
    bot.key_f12()
    assert recorder["press"] == [("f1",), ("f12",)]


# ----------------------------------------------------------------------
# Shortcuts (hotkeys)
# ----------------------------------------------------------------------
def test_control_c(recorder):
    """``control_c`` fires the Ctrl+C hotkey."""
    _Bot().control_c()
    assert recorder["hotkey"] == [("ctrl", "c")]


def test_control_s(recorder):
    """``control_s`` fires the Ctrl+S hotkey."""
    _Bot().control_s()
    assert recorder["hotkey"] == [("ctrl", "s")]


def test_alt_f4(recorder):
    """``alt_f4`` fires the Alt+F4 hotkey."""
    _Bot().alt_f4()
    assert recorder["hotkey"] == [("alt", "f4")]


# ----------------------------------------------------------------------
# Modifier hold / release
# ----------------------------------------------------------------------
def test_hold_shift(recorder):
    """``hold_shift`` holds Shift down via ``pyautogui.keyDown``."""
    _Bot().hold_shift()
    assert recorder["keyDown"] == [("shift",)]
    assert recorder["keyUp"] == []


def test_release_ctrl(recorder):
    """``release_ctrl`` releases Ctrl via ``pyautogui.keyUp``."""
    _Bot().release_ctrl()
    assert recorder["keyUp"] == [("ctrl",)]
    assert recorder["keyDown"] == []


def test_no_real_keystrokes_leak(recorder):
    """A representative sequence records calls only through the patched API."""
    bot = _Bot()
    bot.type_key("x")
    bot.control_a()
    bot.enter()
    # All interactions were captured by the recorder; nothing escaped.
    total = sum(len(v) for v in recorder.values())
    assert total == 3

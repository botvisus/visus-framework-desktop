"""Tests for the mouse_down / mouse_up primitives.

These complement :func:`drag` (which combines down -> move -> up atomically) by
letting callers hold a button across other operations. No real input is sent —
``pyautogui`` is monkeypatched.
"""

from __future__ import annotations

import pyautogui

from visus.desktop.core import mouse_extra
from visus.desktop.core.capabilities import CapabilitiesMixin


class _Bot(CapabilitiesMixin):
    """Tiny host so the mixin methods can be exercised without Tesseract."""


def test_module_mouse_down_calls_pyautogui_with_coords_and_button(monkeypatch):
    calls = []
    monkeypatch.setattr(pyautogui, "mouseDown", lambda **kw: calls.append(kw))
    mouse_extra.mouse_down(10, 20, button="right")
    assert calls == [{"x": 10, "y": 20, "button": "right"}]


def test_module_mouse_up_defaults_to_current_position(monkeypatch):
    calls = []
    monkeypatch.setattr(pyautogui, "mouseUp", lambda **kw: calls.append(kw))
    mouse_extra.mouse_up()
    assert calls == [{"x": None, "y": None, "button": "left"}]


def test_bot_mouse_down_and_up_delegate(monkeypatch):
    down, up = [], []
    monkeypatch.setattr(pyautogui, "mouseDown", lambda **kw: down.append(kw))
    monkeypatch.setattr(pyautogui, "mouseUp", lambda **kw: up.append(kw))

    bot = _Bot()
    bot.mouse_down(5, 6)
    bot.mouse_up(button="middle")

    assert down == [{"x": 5, "y": 6, "button": "left"}]
    assert up == [{"x": None, "y": None, "button": "middle"}]


def test_press_then_release_pattern(monkeypatch):
    """mouse_down + mouse_up implement press-and-hold (not covered by drag)."""
    order = []
    monkeypatch.setattr(pyautogui, "mouseDown", lambda **kw: order.append(("down", kw)))
    monkeypatch.setattr(pyautogui, "mouseUp", lambda **kw: order.append(("up", kw)))

    bot = _Bot()
    bot.mouse_down(100, 200)
    # ... user could do other things between down and up ...
    bot.mouse_up(100, 200)

    assert [step for step, _ in order] == ["down", "up"]
    assert order[0][1]["x"] == 100 and order[1][1]["x"] == 100

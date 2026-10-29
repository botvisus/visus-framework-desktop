"""Tests for ``visus.desktop.core.mouse_extra``.

These tests monkeypatch ``pyautogui`` so they never move the real mouse,
scroll, or click.
"""

from __future__ import annotations

import pyautogui

from visus.desktop.core import mouse_extra


def _record_scroll(monkeypatch):
    calls = []
    monkeypatch.setattr(
        pyautogui,
        "scroll",
        lambda amount, x=None, y=None: calls.append((amount, x, y)),
    )
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: calls.append(("moveTo", *a)))
    return calls


def test_scroll_no_windows_conta_em_cliques_de_roda(monkeypatch):
    """No Windows o pyautogui repassa o numero cru como delta da roda, e um clique
    vale WHEEL_DELTA (120): ``scroll(3)`` rolava 3/120 de um clique, que os apps
    ignoram. ``amount`` e em cliques, como a doc sempre disse."""
    calls = _record_scroll(monkeypatch)
    monkeypatch.setattr(mouse_extra.sys, "platform", "win32")

    mouse_extra.scroll(10, x=100, y=200)
    mouse_extra.scroll(-5)

    assert calls == [("moveTo", 100, 200), (1200, 100, 200), (-600, None, None)]


def test_scroll_fora_do_windows_repassa(monkeypatch):
    """No macOS/Linux o pyautogui ja conta em cliques: o valor passa como veio."""
    calls = _record_scroll(monkeypatch)
    monkeypatch.setattr(mouse_extra.sys, "platform", "linux")

    mouse_extra.scroll(10, x=100, y=200)
    mouse_extra.scroll(-5)

    assert calls == [("moveTo", 100, 200), (10, 100, 200), (-5, None, None)]


def test_scroll_vai_ate_o_ponto_antes_de_rolar(monkeypatch):
    """Windows manda a roda para a janela SOB O CURSOR: com x/y, mover antes."""
    calls = _record_scroll(monkeypatch)
    mouse_extra.scroll(-2, x=10, y=20)
    assert calls[0] == ("moveTo", 10, 20)


def test_drag_moves_then_drags(monkeypatch):
    """``drag`` moves to the start, then drags to the end with the button."""
    move_calls = []
    drag_calls = []
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: move_calls.append((a, k)))
    monkeypatch.setattr(pyautogui, "dragTo", lambda *a, **k: drag_calls.append((a, k)))

    mouse_extra.drag(10, 20, 30, 40, duration=0.5, button="right")

    assert move_calls == [((10, 20), {})]
    assert drag_calls == [((30, 40, 0.5), {"button": "right"})]


def test_triple_click_uses_three_clicks(monkeypatch):
    """``triple_click`` calls ``pyautogui.click`` with ``clicks=3``."""
    calls = []
    monkeypatch.setattr(pyautogui, "click", lambda *a, **k: calls.append((a, k)))

    mouse_extra.triple_click(50, 60, interval=0.05)

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == (50, 60)
    assert kwargs == {"clicks": 3, "interval": 0.05}


def test_move_random_settles_on_exact_target(monkeypatch):
    """``move_random`` jitters first, then settles exactly on ``(x, y)``."""
    move_calls = []
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: move_calls.append((a, k)))
    # Force a deterministic jitter so we can assert on the first move.
    monkeypatch.setattr(mouse_extra.random, "randint", lambda lo, hi: 2)

    mouse_extra.move_random(100, 200, max_offset=3, duration=0.2)

    # First move is the jittered point (100+2, 200+2) with the duration.
    assert move_calls[0] == ((102, 202), {"duration": 0.2})
    # The final move settles exactly on the requested target.
    assert move_calls[-1][0] == (100, 200)


def test_move_random_jitter_within_max_offset(monkeypatch):
    """The jittered move stays within ``max_offset`` of the target."""
    move_calls = []
    monkeypatch.setattr(pyautogui, "moveTo", lambda *a, **k: move_calls.append((a, k)))

    mouse_extra.move_random(0, 0, max_offset=3)

    jitter_x, jitter_y = move_calls[0][0]
    assert -3 <= jitter_x <= 3
    assert -3 <= jitter_y <= 3
    assert move_calls[-1][0] == (0, 0)

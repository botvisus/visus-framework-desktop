"""The action highlight never piles up: a new one closes the previous at once.

A fast run (one click every ~0.14 s, each highlight living ``overlay_duration``
= 1 s) stacked ~7 red boxes on screen: they lingered after the bot moved on and
showed up on the next steps' report screenshots. The ACTION highlight now works
as "the newest replaces the previous"; numbered occurrence overlays
(``show_text_occurrences``) still coexist on purpose.
"""

from __future__ import annotations

import sys
import threading
import time
from unittest.mock import patch

import pytest

from visus.desktop.core import overlay_win32 as ow


@pytest.fixture(autouse=True)
def _no_leftover_slot():
    ow.clear_click_through_overlays()
    yield
    ow.clear_click_through_overlays()


def test_a_new_action_highlight_releases_the_previous_one() -> None:
    first = ow._claim_action_slot()
    second = ow._claim_action_slot()
    assert first.is_set()  # the old one is told to close now
    assert not second.is_set()  # the new one stays up


def test_clear_closes_the_current_action_highlight() -> None:
    current = ow._claim_action_slot()
    ow.clear_click_through_overlays()
    assert current.is_set()


def test_executor_highlight_replaces_the_previous_box() -> None:
    from visus.desktop.core.task_executor import TaskExecutor

    executor = TaskExecutor.__new__(TaskExecutor)  # no OCR / pyautogui setup needed
    executor.config = {"overlay_color": "blue", "overlay_width": 3, "overlay_duration": 900}
    with patch(
        "visus.desktop.core.task_executor.show_click_through_overlay", return_value=True
    ) as shown:
        executor._highlight((1, 2, 3, 4))
    shown.assert_called_once_with(
        (1, 2, 3, 4), color="blue", width=3, duration_ms=900, replace=True
    )


@pytest.mark.skipif(sys.platform != "win32", reason="real click-through windows: Windows only")
def test_real_overlay_is_torn_down_as_soon_as_it_is_replaced() -> None:
    def overlay_threads() -> list[threading.Thread]:
        return [t for t in threading.enumerate() if t.name == "VisusOverlay"]

    before = len(overlay_threads())
    # two highlights 50 ms apart, each asking for 3 s on screen (tiny box, top-left)
    assert ow.show_click_through_overlay((0, 0, 8, 8), duration_ms=3000, replace=True)
    time.sleep(0.05)
    assert ow.show_click_through_overlay((10, 0, 8, 8), duration_ms=3000, replace=True)
    deadline = time.monotonic() + 1.0
    while len(overlay_threads()) > before + 1 and time.monotonic() < deadline:
        time.sleep(0.01)
    # the first one is gone well before its 3 s: only the newest is up
    assert len(overlay_threads()) == before + 1
    ow.clear_click_through_overlays()
    deadline = time.monotonic() + 1.0
    while len(overlay_threads()) > before and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(overlay_threads()) == before


@pytest.mark.skipif(sys.platform != "win32", reason="real click-through windows: Windows only")
def test_numbered_overlays_still_coexist() -> None:
    def overlay_threads() -> list[threading.Thread]:
        return [t for t in threading.enumerate() if t.name == "VisusOverlay"]

    before = len(overlay_threads())
    for n in range(3):  # show_text_occurrences: 1, 2, 3 on screen together
        ow.show_click_through_overlay((n * 12, 0, 8, 8), duration_ms=400, label=str(n + 1))
    time.sleep(0.1)
    assert len(overlay_threads()) == before + 3


def test_every_recorded_step_clears_the_previous_highlight() -> None:
    """A step with no highlight of its own (a native_wait, a type) must not show the
    PREVIOUS click's box on its report screenshot -- the box goes when the bot moves on."""
    from types import SimpleNamespace

    from visus.desktop.core import recording

    bot = SimpleNamespace(
        executor=SimpleNamespace(last_action_location=None),
        _step_depth=0,
        stop_on_failure=False,
        _emit_direct_call_event=lambda *a, **k: None,
    )
    previous_click = ow._claim_action_slot()  # the box of the step before
    seen = {}

    def action() -> bool:
        seen["cleared_before_acting"] = previous_click.is_set()
        return True

    assert recording._run_recorded(bot, "native_wait", None, {}, action) is True
    assert seen["cleared_before_acting"] is True


def test_highlight_window_is_excluded_from_screen_captures(monkeypatch) -> None:
    """O destaque é para a pessoa: fora dos prints (busca de imagem/OCR e o print do passo)."""
    calls = []
    monkeypatch.setattr(
        ow, "user32", type("U", (), {"SetWindowDisplayAffinity": staticmethod(
            lambda hwnd, flag: calls.append((hwnd, flag)) or 1
        )})(),
        raising=False,  # fora do Windows o módulo não tem user32
    )
    assert ow._exclude_from_capture(1234) is True
    assert calls == [(1234, 0x11)]

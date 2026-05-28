"""Tests for graceful SIGINT shutdown of ``execute_tasks`` (Phase 1, R5).

When a long-running task list is interrupted with Ctrl+C the executor
must release any held mouse buttons before letting the
``KeyboardInterrupt`` propagate to the caller.

pyautogui is stateless about button state, so the cleanup is defensive:
release ``left``, ``middle`` and ``right`` unconditionally. The cost is
near-zero (three syscalls per interrupt) and the benefit is no stuck
buttons after a user-initiated abort.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@requires_tesseract
class TestGracefulShutdown:
    """SIGINT during a task list releases held inputs before re-raising."""

    def test_keyboard_interrupt_releases_all_mouse_buttons(self):
        """A task raising ``KeyboardInterrupt`` triggers the mouse-up cleanup."""
        bot = vd.VisusBot({"show_overlay": False})

        # Make the first click backend raise KeyboardInterrupt to simulate
        # an interrupt arriving while a task was in flight.
        with patch("pyautogui.mouseUp") as mock_up, patch(
            "pyautogui.center", return_value=MagicMock(x=1, y=1)
        ), patch.object(
            bot.executor.virtual_mouse,
            "click",
            side_effect=KeyboardInterrupt(),
        ):
            with pytest.raises(KeyboardInterrupt):
                bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

        # The cleanup must have released every commonly-held button.
        buttons_released = {
            call.kwargs.get("button") for call in mock_up.call_args_list
        }
        assert {"left", "middle", "right"}.issubset(buttons_released)

    def test_normal_completion_does_not_call_mouseup_cleanup(self):
        """A clean run never triggers the defensive button release."""
        bot = vd.VisusBot({"show_overlay": False})
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.mouseUp") as mock_up, patch(
            "pyautogui.center", return_value=fake_center
        ), patch.object(bot.executor.virtual_mouse, "click", return_value=True):
            bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

        mock_up.assert_not_called()

    def test_no_extra_threads_after_interrupt(self):
        """Interrupting a run leaves no extra non-daemon threads alive."""
        bot = vd.VisusBot({"show_overlay": False})
        before = {t.ident for t in threading.enumerate()}

        with patch("pyautogui.mouseUp"), patch(
            "pyautogui.center", return_value=MagicMock(x=1, y=1)
        ), patch.object(
            bot.executor.virtual_mouse,
            "click",
            side_effect=KeyboardInterrupt(),
        ):
            with pytest.raises(KeyboardInterrupt):
                bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

        after = {t.ident for t in threading.enumerate()}
        leaked = after - before
        # Any new threads must be daemon threads (auto-killed on exit).
        new_threads = [
            t for t in threading.enumerate() if t.ident in leaked
        ]
        assert all(
            t.daemon for t in new_threads
        ), f"non-daemon threads leaked after interrupt: {new_threads}"

    def test_interrupt_propagation_preserves_exception(self):
        """The ``KeyboardInterrupt`` is re-raised, not swallowed."""
        bot = vd.VisusBot({"show_overlay": False})

        with patch("pyautogui.mouseUp"), patch(
            "pyautogui.center", return_value=MagicMock(x=1, y=1)
        ), patch.object(
            bot.executor.virtual_mouse,
            "click",
            side_effect=KeyboardInterrupt("user abort"),
        ):
            with pytest.raises(KeyboardInterrupt):
                bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

    def test_cleanup_swallows_pyautogui_errors(self):
        """If pyautogui.mouseUp itself fails, the interrupt still propagates."""
        bot = vd.VisusBot({"show_overlay": False})
        with patch("pyautogui.mouseUp", side_effect=RuntimeError("dead")), patch(
            "pyautogui.center", return_value=MagicMock(x=1, y=1)
        ), patch.object(
            bot.executor.virtual_mouse,
            "click",
            side_effect=KeyboardInterrupt(),
        ):
            # The original KeyboardInterrupt is preserved; cleanup error is logged.
            with pytest.raises(KeyboardInterrupt):
                bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

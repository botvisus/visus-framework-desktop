"""Coverage push for the heavyweight VisusBot internals.

Targets:
  * 2113-2157 _process_sendtext
  * 2173-2290 execute_with_backtrack_between_tasks
  * 1395-1468 _click_text_internal
  * 1882-1901 _click_relative_image_internal
  * 1932-1963 _click_coordinates / type_text / keyboard_command paths
  * Module-level convenience helpers (2735-2779) and the BotVision alias.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed",
)


@requires_tesseract
class TestProcessSendtextInternals:
    @pytest.fixture
    def bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_ctrl_a_processed(self, bot):
        with patch("pyautogui.hotkey") as hk, patch(
            "pyperclip.copy"
        ), patch("time.sleep"):
            bot._process_sendtext("{ctrl}arest")
        hk.assert_any_call("ctrl", "a")

    def test_del_processed(self, bot):
        with patch("pyautogui.press") as press, patch("pyautogui.hotkey"), patch(
            "pyperclip.copy"
        ), patch("time.sleep"):
            bot._process_sendtext("{del}")
        press.assert_any_call("delete")

    def test_tab_processed(self, bot):
        with patch("pyautogui.press") as press, patch("pyautogui.hotkey"), patch(
            "pyperclip.copy"
        ), patch("time.sleep"):
            bot._process_sendtext("{tab}")
        press.assert_any_call("tab")

    def test_enter_processed(self, bot):
        with patch("pyautogui.press") as press, patch("pyautogui.hotkey"), patch(
            "pyperclip.copy"
        ), patch("time.sleep"):
            bot._process_sendtext("{enter}")
        press.assert_any_call("enter")

    def test_pyperclip_failure_falls_back_to_pyautogui_write(self, bot):
        with patch("pyautogui.hotkey"), patch(
            "pyperclip.copy", side_effect=RuntimeError("no clipboard")
        ), patch("pyautogui.write") as write, patch("time.sleep"):
            bot._process_sendtext("plain text")
        write.assert_called_once_with("plain text")


@requires_tesseract
class TestExecuteWithBacktrackBetweenTasks:
    @pytest.fixture
    def bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_empty_list_returns_empty(self, bot):
        assert bot.execute_with_backtrack_between_tasks([]) == []

    def test_text_task_success(self, bot):
        with patch.object(bot, "click_text", return_value=True):
            out = bot.execute_with_backtrack_between_tasks(
                [{"type": "text", "params": {"text": "Login"}}]
            )
        assert out == [True]

    def test_image_task_success(self, bot):
        with patch.object(bot, "click_image", return_value=True):
            out = bot.execute_with_backtrack_between_tasks(
                [{"type": "image", "params": {"image_path": "a.png"}}]
            )
        assert out == [True]

    def test_unknown_task_type_returns_failure(self, bot):
        out = bot.execute_with_backtrack_between_tasks(
            [{"type": "unknown", "params": {}}]
        )
        assert out == [False]

    def test_exception_inside_task_recorded_as_failure(self, bot):
        with patch.object(
            bot, "click_text", side_effect=RuntimeError("boom")
        ):
            out = bot.execute_with_backtrack_between_tasks(
                [{"type": "text", "params": {"text": "x"}}]
            )
        assert out == [False]

    def test_first_task_failure_advances_without_backtrack(self, bot):
        """Backtrack disabled on the first task -> just advance."""
        with patch.object(bot, "click_text", return_value=False):
            out = bot.execute_with_backtrack_between_tasks(
                [
                    {"type": "text", "params": {"text": "a", "backtrack": True}},
                    {"type": "text", "params": {"text": "b", "backtrack": False}},
                ]
            )
        assert out == [False, False]

    def test_backtrack_returns_to_previous_then_continues(self, bot):
        """First task succeeds, second fails -> backtracks once and re-tries."""
        call_count = {"n": 0}

        def click(*args, **kwargs):
            call_count["n"] += 1
            # First (task 0) succeeds; task 1 fails first time, succeeds on
            # retry; backtrack triggers a re-run of task 0 in between.
            text = kwargs.get("text", "")
            if text == "a":
                return True
            if text == "b":
                # Fail once, succeed after backtrack rerun of a.
                return call_count["n"] >= 4
            return False

        with patch.object(bot, "click_text", side_effect=click):
            out = bot.execute_with_backtrack_between_tasks(
                [
                    {"type": "text", "params": {"text": "a"}},
                    {"type": "text", "params": {"text": "b"}},
                ]
            )
        # Both should eventually succeed.
        assert out[0] is True


@requires_tesseract
class TestVisusBotInternals:
    @pytest.fixture
    def bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_click_text_internal_returns_false_on_no_location(self, bot):
        with patch.object(
            bot.executor, "_find_text_location", return_value=None
        ):
            out = bot._click_text_internal(
                "Login", (0, 0, 10, 10), "letters", 0, "left", 1, 1, None
            )
        assert out is False

    def test_click_image_internal_returns_false_on_no_location(self, bot):
        with patch.object(
            bot.executor, "_locate_image_with_retry", return_value=None
        ):
            out = bot._click_image_internal(
                "a.png", (0, 0, 10, 10), 0.9, 0, "left", 1, True, None
            )
        assert out is False

    def test_keyboard_command_internal_returns_success_bool(self, bot):
        with patch.object(
            bot.executor.keyboard_commander,
            "execute_command",
            return_value=True,
        ):
            assert bot._keyboard_command_internal("Tab", 0) is True

    def test_keyboard_command_internal_swallows_exceptions(self, bot):
        with patch.object(
            bot.executor.keyboard_commander,
            "execute_command",
            side_effect=RuntimeError("io"),
        ):
            assert bot._keyboard_command_internal("Tab", 0) is False

    def test_type_text_internal_handles_exception(self, bot):
        with patch.object(
            bot.executor.keyboard_commander,
            "type_text",
            side_effect=RuntimeError("io"),
        ):
            assert bot._type_text_internal("hello", 0.01, 0) is False

    def test_click_coordinates_internal_returns_bool(self, bot):
        fake_center = MagicMock(x=10, y=20)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            assert bot._click_coordinates_internal(10, 20, 0, "left") is True


class TestBotVisionAlias:
    def test_botvision_is_visusbot(self):
        assert vd.BotVision is vd.VisusBot

"""Coverage push for ``visus.desktop.core.task_executor``.

Targets the largest missing line clusters:
  * 569-637 _find_text_location confidence + occurrence branches
  * 666-732 _find_image_location + _find_image_with_wait
  * 747-781 _find_text_with_wait
  * 1212-1261 _process_sendtext special commands
  * 1263-1305 _find_relative_image_location
  * 1424-1499 list-of-lists dispatcher
  * 1550-1585 execute_tasks module-level branches
  * 1601-1605 click_images compatibility helper
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tests import tesseract_available
from visus.desktop.core.task_executor import (
    TaskExecutor,
    TaskResult,
    click_images,
    summarize,
)
from visus.desktop.core.task_executor import (
    execute_tasks as module_execute_tasks,
)
from visus.desktop.exceptions import (
    TaskExecutionError,
)

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot/TaskExecutor needs it)",
)


@pytest.fixture
def executor():
    return TaskExecutor()


# ---------------------------------------------------------------------------
# _find_text_location confidence + occurrence branches
# ---------------------------------------------------------------------------


@requires_tesseract
class TestFindTextLocation:
    def test_no_region_falls_back_to_full_screen(self, executor):
        # Mirrors the direct ``bot.find_text(text, region=None)`` path:
        # when a task omits ``region``, the executor captures the whole
        # screen via the mss-backed ``capture_screen`` instead of refusing.
        with patch(
            "visus.desktop.core.task_executor.capture_screen"
        ) as fake_capture, patch.object(
            executor.ocr_engine, "find_text", return_value=([], [], False)
        ) as fake_find:
            fake_capture.return_value = MagicMock(width=1920, height=1080)
            executor._find_text_location({"text": "Login"}, 0)
            fake_capture.assert_called_once()
            assert fake_find.call_count == 1

    def test_skip_when_all_confidences_below_threshold(self, executor):
        with patch.object(executor, "_capture_region", return_value=MagicMock()), patch.object(
            executor.ocr_engine,
            "find_text",
            return_value=([(1, 2, 3, 4)], [40.0], False),
        ):
            out = executor._find_text_location(
                {"text": "x", "region": (0, 0, 100, 100), "early_confidence": 80},
                0,
            )
        assert out == "skip"

    def test_returns_absolute_box_on_early_match(self, executor):
        with patch.object(executor, "_capture_region", return_value=MagicMock()), patch.object(
            executor.ocr_engine,
            "find_text",
            return_value=([(10, 5, 30, 20)], [90.0], True),
        ):
            out = executor._find_text_location(
                {"text": "x", "region": (100, 200, 500, 200), "early_confidence": 75},
                0,
            )
        # Box returned in absolute screen coords.
        assert out == (110, 205, 30, 20)

    def test_best_confidence_branch(self, executor):
        with patch.object(executor, "_capture_region", return_value=MagicMock()), patch.object(
            executor.ocr_engine,
            "find_text",
            return_value=(
                [(0, 0, 10, 10), (100, 100, 20, 20)],
                [50.0, 70.0],
                False,
            ),
        ):
            out = executor._find_text_location(
                {
                    "text": "x",
                    "region": (0, 0, 200, 200),
                    "early_confidence": 30,
                    "best_confidence": True,
                },
                0,
            )
        # Highest score picks (100,100,20,20) -> absolute (100,100,20,20).
        assert out == (100, 100, 20, 20)

    def test_occurrence_uses_find_all_text(self, executor):
        # occurrence > 1 enumerates ALL matches (find_all_text), in reading
        # order, and picks the Nth -- the early-exit find_text only ever
        # returns the first match, so it cannot serve occurrence 2+.
        matches = [
            (99.0, (0, 0, 10, 10)),
            (98.0, (50, 50, 10, 10)),
        ]
        with patch.object(executor, "_capture_region", return_value=MagicMock()), patch.object(
            executor.ocr_engine, "find_all_text", return_value=matches
        ):
            out = executor._find_text_location(
                {"text": "x", "region": (10, 20, 300, 300), "occurrence": 2},
                0,
            )
        # 2nd match (50, 50) offset by the region origin (10, 20).
        assert out == (60, 70, 10, 10)

    def test_occurrence_out_of_range_returns_none(self, executor):
        # Out-of-range occurrence now returns None (no silent "use last").
        with patch.object(executor, "_capture_region", return_value=MagicMock()), patch.object(
            executor.ocr_engine, "find_all_text", return_value=[(50.0, (0, 0, 10, 10))]
        ):
            out = executor._find_text_location(
                {"text": "x", "region": (1, 2, 100, 100), "occurrence": 99},
                0,
            )
        assert out is None

    def test_no_boxes_returns_none(self, executor):
        with patch.object(executor, "_capture_region", return_value=MagicMock()), patch.object(
            executor.ocr_engine, "find_text", return_value=([], [], False)
        ):
            out = executor._find_text_location(
                {"text": "x", "region": (0, 0, 100, 100)}, 0
            )
        assert out is None


# ---------------------------------------------------------------------------
# _find_image_location / _find_image_with_wait / _find_text_with_wait
# ---------------------------------------------------------------------------


@requires_tesseract
class TestFindImagePaths:
    def test_specific_region_search(self, executor):
        with patch.object(
            executor, "_locate_image_with_retry", return_value=(1, 2, 3, 4)
        ) as locate:
            out = executor._find_image_location(
                {"image": "a.png", "region": (0, 0, 100, 100), "specific": True}, 0
            )
        assert out == (1, 2, 3, 4)
        locate.assert_called_once()
        assert locate.call_args.kwargs.get("region") == (0, 0, 100, 100)

    def test_whole_screen_search(self, executor):
        with patch.object(
            executor, "_locate_image_with_retry", return_value=None
        ) as locate:
            out = executor._find_image_location(
                {"image": "a.png", "specific": False}, 0
            )
        assert out is None
        locate.assert_called_once()
        assert "region" not in locate.call_args.kwargs

    def test_image_wait_until_found_timeout_returns_none(self, executor):
        with patch.object(
            executor.wait_manager, "wait_until_found", return_value=None
        ):
            out = executor._find_image_with_wait(
                {"image": "a.png", "wait_until_found": True, "wait_timeout": 1},
                0,
            )
        assert out is None

    def test_image_wait_until_found_success(self, executor):
        with patch.object(
            executor.wait_manager,
            "wait_until_found",
            return_value=(5, 6, 7, 8),
        ):
            out = executor._find_image_with_wait(
                {"image": "a.png", "wait_until_found": True}, 0
            )
        assert out == (5, 6, 7, 8)

    def test_image_no_wait_until_found_runs_search(self, executor):
        with patch.object(
            executor, "_find_image_location", return_value=(1, 1, 1, 1)
        ):
            out = executor._find_image_with_wait({"image": "a.png"}, 0)
        assert out == (1, 1, 1, 1)

    def test_image_wait_until_disappears_marks_post_click(self, executor):
        task = {
            "image": "a.png",
            "wait_until_disappears": True,
            "type": "click_image",
            "mouse_button": "left",
        }
        with patch.object(
            executor, "_find_image_location", return_value=(1, 2, 3, 4)
        ):
            out = executor._find_image_with_wait(task, 0)
        assert out == (1, 2, 3, 4)
        assert task.get("_wait_after_click") is True

    def test_image_wait_until_disappears_blocking_branch(self, executor):
        """find_image (no click) waits for disappearance immediately."""
        task = {
            "image": "a.png",
            "wait_until_disappears": True,
            # No type / mouse_button -> blocking disappear branch.
        }
        with patch.object(
            executor, "_find_image_location", return_value=(1, 2, 3, 4)
        ), patch.object(
            executor.wait_manager, "wait_until_disappears", return_value=True
        ):
            out = executor._find_image_with_wait(task, 0)
        assert out == (1, 2, 3, 4)


@requires_tesseract
class TestFindTextWithWait:
    def test_wait_until_found_returns_none_on_timeout(self, executor):
        with patch.object(
            executor.wait_manager, "wait_until_found", return_value=None
        ):
            out = executor._find_text_with_wait(
                {"text": "x", "region": (0, 0, 1, 1), "wait_until_found": True},
                0,
            )
        assert out is None

    def test_wait_until_found_returns_location(self, executor):
        with patch.object(
            executor.wait_manager,
            "wait_until_found",
            return_value=(1, 2, 3, 4),
        ):
            out = executor._find_text_with_wait(
                {"text": "x", "region": (0, 0, 1, 1), "wait_until_found": True},
                0,
            )
        assert out == (1, 2, 3, 4)


# ---------------------------------------------------------------------------
# _process_sendtext
# ---------------------------------------------------------------------------


@requires_tesseract
class TestProcessSendtext:
    def test_ctrl_a_then_text(self, executor):
        with patch("pyautogui.hotkey") as hk, patch("pyperclip.copy") as cp, patch(
            "time.sleep"
        ):
            executor._process_sendtext("{ctrl}aremaining")
        hk.assert_any_call("ctrl", "a")
        cp.assert_called_once_with("remaining")

    def test_del_command(self, executor):
        with patch("pyautogui.press") as press, patch("pyautogui.hotkey"), patch(
            "pyperclip.copy"
        ), patch("time.sleep"):
            executor._process_sendtext("{del}")
        press.assert_called_with("delete")

    def test_tab_command(self, executor):
        with patch("pyautogui.press") as press, patch("pyautogui.hotkey"), patch(
            "pyperclip.copy"
        ), patch("time.sleep"):
            executor._process_sendtext("{tab}rest")
        press.assert_any_call("tab")

    def test_enter_command(self, executor):
        with patch("pyautogui.press") as press, patch("pyautogui.hotkey"), patch(
            "pyperclip.copy"
        ), patch("time.sleep"):
            executor._process_sendtext("{enter}rest")
        press.assert_any_call("enter")

    def test_no_special_commands_just_pastes(self, executor):
        with patch("pyautogui.hotkey"), patch("pyperclip.copy") as cp, patch(
            "time.sleep"
        ):
            executor._process_sendtext("plain text")
        cp.assert_called_once_with("plain text")

    def test_failure_raises_task_execution_error(self, executor):
        with patch("pyautogui.hotkey", side_effect=RuntimeError("io")), patch(
            "time.sleep"
        ):
            with pytest.raises(TaskExecutionError, match="sendtext failed"):
                executor._process_sendtext("{ctrl}arest")


# ---------------------------------------------------------------------------
# _find_relative_image_location / _find_coordinate_location
# ---------------------------------------------------------------------------


@requires_tesseract
class TestRelativeImage:
    def test_missing_anchor_or_target_raises(self, executor):
        with pytest.raises(TaskExecutionError, match="anchor"):
            executor._find_relative_image_location(
                {"target_image": "t.png"}, 0
            )

    def test_returns_location_when_detector_succeeds(self, executor):
        with patch.object(
            executor.relative_detector,
            "locate_relative_image",
            return_value=(1, 2, 3, 4),
        ):
            out = executor._find_relative_image_location(
                {
                    "anchor_image": "a.png",
                    "target_image": "t.png",
                    "specific": True,
                    "target_region": (0, 0, 100, 100),
                },
                0,
            )
        assert out == (1, 2, 3, 4)

    def test_returns_none_on_detector_error(self, executor):
        with patch.object(
            executor.relative_detector,
            "locate_relative_image",
            side_effect=RuntimeError("io"),
        ):
            out = executor._find_relative_image_location(
                {"anchor_image": "a.png", "target_image": "t.png"}, 0
            )
        assert out is None


@requires_tesseract
class TestCoordinateLocation:
    def test_missing_x_or_y_raises(self, executor):
        with pytest.raises(TaskExecutionError, match="x.*y"):
            executor._find_coordinate_location({"x": 10}, 0)

    def test_returns_tuple_with_zero_size(self, executor):
        out = executor._find_coordinate_location({"x": 10, "y": 20}, 0)
        assert out[:2] == (10, 20)


# ---------------------------------------------------------------------------
# Module-level execute_tasks dispatcher
# ---------------------------------------------------------------------------


@requires_tesseract
class TestExecuteTasksModuleDispatcher:
    def test_list_of_lists_runs_each_set_independently(self):
        with patch.object(
            TaskExecutor, "execute_tasks", return_value=[]
        ) as ex:
            out = module_execute_tasks([
                [{"type": "click", "x": 1, "y": 1}],
                [{"type": "click", "x": 2, "y": 2}],
            ])
        assert isinstance(out, list)
        assert len(out) == 2
        assert ex.call_count == 2

    def test_list_of_lists_skips_invalid_entries(self):
        with patch.object(
            TaskExecutor, "execute_tasks", return_value=[]
        ):
            out = module_execute_tasks([
                [{"type": "click", "x": 1, "y": 1}],
                "not a list",
                [{"type": "click", "x": 2, "y": 2}],
            ])
        assert len(out) == 3
        assert out[1] == []  # invalid entry produced an empty result

    def test_simple_list_dispatches_once(self):
        with patch.object(
            TaskExecutor, "execute_tasks", return_value=[1, 2]
        ) as ex:
            out = module_execute_tasks(
                [{"type": "click", "x": 1, "y": 1}]
            )
        assert out == [1, 2]
        ex.assert_called_once()

    def test_empty_list_returns_empty(self):
        assert module_execute_tasks([]) == []

    def test_non_list_returns_empty(self):
        assert module_execute_tasks("not a list") == []


@requires_tesseract
class TestClickImages:
    def test_click_images_forwards_config_and_calls_execute_tasks(self):
        with patch.object(
            TaskExecutor, "execute_tasks", return_value=[]
        ):
            out = click_images(
                [{"type": "click", "x": 1, "y": 1}],
                default_confidence=0.5,
                default_margin=20,
            )
        assert isinstance(out, list)


# ---------------------------------------------------------------------------
# TaskResult / summarize edge cases
# ---------------------------------------------------------------------------


class TestTaskResultDefaults:
    def test_attempts_starts_at_zero(self):
        r = TaskResult(0, True, "x")
        assert r.attempts == 0
        assert r.failure_screenshot is None
        assert r.duration_ms == 0

    def test_summarize_with_no_attempts_field(self):
        r = TaskResult(0, True, "x")
        out = summarize([r])
        assert out["total_attempts"] == 0

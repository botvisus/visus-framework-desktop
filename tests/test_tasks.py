"""
Tests for task execution and individual backtrack sessions in ``visus.desktop``.

Two feature areas are covered:

* ``execute_tasks`` -- both the ``VisusBot.execute_tasks`` method and the
  module-level ``visus.desktop.execute_tasks`` helper. We verify empty input
  returns early, that mixed task dicts dispatch to the right per-action backend,
  that a list of results comes back, and that list-of-lists input runs as
  sequential sets.
* Backtrack sessions -- ``start_task_session`` / ``end_task_session`` counters,
  ``backtrack=True`` between individual methods, and the auto-start behaviour
  when ``backtrack=True`` is used without an explicit session.

Every test that builds a ``VisusBot`` is guarded with the Tesseract skip marker
(the config constructor requires Tesseract). All real screen / mouse / OCR
effects are mocked: we patch the executor's locate/find methods, the virtual
mouse, and ``_perform_action`` so nothing physical happens.
"""

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@pytest.fixture
def bot():
    """A VisusBot with the overlay disabled (no Tk window) for each test."""
    return vd.VisusBot({"show_overlay": False})


@pytest.fixture
def no_perform_action(bot):
    """Patch the executor's _perform_action so no real click/typing happens.

    Returns the MagicMock standing in for ``_perform_action`` so tests can
    assert on the task dict / location it received.
    """
    with patch.object(bot.executor, "_perform_action") as mock_action:
        yield mock_action


# ---------------------------------------------------------------------------
# execute_tasks -- empty / invalid input
# ---------------------------------------------------------------------------


class TestExecuteTasksEmpty:
    """Empty or invalid input short-circuits without touching the screen."""

    def test_module_level_empty_list(self):
        assert vd.execute_tasks([]) == []

    def test_module_level_non_list(self):
        assert vd.execute_tasks("not a list") == []

    @requires_tesseract
    def test_method_empty_list(self, bot):
        assert bot.execute_tasks([]) == []

    @requires_tesseract
    def test_executor_empty_list_directly(self, bot):
        # The TaskExecutor returns [] for empty input as well.
        assert bot.executor.execute_tasks([]) == []


# ---------------------------------------------------------------------------
# execute_tasks -- dispatch by task type
# ---------------------------------------------------------------------------


@requires_tesseract
class TestExecuteTasksDispatch:
    """A list of mixed task dicts dispatches by key and returns results."""

    def test_returns_list_of_results(self, bot, no_perform_action):
        # Two coordinate clicks: deterministic, no screen lookup required.
        tasks = [
            {"type": "click", "x": 10, "y": 20},
            {"type": "click", "x": 30, "y": 40},
        ]
        results = bot.execute_tasks(tasks)
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_click_task_drives_click_backend(self, bot):
        """A 'click' task resolves coordinates and drives the click backend."""
        fake_center = MagicMock()
        fake_center.x = 100
        fake_center.y = 200
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ) as mock_click:
            results = bot.execute_tasks(
                [{"type": "click", "x": 100, "y": 200, "mouse_button": "left"}]
            )
        assert len(results) == 1
        assert results[0].success is True
        mock_click.assert_called()
        _, kwargs = mock_click.call_args
        assert kwargs["x"] == 100
        assert kwargs["y"] == 200

    def test_type_text_dispatch_via_executor_helper(self, bot):
        """``_execute_type_text`` delegates to keyboard_commander.type_text and skips click."""
        with patch.object(
            bot.executor.keyboard_commander, "type_text"
        ) as mock_type:
            outcome = bot.executor._execute_type_text(
                {"type": "type_text", "text": "hello", "interval": 0.01}, 0
            )
        # "skip" tells execute_tasks no click is needed.
        assert outcome == "skip"
        mock_type.assert_called_once_with("hello", 0.01)

    def test_type_text_task_routes_to_typing(self, bot, no_perform_action):
        """A {'type': 'type_text', 'text': ...} task types via the keyboard backend.

        Explicit action types take precedence over the 'text' heuristic, so the
        task reaches ``_execute_type_text`` (keyboard typing) instead of being
        intercepted by the OCR branch.
        """
        with patch.object(
            bot.executor.keyboard_commander, "type_text"
        ) as mock_type:
            results = bot.execute_tasks(
                [{"type": "type_text", "text": "hello", "interval": 0.01}]
            )
        mock_type.assert_called_once_with("hello", 0.01)
        assert results[0].success is True

    def test_keyboard_command_task_dispatches(self, bot):
        """A 'keyboard_command' task routes to keyboard_commander.execute_command."""
        with patch.object(
            bot.executor.keyboard_commander, "execute_command", return_value=True
        ) as mock_cmd, patch.object(bot.executor, "_perform_action") as mock_action:
            results = bot.execute_tasks(
                [{"type": "keyboard_command", "command": "Ctrl+S"}]
            )
        assert len(results) == 1
        assert results[0].success is True
        mock_cmd.assert_called_once_with("Ctrl+S")
        mock_action.assert_not_called()

    def test_image_task_dispatches_to_locate(self, bot, no_perform_action):
        """An image task routes to _locate_image_with_retry and clicks on success."""
        with patch.object(
            bot.executor,
            "_locate_image_with_retry",
            return_value=(1, 2, 3, 4),
        ) as mock_locate:
            results = bot.execute_tasks(
                [{"image": "button.png", "region": (0, 0, 50, 50), "specific": True}]
            )
        assert results[0].success is True
        mock_locate.assert_called()
        no_perform_action.assert_called_once()

    def test_text_task_dispatches_to_find_text_location(self, bot, no_perform_action):
        """A text task routes through _find_text_location (which we stub)."""
        with patch.object(
            bot.executor, "_find_text_location", return_value=(5, 6, 7, 8)
        ) as mock_find:
            results = bot.execute_tasks(
                [{"text": "Login", "region": (0, 0, 100, 100)}]
            )
        assert results[0].success is True
        mock_find.assert_called()
        no_perform_action.assert_called_once()

    def test_mixed_task_list_dispatches_each_type(self, bot, no_perform_action):
        """A mixed list hits the appropriate backend for each entry.

        Covers the type-keyed dispatch (click, keyboard_command) and an image
        task; each is routed to a distinct, separately mocked backend.
        """
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ), patch.object(
            bot.executor.keyboard_commander, "execute_command", return_value=True
        ) as mock_cmd, patch.object(
            bot.executor, "_locate_image_with_retry", return_value=(1, 2, 3, 4)
        ) as mock_locate:
            tasks = [
                {"type": "click", "x": 1, "y": 1},
                {"type": "keyboard_command", "command": "Ctrl+S"},
                {"image": "b.png", "region": (0, 0, 5, 5)},
            ]
            results = bot.execute_tasks(tasks)
        assert [r.success for r in results] == [True, True, True]
        mock_cmd.assert_called_once_with("Ctrl+S")
        mock_locate.assert_called()

    def test_unknown_task_is_handled_as_failure(self, bot, no_perform_action):
        """A task without text/image/valid type is reported as failed, not raised."""
        results = bot.execute_tasks([{"foo": "bar"}])
        assert len(results) == 1
        assert results[0].success is False
        no_perform_action.assert_not_called()

    def test_empty_task_dict_is_handled_as_failure(self, bot, no_perform_action):
        results = bot.execute_tasks([{}])
        assert len(results) == 1
        assert results[0].success is False

    def test_failing_task_reflected_in_results(self, bot, no_perform_action):
        """An image task whose locate always returns None ends up unsuccessful."""
        with patch.object(
            bot.executor, "_locate_image_with_retry", return_value=None
        ):
            results = bot.execute_tasks(
                [{"image": "missing.png", "region": (0, 0, 10, 10)}]
            )
        assert len(results) == 1
        assert results[0].success is False
        no_perform_action.assert_not_called()

    def test_mixed_success_and_failure_results(self, bot, no_perform_action):
        """A successful click followed by an unknown task yields [True, False]."""
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            results = bot.execute_tasks(
                [{"type": "click", "x": 1, "y": 1}, {"nonsense": True}]
            )
        assert [r.success for r in results] == [True, False]

    def test_list_of_lists_runs_sequentially(self):
        """List-of-lists input returns a list per set (module-level helper)."""
        task_sets = [
            [{"type": "click", "x": 1, "y": 1}],
            [{"type": "click", "x": 2, "y": 2}],
        ]
        # Patch _perform_action on every TaskExecutor instance the helper builds,
        # plus the click backend, so no real mouse action occurs.
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch(
            "visus.desktop.core.task_executor.TaskExecutor._perform_action"
        ), patch(
            "visus.desktop.core.virtual_mouse.VirtualMouse.click", return_value=True
        ):
            all_results = vd.execute_tasks(task_sets)
        assert isinstance(all_results, list)
        assert len(all_results) == 2
        assert all(isinstance(sub, list) for sub in all_results)
        assert all(len(sub) == 1 for sub in all_results)


# ---------------------------------------------------------------------------
# Backtrack sessions
# ---------------------------------------------------------------------------


@requires_tesseract
class TestBacktrackSessions:
    """start_task_session / end_task_session and backtrack between methods."""

    def test_start_session_sets_active_and_resets_history(self, bot):
        bot.individual_task_history = [{"stale": True}]
        bot.start_task_session()
        assert bot.task_session_active is True
        assert bot.individual_task_history == []
        assert bot.current_task_index == -1

    def test_end_session_returns_zero_when_empty(self, bot):
        bot.start_task_session()
        successful, total = bot.end_task_session()
        assert (successful, total) == (0, 0)
        assert bot.task_session_active is False

    def test_end_session_counts_successful_and_total(self, bot):
        """Two backtrack methods, both succeeding -> (2, 2)."""
        bot.start_task_session()
        with patch.object(
            bot, "_click_image_internal", return_value=True
        ), patch.object(bot, "_click_text_internal", return_value=True):
            assert bot.click_image("a.png", backtrack=True) is True
            assert bot.click_text("Save", backtrack=True) is True
        successful, total = bot.end_task_session()
        assert total == 2
        assert successful == 2

    def test_session_records_failures(self, bot):
        """First method succeeds, second fails (and is the only retryable one)."""
        bot.start_task_session()
        with patch.object(
            bot, "_click_image_internal", return_value=True
        ), patch.object(bot, "_click_text_internal", return_value=False):
            bot.click_image("a.png", backtrack=True)
            bot.click_text("Save", backtrack=True)
        successful, total = bot.end_task_session()
        assert total == 2
        assert successful == 1

    def test_backtrack_without_session_auto_starts_one(self, bot):
        """Using backtrack=True without start_task_session auto-starts a session."""
        assert bot.task_session_active is False
        with patch.object(bot, "_click_image_internal", return_value=True):
            result = bot.click_image("a.png", backtrack=True)
        assert result is True
        # The auto-start path flips the session flag on.
        assert bot.task_session_active is True

    def test_first_task_failure_has_no_backtrack(self, bot):
        """The very first task in a session cannot backtrack; it just fails."""
        bot.start_task_session()
        internal = MagicMock(return_value=False)
        with patch.object(bot, "_click_text_internal", internal):
            result = bot.click_text("First", backtrack=True)
        assert result is False
        # Only the single forward attempt happened (no previous task to retry).
        assert internal.call_count == 1
        assert bot.individual_task_history[0]["success"] is False

    def test_backtrack_reruns_previous_then_retries(self, bot):
        """A failed second task re-runs the previous task, then retries itself.

        The second method fails on the first forward attempt and succeeds on the
        retry that follows the backtrack of the previous (image) task.
        """
        bot.start_task_session()
        # The previous task (image) always re-runs successfully.
        with patch.object(
            bot, "_click_image_internal", return_value=True
        ) as img_internal, patch.object(
            bot, "_click_text_internal", side_effect=[False, True]
        ) as txt_internal, patch(
            "time.sleep"
        ):
            bot.click_image("a.png", backtrack=True)  # task 0
            result = bot.click_text("Save", backtrack=True)  # task 1
        assert result is True
        # text method: 1 forward attempt + 1 retry after backtrack.
        assert txt_internal.call_count == 2
        # image method: 1 forward attempt + 1 re-run during backtrack.
        assert img_internal.call_count == 2

    def test_backtrack_gives_up_after_max_attempts(self, bot):
        """If the failing task never recovers, backtrack stops after the limit."""
        bot.start_task_session()
        with patch.object(
            bot, "_click_image_internal", return_value=True
        ), patch.object(
            bot, "_click_text_internal", return_value=False
        ) as txt_internal, patch("time.sleep"):
            bot.click_image("a.png", backtrack=True)
            result = bot.click_text("Save", backtrack=True)
        assert result is False
        # max_backtrack_attempts defaults to 2: 1 forward + at most 1 retry.
        assert txt_internal.call_count <= bot.max_backtrack_attempts + 1
        assert bot.individual_task_history[1]["success"] is False

    def test_backtrack_false_executes_internal_directly(self, bot):
        """With backtrack=False the internal method runs without history tracking."""
        with patch.object(
            bot, "_click_image_internal", return_value=True
        ) as internal:
            result = bot.click_image("a.png", backtrack=False)
        assert result is True
        internal.assert_called_once()
        # No session was started and nothing was recorded.
        assert bot.task_session_active is False
        assert bot.individual_task_history == []

    def test_keyboard_command_backtrack_records_in_session(self, bot):
        """keyboard_command with backtrack=True participates in the session."""
        bot.start_task_session()
        with patch.object(bot, "_keyboard_command_internal", return_value=True):
            assert bot.keyboard_command("Ctrl+S", backtrack=True) is True
        successful, total = bot.end_task_session()
        assert (successful, total) == (1, 1)

    def test_type_text_backtrack_records_in_session(self, bot):
        """type_text with backtrack=True participates in the session."""
        bot.start_task_session()
        with patch.object(bot, "_type_text_internal", return_value=True):
            assert bot.type_text("hello", backtrack=True) is True
        successful, total = bot.end_task_session()
        assert (successful, total) == (1, 1)

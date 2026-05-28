"""Tests for pluggable error sinks (Phase 2, O6).

Set ``config['on_error']`` to a callable that the executor invokes for
every failed task. Sinks are typically Sentry / Datadog / OpenTelemetry
adapters; the contract is just ``callable(TaskResult) -> None``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@requires_tesseract
class TestErrorSinks:
    """``on_error`` fires on failed tasks only and never breaks the run."""

    def test_failing_task_invokes_hook_with_result(self):
        seen: list = []
        bot = vd.VisusBot({"show_overlay": False, "on_error": seen.append})
        bot.execute_tasks([{"foo": "bar"}])
        assert len(seen) == 1
        assert seen[0].success is False
        assert seen[0].task_index == 0

    def test_successful_task_does_not_invoke_hook(self):
        seen: list = []
        bot = vd.VisusBot({"show_overlay": False, "on_error": seen.append})
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])
        assert seen == []

    def test_hook_raising_does_not_mask_results(self):
        """A buggy sink must not corrupt the returned results."""

        def buggy(_result):
            raise RuntimeError("sentry sdk exploded")

        bot = vd.VisusBot({"show_overlay": False, "on_error": buggy})
        results = bot.execute_tasks([{"foo": "bar"}])
        assert len(results) == 1
        assert results[0].success is False

    def test_no_hook_configured_is_a_noop(self):
        bot = vd.VisusBot({"show_overlay": False})  # no on_error
        results = bot.execute_tasks([{"foo": "bar"}])
        assert results[0].success is False  # plain failure, no crash

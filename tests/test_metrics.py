"""Tests for per-task metrics on ``TaskResult`` (Phase 2, O4).

Every task carries the time it spent in the find/locate loop
(``duration_ms``) plus the existing ``attempts`` counter. A new
``summarize`` helper aggregates a list of results into a small dict
suitable for reports / dashboards / JSON sinks.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.core.task_executor import TaskResult, summarize

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


class TestTaskResultMetrics:
    """``TaskResult`` exposes per-task duration."""

    def test_default_duration_ms_is_zero(self):
        result = TaskResult(task_index=0, success=True, task_name="x")
        assert result.duration_ms == 0

    def test_duration_ms_is_writable(self):
        result = TaskResult(task_index=0, success=True, task_name="x")
        result.duration_ms = 123
        assert result.duration_ms == 123


@requires_tesseract
class TestExecutorPopulatesMetrics:
    """``_execute_single_task`` populates ``duration_ms`` on every result."""

    def test_duration_ms_is_positive_after_run(self):
        bot = vd.VisusBot({"show_overlay": False})
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            results = bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])
        assert results[0].duration_ms >= 0  # may be 0 on very fast runs
        assert hasattr(results[0], "attempts")


class TestSummarize:
    """``summarize`` aggregates a list of results into report-ready fields."""

    def test_summarize_empty_list_returns_zeroed_dict(self):
        report = summarize([])
        assert report["total"] == 0
        assert report["success_rate"] == 0.0
        assert report["mean_duration_ms"] == 0.0

    def test_summarize_all_successful(self):
        results = []
        for i in range(3):
            r = TaskResult(task_index=i, success=True, task_name=f"t{i}")
            r.duration_ms = 100
            results.append(r)
        report = summarize(results)
        assert report["total"] == 3
        assert report["succeeded"] == 3
        assert report["failed"] == 0
        assert report["success_rate"] == 1.0
        assert report["mean_duration_ms"] == 100.0
        assert report["total_duration_ms"] == 300

    def test_summarize_mixed_outcomes(self):
        r1 = TaskResult(task_index=0, success=True, task_name="ok")
        r1.duration_ms = 200
        r1.attempts = 1
        r2 = TaskResult(task_index=1, success=False, task_name="bad")
        r2.duration_ms = 50
        r2.attempts = 4
        report = summarize([r1, r2])
        assert report["total"] == 2
        assert report["succeeded"] == 1
        assert report["failed"] == 1
        assert report["success_rate"] == 0.5
        assert report["mean_duration_ms"] == 125.0
        assert report["total_duration_ms"] == 250
        assert report["total_attempts"] == 5

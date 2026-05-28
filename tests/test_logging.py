"""Tests for structured task event logging (Phase 1, O2).

When ``config['log_format'] == 'json'`` the executor emits one JSON line
per task on the ``visus.desktop.task_events`` logger. The text default
(``log_format == 'text'``) keeps the human-readable [INFO] lines and
emits nothing on the events channel.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@pytest.fixture
def task_events(caplog):
    """Capture records emitted on the task-events logger."""
    caplog.set_level(logging.INFO, logger="visus.desktop.task_events")
    return caplog


@requires_tesseract
class TestStructuredTaskEvents:
    """``log_format='json'`` emits a JSON object per task with a fixed schema."""

    def test_emits_one_json_record_per_task(self, task_events):
        """Two tasks → two JSON lines."""
        bot = vd.VisusBot({"show_overlay": False, "log_format": "json"})
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            bot.execute_tasks(
                [
                    {"type": "click", "x": 1, "y": 1},
                    {"type": "click", "x": 2, "y": 2},
                ]
            )

        json_records = [
            r
            for r in task_events.records
            if r.name == "visus.desktop.task_events"
        ]
        assert len(json_records) == 2

    def test_json_schema_for_a_successful_task(self, task_events):
        """A successful click yields the expected JSON keys and values."""
        bot = vd.VisusBot({"show_overlay": False, "log_format": "json"})
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

        records = [
            r for r in task_events.records if r.name == "visus.desktop.task_events"
        ]
        assert len(records) == 1
        event = json.loads(records[0].getMessage())
        assert set(event.keys()) >= {
            "run_id",
            "task_id",
            "task_name",
            "success",
            "duration_ms",
            "error",
            "failure_screenshot",
            "timestamp",
        }
        assert event["task_id"] == 0
        assert event["success"] is True
        assert event["error"] is None
        assert event["failure_screenshot"] is None
        assert isinstance(event["duration_ms"], int)
        assert event["duration_ms"] >= 0
        assert event["run_id"]
        assert event["timestamp"]

    def test_json_schema_for_a_failing_task(self, task_events, tmp_path):
        """A failing task yields ``success=False`` and a populated error/screenshot."""
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "log_format": "json",
                "artifacts_dir": str(tmp_path),
            }
        )
        from PIL import Image as _PILImage

        fake_image = _PILImage.new("RGB", (4, 4), color="black")
        with patch(
            "visus.desktop.core.task_executor.capture_screen",
            return_value=fake_image,
        ):
            bot.execute_tasks([{"foo": "bar"}])

        records = [
            r for r in task_events.records if r.name == "visus.desktop.task_events"
        ]
        assert len(records) == 1
        event = json.loads(records[0].getMessage())
        assert event["success"] is False
        assert event["error"]
        assert event["failure_screenshot"]
        assert event["failure_screenshot"].endswith(".png")

    def test_text_format_emits_no_json_records(self, task_events):
        """The default (text) format does not write to the task-events logger."""
        bot = vd.VisusBot({"show_overlay": False})  # log_format default is text
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

        records = [
            r for r in task_events.records if r.name == "visus.desktop.task_events"
        ]
        assert records == []

    def test_default_log_format_is_text(self):
        """The default ``log_format`` is the human-readable text mode."""
        from visus.desktop.utils import config as _config

        defaults = _config.BotVisionConfig._load_default_config(
            _config.BotVisionConfig.__new__(_config.BotVisionConfig)
        )
        assert defaults["log_format"] == "text"

    def test_same_run_id_across_tasks_of_one_invocation(self, task_events):
        """Every task in a single ``execute_tasks`` shares the same ``run_id``."""
        bot = vd.VisusBot({"show_overlay": False, "log_format": "json"})
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            bot.execute_tasks(
                [
                    {"type": "click", "x": 1, "y": 1},
                    {"type": "click", "x": 2, "y": 2},
                ]
            )

        records = [
            r for r in task_events.records if r.name == "visus.desktop.task_events"
        ]
        events = [json.loads(r.getMessage()) for r in records]
        run_ids = {e["run_id"] for e in events}
        assert len(run_ids) == 1

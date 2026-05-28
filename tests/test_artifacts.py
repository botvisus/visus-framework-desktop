"""Tests for failure artifacts: screenshot-on-failure (Phase 1, O1).

When a task fails, the executor captures a screenshot to
``config['artifacts_dir']`` and attaches the path to the ``TaskResult``.
The filename follows ``<run_id>__<task_id>__<timestamp>.png`` so multiple
runs can coexist in the same directory.

The capture path is patched so these tests don't touch a real display.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@requires_tesseract
class TestScreenshotOnFailure:
    """A failing task writes a PNG and exposes its path on TaskResult."""

    def test_failing_task_writes_screenshot_to_artifacts_dir(self, tmp_path):
        """An unknown-shape task fails and produces a PNG under artifacts_dir."""
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "artifacts_dir": str(tmp_path),
            }
        )
        fake_image = Image.new("RGB", (4, 4), color="black")
        with patch(
            "visus.desktop.core.task_executor.capture_screen",
            return_value=fake_image,
        ):
            results = bot.execute_tasks([{"foo": "bar"}])

        assert len(results) == 1
        assert results[0].success is False

        screenshot_path = results[0].failure_screenshot
        assert screenshot_path is not None
        assert os.path.exists(screenshot_path)
        assert os.path.dirname(screenshot_path) == str(tmp_path)

        filename = os.path.basename(screenshot_path)
        assert filename.endswith(".png")
        parts = filename[:-4].split("__")
        assert len(parts) == 3, f"Unexpected filename format: {filename}"
        run_id, task_id, timestamp = parts
        assert run_id, "run_id must be non-empty"
        assert task_id == "0", "task_id must be the failing task's index"
        assert timestamp, "timestamp must be non-empty"

    def test_default_artifacts_dir_is_visus_artifacts(self, monkeypatch):
        """The shipped default for ``artifacts_dir`` is ``./visus-artifacts``.

        The autouse ``_isolate_failure_artifacts`` fixture redirects the
        default to a tmp dir during the suite, so we bypass it here by
        reading the raw default from the unpatched loader.
        """
        from visus.desktop.utils import config as _config

        # Undo the autouse redirection for this single check.
        monkeypatch.undo()
        defaults = _config.BotVisionConfig._load_default_config(
            _config.BotVisionConfig.__new__(_config.BotVisionConfig)
        )
        assert defaults["artifacts_dir"] == "./visus-artifacts"
        assert defaults["screenshot_on_failure"] is True

    def test_disabling_screenshot_on_failure(self, tmp_path):
        """``screenshot_on_failure=False`` skips capture; result path stays None."""
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "artifacts_dir": str(tmp_path),
                "screenshot_on_failure": False,
            }
        )
        with patch(
            "visus.desktop.core.task_executor.capture_screen"
        ) as mock_capture:
            results = bot.execute_tasks([{"foo": "bar"}])

        assert results[0].success is False
        assert results[0].failure_screenshot is None
        mock_capture.assert_not_called()
        assert not list(tmp_path.glob("*.png"))

    def test_successful_task_does_not_create_screenshot(self, tmp_path):
        """Successful tasks never trigger the failure capture path."""
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "artifacts_dir": str(tmp_path),
            }
        )
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ), patch(
            "visus.desktop.core.task_executor.capture_screen"
        ) as mock_capture:
            results = bot.execute_tasks([{"type": "click", "x": 1, "y": 1}])

        assert results[0].success is True
        assert results[0].failure_screenshot is None
        mock_capture.assert_not_called()
        assert not list(tmp_path.glob("*.png"))

    def test_capture_failure_does_not_break_execution(self, tmp_path):
        """If the screenshot capture itself raises, the task result still returns."""
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "artifacts_dir": str(tmp_path),
            }
        )
        with patch(
            "visus.desktop.core.task_executor.capture_screen",
            side_effect=RuntimeError("display offline"),
        ):
            results = bot.execute_tasks([{"foo": "bar"}])

        assert len(results) == 1
        assert results[0].success is False
        assert results[0].failure_screenshot is None

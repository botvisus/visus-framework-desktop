"""Tests for resume-from-checkpoint in ``execute_tasks`` (Phase 2, R3).

``bot.execute_tasks(tasks, resume=True)`` reads
``<artifacts_dir>/checkpoint.json`` and skips any task index that
completed successfully in a previous interrupted run, provided the
task list hash matches. A successful full run also clears the
checkpoint so the next invocation starts fresh.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


def _click(x, y):
    return {"type": "click", "x": x, "y": y}


@requires_tesseract
class TestResumeFromCheckpoint:
    def test_resume_skips_previously_completed_indices(self, tmp_path):
        artifacts = tmp_path / "art"
        bot = vd.VisusBot(
            {"show_overlay": False, "artifacts_dir": str(artifacts)}
        )
        tasks = [_click(1, 1), _click(2, 2), _click(3, 3)]
        # Pre-seed a checkpoint claiming tasks 0 and 1 already ran.
        artifacts.mkdir(parents=True, exist_ok=True)
        checkpoint = artifacts / "checkpoint.json"
        checkpoint.write_text(
            json.dumps(
                {
                    "tasks_hash": bot.executor._tasks_hash(tasks),
                    "completed_indices": [0, 1],
                }
            )
        )

        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ) as mock_click:
            results = bot.execute_tasks(tasks, resume=True)

        # Only task 2 actually ran; tasks 0 and 1 are returned as skipped
        # placeholders so the indices stay aligned with the input list.
        assert len(results) == 3
        assert mock_click.call_count == 1

    def test_no_resume_runs_everything(self, tmp_path):
        bot = vd.VisusBot(
            {"show_overlay": False, "artifacts_dir": str(tmp_path)}
        )
        tasks = [_click(1, 1), _click(2, 2)]
        # Even if a checkpoint exists, ``resume=False`` (the default) ignores it.
        cp = tmp_path / "checkpoint.json"
        cp.write_text(json.dumps({"tasks_hash": "stale", "completed_indices": [0]}))

        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ) as mock_click:
            bot.execute_tasks(tasks)

        assert mock_click.call_count == 2

    def test_resume_ignores_checkpoint_when_tasks_changed(self, tmp_path):
        """A different task list shape invalidates the checkpoint."""
        bot = vd.VisusBot(
            {"show_overlay": False, "artifacts_dir": str(tmp_path)}
        )
        cp = tmp_path / "checkpoint.json"
        cp.write_text(
            json.dumps({"tasks_hash": "stale-hash", "completed_indices": [0]})
        )
        tasks = [_click(1, 1), _click(2, 2)]
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ) as mock_click:
            bot.execute_tasks(tasks, resume=True)
        assert mock_click.call_count == 2  # both tasks ran

    def test_successful_run_writes_checkpoint(self, tmp_path):
        artifacts = tmp_path / "art"
        bot = vd.VisusBot(
            {"show_overlay": False, "artifacts_dir": str(artifacts)}
        )
        tasks = [_click(1, 1)]
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            bot.execute_tasks(tasks)
        # After a clean run the checkpoint is cleaned up so the next
        # invocation starts fresh.
        assert not (artifacts / "checkpoint.json").exists()

    def test_interrupted_run_leaves_checkpoint_behind(self, tmp_path):
        artifacts = tmp_path / "art"
        bot = vd.VisusBot(
            {"show_overlay": False, "artifacts_dir": str(artifacts)}
        )
        # task 0 OK, task 1 fails -> checkpoint should record [0].
        tasks = [_click(1, 1), {"foo": "bar"}]
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            bot.execute_tasks(tasks)
        cp = artifacts / "checkpoint.json"
        assert cp.exists()
        data = json.loads(cp.read_text())
        assert data["completed_indices"] == [0]

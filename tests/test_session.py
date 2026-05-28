"""Tests for ``Session`` record/replay (Phase 2, O3).

A ``Session`` is a context manager that captures every task event
emitted on the ``visus.desktop.task_events`` logger plus any failure
screenshots referenced by those events. Closing the context writes a
single zip file containing ``events.jsonl`` and a ``screenshots/``
folder. ``Session.replay(path)`` reads the zip back into the in-memory
event list so a recorded run can be inspected or used as a fixture.
"""

from __future__ import annotations

import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.core.session import Session

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@requires_tesseract
class TestSessionRoundTrip:
    """A recorded session replays back to the same event list."""

    def test_round_trip_events_only(self, tmp_path):
        bot = vd.VisusBot({"show_overlay": False, "log_format": "json"})
        zip_path = tmp_path / "run.zip"
        fake_center = MagicMock(x=1, y=1)
        with Session.start_recording(zip_path), patch(
            "pyautogui.center", return_value=fake_center
        ), patch.object(bot.executor.virtual_mouse, "click", return_value=True):
            bot.execute_tasks(
                [
                    {"type": "click", "x": 1, "y": 1},
                    {"type": "click", "x": 2, "y": 2},
                ]
            )

        assert zip_path.exists()
        events = Session.replay(zip_path)
        assert len(events) == 2
        assert {e["task_id"] for e in events} == {0, 1}
        assert all(e["success"] is True for e in events)
        assert all("run_id" in e for e in events)

    def test_round_trip_bundles_failure_screenshot(self, tmp_path):
        artifacts = tmp_path / "art"
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "log_format": "json",
                "artifacts_dir": str(artifacts),
            }
        )
        fake_image = Image.new("RGB", (4, 4), color="black")
        zip_path = tmp_path / "fail.zip"
        with Session.start_recording(zip_path), patch(
            "visus.desktop.core.task_executor.capture_screen",
            return_value=fake_image,
        ):
            bot.execute_tasks([{"foo": "bar"}])

        events = Session.replay(zip_path)
        assert len(events) == 1
        assert events[0]["success"] is False

        with zipfile.ZipFile(zip_path) as zf:
            png_entries = [n for n in zf.namelist() if n.startswith("screenshots/")]
        assert png_entries, "failure screenshot should be bundled in the zip"

    def test_zip_contains_events_jsonl(self, tmp_path):
        bot = vd.VisusBot({"show_overlay": False, "log_format": "json"})
        zip_path = tmp_path / "x.zip"
        with Session.start_recording(zip_path):
            bot.execute_tasks([{"foo": "bar"}])
        with zipfile.ZipFile(zip_path) as zf:
            assert "events.jsonl" in zf.namelist()
            lines = zf.read("events.jsonl").decode("utf-8").splitlines()
        assert len(lines) == 1
        json.loads(lines[0])  # must be valid JSON

    def test_empty_recording_produces_empty_event_list(self, tmp_path):
        zip_path = tmp_path / "empty.zip"
        with Session.start_recording(zip_path):
            pass
        events = Session.replay(zip_path)
        assert events == []


class TestSessionReplay:
    """``replay`` reads ``events.jsonl`` regardless of who wrote the zip."""

    def test_replay_reads_handwritten_jsonl(self, tmp_path):
        zip_path = tmp_path / "manual.zip"
        events_in = [
            {"run_id": "abc", "task_id": 0, "success": True},
            {"run_id": "abc", "task_id": 1, "success": False},
        ]
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "events.jsonl",
                "\n".join(json.dumps(e) for e in events_in),
            )
        out = Session.replay(zip_path)
        assert out == events_in

    def test_replay_missing_file_raises_clear_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Session.replay(tmp_path / "does_not_exist.zip")

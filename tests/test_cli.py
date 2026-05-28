"""Tests for the ``visus`` CLI (Phase 5, D2).

Subcommands covered:
  * ``visus new <name>``    -- scaffold a new project directory.
  * ``visus report <zip>``  -- render a session zip to HTML.
  * ``visus doctor``        -- delegate to the existing diagnostic.
  * ``visus run <script>``  -- execute a Python script in a subprocess.
"""

from __future__ import annotations

import json
import zipfile
from unittest.mock import patch

import pytest

from visus.desktop.cli import main


def _make_session_zip(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "events.jsonl",
            json.dumps(
                {
                    "run_id": "test",
                    "task_id": 0,
                    "task_name": "smoke",
                    "success": True,
                    "duration_ms": 10,
                    "attempts": 1,
                    "error": None,
                    "failure_screenshot": None,
                    "timestamp": "2026-05-28T10:00:00+00:00",
                }
            ),
        )


class TestNewSubcommand:
    def test_new_creates_project_skeleton(self, tmp_path):
        target = tmp_path / "mybot"
        rc = main(["new", str(target)])
        assert rc == 0
        assert (target / "tasks.py").exists()
        assert (target / "README.md").exists()
        assert (target / ".gitignore").exists()

    def test_new_refuses_existing_dir_unless_force(self, tmp_path):
        target = tmp_path / "mybot"
        target.mkdir()
        rc = main(["new", str(target)])
        assert rc != 0
        # With --force the command proceeds.
        rc = main(["new", str(target), "--force"])
        assert rc == 0
        assert (target / "tasks.py").exists()


class TestReportSubcommand:
    def test_report_writes_html(self, tmp_path):
        zip_path = tmp_path / "run.zip"
        html_path = tmp_path / "report.html"
        _make_session_zip(zip_path)
        rc = main(["report", str(zip_path), "--html", str(html_path)])
        assert rc == 0
        assert html_path.exists()
        assert "Visus" in html_path.read_text(encoding="utf-8")


class TestDoctorSubcommand:
    def test_doctor_delegates_to_doctor_main(self):
        with patch("visus.desktop.doctor.main", return_value=0) as doctor:
            rc = main(["doctor"])
        assert rc == 0
        doctor.assert_called_once()


class TestRunSubcommand:
    def test_run_invokes_subprocess(self, tmp_path):
        script = tmp_path / "hello.py"
        script.write_text("print('hi')")
        with patch("subprocess.call", return_value=0) as call:
            rc = main(["run", str(script)])
        assert rc == 0
        cmd = call.call_args[0][0]
        assert cmd[-1] == str(script)


class TestHelpAndUnknown:
    def test_no_args_shows_help_and_exits_nonzero(self, capsys):
        rc = main([])
        out = capsys.readouterr().out + capsys.readouterr().err
        assert rc != 0
        # argparse may have printed usage; either way the command
        # surface should mention the available subcommands.
        assert "new" in out or "report" in out or "doctor" in out

    def test_unknown_subcommand_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc:
            main(["xyz"])
        assert exc.value.code != 0

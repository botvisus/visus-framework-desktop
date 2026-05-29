"""Tests for the ``visus`` CLI root + project commands (Visus CLI Pro).

Covers the back-compatible programmatic ``main(argv)`` contract and the
``new`` / ``run`` / ``report`` / ``doctor`` commands. Command groups for the
automation surface live in the ``test_cli_*`` siblings.
"""

from __future__ import annotations

import json
import zipfile
from unittest.mock import patch

from click.testing import CliRunner

from visus.desktop.cli import cli, main


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

    def test_doctor_propagates_failure_code(self):
        with patch("visus.desktop.doctor.main", return_value=3):
            rc = main(["doctor"])
        assert rc == 3

    def test_doctor_json_payload(self):
        runner = CliRunner()
        with patch("visus.desktop.doctor.main", return_value=0):
            result = runner.invoke(cli, ["doctor", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["exit_code"] == 0
        assert "output" in payload


class TestRunSubcommand:
    def test_run_invokes_subprocess(self, tmp_path):
        script = tmp_path / "hello.py"
        script.write_text("print('hi')")
        with patch("subprocess.call", return_value=0) as call:
            rc = main(["run", str(script)])
        assert rc == 0
        cmd = call.call_args[0][0]
        assert cmd[-1] == str(script)

    def test_run_propagates_script_exit_code(self, tmp_path):
        script = tmp_path / "boom.py"
        script.write_text("raise SystemExit(2)")
        with patch("subprocess.call", return_value=2):
            rc = main(["run", str(script)])
        assert rc == 2


class TestRootBehaviour:
    def test_no_args_shows_help_and_exits_nonzero(self):
        rc = main([])
        assert rc != 0

    def test_unknown_subcommand_exits_nonzero(self):
        rc = main(["definitely-not-a-command"])
        assert rc != 0

    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "Visus CLI Pro" in result.output

    def test_help_lists_command_groups(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        for group in ("smart", "native", "capture", "window", "process"):
            assert group in result.output

"""Tests for ``visus process`` / ``clipboard`` / ``configure`` / ``repl``."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from visus.desktop.cli import cli

runner = CliRunner()


class TestProcess:
    def test_launch(self):
        fake = MagicMock(pid=4321)
        with patch("subprocess.Popen", return_value=fake) as popen:
            result = runner.invoke(cli, ["process", "launch", "notepad.exe", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["pid"] == 4321
        popen.assert_called_once()

    def test_find(self):
        proc = MagicMock()
        proc.info = {"name": "notepad.exe"}
        proc.pid = 99
        with patch("psutil.process_iter", return_value=[proc]):
            result = runner.invoke(cli, ["process", "find", "notepad", "--json"])
        assert result.exit_code == 0
        rows = json.loads(result.output)
        assert rows[0]["pid"] == 99

    def test_kill_requires_confirmation(self):
        with patch("visus.desktop.core.process.kill_process") as kill_fn:
            result = runner.invoke(cli, ["process", "kill", "123"], input="n\n")
        assert result.exit_code == 1
        kill_fn.assert_not_called()

    def test_kill_with_yes(self):
        with patch("visus.desktop.core.process.kill_process", return_value=True) as kill_fn:
            result = runner.invoke(cli, ["process", "kill", "123", "--yes"])
        assert result.exit_code == 0
        kill_fn.assert_called_once_with(123)

    def test_kill_json_without_yes_refuses(self):
        with patch("visus.desktop.core.process.kill_process") as kill_fn:
            result = runner.invoke(cli, ["process", "kill", "123", "--json"])
        assert result.exit_code == 1
        kill_fn.assert_not_called()


class TestClipboard:
    def test_get(self):
        with patch("visus.desktop.utils.clipboard.get_clipboard", return_value="hello"):
            result = runner.invoke(cli, ["clipboard", "get"])
        assert result.exit_code == 0
        assert "hello" in result.output

    def test_set(self):
        with patch("visus.desktop.utils.clipboard.copy") as copy_fn:
            result = runner.invoke(cli, ["clipboard", "set", "world"])
        assert result.exit_code == 0
        copy_fn.assert_called_once_with("world")


class TestConfigure:
    def test_valid_config(self):
        bot = MagicMock()
        bot.config.config = {"confidence_threshold": 80}
        with patch("visus.desktop.VisusBot", return_value=bot) as ctor:
            result = runner.invoke(
                cli, ["configure", '{"confidence_threshold": 80}', "--json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)["confidence_threshold"] == 80
        ctor.assert_called_once_with({"confidence_threshold": 80})

    def test_invalid_json(self):
        result = runner.invoke(cli, ["configure", "{not json"])
        assert result.exit_code == 1

    def test_non_object_json(self):
        result = runner.invoke(cli, ["configure", "[1, 2, 3]"])
        assert result.exit_code == 1

    def test_config_from_file(self, tmp_path):
        cfg = tmp_path / "c.json"
        cfg.write_text('{"show_overlay": false}', encoding="utf-8")
        bot = MagicMock()
        bot.config.config = {"show_overlay": False}
        with patch("visus.desktop.VisusBot", return_value=bot):
            result = runner.invoke(cli, ["configure", f"@{cfg}", "--json"])
        assert result.exit_code == 0


class TestRepl:
    def test_repl_banner_and_exit(self):
        result = runner.invoke(cli, ["repl"], input="exit\n")
        assert result.exit_code == 0
        assert "Visus CLI Pro" in result.output

    def test_repl_dispatches_command(self):
        found = {"found": True, "box": {}, "method": "native", "tried": ["native"]}
        with patch("visus.desktop.core.smart.smart_find", return_value=found):
            result = runner.invoke(
                cli, ["repl"], input='smart find --query Hi --json\nexit\n'
            )
        assert result.exit_code == 0
        assert '"method"' in result.output

    def test_repl_rejects_nested_repl(self):
        result = runner.invoke(cli, ["repl"], input="repl\nexit\n")
        assert result.exit_code == 0
        assert "Already in the REPL" in result.output

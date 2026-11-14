"""Tests for the ``visus native`` command group."""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core.outcome import ActionOutcome

runner = CliRunner()


class TestDumpTree:
    def test_json(self):
        nodes = [
            {"depth": 0, "control_type": "Window", "title": "Notepad", "auto_id": "", "rect": [0, 0, 100, 50]},
            {"depth": 1, "control_type": "Button", "title": "OK", "auto_id": "ok", "rect": [1, 2, 3, 4]},
        ]
        with patch("visus.desktop.core.native_rpa.native_dump_tree", return_value=nodes) as m:
            result = runner.invoke(
                cli, ["native", "dump-tree", "--window", "Notepad", "--json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)[1]["title"] == "OK"
        assert m.call_args.kwargs["window"] == "Notepad"

    def test_human_tree(self):
        nodes = [{"depth": 0, "control_type": "Window", "title": "N", "auto_id": "", "rect": []}]
        with patch("visus.desktop.core.native_rpa.native_dump_tree", return_value=nodes):
            result = runner.invoke(cli, ["native", "dump-tree"])
        assert result.exit_code == 0
        assert "Window" in result.output

    def test_empty_tree_still_zero(self):
        with patch("visus.desktop.core.native_rpa.native_dump_tree", return_value=[]):
            result = runner.invoke(cli, ["native", "dump-tree"])
        assert result.exit_code == 0
        assert "no accessible controls" in result.output


class TestNativeClick:
    def test_click_success(self):
        with patch(
            "visus.desktop.core.native_rpa.native_click_ex",
            return_value=ActionOutcome.sent("Invoke"),
        ) as m:
            result = runner.invoke(
                cli, ["native", "click", "--title", "OK", "--control-type", "Button"]
            )
        assert result.exit_code == 0
        assert "clicked (Invoke)" in result.output
        assert m.call_args.kwargs["title"] == "OK"
        assert m.call_args.kwargs["control_type"] == "Button"

    def test_click_failure(self):
        with patch(
            "visus.desktop.core.native_rpa.native_click_ex",
            return_value=ActionOutcome.not_sent("control not found in the window"),
        ):
            result = runner.invoke(cli, ["native", "click", "--title", "OK"])
        assert result.exit_code == 1
        assert "safe to retry" in result.output

    def test_dry_run_uses_get_state(self):
        state = {"exists": True, "rect": [1, 2, 3, 4]}
        with patch(
            "visus.desktop.core.native_rpa.native_get_state", return_value=state
        ) as gs, patch("visus.desktop.core.native_rpa.native_click_ex") as click_fn:
            result = runner.invoke(
                cli, ["native", "click", "--title", "OK", "--dry-run"]
            )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output
        gs.assert_called_once()
        click_fn.assert_not_called()


class TestNativeText:
    def test_set_text(self):
        with patch(
            "visus.desktop.core.native_rpa.native_set_text_ex",
            return_value=ActionOutcome.sent("keyboard", verified=True),
        ) as m:
            result = runner.invoke(
                cli, ["native", "set-text", "hello", "--auto-id", "edit1"]
            )
        assert result.exit_code == 0
        # `text` is keyword-only in native_set_text_ex: the CLI always passes it by name
        assert m.call_args.kwargs["text"] == "hello"
        assert m.call_args.kwargs["auto_id"] == "edit1"

    def test_get_text(self):
        with patch("visus.desktop.core.native_rpa.native_get_text", return_value="hi"):
            result = runner.invoke(cli, ["native", "get-text", "--title", "Edit"])
        assert result.exit_code == 0
        assert "hi" in result.output

    def test_get_text_missing(self):
        with patch("visus.desktop.core.native_rpa.native_get_text", return_value=None):
            result = runner.invoke(cli, ["native", "get-text", "--title", "Edit"])
        assert result.exit_code == 1


class TestNativeStateAndWait:
    def test_get_state(self):
        state = {"exists": True, "visible": True, "enabled": True}
        with patch("visus.desktop.core.native_rpa.native_get_state", return_value=state):
            result = runner.invoke(cli, ["native", "get-state", "--title", "OK", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["exists"] is True

    def test_wait_success(self):
        with patch("visus.desktop.core.native_rpa.native_wait", return_value=True) as m:
            result = runner.invoke(
                cli, ["native", "wait", "--title", "OK", "--state", "ready"]
            )
        assert result.exit_code == 0
        assert m.call_args.kwargs["state"] == "ready"

    def test_wait_timeout(self):
        with patch("visus.desktop.core.native_rpa.native_wait", return_value=False):
            result = runner.invoke(cli, ["native", "wait", "--title", "OK"])
        assert result.exit_code == 1

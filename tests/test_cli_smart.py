"""Tests for ``visus smart find`` / ``visus smart click``."""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from visus.desktop.cli import cli

runner = CliRunner()

_FOUND = {
    "found": True,
    "box": {"x": 1, "y": 2, "width": 3, "height": 4},
    "method": "native",
    "tried": ["native"],
}
_NOT_FOUND = {"found": False, "box": None, "method": None, "tried": ["native", "ocr"]}


class TestSmartFind:
    def test_found_json(self):
        with patch("visus.desktop.core.smart.smart_find", return_value=_FOUND) as m:
            result = runner.invoke(cli, ["smart", "find", "--query", "Login", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["method"] == "native"
        assert m.call_args.args[0] == "Login"

    def test_found_human(self):
        with patch("visus.desktop.core.smart.smart_find", return_value=_FOUND):
            result = runner.invoke(cli, ["smart", "find", "--query", "Login"])
        assert result.exit_code == 0
        assert "found via native" in result.output

    def test_not_found_exit_code(self):
        with patch("visus.desktop.core.smart.smart_find", return_value=_NOT_FOUND):
            result = runner.invoke(cli, ["smart", "find", "--query", "x"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_parses_coords_region_order(self):
        with patch("visus.desktop.core.smart.smart_find", return_value=_FOUND) as m:
            result = runner.invoke(
                cli,
                [
                    "smart", "find",
                    "--coords", "10,20",
                    "--region", "1,2,3,4",
                    "--order", "native,ocr",
                    "--json",
                ],
            )
        assert result.exit_code == 0
        kwargs = m.call_args.kwargs
        assert kwargs["coordinates"] == [10, 20]
        assert kwargs["search_region"] == [1, 2, 3, 4]
        assert kwargs["order"] == ["native", "ocr"]

    def test_bad_region_is_usage_error(self):
        result = runner.invoke(cli, ["smart", "find", "--region", "1,2,3"])
        assert result.exit_code == 2


class TestSmartClick:
    def test_click_success(self):
        clicked = {"clicked": True, "method": "ocr", "tried": ["native", "ocr"]}
        with patch("visus.desktop.core.smart.smart_click", return_value=clicked) as m:
            result = runner.invoke(cli, ["smart", "click", "--query", "Go", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["clicked"] is True
        assert m.call_args.kwargs["button"] == "left"

    def test_click_failure_exit_code(self):
        missed = {"clicked": False, "method": None, "tried": ["native"]}
        with patch("visus.desktop.core.smart.smart_click", return_value=missed):
            result = runner.invoke(cli, ["smart", "click", "--query", "Go"])
        assert result.exit_code == 1
        assert "not clicked" in result.output

    def test_dry_run_does_not_click(self):
        with patch(
            "visus.desktop.core.smart.smart_find", return_value=_FOUND
        ) as find, patch("visus.desktop.core.smart.smart_click") as click_fn:
            result = runner.invoke(
                cli, ["smart", "click", "--query", "Go", "--dry-run"]
            )
        assert result.exit_code == 0
        assert "[dry-run]" in result.output
        find.assert_called_once()
        click_fn.assert_not_called()

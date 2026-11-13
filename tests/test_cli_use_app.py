"""``visus use-app``: traz o programa para a frente e, fechado, abre e espera."""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core.app import AppWindow, UseAppError

runner = CliRunner()


def test_use_app_json() -> None:
    win = AppWindow("Pasta1 - Excel", hwnd=5, pid=50, opened=True)
    with patch("visus.desktop.core.app.use_app", return_value=win) as use:
        result = runner.invoke(
            cli, ["use-app", "EXCEL.EXE", "--window", "Excel", "--json"]
        )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "title": "Pasta1 - Excel",
        "hwnd": 5,
        "pid": 50,
        "opened": True,
    }
    use.assert_called_once_with("EXCEL.EXE", window="Excel", file=None, timeout=30.0)


def test_use_app_failure_is_a_clear_error() -> None:
    reason = "'Calculadora' is not open - open it before running"
    with patch("visus.desktop.core.app.use_app", side_effect=UseAppError(reason)):
        result = runner.invoke(cli, ["use-app", "--window", "Calculadora"])
    assert result.exit_code != 0
    assert reason in result.output

"""Tests for ``visus capture`` / ``visus screenshot`` / ``visus window``."""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from visus.desktop.cli import cli

runner = CliRunner()


class TestCapture:
    def test_capture_auto(self):
        result_dict = {
            "found": True, "label": "save", "located_by": "win32",
            "box": {"x": 1, "y": 2, "width": 3, "height": 4},
            "template_path": "visus-elements/save.png",
            "annotated_path": "visus-elements/trace/save_annotated.png",
            "clicked": False,
        }
        with patch(
            "visus.desktop.core.elements.capture_element", return_value=result_dict
        ) as m:
            result = runner.invoke(cli, ["capture", "save", "--auto", "Salvar", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["located_by"] == "win32"
        assert m.call_args.kwargs["auto"] == "Salvar"
        assert m.call_args.kwargs["click"] is False

    def test_requires_exactly_one_locator(self):
        result = runner.invoke(cli, ["capture", "x", "--auto", "A", "--text", "B"])
        assert result.exit_code == 1

    def test_no_locator_is_error(self):
        result = runner.invoke(cli, ["capture", "x"])
        assert result.exit_code == 1

    def test_dry_run_disables_click(self):
        result_dict = {
            "found": True, "label": "save", "located_by": "ocr",
            "box": {}, "template_path": "t.png", "annotated_path": "a.png",
            "clicked": False,
        }
        with patch(
            "visus.desktop.core.elements.capture_element", return_value=result_dict
        ) as m:
            result = runner.invoke(
                cli, ["capture", "save", "--text", "Salvar", "--click", "--dry-run"]
            )
        assert result.exit_code == 0
        assert m.call_args.kwargs["click"] is False
        assert "dry-run: not clicked" in result.output

    def test_not_found(self):
        result_dict = {"found": False, "annotated_path": "a.png"}
        with patch("visus.desktop.core.elements.capture_element", return_value=result_dict):
            result = runner.invoke(cli, ["capture", "save", "--text", "Nope"])
        assert result.exit_code == 1


class TestScreenshot:
    def test_screenshot(self, tmp_path):
        # save_screenshot returns the written path; the CLI reads the size back
        from PIL import Image

        out = str(tmp_path / "s.png")
        Image.new("RGB", (100, 50)).save(out)
        with patch("visus.desktop.core.screen.save_screenshot", return_value=out) as m:
            result = runner.invoke(
                cli, ["screenshot", out, "--region", "0,0,100,50", "--json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)["width"] == 100
        assert m.call_args.kwargs["region"] == (0, 0, 100, 50)


class TestWindow:
    def test_focus(self):
        with patch("visus.desktop.core.window.focus_window", return_value=True):
            result = runner.invoke(cli, ["window", "focus", "Notepad"])
        assert result.exit_code == 0
        assert "focused" in result.output

    def test_focus_not_found(self):
        with patch("visus.desktop.core.window.focus_window", return_value=False):
            result = runner.invoke(cli, ["window", "focus", "Nope"])
        assert result.exit_code == 1

    def test_get_window(self):
        info = {"title": "Notepad", "pid": 10, "hwnd": 5, "x": 0, "y": 0, "width": 8, "height": 6}
        with patch("visus.desktop.core.locators.get_window", return_value=info):
            result = runner.invoke(cli, ["window", "get", "Notepad", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)["pid"] == 10

    def test_get_window_missing(self):
        with patch("visus.desktop.core.locators.get_window", return_value=None):
            result = runner.invoke(cli, ["window", "get", "Nope"])
        assert result.exit_code == 1

    def test_close_requires_confirmation(self):
        with patch("visus.desktop.core.window.close_window") as close_fn:
            result = runner.invoke(cli, ["window", "close", "Notepad"], input="n\n")
        assert result.exit_code == 1
        close_fn.assert_not_called()

    def test_close_with_yes(self):
        with patch("visus.desktop.core.window.close_window", return_value=True) as close_fn:
            result = runner.invoke(cli, ["window", "close", "Notepad", "--yes"])
        assert result.exit_code == 0
        close_fn.assert_called_once()

    def test_close_json_without_yes_refuses(self):
        with patch("visus.desktop.core.window.close_window") as close_fn:
            result = runner.invoke(cli, ["window", "close", "Notepad", "--json"])
        assert result.exit_code == 1
        close_fn.assert_not_called()

    def test_ensure_requires_target(self):
        result = runner.invoke(cli, ["window", "ensure"])
        assert result.exit_code == 1

    def test_ensure_found(self):
        state = {
            "found": True, "running": True, "hwnd": 5, "pid": 18756,
            "title": "Sem título - Bloco de Notas", "minimized": False,
            "maximized": False, "foreground": True,
            "rect": {"x": 0, "y": 0, "width": 8, "height": 6},
            "shown": True, "matches": 1,
        }
        with patch("visus.desktop.core.window.ensure_window", return_value=state) as m:
            result = runner.invoke(
                cli, ["window", "ensure", "--process", "notepad.exe", "--json"]
            )
        assert result.exit_code == 0
        assert json.loads(result.output)["pid"] == 18756
        assert m.call_args.kwargs["process"] == "notepad.exe"
        assert m.call_args.kwargs["show"] is True

    def test_ensure_no_show_flag(self):
        state = {"found": True, "running": None, "minimized": True, "matches": 1,
                 "pid": 1, "title": "X", "shown": False}
        with patch("visus.desktop.core.window.ensure_window", return_value=state) as m:
            result = runner.invoke(cli, ["window", "ensure", "--title", "X", "--no-show"])
        assert result.exit_code == 0
        assert m.call_args.kwargs["show"] is False

    def test_ensure_not_found(self):
        state = {"found": False, "running": False, "shown": False, "matches": 0}
        with patch("visus.desktop.core.window.ensure_window", return_value=state):
            result = runner.invoke(cli, ["window", "ensure", "--process", "ghost.exe"])
        assert result.exit_code == 1
        assert "not open" in result.output

    def test_list_windows(self):
        rows = [
            {"hwnd": 1, "title": "A", "pid": 10, "minimized": False,
             "maximized": False, "foreground": True, "rect": {}},
        ]
        with patch("visus.desktop.core.window.list_windows", return_value=rows):
            result = runner.invoke(cli, ["window", "list", "--process", "notepad.exe", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output)[0]["pid"] == 10

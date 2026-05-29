"""Tests for save_screenshot (library + MCP tool).

Closes the find_image template gap: find_image needs a PNG on disk, but
the MCP surface previously only had take_screenshot (base64). This adds
a disk-writing tool with monitor parity to capture_screen / take_screenshot.
"""

from __future__ import annotations

from unittest.mock import patch

from PIL import Image

from visus.desktop.core import screen as _screen


class TestLibrarySaveScreenshot:
    def test_writes_png_and_returns_path(self, tmp_path):
        out = tmp_path / "shot.png"
        with patch.object(
            _screen, "capture_screen", return_value=Image.new("RGB", (8, 8), "red")
        ):
            returned = _screen.save_screenshot(str(out))
        assert returned == str(out)
        assert out.exists()
        assert Image.open(out).size == (8, 8)

    def test_forwards_region(self, tmp_path):
        out = tmp_path / "region.png"
        captured = {}

        def fake(region=None, monitor=None):
            captured["region"] = region
            captured["monitor"] = monitor
            return Image.new("RGB", (4, 4), "white")

        with patch.object(_screen, "capture_screen", side_effect=fake):
            _screen.save_screenshot(str(out), region=(10, 20, 30, 40))
        assert captured["region"] == (10, 20, 30, 40)

    def test_forwards_monitor(self, tmp_path):
        """Monitor parity with capture_screen / take_screenshot."""
        out = tmp_path / "mon.png"
        captured = {}

        def fake(region=None, monitor=None):
            captured["monitor"] = monitor
            return Image.new("RGB", (4, 4), "white")

        with patch.object(_screen, "capture_screen", side_effect=fake):
            _screen.save_screenshot(str(out), monitor=2)
        assert captured["monitor"] == 2

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "nested" / "deep" / "shot.png"
        with patch.object(
            _screen, "capture_screen", return_value=Image.new("RGB", (4, 4), "red")
        ):
            _screen.save_screenshot(str(out))
        assert out.exists()


class TestMcpSaveScreenshotTool:
    def _call(self, **kwargs):
        from visus.desktop import mcp_server as ms

        ms.reset_bot_for_tests()
        return ms._tools_for_tests()["save_screenshot"](**kwargs)

    def test_tool_is_registered(self):
        from visus.desktop import mcp_server as ms

        assert "save_screenshot" in ms._tools_for_tests()

    def test_writes_png_returns_abspath_payload(self, tmp_path):
        out = tmp_path / "mcp_shot.png"
        with patch(
            "visus.desktop.core.screen.capture_screen",
            return_value=Image.new("RGB", (16, 16), "blue"),
        ):
            result = self._call(path=str(out))
        # Returns a JSON-friendly dict with the absolute path + dimensions.
        assert result["path"].endswith("mcp_shot.png")
        assert out.exists()
        assert result["width"] == 16
        assert result["height"] == 16

    def test_tool_forwards_region(self, tmp_path):
        out = tmp_path / "r.png"
        captured = {}

        def fake(region=None, monitor=None):
            captured["region"] = region
            return Image.new("RGB", (5, 5), "white")

        with patch(
            "visus.desktop.core.screen.capture_screen", side_effect=fake
        ):
            self._call(path=str(out), region=[1, 2, 3, 4])
        assert tuple(captured["region"]) == (1, 2, 3, 4)

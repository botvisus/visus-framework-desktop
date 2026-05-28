"""Tests for the MCP server surface (visus.desktop.mcp_server).

The server exposes the visus-desktop primitives as MCP tools via
FastMCP. We exercise the underlying Python callables directly (the
``.fn`` attribute that FastMCP attaches to each registered tool) so
the suite runs without spinning up a transport.

Bot interactions are mocked at the visus.desktop layer so the tests
do not need a real display / OCR / mouse.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot construction requires it)",
)


@pytest.fixture
def server():
    """Return the FastMCP server with a fresh bot singleton each test."""
    from visus.desktop import mcp_server as ms

    ms.reset_bot_for_tests()
    return ms


def _call(server, tool_name: str, **kwargs):
    """Invoke a registered MCP tool by name, returning the raw Python result."""
    tools = server._tools_for_tests()
    assert tool_name in tools, f"unknown tool: {tool_name} (have {list(tools)})"
    return tools[tool_name](**kwargs)


# ---------------------------------------------------------------------------
# Server scaffolding
# ---------------------------------------------------------------------------


def test_module_exposes_a_fastmcp_instance(server):
    from mcp.server.fastmcp import FastMCP

    assert isinstance(server.mcp, FastMCP)


def test_tool_registry_covers_each_capability(server):
    expected = {
        "find_text",
        "click_text",
        "find_image",
        "click_image",
        "click_at",
        "hybrid_find",
        "type_text",
        "keyboard_command",
        "take_screenshot",
        "get_monitors",
        "wait_for_stable_screen",
        "wait_for_file",
        "wait_for_file_stable",
        "get_clipboard",
        "copy_to_clipboard",
        "launch",
        "find_process",
        "kill_process",
        "focus_window",
        "maximize_window",
        "minimize_window",
        "close_window",
        "execute_tasks",
        "extract_text_from_region",
        "start_recording",
        "stop_recording",
        "render_report",
        "doctor",
        "configure",
    }
    present = set(server._tools_for_tests())
    missing = expected - present
    assert not missing, f"missing tools: {sorted(missing)}"


# ---------------------------------------------------------------------------
# find / click
# ---------------------------------------------------------------------------


@requires_tesseract
class TestFindClick:
    def test_find_text_returns_dict(self, server):
        with patch(
            "visus.desktop.VisusBot.find_text", return_value=(10, 20, 30, 40)
        ):
            result = _call(server, "find_text", text="Login")
        assert result == {"x": 10, "y": 20, "width": 30, "height": 40}

    def test_find_text_returns_none_dict_on_miss(self, server):
        with patch("visus.desktop.VisusBot.find_text", return_value=None):
            assert _call(server, "find_text", text="missing") is None

    def test_click_text_returns_bool(self, server):
        with patch(
            "visus.desktop.VisusBot.click_text", return_value=True
        ) as click:
            ok = _call(server, "click_text", text="Submit")
        assert ok is True
        click.assert_called_once()

    def test_click_image_forwards_args(self, server):
        with patch(
            "visus.desktop.VisusBot.click_image", return_value=True
        ) as click:
            _call(
                server,
                "click_image",
                image_path="button.png",
                confidence=0.85,
                region=[10, 20, 30, 40],
            )
        kwargs = click.call_args.kwargs
        assert kwargs["confidence"] == 0.85
        # Region tuples are accepted as list/tuple from JSON.
        assert tuple(kwargs["region"]) == (10, 20, 30, 40)

    def test_click_at_returns_bool(self, server):
        with patch("visus.desktop.VisusBot.click_at", return_value=True):
            assert _call(server, "click_at", x=100, y=200) is True

    def test_hybrid_find_returns_dict(self, server):
        with patch(
            "visus.desktop.VisusBot.hybrid_find", return_value=(5, 6, 7, 8)
        ):
            box = _call(server, "hybrid_find", name="Login")
        assert box == {"x": 5, "y": 6, "width": 7, "height": 8}


# ---------------------------------------------------------------------------
# Screenshot tool returns a base64 PNG payload
# ---------------------------------------------------------------------------


class TestScreenshot:
    def test_take_screenshot_returns_base64_png(self, server):
        fake = Image.new("RGB", (16, 16), color="red")
        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=fake
        ):
            payload = _call(server, "take_screenshot")
        assert payload["mime_type"] == "image/png"
        decoded = base64.b64decode(payload["data_base64"])
        assert decoded.startswith(b"\x89PNG\r\n\x1a\n")
        assert payload["width"] == 16
        assert payload["height"] == 16

    def test_take_screenshot_with_region(self, server):
        captured = {}

        def fake_capture(region=None, monitor=None):
            captured["region"] = region
            return Image.new("RGB", (16, 16), color="white")

        with patch(
            "visus.desktop.core.screen.capture_screen", side_effect=fake_capture
        ):
            _call(server, "take_screenshot", region=[10, 20, 100, 50])
        assert tuple(captured["region"]) == (10, 20, 100, 50)


# ---------------------------------------------------------------------------
# execute_tasks accepts a list[dict] from MCP and returns dicts
# ---------------------------------------------------------------------------


@requires_tesseract
class TestExecuteTasks:
    def test_execute_tasks_round_trips_results(self, server):
        fake_results = [
            MagicMock(
                task_index=0,
                success=True,
                task_name="t0",
                attempts=1,
                duration_ms=42,
                error=None,
                failure_screenshot=None,
            ),
            MagicMock(
                task_index=1,
                success=False,
                task_name="t1",
                attempts=4,
                duration_ms=350,
                error="boom",
                failure_screenshot="/tmp/x.png",
            ),
        ]
        with patch(
            "visus.desktop.VisusBot.execute_tasks", return_value=fake_results
        ):
            out = _call(
                server,
                "execute_tasks",
                tasks=[
                    {"type": "click", "x": 10, "y": 20},
                    {"foo": "bar"},
                ],
            )
        assert len(out) == 2
        assert out[0]["success"] is True
        assert out[0]["duration_ms"] == 42
        assert out[1]["error"] == "boom"
        assert out[1]["failure_screenshot"] == "/tmp/x.png"


# ---------------------------------------------------------------------------
# configure tool re-creates the bot with new config
# ---------------------------------------------------------------------------


@requires_tesseract
class TestConfigure:
    def test_configure_replaces_singleton(self, server):
        first = server.get_bot()
        _call(server, "configure", config={"show_overlay": False})
        second = server.get_bot()
        assert second is not first


# ---------------------------------------------------------------------------
# doctor delegates to the existing health checks
# ---------------------------------------------------------------------------


class TestDoctor:
    def test_doctor_returns_zero_when_all_pass(self, server, capsys):
        with patch(
            "visus.desktop.doctor.run_checks", return_value=0
        ) as run_checks:
            rc = _call(server, "doctor")
        assert rc == 0
        run_checks.assert_called_once()


# ---------------------------------------------------------------------------
# Session round-trip via the MCP tools
# ---------------------------------------------------------------------------


@requires_tesseract
class TestSessionTools:
    def test_start_and_stop_recording_create_zip(self, server, tmp_path):
        zip_path = tmp_path / "rec.zip"
        _call(server, "start_recording", path=str(zip_path))
        _call(server, "stop_recording")
        assert zip_path.exists()

    def test_render_report_writes_html(self, server, tmp_path):
        # Build a one-event session via direct API then render.
        zip_path = tmp_path / "rec.zip"
        html_path = tmp_path / "report.html"
        import zipfile

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "events.jsonl",
                json.dumps(
                    {
                        "run_id": "x",
                        "task_id": 0,
                        "task_name": "t",
                        "success": True,
                        "duration_ms": 5,
                        "attempts": 1,
                        "error": None,
                        "failure_screenshot": None,
                        "timestamp": "2026-05-28T10:00:00+00:00",
                    }
                ),
            )
        _call(server, "render_report", zip_path=str(zip_path), html_path=str(html_path))
        assert html_path.exists()
        assert "Visus" in html_path.read_text(encoding="utf-8")

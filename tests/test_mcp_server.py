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
        "save_screenshot",
        "capture_element",
        "get_window",
        "get_monitors",
        "wait_for_stable_screen",
        "native_dump_tree",
        "native_snapshot",
        "open_app",
        "use_app",
        "native_click",
        "native_drag",
        "native_scroll",
        "native_set_text",
        "native_toggle",
        "native_select",
        "native_expand",
        "native_scroll_into_view",
        "native_get_text",
        "native_get_state",
        "native_wait",
        "smart_find",
        "smart_click",
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
        "ensure_window",
        "list_windows",
        "execute_tasks",
        "extract_text_from_region",
        "start_recording",
        "stop_recording",
        "replay_session",
        "render_report",
        "doctor",
        "configure",
    }
    present = set(server._tools_for_tests())
    missing = expected - present
    assert not missing, f"missing tools: {sorted(missing)}"
    # N7 regression -- new tools must update the expected set above too.
    extra = present - expected
    assert not extra, (
        f"new tools registered but not in the expected set: {sorted(extra)}"
    )


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
    def test_doctor_returns_structured_payload(self, server):
        """C4 regression -- doctor must NOT print to stdout (MCP stdio).

        The structured ``checks`` array is filled from the default check
        functions; ``output`` carries the textual report (captured, not
        leaked to the real stdout).
        """
        from visus.desktop import doctor as _doctor

        smoke = [("Smoke", lambda: (True, "ok"))]
        with patch.object(_doctor, "DEFAULT_CHECKS", smoke), patch.object(
            _doctor, "run_checks", return_value=0
        ) as run_checks:
            payload = _call(server, "doctor")
        assert payload["exit_code"] == 0
        assert isinstance(payload["checks"], list)
        assert payload["checks"][0]["name"] == "Smoke"
        assert payload["checks"][0]["ok"] is True
        run_checks.assert_called_once()

    def test_doctor_does_not_leak_to_stdout(self, server, capsys):
        """The captured stdout must never reach the test's real stdout."""
        _call(server, "doctor")
        captured = capsys.readouterr()
        # ``run_checks`` would normally print [OK]/[FAIL] lines; the MCP
        # wrapper captures them, so nothing should reach stdout here.
        assert "[OK]" not in captured.out
        assert "[FAIL]" not in captured.out


# ---------------------------------------------------------------------------
# Session round-trip via the MCP tools
# ---------------------------------------------------------------------------


@requires_tesseract
class TestSessionTools:
    def test_start_and_stop_recording_create_zip(self, server, tmp_path):
        zip_path = tmp_path / "rec.zip"
        _call(server, "start_recording", path=str(zip_path))
        out = _call(server, "stop_recording")
        assert zip_path.exists()
        assert out["saved"] is True and out["zip"] == str(zip_path)

    def test_stop_without_recording_says_so(self, server):
        assert _call(server, "stop_recording") == {"saved": False}

    def test_every_action_tool_is_a_report_step(self, server, tmp_path):
        """While recording, the agent's direct tool calls -- not only
        execute_tasks -- land in the report, with the run name as headline."""
        zip_path = tmp_path / "rec.zip"
        html_path = tmp_path / "rec.html"
        shot = Image.new("RGB", (32, 32), "white")
        with patch(
            "visus.desktop.core.task_executor.capture_screen", return_value=shot
        ), patch(
            "visus.desktop.core.task_executor.TaskExecutor._perform_action"
        ), patch("visus.desktop.core.human_typing.type_like_a_person"), patch(
            "visus.desktop.core.mouse_extra.scroll"
        ) as scrolled:
            # step PNGs in tmp, never the working directory
            _call(server, "configure", config={"artifacts_dir": str(tmp_path / "art")})
            _call(server, "start_recording", path=str(zip_path), name="pedido")
            assert _call(server, "click_at", x=10, y=20) is True
            assert _call(server, "type_text", text="hunter2", secret=True) is True
            assert server.scroll(amount=-3) is True  # not in _tools_for_tests()
            with patch.object(server.get_bot(), "find_text", return_value=None):
                # a failed step is recorded; the tool still just returns False
                assert _call(server, "click_text", text="Entrar", max_attempts=1) is False
            out = _call(server, "stop_recording", report_path=str(html_path))
        scrolled.assert_called_once()
        assert out["steps"] == 4 and out["failures"] == 1
        assert [t for t, _ in out["timeline"]] == ["click", "type_text", "scroll", "text"]
        assert out["report"] == str(html_path.resolve())
        html = html_path.read_text(encoding="utf-8")
        assert "<h1>pedido</h1>" in html
        assert "hunter2" not in html and "••••••" in html
        # the bot stops recording afterwards
        assert server.get_bot().task_session_active is False

    def test_configure_mid_recording_keeps_recording(self, server, tmp_path):
        zip_path = tmp_path / "rec.zip"
        with patch(
            "visus.desktop.core.task_executor.capture_screen",
            return_value=Image.new("RGB", (8, 8)),
        ), patch("visus.desktop.core.task_executor.TaskExecutor._perform_action"):
            art = str(tmp_path / "art")
            _call(server, "configure", config={"artifacts_dir": art})
            _call(server, "start_recording", path=str(zip_path))
            _call(server, "click_at", x=1, y=1)
            _call(server, "configure", config={"show_overlay": False, "artifacts_dir": art})
            _call(server, "click_at", x=2, y=2)
            out = _call(server, "stop_recording")
        assert out["steps"] == 2
        from visus.desktop.core.session import Session

        assert len({e["run_id"] for e in Session.replay(zip_path)}) == 1

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

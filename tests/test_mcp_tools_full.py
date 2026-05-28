"""Per-tool MCP-layer tests — covers the 18 tools that previously only
had registry coverage (the underlying library was already tested via
the regular suite, but the JSON-friendly adapter / parameter forwarding
was not exercised tool-by-tool).

Every test:
  * resets the bot singleton via ``reset_bot_for_tests``;
  * patches the underlying library function;
  * calls the MCP tool through ``_tools_for_tests()`` (the registry
    used by the FastMCP transport);
  * asserts both the **call site** (arguments forwarded correctly)
    and the **return shape** (JSON-friendly types).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot construction requires it)",
)


@pytest.fixture
def call_tool():
    """Return ``call_tool(name, **kwargs)`` for a fresh server each test."""
    from visus.desktop import mcp_server as ms

    ms.reset_bot_for_tests()
    tools = ms._tools_for_tests()

    def invoke(tool_name, /, **kwargs):
        assert tool_name in tools, f"unknown tool: {tool_name}"
        return tools[tool_name](**kwargs)

    return invoke


# ---------------------------------------------------------------------------
# Find / click — fill the find_image gap
# ---------------------------------------------------------------------------


@requires_tesseract
class TestFindImage:
    def test_find_image_returns_dict(self, call_tool):
        with patch(
            "visus.desktop.VisusBot.find_image", return_value=(11, 22, 33, 44)
        ) as fi:
            result = call_tool("find_image", image_path="btn.png")
        assert result == {"x": 11, "y": 22, "width": 33, "height": 44}
        fi.assert_called_once()

    def test_find_image_returns_none_on_miss(self, call_tool):
        with patch("visus.desktop.VisusBot.find_image", return_value=None):
            assert call_tool("find_image", image_path="missing.png") is None

    def test_find_image_forwards_confidence_and_region(self, call_tool):
        with patch(
            "visus.desktop.VisusBot.find_image", return_value=(0, 0, 1, 1)
        ) as fi:
            call_tool(
                "find_image",
                image_path="btn.png",
                confidence=0.75,
                region=[10, 20, 100, 50],
            )
        kwargs = fi.call_args.kwargs
        assert kwargs["confidence"] == 0.75
        assert tuple(kwargs["region"]) == (10, 20, 100, 50)


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


@requires_tesseract
class TestKeyboardTools:
    def test_type_text_returns_bool_and_forwards_args(self, call_tool):
        with patch(
            "visus.desktop.VisusBot.type_text", return_value=True
        ) as tt:
            ok = call_tool("type_text", text="hello", interval=0.02, delay=0.5)
        assert ok is True
        kwargs = tt.call_args.kwargs
        assert kwargs["interval"] == 0.02
        assert kwargs["delay"] == 0.5

    def test_keyboard_command_forwards_command(self, call_tool):
        with patch(
            "visus.desktop.VisusBot.keyboard_command", return_value=True
        ) as kc:
            ok = call_tool("keyboard_command", command="Ctrl+S", delay=0.1)
        assert ok is True
        args, kwargs = kc.call_args
        assert "Ctrl+S" in args or kwargs.get("command") == "Ctrl+S"


# ---------------------------------------------------------------------------
# Screen — monitors + stable wait
# ---------------------------------------------------------------------------


class TestScreenTools:
    def test_get_monitors_returns_list_of_dicts(self, call_tool):
        from visus.desktop.core.screen import Monitor

        mons = [
            Monitor(1, 0, 0, 1920, 1080, True),
            Monitor(2, 1920, 0, 1280, 1024, False),
        ]
        with patch(
            "visus.desktop.core.screen.get_monitors", return_value=mons
        ):
            result = call_tool("get_monitors")
        assert len(result) == 2
        assert result[0] == {
            "index": 1,
            "x": 0,
            "y": 0,
            "width": 1920,
            "height": 1080,
            "is_primary": True,
        }
        assert result[1]["is_primary"] is False

    def test_wait_for_stable_screen_forwards_args(self, call_tool):
        with patch(
            "visus.desktop.core.screen.wait_for_stable_screen", return_value=True
        ) as w:
            ok = call_tool(
                "wait_for_stable_screen",
                region=[10, 20, 100, 200],
                stable_for=0.7,
                timeout=5,
                poll_interval=0.05,
            )
        assert ok is True
        kwargs = w.call_args.kwargs
        assert tuple(kwargs["region"]) == (10, 20, 100, 200)
        assert kwargs["stable_for"] == 0.7
        assert kwargs["timeout"] == 5


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


class TestFileTools:
    def test_wait_for_file_forwards_args(self, call_tool):
        with patch(
            "visus.desktop.utils.files.wait_for_file", return_value=True
        ) as w:
            ok = call_tool(
                "wait_for_file", path="/tmp/x", timeout=5, poll_interval=0.1
            )
        assert ok is True
        args = w.call_args[0]
        assert args[0] == "/tmp/x"

    def test_wait_for_file_stable_forwards_args(self, call_tool):
        with patch(
            "visus.desktop.utils.files.wait_for_file_stable", return_value=True
        ) as w:
            ok = call_tool(
                "wait_for_file_stable",
                path="/tmp/y",
                timeout=10,
                stable_for=1.5,
                poll_interval=0.2,
            )
        assert ok is True
        kwargs = w.call_args.kwargs
        assert kwargs["stable_for"] == 1.5


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------


class TestClipboardTools:
    def test_get_clipboard_returns_string(self, call_tool):
        with patch(
            "visus.desktop.utils.clipboard.get_clipboard", return_value="hi"
        ):
            assert call_tool("get_clipboard") == "hi"

    def test_get_clipboard_normalizes_none_to_empty(self, call_tool):
        with patch(
            "visus.desktop.utils.clipboard.get_clipboard", return_value=None
        ):
            assert call_tool("get_clipboard") == ""

    def test_copy_to_clipboard_forwards_text(self, call_tool):
        with patch("visus.desktop.utils.clipboard.copy") as cp:
            ok = call_tool("copy_to_clipboard", text="hello")
        assert ok is True
        cp.assert_called_once_with("hello")


# ---------------------------------------------------------------------------
# OCR helper -- extract_text_from_region
# ---------------------------------------------------------------------------


@requires_tesseract
class TestExtractTextTool:
    def test_extract_text_from_region_returns_payload(self, call_tool):
        sample = [{"text": "abc", "box": (1, 2, 3, 4), "confidence": 91.0}]
        with patch(
            "visus.desktop.VisusBot.extract_text_from_region", return_value=sample
        ) as ex:
            out = call_tool(
                "extract_text_from_region",
                region=[10, 20, 100, 30],
                filter_type="numbers",
                full_data=True,
            )
        assert out == sample
        kwargs = ex.call_args.kwargs
        assert kwargs["filter_type"] == "numbers"
        assert kwargs["full_data"] is True


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class TestProcessTools:
    def test_launch_returns_int_pid(self, call_tool):
        with patch(
            "visus.desktop.core.process.launch", return_value=12345
        ) as lp:
            pid = call_tool("launch", command="notepad.exe", args=["foo.txt"])
        assert pid == 12345
        lp.assert_called_once_with("notepad.exe", ["foo.txt"])

    def test_find_process_returns_list_of_ints(self, call_tool):
        with patch(
            "visus.desktop.core.process.find_process", return_value=[1, 2, 3]
        ):
            assert call_tool("find_process", name="chrome") == [1, 2, 3]

    def test_kill_process_returns_bool(self, call_tool):
        with patch(
            "visus.desktop.core.process.kill_process", return_value=True
        ) as kp:
            ok = call_tool("kill_process", pid=999)
        assert ok is True
        kp.assert_called_once_with(999)


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------


class TestWindowTools:
    def test_focus_window_forwards_substring(self, call_tool):
        with patch(
            "visus.desktop.core.window.focus_window", return_value=True
        ) as fw:
            assert call_tool("focus_window", title_substring="Notepad") is True
        fw.assert_called_once_with("Notepad")

    def test_maximize_window(self, call_tool):
        with patch(
            "visus.desktop.core.window.maximize_window", return_value=True
        ):
            assert call_tool("maximize_window", title_substring="App") is True

    def test_minimize_window(self, call_tool):
        with patch(
            "visus.desktop.core.window.minimize_window", return_value=True
        ):
            assert call_tool("minimize_window", title_substring="App") is True

    def test_close_window(self, call_tool):
        with patch(
            "visus.desktop.core.window.close_window", return_value=True
        ):
            assert call_tool("close_window", title_substring="App") is True

    def test_window_tool_failure_returns_false(self, call_tool):
        with patch(
            "visus.desktop.core.window.focus_window", return_value=False
        ):
            assert call_tool("focus_window", title_substring="ghost") is False


# ---------------------------------------------------------------------------
# Sessions -- replay
# ---------------------------------------------------------------------------


class TestReplaySession:
    def test_replay_session_returns_events_list(self, call_tool, tmp_path):
        import json
        import zipfile

        zip_path = tmp_path / "rec.zip"
        events = [
            {"run_id": "r", "task_id": 0, "success": True},
            {"run_id": "r", "task_id": 1, "success": False, "error": "x"},
        ]
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr(
                "events.jsonl",
                "\n".join(json.dumps(e) for e in events),
            )
        out = call_tool("replay_session", zip_path=str(zip_path))
        assert out == events

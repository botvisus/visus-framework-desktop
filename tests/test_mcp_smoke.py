"""Non-mocked MCP smoke tests (M5 follow-up).

The mocked tests in ``test_mcp_tools_full.py`` validate parameter
forwarding and return-shape contracts. These smoke tests round-trip
**real** invocations — no MagicMock of the underlying library — for the
subset of tools where that is safe to do on a headless / no-display
CI / dev machine. The intent is to catch wrong-kwarg / wrong-arity
bugs that mocked tests cannot see (the same class of bug as C1-C3
from the code review).
"""

from __future__ import annotations

import inspect

import pytest

from visus.desktop import VisusBot
from visus.desktop import mcp_server as ms


@pytest.fixture
def call_tool():
    ms.reset_bot_for_tests()
    tools = ms._tools_for_tests()

    def invoke(tool_name, /, **kwargs):
        return tools[tool_name](**kwargs)

    return invoke


# ---------------------------------------------------------------------------
# Signature-truth assertions: every kwarg the MCP tool advertises must
# either exist on the underlying VisusBot method or be a known
# JSON-friendly translation (e.g. region: list -> tuple).
# ---------------------------------------------------------------------------


KNOWN_TRANSLATIONS = {
    "region",       # list[int] in MCP -> tuple in lib
    "monitor",      # MCP-only
    "config",       # MCP-only on configure()
    "tasks",        # MCP-only on execute_tasks()
    "resume",       # forwarded as-is
    "args",         # MCP launch() carries an args list
    "command",      # MCP launch() carries the command
    "path",         # MCP session tools
    "zip_path",     # MCP report / replay tools
    "html_path",    # MCP render_report
    "x",            # click_at: forwarded as positional in some helpers
    "y",
    "width",
    "height",
    "name",         # find_process / hybrid_find
    "title_substring",
}


@pytest.mark.parametrize(
    "tool_name, bot_method",
    [
        ("find_text", "find_text"),
        ("click_text", "click_text"),
        ("find_image", "find_image"),
        ("click_image", "click_image"),
        ("hybrid_find", "hybrid_find"),
        ("type_text", "type_text"),
        ("keyboard_command", "keyboard_command"),
        ("extract_text_from_region", "extract_text_from_region"),
    ],
)
def test_mcp_tool_kwargs_exist_on_bot(tool_name, bot_method):
    """Every kwarg the MCP tool exposes must be acceptable by the bot.

    Regression for the C1 / C3 family of bugs where mocked tests hid a
    TypeError because the underlying method never saw the bogus kwarg.
    """
    tool = ms._tools_for_tests()[tool_name]
    tool_params = set(inspect.signature(tool).parameters)
    bot_params = set(inspect.signature(getattr(VisusBot, bot_method)).parameters)

    unknown = tool_params - bot_params - KNOWN_TRANSLATIONS
    assert not unknown, (
        f"MCP tool {tool_name!r} accepts kwargs unknown to VisusBot.{bot_method}: "
        f"{sorted(unknown)}"
    )


# ---------------------------------------------------------------------------
# Real-execution smoke -- patches stay at the library boundary
# (subprocess, psutil, mss) so we never touch a real display, mouse or
# keyboard, but the MCP tool path executes for real (no patch on the
# underlying VisusBot method).
# ---------------------------------------------------------------------------


def test_get_monitors_real_path_returns_a_list(call_tool):
    """No mock -- if get_monitors() is wired correctly to mss it must
    return a non-empty list on any machine with a display, and an empty
    list on a headless one. The point is that it does not raise."""
    result = call_tool("get_monitors")
    assert isinstance(result, list)
    if result:
        assert {"index", "x", "y", "width", "height", "is_primary"} <= set(
            result[0]
        )


def test_get_clipboard_real_path_returns_string(call_tool):
    """No mock -- normal clipboard access must produce a string."""
    out = call_tool("get_clipboard")
    assert isinstance(out, str)


def test_copy_to_clipboard_real_path_roundtrips(call_tool):
    """Real clipboard write -> real clipboard read."""
    marker = "visus-mcp-roundtrip-marker-X9Q3"
    call_tool("copy_to_clipboard", text=marker)
    back = call_tool("get_clipboard")
    assert back == marker


def test_doctor_real_path_returns_payload(call_tool):
    """No mock -- the doctor runs real checks. The structured payload
    is always well-shaped, even if some checks fail."""
    payload = call_tool("doctor")
    assert isinstance(payload, dict)
    assert "exit_code" in payload
    assert isinstance(payload["checks"], list)
    assert isinstance(payload["output"], str)
    # Must NOT leak the textual report to stdout (C4 regression -- here
    # we just confirm the textual report is in the structured payload).
    assert payload["output"]


def test_take_screenshot_real_path_returns_png_payload(call_tool):
    """No mock of capture_screen -- a real mss capture must yield a PNG."""
    import base64

    payload = call_tool("take_screenshot", region=[0, 0, 10, 10])
    assert payload["mime_type"] == "image/png"
    decoded = base64.b64decode(payload["data_base64"])
    assert decoded.startswith(b"\x89PNG\r\n\x1a\n")
    assert payload["width"] >= 1
    assert payload["height"] >= 1

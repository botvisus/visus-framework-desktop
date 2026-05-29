"""Visus Desktop MCP server.

Exposes the visus-desktop automation primitives as MCP tools via
``FastMCP`` (the ``mcp[cli]`` package). Once running, any MCP-aware
client (Claude Desktop, Claude Code, Cursor, custom agents) can call
``find_text``, ``click_image``, ``take_screenshot``, ``execute_tasks``,
``start_recording`` / ``stop_recording`` / ``render_report``, and the
process / window / clipboard helpers.

Start the server with::

    visus-mcp                       # stdio transport (default)
    python -m visus.desktop.mcp_server

Or wire it into Claude Desktop / Code via the host config snippet
shown in ``docs/mcp.md``.

The bot is constructed lazily on first tool call and kept as a
module-level singleton so state (sessions, last extracted text,
recording handles) persists across calls in the same server lifetime.
"""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("visus-desktop")

# ---------------------------------------------------------------------------
# Lazy bot singleton + helpers
# ---------------------------------------------------------------------------

_bot = None
_recording_ctx = None


def get_bot(config: dict | None = None):
    """Return the current ``VisusBot`` singleton, creating it on demand."""
    global _bot
    if _bot is None or config is not None:
        from . import VisusBot

        _bot = VisusBot(config)
    return _bot


def reset_bot_for_tests() -> None:
    """Drop the singleton so unit tests start from a clean slate."""
    global _bot, _recording_ctx
    _bot = None
    _recording_ctx = None


def _box_to_dict(box) -> dict | None:
    """Convert a ``(x, y, w, h)`` tuple to a JSON-friendly dict."""
    if box is None:
        return None
    x, y, w, h = box
    return {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}


def _result_to_dict(result) -> dict:
    """Serialize a ``TaskResult`` (or duck-typed mock) for MCP output."""
    return {
        "task_index": int(getattr(result, "task_index", 0)),
        "task_name": getattr(result, "task_name", None),
        "success": bool(getattr(result, "success", False)),
        "attempts": int(getattr(result, "attempts", 0) or 0),
        "duration_ms": int(getattr(result, "duration_ms", 0) or 0),
        "error": getattr(result, "error", None),
        "failure_screenshot": getattr(result, "failure_screenshot", None),
    }


def _coerce_region(region):
    """Accept lists from JSON and pass tuples down to the library."""
    if region is None:
        return None
    return tuple(region)


# ---------------------------------------------------------------------------
# Configuration tool
# ---------------------------------------------------------------------------


@mcp.tool()
def configure(config: dict) -> dict:
    """Recreate the VisusBot singleton with new configuration.

    Pass any keys accepted by ``BotVisionConfig`` (e.g.
    ``confidence_threshold``, ``show_overlay``, ``log_format``,
    ``screenshot_on_failure``, ``ocr_backend``, ``matcher``,
    ``screen_cache_ms``). Returns the active config dict after the
    rebuild.
    """
    bot = get_bot(config)
    return dict(bot.config.config)


# ---------------------------------------------------------------------------
# Find / click primitives
# ---------------------------------------------------------------------------


@mcp.tool()
def find_text(
    text: str,
    region: list[int] | None = None,
    confidence_threshold: float = 75.0,
    occurrence: int = 1,
) -> dict | None:
    """Locate visible on-screen ``text`` via OCR.

    Returns the bounding box ``{x, y, width, height}`` of the match or
    ``None`` when no occurrence above ``confidence_threshold`` is found.
    """
    box = get_bot().find_text(
        text,
        region=_coerce_region(region),
        confidence_threshold=confidence_threshold,
        occurrence=occurrence,
    )
    return _box_to_dict(box)


@mcp.tool()
def click_text(
    text: str,
    region: list[int] | None = None,
    delay: float = 0,
    mouse_button: str = "left",
    occurrence: int = 1,
) -> bool:
    """Find on-screen ``text`` via OCR and click on it. Returns True on success."""
    return bool(
        get_bot().click_text(
            text,
            region=_coerce_region(region),
            delay=delay,
            mouse_button=mouse_button,
            occurrence=occurrence,
        )
    )


@mcp.tool()
def find_image(
    image_path: str,
    region: list[int] | None = None,
    confidence: float = 0.9,
) -> dict | None:
    """Locate an image template (PNG) on the current screen.

    Uses the configured matcher (cv2.matchTemplate by default, with
    pyscreeze as fallback). Returns the bounding box of the best
    match or ``None`` when score < ``confidence``.
    """
    box = get_bot().find_image(
        image_path,
        region=_coerce_region(region),
        confidence=confidence,
    )
    return _box_to_dict(box)


@mcp.tool()
def click_image(
    image_path: str,
    region: list[int] | None = None,
    confidence: float = 0.9,
    delay: float = 0,
    mouse_button: str = "left",
) -> bool:
    """Locate a template image and click on it. Returns True on success."""
    return bool(
        get_bot().click_image(
            image_path,
            region=_coerce_region(region),
            confidence=confidence,
            delay=delay,
            mouse_button=mouse_button,
        )
    )


@mcp.tool()
def click_at(
    x: int,
    y: int,
    width: int = 0,
    height: int = 0,
    mouse_button: str = "left",
    delay: float = 0,
) -> bool:
    """Click at absolute screen coordinates (no find step)."""
    return bool(
        get_bot().click_at(
            (x, y, width, height), mouse_button=mouse_button, delay=delay
        )
    )


@mcp.tool()
def hybrid_find(name: str, region: list[int] | None = None) -> dict | None:
    """Resolve ``name`` via native (pywinauto) → OCR → image, in order.

    ``name`` is matched against the foreground app's UI tree first; if
    the native layer cannot find it, OCR runs on screen text; if that
    misses and ``name`` looks like an image filename, the matcher
    searches for it as a template image.
    """
    box = get_bot().hybrid_find(name, region=_coerce_region(region))
    return _box_to_dict(box)


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


@mcp.tool()
def type_text(text: str, interval: float = 0.05, delay: float = 0) -> bool:
    """Type ``text`` into the focused field. Supports {ctrl}a, {tab}, {enter}, ..."""
    return bool(get_bot().type_text(text, interval=interval, delay=delay))


@mcp.tool()
def keyboard_command(command: str, delay: float = 0) -> bool:
    """Press a named keyboard shortcut (e.g. ``Ctrl+S``, ``Alt+F4``, ``Enter``)."""
    return bool(get_bot().keyboard_command(command, delay=delay))


# ---------------------------------------------------------------------------
# Screen / monitor / waits
# ---------------------------------------------------------------------------


@mcp.tool()
def take_screenshot(
    region: list[int] | None = None,
    monitor: int | None = None,
) -> dict:
    """Capture the screen and return a base64-encoded PNG.

    The response shape is ``{mime_type, data_base64, width, height}``.
    Pass ``region=[x, y, w, h]`` to crop, or ``monitor=N`` to target a
    specific physical monitor (1-based; see ``get_monitors``).
    """
    from .core.screen import capture_screen

    image = capture_screen(region=_coerce_region(region), monitor=monitor)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return {
        "mime_type": "image/png",
        "data_base64": encoded,
        "width": image.width,
        "height": image.height,
    }


@mcp.tool()
def save_screenshot(
    path: str,
    region: list[int] | None = None,
    monitor: int | None = None,
) -> dict:
    """Capture the screen and save it to ``path`` on disk as a PNG.

    Unlike ``take_screenshot`` (which returns base64), this writes a real
    file -- exactly what ``find_image`` / ``click_image`` need as a
    template. Parent directories are created automatically. Returns
    ``{path, width, height}`` with ``path`` resolved to an absolute path.

    Pass ``region=[x, y, w, h]`` to crop, or ``monitor=N`` (1-based) to
    target a specific physical monitor.

    Typical capture-then-locate flow, fully inside MCP::

        save_screenshot(path="btn.png", region=[740, 589, 78, 30])
        find_image(image_path="btn.png")
        click_image(image_path="btn.png")
    """
    from .core.screen import save_screenshot as _save

    written = _save(path, region=_coerce_region(region), monitor=monitor)
    abspath = os.path.abspath(written)
    from PIL import Image

    with Image.open(abspath) as img:
        width, height = img.size
    return {"path": abspath, "width": int(width), "height": int(height)}


@mcp.tool()
def get_monitors() -> list[dict]:
    """List the connected physical monitors."""
    from .core.screen import get_monitors as _get_monitors

    return [
        {
            "index": m.index,
            "x": m.x,
            "y": m.y,
            "width": m.width,
            "height": m.height,
            "is_primary": m.is_primary,
        }
        for m in _get_monitors()
    ]


@mcp.tool()
def wait_for_stable_screen(
    region: list[int] | None = None,
    stable_for: float = 0.5,
    timeout: float = 15.0,
    poll_interval: float = 0.1,
) -> bool:
    """Block until the screen stops changing or ``timeout`` elapses."""
    from .core.screen import wait_for_stable_screen as _wait

    return bool(
        _wait(
            region=_coerce_region(region),
            stable_for=stable_for,
            timeout=timeout,
            poll_interval=poll_interval,
        )
    )


# ---------------------------------------------------------------------------
# Files / clipboard
# ---------------------------------------------------------------------------


@mcp.tool()
def wait_for_file(path: str, timeout: float = 10.0, poll_interval: float = 0.5) -> bool:
    """Block until ``path`` exists and is readable, or ``timeout`` elapses."""
    from .utils.files import wait_for_file as _wait

    return bool(_wait(path, timeout=timeout, poll_interval=poll_interval))


@mcp.tool()
def wait_for_file_stable(
    path: str,
    timeout: float = 30.0,
    stable_for: float = 1.0,
    poll_interval: float = 0.5,
) -> bool:
    """Block until ``path`` exists and its size stops changing for ``stable_for``s."""
    from .utils.files import wait_for_file_stable as _wait

    return bool(
        _wait(
            path,
            timeout=timeout,
            stable_for=stable_for,
            poll_interval=poll_interval,
        )
    )


@mcp.tool()
def get_clipboard() -> str:
    """Read the current text contents of the system clipboard."""
    from .utils.clipboard import get_clipboard as _get

    return _get() or ""


@mcp.tool()
def copy_to_clipboard(text: str) -> bool:
    """Put ``text`` on the system clipboard. Returns True on success."""
    from .utils.clipboard import copy as _copy

    _copy(text)
    return True


@mcp.tool()
def extract_text_from_region(
    region: list[int],
    filter_type: str = "both",
    return_full_data: bool = False,
    confidence_threshold: float = 50.0,
) -> Any:
    """OCR-extract all text from ``region``.

    ``filter_type``: 'letters' | 'numbers' | 'both'.
    When ``return_full_data`` is true, returns
    ``[{text, confidence, box, absolute_box}, ...]`` instead of a flat
    list of strings. ``confidence_threshold`` filters OCR matches below
    that score (0-100).
    """
    return get_bot().extract_text_from_region(
        region=_coerce_region(region),
        filter_type=filter_type,
        return_full_data=return_full_data,
        confidence_threshold=confidence_threshold,
    )


# ---------------------------------------------------------------------------
# Process + window management
# ---------------------------------------------------------------------------


@mcp.tool()
def launch(command: str, args: list[str] | None = None) -> dict:
    """Launch a process. Returns ``{pid, command}``.

    On Windows uses ``subprocess.Popen`` so a real PID is captured (the
    library's ``os.startfile`` path returns no PID; for the MCP surface
    we always need one so agents can later ``kill_process(pid=…)``).
    The MCP layer accepts an explicit ``args`` list to avoid the
    space-splitting fragility of the underlying ``launch(path)`` API.
    """
    import shlex
    import subprocess

    if args is None:
        # Honour shell-style quoting via shlex on POSIX-like input; on
        # Windows ``subprocess.Popen`` accepts a string directly.
        argv = shlex.split(command, posix=(os.name != "nt"))
    else:
        argv = [command, *args]
    proc = subprocess.Popen(argv)  # noqa: S603 - caller-controlled command
    return {"pid": int(proc.pid), "command": argv}


@mcp.tool()
def find_process(name: str) -> list[dict]:
    """Return all running processes whose name contains ``name``.

    Iterates over ``psutil.process_iter`` and returns
    ``[{pid, name}]`` (case-insensitive substring match). Empty list
    when nothing matches — never raises.
    """
    import psutil

    needle = (name or "").lower()
    matches: list[dict] = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            proc_name = proc.info.get("name") or ""
            if needle and needle in proc_name.lower():
                matches.append({"pid": int(proc.pid), "name": proc_name})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return matches


@mcp.tool()
def kill_process(pid: int) -> bool:
    """Terminate the process with the given ``pid``. Returns True on success."""
    from .core.process import kill_process as _kill

    return bool(_kill(pid))


@mcp.tool()
def focus_window(title_substring: str) -> bool:
    """Bring a window matching ``title_substring`` to the foreground."""
    from .core.window import focus_window as _focus

    return bool(_focus(title_substring))


@mcp.tool()
def maximize_window(title_substring: str) -> bool:
    """Maximize a window matching ``title_substring``."""
    from .core.window import maximize_window as _max

    return bool(_max(title_substring))


@mcp.tool()
def minimize_window(title_substring: str) -> bool:
    """Minimize a window matching ``title_substring``."""
    from .core.window import minimize_window as _min

    return bool(_min(title_substring))


@mcp.tool()
def close_window(title_substring: str) -> bool:
    """Request that a window matching ``title_substring`` close."""
    from .core.window import close_window as _close

    return bool(_close(title_substring))


# ---------------------------------------------------------------------------
# Task lists
# ---------------------------------------------------------------------------


@mcp.tool()
def execute_tasks(tasks: list[dict], resume: bool = False) -> list[dict]:
    """Run a list of task dicts (see docs/api_reference.md for the schema).

    Returns one result dict per task with ``success``, ``duration_ms``,
    ``attempts``, ``error`` and ``failure_screenshot``.
    """
    results = get_bot().execute_tasks(tasks, resume=resume)
    return [_result_to_dict(r) for r in results]


# ---------------------------------------------------------------------------
# Sessions: start/stop recording + render report
# ---------------------------------------------------------------------------


@mcp.tool()
def start_recording(path: str) -> str:
    """Begin recording every task event to ``path`` (a session zip).

    Raises ``RuntimeError`` if a recording is already in progress --
    callers must explicitly ``stop_recording()`` before opening a new
    one so the previous zip is not orphaned.
    """
    global _recording_ctx
    if _recording_ctx is not None:
        raise RuntimeError(
            "recording already in progress; call stop_recording first"
        )
    from .core.session import Session

    _recording_ctx = Session.start_recording(path)
    _recording_ctx.__enter__()
    return os.path.abspath(path)


@mcp.tool()
def stop_recording() -> bool:
    """Finalize the active recording started with ``start_recording``."""
    global _recording_ctx
    if _recording_ctx is None:
        return False
    _recording_ctx.__exit__(None, None, None)
    _recording_ctx = None
    return True


@mcp.tool()
def replay_session(zip_path: str) -> list[dict]:
    """Read the events list from a session zip."""
    from .core.session import Session

    return Session.replay(zip_path)


@mcp.tool()
def render_report(zip_path: str, html_path: str) -> str:
    """Render a session zip into a styled single-file HTML report."""
    from .core.session import Session

    Session.write_report(zip_path, html_path)
    return os.path.abspath(html_path)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@mcp.tool()
def doctor() -> dict:
    """Run the health-check suite. Returns ``{exit_code, checks, output}``.

    Captures stdout so the doctor's ``[OK]/[FAIL]`` lines never leak
    into the MCP stdio JSON-RPC stream. The structured ``checks``
    array carries one entry per check for agents that want to act on
    individual failures without parsing the textual output.
    """
    import contextlib
    import io

    from . import doctor as _doctor

    # Drive the doctor's default check list ourselves so we can return
    # a structured per-check payload without scraping printf output.
    structured: list[dict] = []
    for name, fn in _doctor.DEFAULT_CHECKS:
        try:
            ok, detail = fn()
        except Exception as exc:  # never crash the diagnostic itself
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        structured.append({"name": name, "ok": bool(ok), "detail": str(detail)})

    # Still run the printf path for the text "output" field, but redirect
    # stdout so no bytes hit the MCP transport.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exit_code = _doctor.run_checks()
    return {
        "exit_code": int(exit_code),
        "checks": structured,
        "output": buf.getvalue(),
    }


# ---------------------------------------------------------------------------
# In-process testing helpers
# ---------------------------------------------------------------------------


def _tools_for_tests() -> dict:
    """Return ``{tool_name: underlying_callable}`` for unit tests."""
    return {
        name: obj
        for name, obj in globals().items()
        if callable(obj) and getattr(obj, "_visus_tool", False)
    }


# Tag every @mcp.tool callable so ``_tools_for_tests`` can find them.
# FastMCP keeps the original function importable at its module name,
# so the test harness can just call it directly.
for _name, _obj in list(globals().items()):
    if (
        callable(_obj)
        and _name in {
            "configure", "find_text", "click_text", "find_image", "click_image",
            "click_at", "hybrid_find", "type_text", "keyboard_command",
            "take_screenshot", "save_screenshot", "get_monitors",
            "wait_for_stable_screen",
            "wait_for_file", "wait_for_file_stable", "get_clipboard",
            "copy_to_clipboard", "extract_text_from_region", "launch",
            "find_process", "kill_process", "focus_window", "maximize_window",
            "minimize_window", "close_window", "execute_tasks",
            "start_recording", "stop_recording", "replay_session",
            "render_report", "doctor",
        }
    ):
        _obj._visus_tool = True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """Console-script entry point: start the MCP server on stdio."""
    mcp.run()
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via console-script
    raise SystemExit(main())

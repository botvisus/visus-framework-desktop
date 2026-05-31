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
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

_INSTRUCTIONS = """\
Visus Desktop — build reliable RPA for Windows GUI apps by control, image,
OCR, or coordinates.

THE CORE IDEA — locate with your eyes, run on images.
  The native control tree and OCR are how YOU (the agent) SEE the screen while
  BUILDING a flow: they find WHERE a thing is. `capture_element` turns a
  sighting into a reusable PNG template. The automation you hand back then
  clicks those templates with `click_image` / `click_relative_image` —
  template matching is fast and deterministic; running OCR every execution is
  slow and brittle. Re-run OCR/native at RUNTIME only for dynamic text, a
  changing layout, or to anchor a relative click. (Accessible apps are the
  exception — see step 2: act by control and skip templates entirely.)

WORKFLOW — follow in order:

1. TARGET THE WINDOW. `ensure_window(process="app.exe")` first — instant; says
   if the app is open/minimized/where, and raises it. Prefer `process=` over
   `title=` ("Notepad" can match an editor showing `notepad.py`). Its `rect`
   scopes every later search. Don't use `native_dump_tree` just to test
   existence — that's slow.

2. SEE THE UI: `native_dump_tree(window=...)`. If it returns controls, the app
   is ACCESSIBLE — act by control (`native_click` / `native_set_text` /
   `native_get_text` / `native_wait`). This is the most robust path (no pixels,
   immune to theme/DPI/resolution/language) and needs NO templates. If it
   returns `[]` (Win11 file pickers, Java Swing, some Electron), see by OCR
   instead (step 3).

3. CAPTURE EACH TARGET (build time, for the pixel path). Per button/field,
   locate AND save a template in one call:
     `capture_element(label="save", auto="Save", window="App", click=...)`
   `auto=` tries Win32-menu → OCR → UIA and writes `<label>.png` cropped from
   the EXACT box it found (`located_by` says which won); `click=True` also
   clicks. NEVER eyeball a crop or hand-pick pixels for `save_screenshot` — the
   template must come from a located box. If a locator misses, FIX it: scope
   `search_region` to where the element actually is, lower
   `confidence_threshold`, or try `text=` / `native=`. A word can repeat
   (button "Salvar" vs title "Salvar como") — scope to the button area, or
   `find_all_text` then pick the right `occurrence`. (`smart_click`/`smart_find`
   run native→image→OCR→coords in one shot and report the winner — handy when
   unsure which layer fits.)

4. ASSEMBLE THE RUNTIME FLOW (image-based — fast, repeatable):
   `click_image("save.png", region=<window rect>)` (scope so a look-alike
   elsewhere can't match); `click_relative_image` for "the target near anchor";
   `type_text` (inline tokens `{ctrl}a {tab} {enter}`) and `keyboard_command`
   (CASE-SENSITIVE: `Enter`, `Escape`, `Ctrl+S` — not "esc") for input;
   `click_at` only if the user gave coordinates.

5. SYNC, DON'T SLEEP. After a UI change `wait_for_stable_screen`; for downloads
   `wait_for_file_stable`; for a control `native_wait`.

6. VERIFY BY EFFECT, not by return value. A click returning true ≠ it worked.
   Confirm the real outcome — file mtime/size changed, `native_get_text`/
   `native_get_state` changed, screen settled. (A `wait_for_file` that only
   checks existence is a false positive when the file already existed.)

7. PACKAGE. `execute_tasks([...])` for atomic retry/backtrack; wrap in
   `start_recording`/`stop_recording` → `render_report` for an auditable HTML
   artifact.

ALWAYS scope a search with `region=[x,y,w,h]` — unscoped is the #1 cause of
wrong clicks. With leftover look-alike windows, disambiguate via `list_windows`
(foreground/largest rect, not title alone) and FOCUS the target window/dialog
before sending clicks or keys.

DIALOGS (Save As / Open / confirm): the Win11 file picker usually gives an
empty native tree → go OCR. Type the FULL path into the name field (saves
anywhere, regardless of the dialog's current folder). The default button fires
on `Enter`, BUT an overwrite confirm ("Sim"/"Não", "Yes"/"No") DEFAULTS TO
"Não" — so `Enter` cancels it; click "Sim" (focus that dialog first) or send
`Left` then `Enter`.

FULL REFERENCE ON DEMAND: this server ships two readable resources — read
`visus://docs/mcp` for the complete per-parameter tool reference, and
`visus://docs/cli` for the CLI. Pull them when a short docstring isn't enough;
no source repo required.

THE WHOLE TOOLBOX IS ALSO A CLI. Every capability is a `visus ...` shell
command with `--json` output — use it whenever driving from the shell is easier
(quick "give me eyes" probes, scripting, piping, or building a runnable script
for the user). Examples: `visus text find-all "Save" --region X,Y,W,H
--ocr rapidocr --json`, `visus native dump-tree --window "App" --json`,
`visus smart click --query "Save" --window "App"`, `visus capture save
--auto "Save" --click`. See the `visus://docs/cli` resource or `visus --help`.

RETURNS: find/get → box `{x,y,width,height}` or null; click/act → bool or
`{...,"clicked"/"found":bool}`; null/false = not found / not done.

SAFETY: confirm destructive actions (`kill_process`, `close_window`,
overwriting files) with the user first. Absolute coordinates only when the user
provided them.
"""

mcp = FastMCP("visus-desktop", instructions=_INSTRUCTIONS)

# ---------------------------------------------------------------------------
# Documentation resources — the full references ship inside the package
# (``resources/*.md``) and are exposed over MCP so any client can read them
# on demand, without the source repo. Kept in sync from ``docs/`` by a
# pre-commit hook (scripts/sync_mcp_resources.py).
# ---------------------------------------------------------------------------

_RESOURCES_DIR = Path(__file__).resolve().parent / "resources"


def _read_resource(filename: str) -> str:
    path = _RESOURCES_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - packaging/install issue
        return f"(resource '{filename}' unavailable: {exc})"


@mcp.resource(
    "visus://docs/mcp",
    name="Visus MCP tool reference",
    description=(
        "Complete reference for every visus-desktop MCP tool — all parameters, "
        "return shapes, and usage notes. Read this when you need the exact "
        "signature of a tool beyond its short docstring."
    ),
    mime_type="text/markdown",
)
def docs_mcp_reference() -> str:
    return _read_resource("mcp.md")


@mcp.resource(
    "visus://docs/cli",
    name="Visus CLI Pro reference",
    description=(
        "Complete reference for the `visus` command-line tool — every command "
        "group, flag, and `--json` output. Read this to drive a step from the "
        "shell instead of an MCP tool when that is simpler."
    ),
    mime_type="text/markdown",
)
def docs_cli_reference() -> str:
    return _read_resource("cli.md")


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
    """Change global behavior by rebuilding the bot with new config.

    USE WHEN: a default isn't working — e.g. lower ``confidence_threshold``
    if OCR misses, switch ``matcher`` to "pyscreeze" if cv2 is too strict,
    set ``ocr_backend`` to "rapidocr", or ``show_overlay`` false to hide the
    click overlay. Settings persist for the rest of the server session.
    PARAMS: a dict of ``BotVisionConfig`` keys (``confidence_threshold``,
    ``show_overlay``, ``log_format``, ``screenshot_on_failure``,
    ``ocr_backend``, ``matcher``, ``screen_cache_ms``, ...).
    RETURNS: the active config dict after the rebuild.
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
    filter_type: str = "both",
    confidence_threshold: float = 75.0,
    occurrence: int = 1,
    max_attempts: int = 3,
    backtrack: bool = False,
    wait_until_found: bool = False,
    wait_until_disappears: bool = False,
    wait_timeout: int | None = None,
) -> dict | None:
    """Find visible on-screen ``text`` via OCR; return its box (do not click).

    USE WHEN: you need the location of a text label, or to verify text is
    present, without clicking. To click it instead, use ``click_text``.
    PARAMS: ``region=[x,y,w,h]`` scopes the search (pass the window rect from
    ``ensure_window`` — strongly recommended); ``filter_type`` is
    letters|numbers|both; ``occurrence`` picks the Nth match (1-based);
    ``confidence_threshold`` is 0-100 (lower to ~50 to debug a miss).
    ROBUSTNESS: ``wait_until_found`` polls until the text APPEARS (up to
    ``wait_timeout`` s); ``wait_until_disappears`` waits until it is GONE;
    ``backtrack`` + ``max_attempts`` retry with adjusted thresholds.
    RETURNS: ``{x, y, width, height}`` of the match, or ``null``.
    """
    box = get_bot().find_text(
        text,
        region=_coerce_region(region),
        filter_type=filter_type,
        confidence_threshold=confidence_threshold,
        occurrence=occurrence,
        max_attempts=max_attempts,
        backtrack=backtrack,
        wait_until_found=wait_until_found,
        wait_until_disappears=wait_until_disappears,
        wait_timeout=wait_timeout,
    )
    return _box_to_dict(box)


@mcp.tool()
def click_text(
    text: str,
    region: list[int] | None = None,
    filter_type: str = "both",
    delay: float = 0,
    mouse_button: str = "left",
    occurrence: int = 1,
    sendtext: str | None = None,
    confidence_threshold: float | None = None,
    max_attempts: int = 3,
    backtrack: bool = False,
    wait_until_found: bool = False,
    wait_until_disappears: bool = False,
    wait_timeout: int | None = None,
) -> bool:
    """Find on-screen ``text`` via OCR and click its center.

    USE WHEN: clicking a button/link/menu identified by its visible text on
    any UI that renders text (works on Java Swing, Electron, remote desktop).
    PARAMS: ``region`` scopes the search; ``filter_type`` letters|numbers|both;
    ``occurrence`` picks the Nth match; ``mouse_button`` left|right|double|
    move_to; ``sendtext`` types a string right after the click (fill a field
    you just clicked); ``confidence_threshold`` 0-100 (default = config).
    ROBUSTNESS: ``wait_until_found`` / ``wait_until_disappears`` (+
    ``wait_timeout``) and ``backtrack`` + ``max_attempts`` — see ``find_text``.
    RETURNS: True if found and clicked, False otherwise.
    """
    return bool(
        get_bot().click_text(
            text,
            region=_coerce_region(region),
            filter_type=filter_type,
            delay=delay,
            mouse_button=mouse_button,
            occurrence=occurrence,
            sendtext=sendtext,
            confidence_threshold=confidence_threshold,
            max_attempts=max_attempts,
            backtrack=backtrack,
            wait_until_found=wait_until_found,
            wait_until_disappears=wait_until_disappears,
            wait_timeout=wait_timeout,
        )
    )


@mcp.tool()
def find_all_text(
    text: str,
    region: list[int] | None = None,
    filter_type: str = "both",
    confidence_threshold: float | None = None,
) -> list[dict]:
    """List EVERY on-screen occurrence of ``text`` via OCR (do not click).

    USE WHEN: the same label appears more than once and you must pick the
    right one by position before clicking — e.g. several "OK" buttons, or
    repeated rows. Unlike ``find_text`` (first match only), this returns
    all matches so you can choose an ``occurrence`` index for ``click_text``.
    PARAMS: ``region=[x,y,w,h]`` scopes the search (pass the window rect);
    ``filter_type`` is "letters"|"numbers"|"both"; ``confidence_threshold``
    is 0-100 (defaults to the configured threshold).
    RETURNS: a list of ``{occurrence, x, y, width, height, confidence}`` in
    reading order (top-to-bottom, left-to-right); empty if nothing matched.
    """
    matches = get_bot().find_all_text(
        text,
        region=_coerce_region(region),
        filter_type=filter_type,
        confidence_threshold=confidence_threshold,
    )
    return [
        {
            "occurrence": i,
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
            "confidence": round(float(conf), 2),
        }
        for i, (x, y, w, h, conf) in enumerate(matches, start=1)
    ]


@mcp.tool()
def find_image(
    image_path: str,
    region: list[int] | None = None,
    confidence: float = 0.9,
    specific: bool = True,
    occurrence: int = 1,
    max_attempts: int = 3,
    backtrack: bool = False,
    wait_until_found: bool = False,
    wait_until_disappears: bool = False,
    wait_timeout: int | None = None,
) -> dict | None:
    """Find a template PNG on screen; return its box (do not click).

    USE WHEN: you have a reusable template image (from ``capture_element`` or
    ``save_screenshot``) and want to locate it. To click it, use
    ``click_image``. The template must be captured at the same DPI/scale as
    the live screen.
    PARAMS: ``image_path`` is a PNG on disk; ``region`` scopes the search
    (pass the window rect); ``confidence`` is 0-1 (0.9 default; lower to ~0.7
    if a match is missed); ``specific`` true = search the region, false =
    whole screen + scale variations (helps across resolutions).
    ROBUSTNESS: ``wait_until_found`` / ``wait_until_disappears`` (+
    ``wait_timeout``) poll for the template; ``max_attempts`` retries.
    RETURNS: ``{x, y, width, height}`` of the best match, or ``null``.
    """
    box = get_bot().find_image(
        image_path,
        region=_coerce_region(region),
        confidence=confidence,
        specific=specific,
        occurrence=occurrence,
        max_attempts=max_attempts,
        backtrack=backtrack,
        wait_until_found=wait_until_found,
        wait_until_disappears=wait_until_disappears,
        wait_timeout=wait_timeout,
    )
    return _box_to_dict(box)


@mcp.tool()
def click_image(
    image_path: str,
    region: list[int] | None = None,
    confidence: float = 0.9,
    delay: float = 0,
    mouse_button: str = "left",
    specific: bool = True,
    occurrence: int = 1,
    sendtext: str | None = None,
    max_attempts: int = 3,
    backtrack: bool = False,
    wait_until_found: bool = False,
    wait_until_disappears: bool = False,
    wait_timeout: int | None = None,
) -> bool:
    """Find a template PNG on screen and click its center.

    USE WHEN: clicking a previously-captured element (the standard
    capture-then-click flow). Capture the template once with
    ``capture_element`` / ``save_screenshot``, then click it here.
    PARAMS: ``image_path`` is a PNG on disk; ``region`` scopes the search
    (pass the window rect — prevents matching a look-alike elsewhere);
    ``confidence`` 0-1; ``mouse_button`` left|right|double|move_to;
    ``specific`` true = region, false = whole screen + scales; ``sendtext``
    types a string right after the click.
    ROBUSTNESS: ``wait_until_found`` / ``wait_until_disappears`` (+
    ``wait_timeout``), ``backtrack`` + ``max_attempts``.
    RETURNS: True if found and clicked, False otherwise.
    """
    return bool(
        get_bot().click_image(
            image_path,
            region=_coerce_region(region),
            confidence=confidence,
            delay=delay,
            mouse_button=mouse_button,
            specific=specific,
            occurrence=occurrence,
            sendtext=sendtext,
            max_attempts=max_attempts,
            backtrack=backtrack,
            wait_until_found=wait_until_found,
            wait_until_disappears=wait_until_disappears,
            wait_timeout=wait_timeout,
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
    """Click at absolute screen coordinates — no find step. LAST RESORT.

    USE WHEN: the user gave you explicit coordinates, or every targeting
    method (native / capture / OCR / image) failed. Coordinates break on any
    resolution/DPI/layout change — prefer ``native_click`` / ``click_text`` /
    ``click_image`` / ``smart_click``.
    PARAMS: ``x, y`` is the point; ``width, height`` optional (clicks the
    center of the box if given); ``mouse_button`` "left"|"right"|"middle".
    RETURNS: True (the click is issued at the coordinates as given).
    """
    return bool(
        get_bot().click_at(
            (x, y, width, height), mouse_button=mouse_button, delay=delay
        )
    )


@mcp.tool()
def hybrid_find(name: str, region: list[int] | None = None) -> dict | None:
    """Find ``name`` trying native → OCR → image template, in order (no click).

    USE WHEN: you want a single find call and are unsure which method fits.
    For clicking, prefer ``smart_click`` (same idea, also clicks and reports
    which method won). ``name`` is matched against the foreground app's UI
    tree first, then as OCR text, then (if it looks like a filename) as a
    template image.
    PARAMS: ``region`` scopes the OCR/image layers.
    RETURNS: ``{x, y, width, height}`` of the first hit, or ``null``.
    """
    box = get_bot().hybrid_find(name, region=_coerce_region(region))
    return _box_to_dict(box)


@mcp.tool()
def find_relative_image(
    anchor_image: str,
    target_image: str,
    max_distance: int = 200,
    confidence: float = 0.9,
    target_region: list[int] | None = None,
    wait_until_found: bool = False,
    wait_until_disappears: bool = False,
    wait_timeout: int | None = None,
) -> dict | None:
    """Find a target template NEAR a unique anchor template (no click).

    USE WHEN: the target alone is ambiguous (many identical icons) but there is
    a unique nearby anchor — e.g. the edit field next to a specific label.
    PARAMS: ``max_distance`` caps the px gap between anchor and target (keep it
    small to reject a far-away twin); ``confidence`` is 0-1; ``target_region``
    scopes the target search.
    ROBUSTNESS: ``wait_until_found`` / ``wait_until_disappears`` (+
    ``wait_timeout``) poll for the pair.
    RETURNS: ``{x, y, width, height}`` of the closest target, or ``null``.
    """
    box = get_bot().find_relative_image(
        anchor_image, target_image, max_distance=max_distance,
        confidence=confidence, target_region=_coerce_region(target_region),
        wait_until_found=wait_until_found, wait_until_disappears=wait_until_disappears,
        wait_timeout=wait_timeout,
    )
    return _box_to_dict(box)


@mcp.tool()
def click_relative_image(
    anchor_image: str,
    target_image: str,
    max_distance: int = 200,
    confidence: float = 0.9,
    target_region: list[int] | None = None,
    delay: float = 0,
    mouse_button: str = "left",
    sendtext: str | None = None,
    max_attempts: int = 3,
    backtrack: bool = False,
    wait_until_found: bool = False,
    wait_until_disappears: bool = False,
    wait_timeout: int | None = None,
) -> bool:
    """Find a target template near a unique anchor and click it.

    Same locating logic as ``find_relative_image``; clicks the target's center.
    ``mouse_button`` is left|right|double|move_to; ``sendtext`` types a string
    right after the click. ``backtrack`` + ``max_attempts`` and the
    ``wait_until_*`` (+ ``wait_timeout``) knobs add retry/polling robustness.
    """
    return bool(
        get_bot().click_relative_image(
            anchor_image, target_image, max_distance=max_distance,
            confidence=confidence, target_region=_coerce_region(target_region),
            delay=delay, mouse_button=mouse_button, sendtext=sendtext,
            max_attempts=max_attempts, backtrack=backtrack,
            wait_until_found=wait_until_found,
            wait_until_disappears=wait_until_disappears, wait_timeout=wait_timeout,
        )
    )


@mcp.tool()
def find_all(
    image_path: str,
    region: list[int] | None = None,
    confidence: float = 0.9,
) -> list[dict]:
    """Find EVERY occurrence of one template PNG on screen (no click).

    USE WHEN: a repeated icon/element appears multiple times and you need all
    of them (e.g. every row's delete button). For repeated TEXT use
    ``find_all_text`` instead.
    RETURNS: a list of ``{x, y, width, height}`` boxes (empty if none).
    """
    from .core.locate import find_all as _find_all

    boxes = _find_all(image_path, region=_coerce_region(region), confidence=confidence)
    return [{"x": b[0], "y": b[1], "width": b[2], "height": b[3]} for b in boxes]


@mcp.tool()
def find_multiple(
    images: list[str],
    region: list[int] | None = None,
    confidence: float = 0.9,
) -> dict:
    """Locate the first match of SEVERAL template PNGs in one call (no click).

    USE WHEN: probing which of several possible elements is on screen (e.g. is
    the "Accept" or the "Decline" dialog showing?).
    PARAMS: ``images`` is a list of PNG paths; each is searched independently.
    RETURNS: ``{path: {x, y, width, height} | null}`` for each input path.
    """
    from .core.locate import find_multiple as _find_multiple

    found = _find_multiple(images, region=_coerce_region(region), confidence=confidence)
    return {
        key: (
            {"x": box[0], "y": box[1], "width": box[2], "height": box[3]}
            if box else None
        )
        for key, box in found.items()
    }


# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------


@mcp.tool()
def type_text(
    text: str, interval: float = 0.05, delay: float = 0, backtrack: bool = False
) -> bool:
    """Type ``text`` into the CURRENTLY FOCUSED field (click/focus it first).

    USE WHEN: entering free text. Embedded tokens are expanded inline:
    ``{ctrl}a`` (select all), ``{tab}``, ``{enter}``, ``{escape}``. For a
    standalone shortcut prefer ``keyboard_command``.
    PARAMS: ``interval`` is the per-character delay (raise it for apps that
    drop fast keystrokes); ``delay`` pauses after typing; ``backtrack`` retries
    within a task session on failure.
    RETURNS: True once typed. Does NOT move focus — make sure the right field
    is focused (e.g. ``native_click`` / ``click_text`` it first).
    """
    return bool(
        get_bot().type_text(text, interval=interval, delay=delay, backtrack=backtrack)
    )


@mcp.tool()
def keyboard_command(command: str, delay: float = 0, backtrack: bool = False) -> bool:
    """Press a named key or shortcut. Tokens are CASE-SENSITIVE.

    USE WHEN: pressing a single key or chord (not typing text).
    VALID TOKENS (exact case): single keys ``Enter``, ``Escape``, ``Tab``,
    ``Delete``, ``F1``..``F12``, arrow ``Up``/``Down``/``Left``/``Right``;
    chords ``Ctrl+S``, ``Ctrl+C``, ``Ctrl+V``, ``Ctrl+A``, ``Ctrl+Z``,
    ``Alt+F4``, ``Alt+Tab``, ``Shift+Tab``, ``Ctrl+T``, ``Ctrl+W``. It is
    ``Escape`` (not "esc") and ``Enter`` (not "return key").
    RETURNS: True if the token was recognized and sent; False if the token is
    not in the supported set (check the case/spelling above).
    """
    return bool(get_bot().keyboard_command(command, delay=delay, backtrack=backtrack))


# ---------------------------------------------------------------------------
# Mouse gestures (low-level, coordinate-based)
# ---------------------------------------------------------------------------


@mcp.tool()
def scroll(amount: int, x: int | None = None, y: int | None = None) -> bool:
    """Scroll the mouse wheel. Positive = up, negative = down.

    USE WHEN: a target is off-screen in a scrollable view. Optionally move to
    ``(x, y)`` first (e.g. hover the pane you want to scroll).
    RETURNS: True.
    """
    from .core.mouse_extra import scroll as _scroll

    _scroll(amount, x=x, y=y)
    return True


@mcp.tool()
def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.5,
    button: str = "left",
) -> bool:
    """Drag from ``(start_x, start_y)`` to ``(end_x, end_y)`` holding ``button``.

    USE WHEN: sliders, reordering, selection rectangles, drag-and-drop.
    RETURNS: True.
    """
    from .core.mouse_extra import drag as _drag

    _drag(start_x, start_y, end_x, end_y, duration=duration, button=button)
    return True


@mcp.tool()
def triple_click(
    x: int | None = None, y: int | None = None, interval: float = 0.05
) -> bool:
    """Triple-click at ``(x, y)`` (or the current cursor position).

    USE WHEN: selecting a whole line/paragraph before overtyping it.
    RETURNS: True.
    """
    from .core.mouse_extra import triple_click as _triple

    _triple(x=x, y=y, interval=interval)
    return True


@mcp.tool()
def move_random(x: int, y: int, max_offset: int = 3, duration: float = 0.2) -> bool:
    """Move the cursor to ``(x, y)`` with a light human-like jitter.

    USE WHEN: you want a less robotic cursor path (the move settles exactly on
    the target after a small random offset).
    RETURNS: True.
    """
    from .core.mouse_extra import move_random as _move

    _move(x, y, max_offset=max_offset, duration=duration)
    return True


@mcp.tool()
def mouse_down(
    x: int | None = None, y: int | None = None, button: str = "left"
) -> bool:
    """Press a mouse button at ``(x, y)`` (or current position) WITHOUT releasing.

    USE WHEN: a press-and-hold pattern ``drag`` doesn't cover. Pair with
    ``mouse_up``. ``button`` is left|middle|right.
    RETURNS: True.
    """
    from .core.mouse_extra import mouse_down as _down

    _down(x=x, y=y, button=button)
    return True


@mcp.tool()
def mouse_up(
    x: int | None = None, y: int | None = None, button: str = "left"
) -> bool:
    """Release a previously-pressed mouse button at ``(x, y)`` (or current position).

    RETURNS: True.
    """
    from .core.mouse_extra import mouse_up as _up

    _up(x=x, y=y, button=button)
    return True


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
def get_window(title_substring: str) -> dict | None:
    """Resolve a window by title substring; no focus required.

    Returns ``{title, pid, hwnd, x, y, width, height}`` for the first
    visible window whose title contains ``title_substring``
    (case-insensitive), or ``None``. Use it to scope a capture to the
    right window even when it is behind others -- pass its rect to
    ``take_screenshot``/``save_screenshot`` as ``region`` or to
    ``capture_element``/``find_image`` as ``search_region``/``region``.
    """
    from .core.locators import get_window as _gw

    return _gw(title_substring)


@mcp.tool()
def capture_element(
    label: str,
    auto: str | None = None,
    text: str | None = None,
    native: str | None = None,
    region: list[int] | None = None,
    window: str | None = None,
    search_region: list[int] | None = None,
    click: bool = False,
    mouse_button: str = "left",
    padding: int = 0,
    confidence_threshold: float = 75.0,
    native_timeout: float = 5.0,
    elements_dir: str = "./visus-elements",
) -> dict:
    """Locate a UI element, save a reusable template + annotated shot, click.

    The coordinate-free way to build a click-by-image flow. Provide
    EXACTLY ONE locator:
      * ``auto="Arquivo"``   -- **recommended**. Tries Win32 menu -> OCR ->
        UIA directed, in order. Win32 is instant + pixel-exact for native
        menus; OCR works on anything that renders text (incl. Java Swing,
        Electron, remote desktop); UIA directed catches accessible controls
        OCR missed. ``located_by`` in the result tells you which won.
      * ``text="Arquivo"``   -- OCR only. Optionally narrow with
        ``search_region``.
      * ``native="SaveBtn"`` -- targeted UIA only (fast child_window
        FindFirst, not a full tree walk).
      * ``region=[x,y,w,h]`` -- you already know the box.

    ``window="Bloco de Notas"`` (title substring) scopes the Win32/UIA
    strategies to that window even when it is NOT focused; without it the
    foreground window is targeted.

    Saves a tight template to ``<elements_dir>/<label>.png`` (reuse it
    later with ``find_image`` / ``click_image``) and an annotated
    full-screen PNG with a rectangle around the match to
    ``<elements_dir>/trace/<label>_annotated.png``. With ``click=True`` it
    clicks the element's center.

    Returns ``{found, label, located_by, box, template_path,
    annotated_path, clicked}``. On a miss ``found`` is False and only the
    annotated screenshot (no rectangle) is written.

    Example -- Notepad save-as, coordinate-free, fastest path first::

        capture_element(label="arquivo",     auto="Arquivo",     click=True)
        capture_element(label="salvar_como", auto="Salvar como", click=True)
        capture_element(label="btn_salvar",  auto="Salvar",      click=True)
    """
    from .core import elements as _elements

    return _elements.capture_element(
        label,
        auto=auto,
        text=text,
        native=native,
        region=_coerce_region(region),
        window=window,
        search_region=_coerce_region(search_region),
        click=click,
        mouse_button=mouse_button,
        padding=padding,
        confidence_threshold=confidence_threshold,
        native_timeout=native_timeout,
        elements_dir=elements_dir,
        bot=get_bot(),
    )


# ---------------------------------------------------------------------------
# Smart cascade -- try every technique in order (native->image->ocr->coords)
# ---------------------------------------------------------------------------


@mcp.tool()
def smart_find(
    query: str | None = None,
    image: str | None = None,
    coordinates: list[int] | None = None,
    window: str | None = None,
    pid: int | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    search_region: list[int] | None = None,
    confidence: float = 0.9,
    confidence_threshold: float = 75.0,
    order: list[str] | None = None,
    timeout: float = 5.0,
) -> dict:
    """Locate a target by cascading native -> image -> ocr -> coordinates.

    The "do whatever works" locator. Provide whatever you have: ``query``
    (used for native title + OCR text), ``image`` (a template PNG path),
    ``coordinates`` ([x, y] last resort), plus optional ``window`` /
    ``control_type`` / ``auto_id`` to sharpen the native match. A method
    is skipped when its input is missing.

    ``order`` overrides the cascade -- pass e.g. ``["native"]`` to force a
    single method, or ``["ocr", "image"]`` to reorder. Default:
    ``["native", "image", "ocr", "coordinates"]``.

    Returns ``{found, box, method, tried}`` -- ``method`` is the winner,
    ``tried`` lists what was attempted.
    """
    from .core import smart as _smart

    return _smart.smart_find(
        query, image=image, coordinates=coordinates, window=window, pid=pid,
        control_type=control_type, auto_id=auto_id,
        search_region=_coerce_region(search_region), confidence=confidence,
        confidence_threshold=confidence_threshold, order=order, timeout=timeout,
        bot=get_bot(),
    )


@mcp.tool()
def smart_click(
    query: str | None = None,
    image: str | None = None,
    coordinates: list[int] | None = None,
    window: str | None = None,
    pid: int | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    search_region: list[int] | None = None,
    button: str = "left",
    confidence: float = 0.9,
    confidence_threshold: float = 75.0,
    order: list[str] | None = None,
    timeout: float = 5.0,
    retries: int = 0,
    delay: float = 0.3,
) -> dict:
    """Click a target by cascading native -> image -> ocr -> coordinates.

    The most robust single click: each layer uses its own action (native
    UIA invoke/click, image-template click, OCR click, coordinate click),
    trying the next only when the previous misses. Same inputs as
    ``smart_find``; ``order`` forces/reorders methods. Returns
    ``{clicked, method, tried}``.

    Example -- click "Salvar", native first then image/OCR fallback::

        smart_click(query="Salvar", image="btn_salvar.png", window="Bloco")
    """
    from .core import smart as _smart

    return _smart.smart_click(
        query, image=image, coordinates=coordinates, window=window, pid=pid,
        control_type=control_type, auto_id=auto_id,
        search_region=_coerce_region(search_region), button=button,
        confidence=confidence, confidence_threshold=confidence_threshold,
        order=order, timeout=timeout, retries=retries, delay=delay,
        bot=get_bot(),
    )


# ---------------------------------------------------------------------------
# Native RPA -- operate controls through the accessibility tree (no pixel)
# ---------------------------------------------------------------------------


@mcp.tool()
def native_dump_tree(
    window: str | None = None,
    pid: int | None = None,
    max_depth: int = 3,
    timeout: float = 5.0,
) -> list[dict]:
    """Return the accessibility control tree of a window (no pixel).

    Each node is ``{depth, control_type, title, auto_id, rect}``. This is
    how an agent *sees* a native UI: dump the tree, read the control
    types / titles / automation_ids, then act on one with
    ``native_click`` / ``native_set_text``. Target by ``window`` (title
    substring) or ``pid`` (else the foreground window). Walks ``children()``
    to ``max_depth`` (fast; not the full subtree).

    Returns ``[]`` for non-accessible apps (Java Swing without the Access
    Bridge, some Electron) -- use OCR / ``capture_element`` there.
    """
    from .core.native_rpa import native_dump_tree as _fn

    return _fn(window=window, pid=pid, max_depth=max_depth, timeout=timeout)


@mcp.tool()
def native_click(
    window: str | None = None,
    pid: int | None = None,
    title: str | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    found_index: int | None = None,
    button: str = "left",
    double: bool = False,
    method: str = "auto",
    timeout: float = 5.0,
    retries: int = 0,
    delay: float = 0.3,
) -> bool:
    """Click a control by selector -- no coordinates, no image (UIA).

    Select with any of ``title`` / ``control_type`` (Button, MenuItem,
    Edit, ...) / ``auto_id`` / ``found_index``. ``method``: ``invoke``
    (UIA, no mouse), ``click`` (real mouse), ``auto`` (invoke then click).
    ``retries`` + ``delay`` re-attempt a flaky control (backtrack-style).
    Most robust automation when the app is accessible.
    """
    from .core.native_rpa import native_click as _fn

    return _fn(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, button=button,
        double=double, method=method, timeout=timeout, retries=retries,
        delay=delay,
    )


@mcp.tool()
def native_set_text(
    text: str,
    window: str | None = None,
    pid: int | None = None,
    title: str | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    found_index: int | None = None,
    timeout: float = 5.0,
    retries: int = 0,
    delay: float = 0.3,
) -> bool:
    """Set the text of an editable control by selector (UIA value pattern)."""
    from .core.native_rpa import native_set_text as _fn

    return _fn(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, text=text, timeout=timeout,
        retries=retries, delay=delay,
    )


@mcp.tool()
def native_get_text(
    window: str | None = None,
    pid: int | None = None,
    title: str | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    found_index: int | None = None,
    timeout: float = 5.0,
) -> str | None:
    """Read a control's text/value by selector. Returns the string or None."""
    from .core.native_rpa import native_get_text as _fn

    return _fn(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, timeout=timeout,
    )


@mcp.tool()
def native_get_state(
    window: str | None = None,
    pid: int | None = None,
    title: str | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    found_index: int | None = None,
    timeout: float = 5.0,
) -> dict | None:
    """Snapshot a control's state by selector.

    ``{exists, visible, enabled, checked, value, control_type, rect}``.
    ``checked`` is the UIA toggle state for checkboxes (None otherwise).
    """
    from .core.native_rpa import native_get_state as _fn

    return _fn(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, timeout=timeout,
    )


@mcp.tool()
def native_wait(
    window: str | None = None,
    pid: int | None = None,
    title: str | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    found_index: int | None = None,
    state: str = "exists",
    timeout: float = 10.0,
    poll_interval: float = 0.3,
) -> bool:
    """Wait until a control reaches ``state`` by selector.

    ``state``: ``exists`` | ``visible`` | ``enabled`` | ``ready``
    (ready = exists + visible + enabled). Returns True when satisfied.
    """
    from .core.native_rpa import native_wait as _fn

    return _fn(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, state=state,
        timeout=timeout, poll_interval=poll_interval,
    )


@mcp.tool()
def get_monitors() -> list[dict]:
    """List connected monitors so you can target one in a multi-screen setup.

    USE WHEN: the target app may be on a secondary monitor, or you need to
    pass ``monitor=N`` to ``take_screenshot`` / ``save_screenshot``.
    RETURNS: ``[{index, x, y, width, height, is_primary}]``. ``index`` is the
    1-based value those screenshot tools expect.
    """
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
def get_display_size() -> dict:
    """Return the primary display size as ``{width, height}`` (pixels).

    USE WHEN: you need the screen bounds to build a full-screen ``region`` or
    sanity-check coordinates. For multi-monitor layouts use ``get_monitors``.
    """
    from .core.screen import get_display_size as _size

    width, height = _size()
    return {"width": int(width), "height": int(height)}


@mcp.tool()
def wait_for_stable_screen(
    region: list[int] | None = None,
    stable_for: float = 0.5,
    timeout: float = 15.0,
    poll_interval: float = 0.1,
) -> bool:
    """Block until the screen stops changing — use INSTEAD of sleeping.

    USE WHEN: you triggered a UI transition (opened a dialog, navigated) and
    must wait for it to settle before the next find/click. Hard-coded sleeps
    are a smell — use this.
    PARAMS: ``region`` narrows to the area you care about (faster, less noise);
    ``stable_for`` is how long it must stay unchanged (bump to ~0.8 for
    animations); ``timeout`` caps the wait.
    RETURNS: True once stable, False if it never settled before ``timeout``.
    """
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
    """Block until ``path`` exists and is readable, or ``timeout`` elapses.

    USE WHEN: waiting for a file to appear (e.g. an export). For DOWNLOADS use
    ``wait_for_file_stable`` instead — a file can exist while still being
    written.
    RETURNS: True if the file appeared in time, False on timeout.
    """
    from .utils.files import wait_for_file as _wait

    return bool(_wait(path, timeout=timeout, poll_interval=poll_interval))


@mcp.tool()
def wait_for_file_stable(
    path: str,
    timeout: float = 30.0,
    stable_for: float = 1.0,
    poll_interval: float = 0.5,
) -> bool:
    """Block until ``path`` exists AND its size stops growing — for downloads.

    USE WHEN: waiting for a download/export to FINISH (not just start). The
    size must hold steady for ``stable_for`` seconds, so a partially-written
    file does not count as done.
    PARAMS: ``timeout`` upper bound (~300s for big downloads); ``stable_for``
    the quiet period that means "finished".
    RETURNS: True when complete, False on timeout.
    """
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
    """Read the system clipboard text.

    USE WHEN: capturing a value the user/app copied, or reading a field you
    just selected-all + copied (``keyboard_command("Ctrl+C")``) — often more
    reliable than OCR for exact text.
    RETURNS: the clipboard text, or "" if empty / non-text.
    """
    from .utils.clipboard import get_clipboard as _get

    return _get() or ""


@mcp.tool()
def copy_to_clipboard(text: str) -> bool:
    """Put ``text`` on the system clipboard (e.g. to paste with Ctrl+V).

    USE WHEN: pasting is more reliable than typing (long/Unicode text, or apps
    that drop fast keystrokes): copy here, then ``keyboard_command("Ctrl+V")``.
    RETURNS: True.
    """
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
    """Start an application/process. Returns its pid.

    USE WHEN: the target app is not running (``ensure_window`` returned
    ``found=false``). After launching, call ``ensure_window(process=...)`` to
    wait for and focus its window before acting.
    PARAMS: ``command`` is the executable (e.g. "notepad.exe"); pass distinct
    arguments as the ``args`` list (avoids space-splitting bugs).
    RETURNS: ``{pid, command}`` — keep the pid to ``kill_process`` later.

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
    """List running processes whose name contains ``name`` (no windows needed).

    USE WHEN: checking if an app is running, or finding a pid to
    ``kill_process``. To also locate/focus its WINDOW, use ``ensure_window``
    instead (it does both).
    RETURNS: ``[{pid, name}]`` (case-insensitive substring); ``[]`` if none.
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
def is_process_running(name: str) -> bool:
    """Return True if any running process's name contains ``name``.

    USE WHEN: a quick boolean check (is the app up?) without needing the pid
    list from ``find_process``.
    """
    from .core.process import is_process_running as _running

    return bool(_running(name))


@mcp.tool()
def kill_process(pid: int) -> bool:
    """Terminate a process by pid. DESTRUCTIVE — confirm with the user first.

    USE WHEN: the user asked to close/kill an app and a graceful
    ``close_window`` is not appropriate. Get the pid from ``ensure_window`` /
    ``find_process`` / ``launch``.
    RETURNS: True if terminated, False otherwise.
    """
    from .core.process import kill_process as _kill

    return bool(_kill(pid))


@mcp.tool()
def focus_window(title_substring: str) -> bool:
    """Bring a window (matched by title substring) to the foreground.

    USE WHEN: you only need to focus by title. PREFER ``ensure_window`` — it
    also restores a minimized window, matches by process (no title
    false-positives), and reports the resulting state in one call.
    RETURNS: True if a matching window was focused, False if none matched.
    """
    from .core.window import focus_window as _focus

    return bool(_focus(title_substring))


@mcp.tool()
def maximize_window(title_substring: str) -> bool:
    """Maximize a window matched by title substring.

    USE WHEN: you want the target app full-screen so more of its UI is visible
    for OCR/image steps. RETURNS True if matched, False otherwise.
    """
    from .core.window import maximize_window as _max

    return bool(_max(title_substring))


@mcp.tool()
def minimize_window(title_substring: str) -> bool:
    """Minimize a window matched by title substring.

    USE WHEN: getting a window out of the way. To bring it back later use
    ``ensure_window`` (it restores minimized windows). RETURNS True if matched.
    """
    from .core.window import minimize_window as _min

    return bool(_min(title_substring))


@mcp.tool()
def close_window(title_substring: str) -> bool:
    """Gracefully close a window (posts WM_CLOSE). Confirm with the user first.

    USE WHEN: closing an app cleanly (it may prompt to save). DESTRUCTIVE —
    get user confirmation. For a forced kill use ``kill_process``.
    RETURNS: True if a matching window received the close request.
    """
    from .core.window import close_window as _close

    return bool(_close(title_substring))


@mcp.tool()
def ensure_window(
    title: str | None = None,
    process: str | None = None,
    show: bool = True,
    foreground: bool = True,
) -> dict:
    """**Call this FIRST** before automating any app -- fast, reliable targeting.

    One call answers "is the app open? minimized? where?" AND brings it to the
    front, in a few milliseconds (pure win32 -- never use the slow
    ``native_dump_tree`` just to check if a window exists).

    Match by ``title`` (substring), ``process`` (name, e.g. ``"notepad.exe"``),
    or both. **Prefer ``process`` to avoid title false-positives** -- e.g.
    ``title="Notepad"`` can match an editor showing a file named
    ``notepad_demo.py``; ``process="notepad.exe"`` cannot.

    With ``show=True`` (default) a minimized window is restored and brought to
    the foreground, so subsequent screenshot / OCR / capture steps operate on a
    visible window (this prevents the #1 cause of automation failure: capturing
    a minimized/off-screen or wrong window). Pass ``show=False`` for a
    read-only state probe.

    Returns ``{found, running, hwnd, pid, title, minimized, maximized,
    foreground, rect, shown, matches}``. ``running`` is the process check
    (``None`` if ``process`` not given; ``True`` even when an app runs without a
    window). ``rect`` is ``null`` while minimized. ``matches`` > 1 means the
    target is ambiguous -- narrow it with ``process`` or a longer ``title``.
    Then pass ``title``/``process`` straight to ``capture_element`` /
    ``native_*`` / ``smart_*``.
    """
    from .core.window import ensure_window as _ensure

    return _ensure(
        title=title, process=process, show=show, foreground=foreground
    )


@mcp.tool()
def list_windows(
    title: str | None = None, process: str | None = None
) -> list[dict]:
    """List visible windows (read-only) matching ``title`` and/or ``process``.

    Each entry: ``{hwnd, title, pid, minimized, maximized, foreground, rect}``.
    Use it to disambiguate when ``ensure_window`` reports ``matches`` > 1, or to
    discover what is open. Fast (pure win32); focuses/moves nothing.
    """
    from .core.window import list_windows as _list

    return _list(title=title, process=process)


# ---------------------------------------------------------------------------
# Task lists
# ---------------------------------------------------------------------------


@mcp.tool()
def execute_tasks(tasks: list[dict], resume: bool = False) -> list[dict]:
    """Run a sequence of task dicts (find / click / type / keys) with retry.

    Each task is a dict. The action is chosen by an explicit ``type`` key, or
    inferred from a ``text`` / ``image`` key. Coordinates are never required.

    TASK TYPES (every field; the action is chosen by ``type`` or inferred
    from a ``text`` / ``image`` key):

      IMAGE -- find a template PNG (from ``capture_element`` /
      ``save_screenshot``) and click its center::
          {"image": "save.png", "region": [x,y,w,h], "confidence": 0.8,
           "specific": true, "mouse_button": "left"}
        ``confidence`` 0-1 (default 0.9); ``specific`` true = search only in
        ``region`` (fast), false = whole screen allowing scale variation.

      TEXT (OCR) -- find on-screen text and click it::
          {"text": "Save", "region": [x,y,w,h], "char_type": "both",
           "occurrence": 1, "sendtext": "admin"}
        ``region`` is REQUIRED for OCR; ``char_type`` = letters|numbers|both;
        ``occurrence`` = Nth match (1-based); ``sendtext`` = type this string
        right after the click (great for filling a field you just clicked).

      TYPE_TEXT -- type into the already-focused field::
          {"type": "type_text", "text": "hello", "interval": 0.05}
        Inline tokens expand: {ctrl}a, {tab}, {enter}, {escape}.

      KEYBOARD_COMMAND -- press a key/chord (token CASE-SENSITIVE)::
          {"type": "keyboard_command", "command": "Ctrl+S"}
        Valid: Enter, Escape, Tab, Delete, F1..F12, Up/Down/Left/Right,
        Ctrl+S, Ctrl+C, Ctrl+V, Ctrl+A, Ctrl+Z, Alt+F4, Alt+Tab, Shift+Tab.

      CLICK -- absolute coordinates (ONLY when the user gave them)::
          {"type": "click", "x": 100, "y": 200, "mouse_button": "left"}

      EXTRACT_TEXT -- OCR a region, no click::
          {"type": "extract_text", "region": [x,y,w,h], "char_type": "both",
           "return_full_data": false}

      RELATIVE_IMAGE -- find a target template NEAR a unique anchor, then
      click the target::
          {"type": "relative_image", "anchor_image": "cancel.png",
           "target_image": "save.png", "max_distance": 180, "confidence": 0.8,
           "specific": true, "target_region": [x,y,w,h]}
        ``max_distance`` = max px between anchor and target (keep it small to
        reject a same-text twin far away, e.g. a title vs a button);
        ``target_region`` (with ``specific``: true) scopes the target search.

    COMMON OPTIONS (on any task): ``mouse_button`` = left|right|double|move_to;
    ``delay`` = seconds to wait after the action; ``region`` = [x,y,w,h] --
    ALWAYS scope it to the target window so a match can't land elsewhere.

    WAIT & RETRY OPTIONS (the robustness knobs — use where flaky):
      * ``backtrack: true`` — if THIS task fails, jump back and re-run the
        earlier step(s), then retry. For multi-step flows where a later step
        only works if an earlier one really landed.
      * ``wait_until_found: true`` — poll until the ``image``/``text`` target
        APPEARS (up to ``wait_timeout`` s), THEN act on it. Use instead of
        sleeping after a UI transition (e.g. wait for a dialog's button to
        render before clicking it).
      * ``wait_until_disappears: true`` — for a CLICK task: click first, then
        wait until the target is GONE. The killer use: confirm a dialog
        actually closed (e.g. click Save, then wait for the dialog to vanish).
        The disappearance is checked against this task's own ``image``/``text``
        + ``region``. A find-only task (no click) instead waits for it to
        vanish before continuing.
      * ``wait_timeout`` — seconds for the two waits above (default 30).

    GOTCHAS:
      * ``wait_until_found`` / ``wait_until_disappears`` work on ``image`` /
        ``text`` tasks. A ``relative_image`` task is located-then-clicked with
        no find-stage wait — use ``backtrack`` for its retries. To still wait
        for something to disappear AFTER a relative click, add an explicit
        ``image`` + ``region`` (+ ``wait_until_disappears``) to that task: the
        post-click step checks those. (Anchor a disappearance on a UNIQUE
        element — e.g. the "Cancelar" button — so it can't match a same-text
        twin elsewhere.)
      * Always scope ``region`` to the target window/area so a template can't
        match an identical-looking element elsewhere on screen.

    Returns one result per task: ``{task_index, task_name, success, attempts,
    duration_ms, error, failure_screenshot}``. A failed step writes a
    ``failure_screenshot`` PNG to inspect.

    RECOMMENDED end-to-end flow (capture -> click-by-image -> record -> report):
      1. ``ensure_window(process="notepad.exe")``      # open/focus; read rect
      2. ``capture_element(label="save", auto="Save", window=...)``  # -> save.png
      3. ``start_recording("run.zip")``
      4. ``execute_tasks([{"image": "save.png", "region": <rect>}, ...])``
      5. ``stop_recording()`` then ``render_report("run.zip", "run.html")``
    """
    results = get_bot().execute_tasks(tasks, resume=resume)
    return [_result_to_dict(r) for r in results]


# ---------------------------------------------------------------------------
# Sessions: start/stop recording + render report
# ---------------------------------------------------------------------------


@mcp.tool()
def start_recording(path: str) -> str:
    """Start recording task events into a session zip at ``path``.

    USE WHEN: you want an auditable record + HTML report of a run. Call this,
    then run your ``execute_tasks`` / click steps, then ``stop_recording``,
    then ``render_report``. Only one recording at a time.
    RETURNS: the absolute zip path. Raises if a recording is already active
    (call ``stop_recording`` first).
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
    """Finalize the active recording and write the session zip to disk.

    USE WHEN: done with the steps you wanted to record. Always pair with a
    prior ``start_recording``; then ``render_report`` to view it.
    RETURNS: True if a recording was active and saved, False if none was open.
    """
    global _recording_ctx
    if _recording_ctx is None:
        return False
    _recording_ctx.__exit__(None, None, None)
    _recording_ctx = None
    return True


@mcp.tool()
def replay_session(zip_path: str) -> list[dict]:
    """Read back the recorded task events from a session zip.

    NOTE: this does NOT re-run the automation — it returns the recorded
    history. To execute the steps again, call ``execute_tasks`` with the same
    task list.
    USE WHEN: inspecting/asserting what a recorded run did.
    RETURNS: ``[{run_id, task_id, task_name, success, duration_ms, error,
    failure_screenshot, timestamp, logs}, ...]`` (empty if nothing was
    recorded). ``logs`` is the list of ``visus.*`` log lines captured during
    that task's window (verbosity follows the recorded ``log_level``).
    """
    from .core.session import Session

    return Session.replay(zip_path)


@mcp.tool()
def render_report(zip_path: str, html_path: str) -> str:
    """Render a session zip into a styled single-file HTML report.

    USE WHEN: producing a human-readable artifact of a recorded run (timeline,
    per-task durations/attempts, embedded failure screenshots) — the right
    thing to hand a person when a flow needs review.
    RETURNS: the absolute path of the written HTML file.
    """
    from .core.session import Session

    Session.write_report(zip_path, html_path)
    return os.path.abspath(html_path)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


@mcp.tool()
def doctor() -> dict:
    """Verify the environment is healthy (Tesseract, display, deps, pywinauto).

    USE WHEN: at the start of a session, or to diagnose why automation fails
    (e.g. OCR errors → Tesseract missing; native_* empty → pywinauto missing).
    RETURNS: ``{exit_code, checks: [{name, ok, detail}], output}``.
    ``exit_code`` != 0 means at least one check failed; read ``checks`` to see
    which and act on it (install the missing dependency, fix the path).

    Captures stdout so the doctor's ``[OK]/[FAIL]`` lines never leak
    into the MCP stdio JSON-RPC stream.
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
            "take_screenshot", "save_screenshot", "capture_element",
            "get_window", "get_monitors", "wait_for_stable_screen",
            "native_dump_tree", "native_click", "native_set_text",
            "native_get_text", "native_get_state", "native_wait",
            "smart_find", "smart_click",
            "wait_for_file", "wait_for_file_stable", "get_clipboard",
            "copy_to_clipboard", "extract_text_from_region", "launch",
            "find_process", "kill_process", "focus_window", "maximize_window",
            "minimize_window", "close_window", "ensure_window", "list_windows",
            "execute_tasks",
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

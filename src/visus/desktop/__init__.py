r"""
Visus Desktop — Advanced GUI Automation (OCR + image + native control).

A Python library to automate Windows desktop apps by four interchangeable
techniques: native accessibility control (no pixels), template-image matching,
OCR text matching, and absolute coordinates. Pick a technique, or let the
smart cascade try them in order. Everything is also exposed as an MCP server
(for AI agents) and a terminal CLI (`visus`).

═══════════════════════════════════════════════════════════════════════════════
⚠️  REQUIREMENT: TESSERACT OCR (only for the OCR features)
═══════════════════════════════════════════════════════════════════════════════
    1. Download: https://github.com/UB-Mannheim/tesseract/wiki
    2. Install to: C:\\Program Files\\Tesseract-OCR\\
    3. Add it to the system PATH
    4. Test:  tesseract --version
    (Not needed if you set config['ocr_backend']='rapidocr' or only use
     native / image / coordinate targeting. Run `visus doctor` to check.)

═══════════════════════════════════════════════════════════════════════════════
📦 INSTALLATION
═══════════════════════════════════════════════════════════════════════════════
    pip install visus-desktop                 # core
    pip install "visus-desktop[native]"       # + pywinauto (native RPA, Win)
    pip install "visus-desktop[mcp]"          # + MCP server (visus-mcp)
    pip install "visus-desktop[rapidocr]"     # + ONNX OCR backend (no Tesseract)

═══════════════════════════════════════════════════════════════════════════════
🚀 QUICKSTART
═══════════════════════════════════════════════════════════════════════════════
    >>> from visus.desktop import VisusBot, ensure_window
    >>> ensure_window(process="notepad.exe")        # open/restore/focus first
    >>> bot = VisusBot()
    >>> bot.click_text("Login")                      # OCR-find text and click
    >>> bot.type_text("admin")                        # type into focused field
    >>> bot.click_image("save_button.png")           # template-match and click

═══════════════════════════════════════════════════════════════════════════════
🧱 THE API — every public name, by category
═══════════════════════════════════════════════════════════════════════════════

▶ MAIN CLASS
    VisusBot(config=None)
        The central automation object. Key methods:
          .find_text(text, region=None, confidence_threshold=75, occurrence=1)
          .click_text(text, region=None, mouse_button="left", sendtext=None,
                      occurrence=1, backtrack=False)
          .find_image(image_path, region=None, confidence=0.9)
          .click_image(image_path, region=None, confidence=0.9,
                       mouse_button="left", backtrack=False)
          .click_at((x, y, w, h), mouse_button="left")
          .type_text(text, interval=0.05)
          .keyboard_command(command)          # "Enter", "Ctrl+S", ... (case-sensitive)
          .extract_text_from_region(region, filter_type="both", ...)
          .execute_tasks(tasks, resume=False)
          .start_task_session() / .end_task_session()   # manual backtrack scope
    BotVision   — backward-compatibility alias for VisusBot.

▶ TASK-LIST EXECUTION (run a whole flow, with retry/backtrack)
    execute_tasks(tasks, resume=False)
        tasks is a list of dicts. Shapes:
          {"image": "btn.png", "region": (x,y,w,h), "confidence": 0.9,
           "mouse_button": "left", "backtrack": True}
          {"text": "Login", "region": (x,y,w,h), "char_type": "letters",
           "sendtext": "user", "occurrence": 1}
          {"type": "type_text", "text": "hello", "interval": 0.05}
          {"type": "keyboard_command", "command": "Escape"}   # case-sensitive token
          {"type": "click", "x": 500, "y": 300, "mouse_button": "right"}
          {"type": "relative_image", "anchor_image": "icon.png",
           "target_image": "ok.png", "max_distance": 200}
          {"type": "extract_text", "region": (x,y,w,h)}
        Any task: backtrack, wait_until_found, wait_until_disappears, delay.
    click_images(...)        — legacy task-list helper (compatibility).
    run_automation(...)      — legacy `__main__` entry helper (compatibility).

▶ FIND / CLICK CONVENIENCE (one-shot, builds a temp bot internally)
    find_text(text, region=None, confidence_threshold=75, occurrence=1) -> box|None
    click_text(text, region=None, mouse_button="left", sendtext=None, ...) -> bool
    find_image(image_path, region=None, confidence=0.9) -> box|None
    click_image(image_path, region=None, confidence=0.9, ...) -> bool
    click_at(x, y, mouse_button="left") -> bool      # absolute coords (last resort)
    type_text(text) -> bool

▶ RELATIVE-IMAGE (find a target near a unique anchor)
    find_relative_image(anchor_image, target_image, max_distance=200, ...) -> box|None
    click_relative_image(anchor_image, target_image, ...) -> bool

▶ COORDINATES / KEYBOARD
    click_coordinates(x, y, mouse_button="left") -> bool
    type_text_standalone(text) -> bool
    keyboard_command_standalone(command) -> bool   # e.g. "Ctrl+S", "Escape"
    get_available_keyboard_commands() -> list[str]  # the valid, case-sensitive tokens

▶ TEXT EXTRACTION (OCR a region, no click)
    extract_text_from_region_standalone(region, filter_type="both",
        return_full_data=False, confidence_threshold=50) -> list|dict

▶ SMART CASCADE & COORDINATE-FREE CAPTURE (recommended for robustness)
    smart_find(query=None, image=None, coordinates=None, window=None,
        control_type=None, order=None, ...) -> {found, box, method, tried}
    smart_click(...) -> {clicked, method, tried}
        One call tries native → image → OCR → coordinates (configurable order)
        and reports which won. The simplest robust "find/click this".
    capture_element(label, auto=None, text=None, native=None, region=None,
        window=None, click=False, elements_dir="./visus-elements")
        -> {found, located_by, box, template_path, annotated_path, clicked}
        Locate an element (Win32 menu → OCR → UIA), save a reusable PNG
        template + an annotated screenshot, optionally click it. The
        coordinate-free way to build a click-by-image flow step by step.

▶ NATIVE RPA (no pixels — accessibility tree; needs the [native] extra)
    Import from visus.desktop.core.native_rpa:
      native_dump_tree(window=None, pid=None, max_depth=3) -> [ {depth,
          control_type, title, auto_id, rect} ]   # "see" the UI structure
      native_click(window/pid, title=, control_type=, auto_id=, method="auto")
      native_set_text(text, ...selector...) ; native_get_text(...) -> str|None
      native_get_state(...) -> {exists,visible,enabled,checked,value,rect}
      native_wait(..., state="ready", timeout=10)
    Immune to theme/DPI/resolution/language; empty on non-accessible UIs
    (Java Swing without Access Bridge) — fall back to OCR/image there.

▶ WINDOWS / PROCESSES  (fast win32; target the right app first)
    ensure_window(title=None, process=None, show=True, foreground=True)
        -> {found, running, hwnd, pid, title, minimized, maximized,
            foreground, rect, shown, matches}
        ★ CALL THIS FIRST. Is the app open / minimized / where? — and brings
        it to the front. Prefer process= (avoids title false-positives).
    list_windows(title=None, process=None) -> [ {hwnd,title,pid,minimized,...} ]
    get_window(title_substring) -> {title,pid,hwnd,x,y,width,height}|None
    focus_window / maximize_window / minimize_window / close_window(title) -> bool
    launch(command, args=None) -> pid     ;  find_process(name) -> [Process]
    is_process_running(name) -> bool      ;  kill_process(pid) -> bool

▶ SCREEN / MONITORS
    take_screenshot(region=None, monitor=None)   # PIL.Image
    save_screenshot(path, region=None, monitor=None) -> {path,width,height}
    capture_screen(region=None, monitor=None)    ;  get_display_size() -> (w,h)
    get_monitors() -> [Monitor]   ;  Monitor(index,x,y,width,height,is_primary)
    wait_for_stable_screen(region=None, stable_for=0.5, timeout=15) -> bool

▶ FILES / CLIPBOARD
    wait_for_file(path, timeout=10) -> bool
    wait_for_file_stable(path, timeout=30, stable_for=1.0) -> bool   # downloads
    copy_to_clipboard(text) / paste() / get_clipboard() -> str

▶ MOUSE (low-level gestures)
    scroll(clicks)   drag(x1,y1,x2,y2)   triple_click(x,y)
    move_random(...)   mouse_down(button)   mouse_up(button)

▶ IMAGE MAP / MULTI-MATCH
    ImageMap(mapping)            # named templates -> reuse by key
    find_all(image, region=None) ;  find_multiple(images)

▶ SESSIONS / REPORTS
    Session.start_recording(zip)  # context manager around execute_tasks
    Session.replay(zip) -> [events]            # reads events; does NOT re-run
    Session.write_report(zip, html)            # styled HTML report

▶ CORE CLASSES (advanced)
    TaskExecutor, TaskResult, OCREngine, OCRResult, ImageProcessor,
    VisualOverlay, RelativeImageDetector, KeyboardCommander, Backend

▶ CONFIG / UTILITIES
    BotVisionConfig(config_dict=None)    get_default_config() -> dict
        Hover the class for the full reference grouped by topic. Pass a
        partial dict; everything else uses the defaults. Common keys:
        confidence_threshold, retry_attempts, default_delay,
        show_overlay / overlay_color / overlay_duration / overlay_width,
        default_mouse_button, use_virtual_mouse, click_duration,
        movement_duration, matcher ("cv2"|"pyscreeze"),
        ocr_backend ("tesseract"|"rapidocr"), ocr_languages,
        wait_timeout, screenshot_delay, log_level, log_format
        ("text"|"json"), artifacts_dir, screenshot_on_failure.
        ``log_level`` and ``log_format`` take effect immediately on
        construction; mutate at runtime via cfg.config[key] = value.
    retry(...)            # decorator: re-run a callable on transient failure
    clean_text(s) / limpar_texto(s)      matches_filter(text, filter_type)
    preprocess_image_for_ocr(img)        find_text_with_multiple_preprocessing(...)
    show_overlay(region)                 locate_image_with_retry(image, ...)

▶ EXCEPTIONS
    BotVisionError (base), ImageNotFoundError, TextNotFoundError,
    TaskExecutionError, ImageProcessingError, OCRProcessingError,
    TesseractNotFoundError, InvalidRegionError, ConfigurationError,
    NotSupportedOnThisOS, NativeError

═══════════════════════════════════════════════════════════════════════════════
🤖 USING THE MCP SERVER (drive everything from an AI agent)
═══════════════════════════════════════════════════════════════════════════════
    Install + run:
        pip install "visus-desktop[mcp]"
        visus-mcp                       # stdio transport (what hosts expect)

    Wire into Claude Code / Desktop / Cursor (settings.json):
        { "mcpServers": { "visus-desktop": { "command": "visus-mcp" } } }
    Restart the host; 57 tools become available to the agent.

    Tool groups (each tool's docstring tells the agent when/how to use it):
      • Targeting:   ensure_window ★, list_windows, get_window
      • Find/click:  find_text, find_all_text, click_text, find_image,
                     click_image, click_at, hybrid_find
      • Smart/capture: smart_find, smart_click, capture_element
      • Native RPA:  native_dump_tree, native_click, native_set_text,
                     native_get_text, native_get_state, native_wait
      • Keyboard:    type_text, keyboard_command
      • Screen:      take_screenshot, save_screenshot, get_monitors,
                     wait_for_stable_screen
      • Files/clip:  wait_for_file, wait_for_file_stable, get_clipboard,
                     copy_to_clipboard, extract_text_from_region
      • Process/win: launch, find_process, kill_process, focus_window,
                     maximize_window, minimize_window, close_window
      • Task lists:  execute_tasks
      • Sessions:    start_recording, stop_recording, replay_session, render_report
      • Diagnostics: doctor, configure

    Recommended agent flow:
        ensure_window(process="app.exe")           # open/focus, get rect
        native_dump_tree(window="App")             # if accessible -> act natively
        capture_element(label="save", auto="Save", window="App", click=True)
        # or smart_click(query="Save", window="App")
        start_recording("run.zip"); execute_tasks([...]); stop_recording()
        render_report("run.zip", "run.html")
    Full reference: docs/mcp.md. Agent playbooks: skills/.

═══════════════════════════════════════════════════════════════════════════════
⌨️  TERMINAL CLI — "Visus CLI Pro" (the `visus` command)
═══════════════════════════════════════════════════════════════════════════════
    Mirrors the MCP surface in the shell (great for scripts/CI). --json on any:
        visus window ensure --process notepad.exe
        visus smart click --query "Login" --dry-run
        visus capture save --auto "Save" --click
        visus native dump-tree --window "Notepad" --json
        visus repl                  # interactive shell
        visus doctor                # environment health check
    Full reference: docs/cli.md.

═══════════════════════════════════════════════════════════════════════════════
💡 TIPS & TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════
    • Always ensure_window(process=) first; scope find/click with region=.
    • backtrack=True for fragile multi-step flows; retry() for arbitrary calls.
    • Element not found → lower confidence / widen region / re-capture template.
    • Inaccurate OCR → narrow region, filter_type="letters", or try rapidocr.
    • Wrong window clicked → match by process, not title; pass the window rect.
    • Run `visus doctor` (or the doctor MCP tool) to diagnose the environment.
"""

import functools
import logging
import time

from .core.capabilities import CapabilitiesMixin
from .core.elements import capture_element
from .core.image_map import ImageMap
from .core.image_processing import ImageProcessor, preprocess_image_for_ocr
from .core.keyboard_commands import KeyboardCommander  # NEW FEATURE
from .core.keyboard_extra import KeyboardMixin
from .core.locate import find_all, find_multiple
from .core.locators import get_window
from .core.mouse_extra import (
    drag,
    mouse_down,
    mouse_up,
    move_random,
    scroll,
    triple_click,
)
from .core.native import Backend, NativeError
from .core.ocr_engine import OCREngine, OCRResult, find_text_with_multiple_preprocessing
from .core.overlay import VisualOverlay, show_overlay
from .core.process import (
    find_process,
    is_process_running,
    kill_process,
    launch,
    open_app,
)
from .core.relative_image import RelativeImageDetector  # NEW FEATURE
from .core.screen import (
    Monitor,
    capture_screen,
    get_display_size,
    get_monitors,
    save_screenshot,
    take_screenshot,
    wait_for_stable_screen,
)
from .core.session import Session
from .core.smart import smart_click, smart_find

# Import the main classes
from .core.task_executor import TaskExecutor, TaskResult
from .core.window import (
    close_window,
    ensure_window,
    focus_window,
    list_windows,
    maximize_window,
    minimize_window,
)
from .exceptions import (
    BotVisionError,
    ConfigurationError,
    ImageNotFoundError,
    ImageProcessingError,
    InvalidRegionError,
    NotSupportedOnThisOS,
    OCRProcessingError,
    TaskExecutionError,
    TesseractNotFoundError,
    TextNotFoundError,
)
from .utils.clipboard import copy as copy_to_clipboard
from .utils.clipboard import get_clipboard, paste
from .utils.config import BotVisionConfig, get_default_config
from .utils.files import wait_for_file, wait_for_file_stable
from .utils.retry import retry
from .utils.text_filters import clean_text, limpar_texto, matches_filter

# Library version
__version__ = "0.3.0"
__author__ = "Matheus Pereira"
__email__ = "matheuszwilkdev@gmail.com"
__license__ = "MIT"

# Default logging configuration
logger = logging.getLogger(__name__)


# Keys we copy from the wrapped method's kwargs into the recorded event
# so reports show the relevant context per call (the executor's own
# ``_emit_task_event`` picks these up via ``_task_type`` / ``_task_target``).
_RECORDED_KWARGS = (
    "text", "image", "image_path", "anchor_image", "target_image",
    "command", "region", "x", "y", "confidence", "confidence_threshold",
    "mouse_button", "occurrence", "specific", "max_distance", "filter_type",
)


def _records_in_session(type_field):
    """Decorator: emit a structured ``task_event`` for the wrapped call.

    Applied to public ``VisusBot`` action methods (``click_text``,
    ``click_image``, ``type_text``, …). When the call happens inside a
    ``with bot.start_task_session()`` scope, the result is forwarded to
    :meth:`VisusBot._emit_direct_call_event` so a parallel
    :class:`Session.start_recording` zip contains the same event line +
    per-step / failure screenshot it would have captured via
    :meth:`execute_tasks`. Outside a session the wrapper is transparent.
    """
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if not getattr(self, "task_session_active", False):
                return method(self, *args, **kwargs)

            started = time.monotonic()
            try:
                result = method(self, *args, **kwargs)
            except Exception as exc:
                self._emit_direct_call_event(
                    _build_event_task(type_field, method, args, kwargs),
                    success=False,
                    started_at=started,
                    error=str(exc),
                )
                raise

            success = bool(result) if isinstance(result, bool) else True
            self._emit_direct_call_event(
                _build_event_task(type_field, method, args, kwargs),
                success=success,
                started_at=started,
                error=None if success else f"{method.__name__} returned falsy",
            )
            return result
        return wrapper
    return decorator


def _build_event_task(type_field, method, args, kwargs):
    """Construct the task dict consumed by ``_emit_task_event``.

    Maps the first positional arg to a sensible task field based on
    ``type_field`` (so ``click_text("Login")`` ends up as
    ``{"type": "text", "text": "Login"}``), and folds in any recognized
    kwargs that add useful context to the event.
    """
    task = {"type": type_field}
    if args:
        primary_key = {
            "text": "text",
            "image": "image",
            "click": "x",  # click_at / click_coordinates -- args[0] is x or location
            "relative_image": "anchor_image",
            "type_text": "text",
            "keyboard_command": "command",
        }.get(type_field)
        if primary_key:
            task[primary_key] = args[0]
        else:
            task["arg"] = args[0]
    for key in _RECORDED_KWARGS:
        if key in kwargs and key not in task:
            task[key] = kwargs[key]
    return task


def _window_in_front(window):
    """Traz ``window`` para a frente e CONFERE antes do teclado -- como uma pessoa olha
    antes de digitar. False (e nada é digitado) quando outra janela continua na frente."""
    from .core.window import foreground_title, front_window

    if front_window(window) is not None:
        return True
    logger.warning(
        f"'{window}' is not the window in front (now: '{foreground_title()}') -- "
        "nothing was typed"
    )
    return False


class VisusBot(CapabilitiesMixin, KeyboardMixin):
    """High-level GUI automation: native control, image, OCR, coordinates.

    ``VisusBot`` is the single entry point users typically import. It bundles
    the smart-cascade finder (native → image → OCR → coordinates), a
    keyboard/mouse driver (physical or virtual), an OCR engine, and a
    click-through visual overlay for debugging. Every public method is also
    exposed via the ``visus`` CLI and the ``visus-mcp`` MCP server.

    Built-in capabilities (see method docstrings for full signatures):

        **Finding things on screen**

        * :meth:`find_text` / :meth:`click_text` -- OCR-based text targeting
          with confidence threshold, character-class filter, and per-region
          search.
        * :meth:`find_image` / :meth:`click_image` -- Template matching with
          ``cv2.matchTemplate`` (falls back to pyscreeze); supports
          scale-variation search when ``specific=False``.
        * :meth:`find_relative_image` -- Find a target image near an anchor
          (good for picking the right row in a repeating grid).
        * :meth:`hybrid_find` -- Try the smart cascade in order until one
          method locates the target.

        **Acting on things**

        * :meth:`click_at` -- Click absolute (x, y, w, h) coordinates.
        * :meth:`type_text` -- Type a string into the focused field.
        * Mouse extras from :class:`CapabilitiesMixin`: :meth:`drag`,
          :meth:`triple_click`, :meth:`scroll`, :meth:`move_random`.
        * Keyboard from :class:`KeyboardMixin`: hotkeys, key presses,
          special-sequence parsing (``{ctrl}a{del}{tab}``).

        **Robustness primitives**

        * Backtrack: pass ``backtrack=True`` to retry failed steps and
          re-walk the recent action history (see
          :meth:`start_task_session`).
        * Waits: ``wait_until_found`` / ``wait_until_disappears`` /
          ``wait_timeout`` on find/click methods.
        * Failure artifacts: when ``screenshot_on_failure=True`` is set in
          the config, every uncaught failure dumps a PNG + JSON blob into
          ``artifacts_dir``.

        **Overlay (visual feedback)**

        * :meth:`configure_overlay`, :meth:`get_overlay_config`,
          :attr:`show_overlay`. On Windows the overlay is a layered
          click-through window (``WS_EX_TRANSPARENT``), so the click that
          follows lands on the host below regardless of tech (native,
          Java, Electron, browsers).

    Examples:
        Defaults are usually fine; install Tesseract and go::

            from visus.desktop import VisusBot, ensure_window
            ensure_window(process="notepad.exe")
            bot = VisusBot()
            bot.click_text("File")
            bot.type_text("hello world")

        Tune via a dict (delegated to :class:`BotVisionConfig`)::

            bot = VisusBot(config={
                "confidence_threshold": 80.0,
                "overlay_color": "green",
                "matcher": "cv2",
            })

        Or build the config object yourself for finer control::

            from visus.desktop import BotVisionConfig
            cfg = BotVisionConfig({"show_overlay": False})
            bot = VisusBot(config=cfg)
    """

    def __init__(self, config=None):
        """Initialize Visus Desktop.

        Wires the executor, OCR engine, image processor, and overlay
        master toggle. Construction is cheap; Tesseract is auto-detected only
        when ``ocr_backend == "tesseract"`` (the default backend is now
        ``rapidocr``, which uses bundled models and skips detection).

        Args:
            config: Custom settings. Three forms are accepted:

                * ``None`` (default) -- use the library defaults.
                * ``dict`` -- a mapping of any subset of the keys
                  documented on :class:`BotVisionConfig` (hover that class
                  for the full reference of every key, type, and default).
                  Common ones:

                  - ``confidence_threshold`` (float, ``75.0``): OCR cutoff.
                  - ``retry_attempts`` (int, ``3``): default retries.
                  - ``default_delay`` (float, ``1.0``): pause between
                    actions (s).
                  - ``show_overlay`` (bool, ``True``): master toggle for
                    the click-through visual overlay.
                  - ``overlay_color`` (str, ``"red"``) /
                    ``overlay_duration`` (int ms, ``1000``) /
                    ``overlay_width`` (int px, ``4``): overlay look.
                  - ``default_mouse_button`` (str, ``"left"``): one of
                    ``"left"``, ``"right"``, ``"double"``, ``"move_to"``.
                  - ``use_virtual_mouse`` (bool, ``False``): click without
                    moving the physical cursor (Windows, PostMessage).
                  - ``matcher`` (str, ``"cv2"``): ``"cv2"`` or
                    ``"pyscreeze"``.
                  - ``ocr_backend`` (str, ``"rapidocr"``): ``"rapidocr"``
                    (default) or ``"tesseract"``.
                  - ``ocr_languages`` (list[str], ``["eng"]``).
                  - ``wait_timeout`` (int s, ``30``): default wait timeout.
                  - ``log_level`` (str, ``"INFO"``) /
                    ``log_format`` (str, ``"text"`` or ``"json"``).
                  - ``artifacts_dir`` (str, ``"./visus-artifacts"``) /
                    ``screenshot_on_failure`` (bool, ``True``).

                * :class:`BotVisionConfig` -- a pre-built config object,
                  used as-is. Use this when you want to reuse the same
                  config across several bots or when you have already
                  validated it.

        Examples:
            >>> bot = VisusBot()  # defaults
            >>> bot = VisusBot(config={"overlay_color": "green"})
            >>> from visus.desktop import BotVisionConfig
            >>> cfg = BotVisionConfig({"show_overlay": False})
            >>> bot = VisusBot(config=cfg)
        """
        if isinstance(config, dict):
            self.config = BotVisionConfig(config)
        elif isinstance(config, BotVisionConfig):
            self.config = config
        else:
            self.config = get_default_config()

        # Bind the hybrid finder lazily so that monkeypatches on
        # ``self.hybrid_find`` (e.g. in tests) take effect for hybrid
        # task dispatch in the executor.
        self.executor = TaskExecutor(
            self.config,
            hybrid_finder=lambda name, **kw: self.hybrid_find(name, **kw),
        )
        self.ocr_engine = OCREngine(self.config)
        self.image_processor = ImageProcessor()

        # Overlay master toggle - accessible via the ``show_overlay`` property.
        self._show_overlay = self.config.get("show_overlay", True)

        # Backtrack system for individual methods
        self.individual_task_history = []  # History of executed methods
        self.backtrack_enabled_globally = False  # Whether it is in backtrack mode
        self.current_task_index = -1  # Index of the current task
        self.max_backtrack_attempts = 2  # Maximum backtrack attempts per task
        self.task_session_active = False  # Whether it is in an individual task session

    def _add_to_task_history(self, method_name, args, kwargs):
        """Add a method to the individual task history."""
        task_info = {
            "method": method_name,
            "args": args,
            "kwargs": kwargs,
            "index": len(self.individual_task_history),
            "success": None,
            "backtrack_attempts": 0,
            "timestamp": time.time(),
        }
        self.individual_task_history.append(task_info)
        self.current_task_index = len(self.individual_task_history) - 1
        return self.current_task_index

    def start_task_session(self):
        """Open a manual task session.

        While a session is active, direct calls like :meth:`click_text` and
        :meth:`click_image` emit the same structured ``task_event`` as
        :meth:`execute_tasks` so they show up in a
        :class:`~visus.desktop.core.session.Session` recording (events +
        per-step screenshots in the zip). Also enables the backtrack
        history for retries between methods.
        """
        import uuid

        self.task_session_active = True
        self.individual_task_history = []
        self.current_task_index = -1
        # Tag every event emitted during this session with a stable run id
        # so the resulting events.jsonl groups cleanly in reports.
        self.executor.current_run_id = uuid.uuid4().hex[:8]
        logger.debug(
            "Task session started (run_id=%s) -- direct calls will be recorded",
            self.executor.current_run_id,
        )

    def end_task_session(self):
        """Close the manual task session opened by :meth:`start_task_session`."""
        self.task_session_active = False
        successful_tasks = sum(
            1 for task in self.individual_task_history if task.get("success", False)
        )
        total_tasks = len(self.individual_task_history)
        logger.debug(
            "Task session ended: %d/%d successful tasks (run_id=%s)",
            successful_tasks, total_tasks, self.executor.current_run_id,
        )
        self.executor.current_run_id = None
        return successful_tasks, total_tasks

    def _emit_direct_call_event(
        self, task_for_event, success, started_at, location=None, error=None
    ):
        """Emit a structured ``task_event`` for a direct method call.

        No-op unless a task session is open (so direct calls outside a
        session keep their original "no zip noise" behavior). Mirrors the
        shape of :meth:`TaskExecutor._emit_task_event`, including the
        success / failure screenshot decision driven by
        ``screenshot_steps`` and ``screenshot_on_failure``.
        """
        if not getattr(self, "task_session_active", False):
            return
        if self.config.get("log_format", "text") != "json":
            return

        task_index = len(self.individual_task_history)
        self.individual_task_history.append({
            "method": task_for_event.get("type") or task_for_event.get("text") or "direct",
            "success": bool(success),
        })

        target = (
            task_for_event.get("text")
            or task_for_event.get("image")
            or task_for_event.get("type", "direct_call")
        )
        # If the caller (decorator) didn't pass a location, fall back to
        # the one stashed by ``TaskExecutor._perform_action`` -- that's
        # what direct ``click_text`` / ``click_image`` calls landed on,
        # so the screenshot can be annotated even though the public
        # method only returned bool.
        effective_location = location or getattr(
            self.executor, "last_action_location", None
        )
        result = TaskResult(task_index, bool(success), str(target), effective_location)
        result.attempts = 1
        result.duration_ms = int((time.monotonic() - started_at) * 1000)
        result.error = error
        if success and self.config.get("screenshot_steps"):
            result.step_screenshot = self.executor._capture_step_screenshot(
                task_index, location=effective_location
            )
        elif not success and self.config.get("screenshot_on_failure", True):
            result.failure_screenshot = self.executor._save_failure_screenshot(
                task_index, location=effective_location
            )
        self.executor._emit_task_event(result, task_for_event)

    # Overlay control properties
    @property
    def show_overlay(self):
        """Control whether the visual overlay is displayed before clicks."""
        return self._show_overlay

    @show_overlay.setter
    def show_overlay(self, value):
        """Set whether the visual overlay is displayed before clicks."""
        self._show_overlay = bool(value)
        # Also update the configuration
        self.config.config["show_overlay"] = self._show_overlay

    def configure_overlay(self, enabled=None, color=None, duration=None, width=None):
        """
        Conveniently configure the overlay parameters.

        Args:
            enabled (bool, optional): Whether the overlay is enabled
            color (str, optional): Overlay color - options: 'red', 'blue', 'green', 'yellow',
                                   'purple', 'orange', 'cyan', 'magenta', 'white', 'black'
            duration (int, optional): Duration in milliseconds (500-5000 recommended)
            width (int, optional): Overlay line width (1-10 recommended)

        Examples:
            >>> bot = VisusBot()
            >>> bot.configure_overlay(enabled=True, color="blue", duration=2000)
            >>> bot.configure_overlay(color="green", width=6)

        Raises:
            ValueError: If an invalid color is provided
        """
        valid_colors = [
            "red",
            "blue",
            "green",
            "yellow",
            "purple",
            "orange",
            "cyan",
            "magenta",
            "white",
            "black",
        ]

        if enabled is not None:
            self.show_overlay = enabled

        if color is not None:
            if color.lower() not in [c.lower() for c in valid_colors]:
                raise ValueError(
                    f"Invalid color '{color}'. Available colors: {', '.join(valid_colors)}"
                )
            self.config.config["overlay_color"] = color.lower()

        if duration is not None:
            if not isinstance(duration, (int, float)) or duration <= 0:
                raise ValueError(
                    f"Duration must be a positive number, received: {duration}"
                )
            if duration > 10000:
                logger.warning(
                    f"Duration too high ({duration}ms). Consider using less than 5000ms."
                )
            self.config.config["overlay_duration"] = int(duration)

        if width is not None:
            if not isinstance(width, (int, float)) or width <= 0:
                raise ValueError(f"Width must be a positive number, received: {width}")
            if width > 15:
                logger.warning(
                    f"Width too high ({width}). Consider using less than 10."
                )
            self.config.config["overlay_width"] = int(width)

    def get_overlay_config(self):
        """
        Return the current overlay configuration.

        Returns:
            dict: Overlay settings
        """
        return {
            "enabled": self.show_overlay,
            "color": self.config.config.get("overlay_color", "red"),
            "duration": self.config.config.get("overlay_duration", 1000),
            "width": self.config.config.get("overlay_width", 4),
        }

    @staticmethod
    def get_available_overlay_colors():
        """
        Return the list of available overlay colors.

        Returns:
            list: List of available colors

        Examples:
            >>> colors = VisusBot.get_available_overlay_colors()
            >>> print("Available colors:", colors)
        """
        return [
            "red",
            "blue",
            "green",
            "yellow",
            "purple",
            "orange",
            "cyan",
            "magenta",
            "white",
            "black",
        ]

    def test_overlay_colors(self, duration=1500):
        """
        Test all available overlay colors.

        Args:
            duration (int): Duration of each color in milliseconds

        Examples:
            >>> bot = VisusBot()
            >>> bot.test_overlay_colors()  # Shows each color for 1.5 seconds
        """
        from .core.overlay import VisualOverlay

        colors = self.get_available_overlay_colors()
        test_region = (400, 300, 200, 100)  # Center of the screen

        print("🎨 Testing overlay colors...")
        print("📍 Look at the center of the screen!")

        for i, color in enumerate(colors, 1):
            print(f"   {i}. Color: {color.upper()}")
            overlay = VisualOverlay(color=color, width=6, duration=duration)
            overlay.show(test_region, blocking=True)

        print("✅ Color test complete!")

    def _execute_with_individual_backtrack(
        self, method_name, method_func, *args, **kwargs
    ):
        """
        Execute an individual method with backtrack capability.

        Args:
            method_name (str): Name of the method ('click_image', 'click_text', etc.)
            method_func (callable): The method function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            bool: Result of the execution
        """
        backtrack = kwargs.get("backtrack", False)

        # If backtrack is not enabled or there is no active session, execute normally
        if not backtrack or not self.task_session_active:
            if backtrack and not self.task_session_active:
                # Auto-start a session if backtrack=True but no session is active
                self.start_task_session()

            # Remove backtrack from kwargs to avoid infinite recursion
            execution_kwargs = kwargs.copy()
            execution_kwargs.pop("backtrack", None)
            return method_func(*args, **execution_kwargs)

        # Add to the history
        task_index = self._add_to_task_history(method_name, args, kwargs)

        logger.info(
            f"🎯 Running {method_name} (task {task_index + 1}) with backtrack enabled"
        )

        # Remove backtrack from kwargs to avoid infinite recursion
        execution_kwargs = kwargs.copy()
        execution_kwargs.pop("backtrack", None)

        # Try to execute the method
        success = method_func(*args, **execution_kwargs)

        # Update the result in the history
        self.individual_task_history[task_index]["success"] = success

        if success:
            logger.info(
                f"✓ {method_name} (task {task_index + 1}) executed successfully!"
            )
            return True
        else:
            # Failed - check whether a backtrack is possible
            if task_index > 0:  # There are previous tasks
                current_task = self.individual_task_history[task_index]

                if current_task["backtrack_attempts"] < self.max_backtrack_attempts:
                    current_task["backtrack_attempts"] += 1

                    # Execute the previous task
                    prev_task = self.individual_task_history[task_index - 1]
                    logger.info(
                        f"🔄 BACKTRACK: {method_name} (task {task_index + 1}) failed. "
                        f"Re-running the previous task ({prev_task['method']}) and trying again..."
                    )

                    # Re-run the previous task
                    prev_method_name = prev_task["method"]
                    prev_method_func = getattr(self, f"_{prev_method_name}_internal")
                    prev_kwargs = prev_task["kwargs"].copy()
                    prev_kwargs.pop(
                        "backtrack", None
                    )  # Remove backtrack to avoid recursion

                    prev_success = prev_method_func(*prev_task["args"], **prev_kwargs)
                    self.individual_task_history[task_index - 1]["success"] = (
                        prev_success
                    )

                    if prev_success:
                        logger.info(
                            f"✓ Previous task ({prev_task['method']}) re-run successfully"
                        )

                        # Wait a bit and try the current task again
                        time.sleep(0.5)
                        logger.info(
                            f"🔄 Retrying {method_name} (task {task_index + 1}) after backtrack..."
                        )

                        retry_success = method_func(*args, **execution_kwargs)
                        self.individual_task_history[task_index]["success"] = (
                            retry_success
                        )

                        if retry_success:
                            logger.info(
                                f"✓ {method_name} (task {task_index + 1}) succeeded after backtrack!"
                            )
                            return True
                        else:
                            logger.warning(
                                f"✗ {method_name} (task {task_index + 1}) still failed after backtrack"
                            )
                    else:
                        logger.warning(
                            f"✗ Previous task ({prev_task['method']}) also failed on re-run"
                        )
                else:
                    logger.warning(
                        f"✗ {method_name} (task {task_index + 1}) failed after {self.max_backtrack_attempts} backtrack attempts"
                    )
            else:
                logger.warning(
                    f"✗ {method_name} (task {task_index + 1}) failed but it is the first task (no backtrack possible)"
                )

            return False

    # ------------------------------------------------------------------
    # Hybrid targeting (Phase 3 / T1)
    # ------------------------------------------------------------------

    _IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")

    # Control types queried (in order) before falling back to an
    # unfiltered descendants() walk. Filtering by control_type at the UIA
    # level is far cheaper than pulling the whole accessibility tree, so
    # clickable elements (menu items, buttons, tabs, links) are found fast.
    _NATIVE_CONTROL_TYPES = (
        "MenuItem",
        "Button",
        "TabItem",
        "ListItem",
        "Hyperlink",
        "Text",
        "Edit",
        "CheckBox",
        "RadioButton",
        "ComboBox",
    )

    def _hybrid_native_lookup(self, name, region=None, native_timeout: float = 5.0):
        """Best-effort native UIA lookup used by :meth:`hybrid_find`.

        Searches the foreground window's UIA tree (via ``pywinauto.Desktop``)
        for a control whose **title**, **automation_id**, or **control_type**
        contains ``name`` (case-insensitive). Returns an ``(x, y, w, h)`` box
        or ``None`` when not found.

        Two safeguards keep UIA's notoriously slow tree enumeration from
        hanging the caller:

        * **control_type filtering** -- cheap ``descendants(control_type=...)``
          queries for common clickable types run first; the expensive
          unfiltered walk is only the last resort.
        * **``native_timeout``** -- the whole lookup runs in a worker thread
          and is abandoned (returns ``None``) if it exceeds the timeout, so
          the hybrid chain falls back to OCR promptly instead of blocking.

        On non-Windows / missing pywinauto it returns ``None`` cleanly.
        """
        try:
            import pywinauto  # type: ignore[import-not-found]  # noqa: F401
        except ImportError:
            return None

        result: dict = {"box": None}

        def _work() -> None:
            try:
                import pywinauto as _pwa

                desktop = _pwa.Desktop(backend="uia")
                top = desktop.window(active_only=True)
                if not top.exists(timeout=0.5):
                    return
                needle = (name or "").lower()
                if not needle:
                    return

                def _match(descendant):
                    try:
                        info = descendant.element_info
                        title = (info.name or "").lower()
                        auto_id = (getattr(info, "automation_id", "") or "").lower()
                        ctrl = (getattr(info, "control_type", "") or "").lower()
                    except Exception:
                        return None
                    if needle in title or needle in auto_id or needle in ctrl:
                        try:
                            r = descendant.rectangle()
                        except Exception:
                            return None
                        return (
                            int(r.left),
                            int(r.top),
                            int(r.right - r.left),
                            int(r.bottom - r.top),
                        )
                    return None

                # Cheap filtered passes first, then the unfiltered fallback.
                queries = [
                    {"control_type": ct} for ct in self._NATIVE_CONTROL_TYPES
                ]
                queries.append({})  # unfiltered last resort
                for kwargs in queries:
                    try:
                        candidates = top.descendants(**kwargs)
                    except Exception:
                        continue
                    for descendant in candidates:
                        box = _match(descendant)
                        if box is not None:
                            result["box"] = box
                            return
            except Exception as exc:  # any pywinauto-level fault is non-fatal
                logger.debug("native hybrid lookup failed: %s", exc)

        import threading

        worker = threading.Thread(target=_work, daemon=True)
        worker.start()
        worker.join(timeout=native_timeout)
        if worker.is_alive():
            logger.debug(
                "native lookup exceeded %.1fs; giving up (falling back to OCR)",
                native_timeout,
            )
            return None
        return result["box"]

    def hybrid_find(self, name, region=None):
        """Find a target by trying native → OCR → image in order.

        Each layer is mockable; the first hit wins. Returns an
        ``(x, y, w, h)`` tuple or ``None``. The image layer is only
        attempted when ``name`` looks like an image filename (one of
        ``.png .jpg .jpeg .bmp .gif .tiff``).
        """
        # Layer 1 -- native UI handle (pywinauto).
        try:
            box = self._hybrid_native_lookup(name, region=region)
        except Exception:
            box = None
        if box:
            return box

        # Layer 2 -- OCR.
        box = self.find_text(name, region=region)
        if box:
            return box

        # Layer 3 -- image template (only for paths that look like images).
        lower = name.lower() if isinstance(name, str) else ""
        if lower.endswith(self._IMAGE_SUFFIXES):
            box = self.find_image(name, region=region)
            if box:
                return box
        return None

    def execute_tasks(self, tasks, resume: bool = False):
        """
        Execute a list of tasks sequentially.

        Args:
            tasks (list): List of dictionaries with task settings
            resume (bool): When True, skip indices already completed in a
                previous interrupted run (Phase 2 / R3). The checkpoint
                file ``<artifacts_dir>/checkpoint.json`` is invalidated
                when the task list changes shape.

        Returns:
            list: List of TaskResult objects with the result of each task

        Examples:
            >>> # Basic tasks
            >>> tasks = [
            ...     {'text': 'Login', 'region': (100, 100, 500, 300)},
            ...     {'image': 'button.png', 'delay': 2}
            ... ]
            >>>
            >>> # Advanced tasks with ALL the new features:
            >>> advanced_tasks = [
            ...     # 1. OCR text search
            ...     {
            ...         'text': 'Usuário',
            ...         'region': (100, 100, 500, 300),
            ...         'char_type': 'letters',
            ...         'confidence': 0.8,
            ...         'occurrence': 1,
            ...         'backtrack': True,
            ...         'delay': 1,
            ...         'sendtext': 'admin{tab}password{enter}'
            ...     },
            ...     # 2. Relative image search (NEW!)
            ...     {
            ...         'type': 'relative_image',
            ...         'anchor_image': 'warning_icon.png',
            ...         'target_image': 'ok_button.png',
            ...         'max_distance': 200,
            ...         'confidence': 0.9,
            ...         'target_region': (0, 0, 800, 600),
            ...         'specific': True,
            ...         'backtrack': True,
            ...         'delay': 1
            ...     },
            ...     # 3. Click on specific coordinates (NEW!)
            ...     {
            ...         'type': 'click',
            ...         'x': 100,
            ...         'y': 200,
            ...         'mouse_button': 'right',
            ...         'delay': 0.5,
            ...         'backtrack': False
            ...     },
            ...     # 4. Text typing (NEW!)
            ...     {
            ...         'type': 'type_text',
            ...         'text': 'Hello World!',
            ...         'interval': 0.05,
            ...         'delay': 1
            ...     },
            ...     # 5. Keyboard command (NEW!)
            ...     {
            ...         'type': 'keyboard_command',
            ...         'command': 'Ctrl+S',
            ...         'delay': 1
            ...     }
            ... ]
            >>>
            >>> results = bot.execute_tasks(advanced_tasks)
        """
        return self.executor.execute_tasks(tasks, resume=resume)

    def find_text(
        self,
        text,
        region=None,
        filter_type="both",
        confidence_threshold=75.0,
        occurrence=1,
        max_attempts=3,
        backtrack=False,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
        word_box=False,
        enumerate_all=False,
    ):
        """
        Find text on screen using advanced OCR with all features.

        Args:
            text (str): Text to find
            region (tuple, optional): (x, y, width, height) of the search region
            filter_type (str): Filter type ("numbers", "letters", "both") - equivalent to char_type
            confidence_threshold (float): Minimum confidence threshold
            occurrence (int): Which occurrence to look for (1 = first, 2 = second, etc.)
            enumerate_all (bool): Count ``occurrence`` over the full,
                reading-order list (what ``find_all_text`` / ``find-all`` prints)
                even when it is 1, so the Nth here is always the #N there.
                False keeps the fast early-exit search for occurrence 1.
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to try multiple times with adjustments
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            tuple: Coordinates (x, y, width, height) where the text was found, or None

        Examples:
            >>> location = bot.find_text("Confirmar", region=(0, 0, 800, 600), backtrack=True)
            >>> if location:
            ...     print(f"Text found at: {location}")
        """
        import time

        if confidence_threshold is None:  # same default as find_all_text
            confidence_threshold = self.config.confidence_threshold

        # If there are wait parameters, build a task and use the executor with wait
        if wait_until_found or wait_until_disappears:
            temp_task = {
                "text": text,
                "region": region,
                "char_type": filter_type,
                "confidence_threshold": confidence_threshold,
                "occurrence": occurrence,
                "enumerate_all": enumerate_all,
                "word_box": word_box,
                "wait_until_found": wait_until_found,
                "wait_until_disappears": wait_until_disappears,
                "wait_timeout": wait_timeout,
            }

            # Use the executor's wait-aware method
            if wait_until_found:
                return self.executor._find_text_with_wait(temp_task, 0)
            elif wait_until_disappears:
                return self.executor._find_text_with_wait(temp_task, 0)

        # Original behavior without wait
        attempts = 0
        while attempts < max_attempts:
            if region is None:
                # If no region was specified, capture the whole screen
                import pyautogui

                screen = pyautogui.screenshot()
                region = (0, 0, screen.width, screen.height)
                region_img = screen
            else:
                region_img = self.executor._capture_region(region)

            # Whether the captured image already spans the whole region
            # (so box coords are already absolute) or needs offsetting.
            _full = region == (0, 0, region_img.width, region_img.height)
            _ox, _oy = (0, 0) if _full else (region[0], region[1])

            # Backend-agnostic OCR narrative on the ``visus`` logger, so it
            # shows up in a session recording regardless of which OCR engine
            # is active (the engines' own loggers are noisy and filtered out).
            backend = self.config.get("ocr_backend", "rapidocr")
            logger.info(
                "OCR search: '%s' (occurrence=%d, filter=%s, backend=%s) in region %s",
                text, occurrence, filter_type, backend, region,
            )

            if occurrence > 1 or word_box or enumerate_all:
                # ``ocr_engine.find_text`` early-exits with only the first
                # high-confidence match (and only at line granularity), so it
                # can't serve the Nth occurrence nor a word-level box. Enumerate
                # ALL matches (deduped, reading order) and pick the Nth; pass
                # ``word_box`` so the box is tightened to the word itself.
                matches = self.ocr_engine.find_all_text(
                    region_img, text, filter_type, confidence_threshold,
                    word_box=word_box,
                )
                logger.info(
                    "OCR found %d occurrence(s) of '%s'", len(matches), text
                )
                if len(matches) >= occurrence:
                    conf, bx = matches[occurrence - 1]
                    box = (_ox + bx[0], _oy + bx[1], bx[2], bx[3])
                    logger.info(
                        "Selected occurrence %d of '%s' at %s (confidence %.1f%%)",
                        occurrence, text, box, conf,
                    )
                    return box
                logger.warning(
                    "Occurrence %d of '%s' not found (%d match(es))",
                    occurrence, text, len(matches),
                )
            else:
                found_boxes, scores, _ = self.ocr_engine.find_text(
                    region_img, text, filter_type, confidence_threshold
                )
                if found_boxes:
                    bx = found_boxes[0]
                    box = (_ox + bx[0], _oy + bx[1], bx[2], bx[3])
                    conf = scores[0] if scores else 0.0
                    logger.info(
                        "Found '%s' at %s (confidence %.1f%%)", text, box, conf
                    )
                    return box
                logger.warning("Text '%s' not found in region %s", text, region)

            # If nothing was found and backtrack is enabled, try again
            if backtrack and attempts < max_attempts - 1:
                attempts += 1
                logger.info(f"Attempt {attempts}/{max_attempts} to find '{text}'")

                # Adjust parameters for the next attempt
                confidence_threshold = max(60.0, confidence_threshold - 5.0)
                time.sleep(0.5)
            else:
                break

        return None

    def find_all_text(
        self,
        text,
        region=None,
        filter_type="both",
        confidence_threshold=None,
        word_box=False,
    ):
        """List every occurrence of ``text`` visible on screen (or in ``region``).

        Unlike :meth:`find_text` (which stops at the first high-confidence
        hit), this scans the OCR output exhaustively and returns every
        distinct match. Use it when the same string appears multiple
        times and you need to disambiguate by position -- e.g. clicking
        the second ``"OK"`` on a form, or numbering visible rows.

        Args:
            text (str): Substring to look for (case-insensitive, after
                ``filter_type`` normalization).
            region (tuple, optional): ``(x, y, w, h)`` search area in
                screen coordinates. ``None`` searches the full screen.
            filter_type (str): ``"letters"`` / ``"numbers"`` / ``"both"``.
            confidence_threshold (float, optional): Minimum OCR confidence
                (0-100). Defaults to ``config.confidence_threshold``.
            word_box (bool): When True, narrow each box from the whole OCR
                text line to just ``text`` itself (handy to locate a word
                inside a long run such as a URL). Default False keeps the full
                line box. On RapidOCR this uses the engine's native per-word
                boxes (``return_word_box``), falling back to a character-offset
                estimate if unavailable; a no-op on Tesseract, whose boxes are
                already word-level.

        Returns:
            list[tuple]: ``[(x, y, w, h, confidence), ...]`` in screen
            coordinates, sorted in reading order (top-to-bottom,
            left-to-right). Spatially overlapping detections collapse
            to a single entry that keeps the best confidence.

        Examples:
            >>> matches = bot.find_all_text("Confirm")
            >>> for i, (x, y, w, h, conf) in enumerate(matches, start=1):
            ...     print(f"  #{i} at ({x}, {y}) confidence={conf:.1f}%")
        """
        import pyautogui

        if region is None:
            screen = pyautogui.screenshot()
            region = (0, 0, screen.width, screen.height)
            region_img = screen
        else:
            region_img = self.executor._capture_region(region)

        threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else self.config.confidence_threshold
        )
        matches = self.ocr_engine.find_all_text(
            region_img, text, filter_type, threshold, word_box=word_box
        )
        # Box is relative to the captured region; convert to screen coordinates.
        return [
            (region[0] + box[0], region[1] + box[1], box[2], box[3], conf)
            for conf, box in matches
        ]

    def show_text_occurrences(
        self,
        text,
        region=None,
        filter_type="both",
        confidence_threshold=None,
        color="red",
        duration_ms=3000,
        width=3,
        word_box=False,
    ):
        """Overlay every occurrence of ``text`` on screen, numbered ``1, 2, 3...``.

        Calls :meth:`find_all_text` and draws a click-through Win32
        overlay around each match with the position number above the
        top-left corner. Overlays fade after ``duration_ms`` and do not
        intercept clicks. On non-Windows the overlays are skipped but
        the match list is still returned.

        Args:
            text (str): Substring to look for.
            region (tuple, optional): Search region.
            filter_type (str): OCR char filter.
            confidence_threshold (float, optional): Minimum confidence.
            color (str): Overlay color.
            duration_ms (int): How long each overlay stays on screen.
            width (int): Outline thickness in pixels.
            word_box (bool): Narrow each box to just ``text`` instead of the
                whole OCR line (see :meth:`find_all_text`). Default False.

        Returns:
            list[tuple]: Same shape as :meth:`find_all_text`.

        Examples:
            >>> matches = bot.show_text_occurrences("Login", duration_ms=4000)
            >>> print(f"Found {len(matches)} occurrence(s)")
        """
        from .core.overlay_win32 import show_click_through_overlay

        matches = self.find_all_text(
            text, region, filter_type, confidence_threshold, word_box=word_box
        )
        for i, (x, y, w, h, _) in enumerate(matches, start=1):
            show_click_through_overlay(
                (x, y, w, h),
                color=color,
                width=width,
                duration_ms=duration_ms,
                label=str(i),
            )
        logger.info(
            f"show_text_occurrences('{text}'): {len(matches)} match(es)"
        )
        return matches

    @_records_in_session("text")
    def click_text(
        self,
        text,
        region=None,
        filter_type="both",
        delay=0,
        mouse_button="left",
        occurrence=1,
        backtrack=False,
        max_attempts=3,
        sendtext=None,
        confidence_threshold=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
        word_box=False,
        enumerate_all=False,
    ):
        """
        Find and click on text with advanced features.

        Args:
            text (str): Text to click on
            region (tuple, optional): Search region (x, y, width, height)
            filter_type (str): Filter type ("numbers", "letters", "both")
            delay (float): Delay after the click in seconds
            mouse_button (str): Mouse click type:
                • "left" - Simple left click (default)
                • "right" - Right click
                • "double" or "double left" - Double left click
                • "move_to" - Just moves the mouse without clicking
            occurrence (int): Which occurrence to click (1=first)
            enumerate_all (bool): Count ``occurrence`` over the full,
                reading-order list (what ``find-all`` prints) even when it
                is 1, so the Nth here is always the #N there.
            backtrack (bool): Whether to use real backtracking between individual methods
            max_attempts (int): Maximum number of attempts
            sendtext (str, optional): Text to type after the click
            confidence_threshold (float, optional): Custom confidence threshold
            show_overlay (bool, optional): Whether to show the red overlay before the click
                                         If None, uses the global configuration
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            bool: True if found and clicked, False otherwise
        """
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay

        # If backtrack is True, use the individual backtrack system
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_text",
                self._click_text_internal,
                text,
                region,
                filter_type,
                delay,
                mouse_button,
                occurrence,
                max_attempts,
                sendtext,
                confidence_threshold,
                show_overlay,
                wait_until_found,
                wait_until_disappears,
                wait_timeout,
                word_box,
                enumerate_all,
                backtrack=backtrack,
            )

        # Original behavior without backtrack
        return self._click_text_internal(
            text,
            region,
            filter_type,
            delay,
            mouse_button,
            occurrence,
            max_attempts,
            sendtext,
            confidence_threshold,
            show_overlay,
            wait_until_found,
            wait_until_disappears,
            wait_timeout,
            word_box,
            enumerate_all,
        )

    def _click_text_internal(
        self,
        text,
        region=None,
        filter_type="both",
        delay=0,
        mouse_button="left",
        occurrence=1,
        max_attempts=3,
        sendtext=None,
        confidence_threshold=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
        word_box=False,
        enumerate_all=False,
    ):
        """Internal version of click_text without backtrack (for use by the backtrack system)."""
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay
        attempts = 0
        while attempts < max_attempts:
            attempts += 1

            try:
                if attempts > 1:
                    logger.info(
                        f"Attempt {attempts}/{max_attempts} to click on '{text}'"
                    )

                # Use the custom threshold if provided, otherwise use the one from the configuration
                threshold = confidence_threshold or self.config.confidence_threshold

                location = self.find_text(
                    text,
                    region,
                    filter_type,
                    threshold,
                    occurrence,
                    max_attempts=1,
                    backtrack=False,
                    wait_until_found=wait_until_found,
                    wait_until_disappears=wait_until_disappears,
                    wait_timeout=wait_timeout,
                    word_box=word_box,
                    enumerate_all=enumerate_all,
                )

                if location:
                    # Build a temporary task to use the executor
                    temp_task = {
                        "mouse_button": mouse_button,
                        "delay": delay,
                        "sendtext": sendtext,
                        "show_overlay": show_overlay,
                    }

                    try:
                        self.executor._perform_action(temp_task, location)
                        return True
                    except Exception as e:
                        logger.error(f"Error clicking on text: {e}")
                        if attempts >= max_attempts or self._virtual_click_refused():
                            # a strict virtual mouse refusing is final: another
                            # OCR pass would find the same spot and be refused again
                            return False
                        time.sleep(0.5)
                else:
                    logger.warning(f"Text '{text}' not found on attempt {attempts}")
                    if attempts < max_attempts:
                        time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error on attempt {attempts} for '{text}': {e}")
                if attempts >= max_attempts:
                    return False
                time.sleep(0.5)

        return False

    def _click_image_internal(
        self,
        image_path,
        region=None,
        confidence=0.9,
        delay=0,
        mouse_button="left",
        max_attempts=3,
        specific=True,
        sendtext=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
        occurrence=1,
        enumerate_all=False,
    ):
        """Internal version of click_image without backtrack (for use by the backtrack system)."""
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay

        # For click_image, wait_until_disappears must wait AFTER the click, not before
        # So we pass only wait_until_found to find_image
        location = self.find_image(
            image_path,
            region,
            confidence,
            max_attempts,
            False,
            specific,
            wait_until_found,
            False,
            wait_timeout,
            occurrence=occurrence,
            enumerate_all=enumerate_all,
        )  # backtrack=False for find_image

        if location:
            # Build a temporary task to use the executor
            temp_task = {
                "image": image_path,
                "region": region,
                "confidence": confidence,
                "specific": specific,
                "mouse_button": mouse_button,
                "delay": delay,
                "sendtext": sendtext,
                "show_overlay": show_overlay,
                "wait_until_disappears": wait_until_disappears,
                "wait_timeout": wait_timeout,
            }

            try:
                self.executor._perform_action(temp_task, location)
                return True
            except Exception as e:
                logger.error(f"Error clicking on image: {e}")
                return False

        return False

    def extract_text_from_region(
        self,
        region=None,
        filter_type="both",
        confidence_threshold=50.0,
        return_full_data=False,
        max_attempts=3,
        backtrack=False,
    ):
        """
        Extract all text found in a specific region of the screen.

        Args:
            region (tuple, optional): (x, y, width, height) of the region to extract text from.
                                    If None, extracts from the whole screen
            filter_type (str): Filter type for the text:
                • "numbers" - Numbers only
                • "letters" - Letters only
                • "both" - Numbers and letters (default)
            confidence_threshold (float): Minimum confidence threshold (0-100)
            return_full_data (bool): If True, returns full data with coordinates and confidence
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to try multiple times with adjustments

        Returns:
            If return_full_data=False:
                list: List of strings with all the text found
            If return_full_data=True:
                list: List of dictionaries with:
                    - 'text': Text found
                    - 'confidence': Confidence level (0-100)
                    - 'box': Coordinates (x, y, width, height)
                    - 'absolute_box': Absolute coordinates on screen

        Examples:
            Simple extraction:
            >>> texts = bot.extract_text_from_region(region=(100, 100, 400, 300))
            >>> print("Texts found:", texts)

            Extraction with full data:
            >>> data = bot.extract_text_from_region(
            ...     region=(100, 100, 400, 300),
            ...     return_full_data=True,
            ...     confidence_threshold=70.0
            ... )
            >>> for item in data:
            ...     print(f"'{item['text']}' - Confidence: {item['confidence']:.1f}% - Position: {item['absolute_box']}")

            Numbers only:
            >>> numbers = bot.extract_text_from_region(
            ...     region=(50, 50, 200, 100),
            ...     filter_type="numbers"
            ... )
        """
        import time

        attempts = 0
        while attempts < max_attempts:
            try:
                if region is None:
                    # If no region was specified, capture the whole screen
                    import pyautogui

                    screen = pyautogui.screenshot()
                    region = (0, 0, screen.width, screen.height)
                    region_img = screen
                else:
                    region_img = self.executor._capture_region(region)

                # Use the OCR engine's extract_all_text method
                ocr_results = self.ocr_engine.extract_all_text(region_img, filter_type)

                # Filter by confidence
                filtered_results = [
                    result
                    for result in ocr_results
                    if result.confidence >= confidence_threshold
                ]

                if not filtered_results and backtrack and attempts < max_attempts - 1:
                    # If nothing was found and backtrack is enabled, adjust parameters
                    attempts += 1
                    logger.info(
                        f"Attempt {attempts}/{max_attempts} for text extraction"
                    )
                    confidence_threshold = max(30.0, confidence_threshold - 10.0)
                    time.sleep(0.5)
                    continue

                if return_full_data:
                    # Return full data with absolute coordinates
                    full_data = []
                    for result in filtered_results:
                        absolute_box = (
                            (
                                region[0] + result.box[0],
                                region[1] + result.box[1],
                                result.box[2],
                                result.box[3],
                            )
                            if region != (0, 0, region_img.width, region_img.height)
                            else result.box
                        )

                        full_data.append(
                            {
                                "text": result.text,
                                "confidence": result.confidence,
                                "box": result.box,  # Coordinates relative to the region
                                "absolute_box": absolute_box,  # Absolute coordinates on screen
                            }
                        )

                    return full_data
                else:
                    # Return only the texts
                    return [result.text for result in filtered_results]

            except Exception as e:
                logger.error(f"Error on attempt {attempts} for text extraction: {e}")
                if backtrack and attempts < max_attempts - 1:
                    attempts += 1
                    time.sleep(0.5)
                else:
                    break

        # If it got here, it failed
        return [] if not return_full_data else []

    def get_last_extracted_text(self):
        """
        Get the last extracted text when used in task lists.

        Returns:
            list: Last text extraction result, or None if no extraction has been done

        Examples:
            >>> tasks = [
            ...     {
            ...         'type': 'extract_text',
            ...         'region': (100, 100, 400, 300),
            ...         'filter_type': 'both'
            ...     }
            ... ]
            >>> results = bot.execute_tasks(tasks)
            >>> extracted_texts = bot.get_last_extracted_text()
            >>> print("Texts found:", extracted_texts)
        """
        return getattr(self.executor, "last_extracted_text", None)

    def find_image(
        self,
        image_path,
        region=None,
        confidence=0.9,
        max_attempts=3,
        backtrack=False,
        specific=True,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
        scales=None,
        occurrence=1,
        enumerate_all=False,
    ):
        """
        Find an image on screen with all the advanced features.

        Args:
            image_path (str): Path to the image
            region (tuple, optional): Search region
            confidence (float): Confidence level
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to try multiple times with adjustments
            specific (bool): If True, searches in the region; if False, searches the whole screen + scale variations
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)
            scales (list, optional): List of scales to try (e.g.: [1.0, 0.95, 1.05])
            occurrence (int): Which match to return when the template appears more
                than once, 1-based in reading order (top-to-bottom, left-to-right).
                ``occurrence > 1`` enumerates every match and picks the Nth.

        Returns:
            tuple: Coordinates of the image or None
        """
        import time

        image_path = self.image_map.resolve(image_path)

        # occurrence > 1: a single-best match (the default find path) can't serve
        # the 2nd/3rd copy. Enumerate every match and pick the Nth in reading
        # order (top-to-bottom, left-to-right) -- mirrors click_text(occurrence=N).
        if occurrence and (occurrence > 1 or enumerate_all):
            from .core.locate import find_all as _find_all
            from .core.reading_order import reading_order

            # Honor `specific` exactly like the single-match path below: restrict
            # to `region` only when specific=True. With specific=False (search the
            # whole screen) a captured template carries the FIRST copy's box as
            # `region`, so restricting find_all to it would only ever see 1 match
            # and the 2nd/3rd copies (outside that box) could never be selected.
            search_region = tuple(region) if (specific and region) else None
            # Same numbering as `image find-all`; and honor wait_until_found here
            # too (this branch used to return before the wait handling below).
            deadline = None
            if wait_until_found:
                timeout = wait_timeout if wait_timeout is not None else self.config.get("wait_timeout", 30)
                deadline = time.monotonic() + float(timeout)
            while True:
                boxes = reading_order(
                    _find_all(image_path, region=search_region, confidence=confidence)
                )
                if len(boxes) >= occurrence or deadline is None or time.monotonic() >= deadline:
                    break
                time.sleep(0.5)
            logger.info(
                "Image '%s' found %d occurrence(s)", image_path, len(boxes)
            )
            if len(boxes) >= occurrence:
                box = boxes[occurrence - 1]
                logger.info(
                    "Selected image occurrence %d at %s", occurrence, box
                )
                return box
            logger.warning(
                "Image occurrence %d of '%s' not found (%d match(es))",
                occurrence, image_path, len(boxes),
            )
            return None

        if scales is None:
            scales = [1.0, 0.95, 1.05] if not specific else [1.0]

        # If there are wait parameters, build a task and use the executor with wait
        if wait_until_found or wait_until_disappears:
            temp_task = {
                "image": image_path,
                "region": region,
                "confidence": confidence,
                "specific": specific,
                "wait_until_found": wait_until_found,
                "wait_until_disappears": wait_until_disappears,
                "wait_timeout": wait_timeout,
            }

            # Use the executor's wait-aware method
            return self.executor._find_image_with_wait(temp_task, 0)

        # Original behavior without wait
        attempts = 0
        while attempts < max_attempts:
            try:
                # Try with different scales if not specific
                for scale in scales:
                    try:
                        if scale != 1.0 and not specific:
                            # Resize the reference image
                            import os

                            from PIL import Image

                            ref_img = Image.open(image_path)
                            new_width = int(ref_img.width * scale)
                            new_height = int(ref_img.height * scale)
                            scaled_img = ref_img.resize((new_width, new_height))

                            # Save temporarily
                            temp_path = f"temp_scaled_{scale}_{attempts}.png"
                            scaled_img.save(temp_path)

                            # NEW LOGIC: specific controls where to search
                            if specific and region:
                                # If specific AND there is a region, search in the region
                                location = self.executor._locate_image_with_retry(
                                    temp_path, region, confidence
                                )
                            else:
                                # If not specific OR no region, search the whole screen
                                location = self.executor._locate_image_with_retry(
                                    temp_path, None, confidence
                                )

                            # Remove the temporary file
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        else:
                            # NEW LOGIC: specific controls where to search
                            if specific and region:
                                # If specific AND there is a region, search in the region
                                logger.info(
                                    f"Searching for image in region {region} (specific=True)"
                                )
                                location = self.executor._locate_image_with_retry(
                                    image_path, region, confidence
                                )
                            else:
                                # If not specific OR no region, search the whole screen
                                logger.info(
                                    "Searching for image across the whole screen (specific=False)"
                                )
                                location = self.executor._locate_image_with_retry(
                                    image_path, None, confidence
                                )

                        if location:
                            return location

                    except Exception as e:
                        logger.debug(f"Error searching for image at scale {scale}: {e}")
                        continue
                # If nothing was found and backtrack is enabled, adjust parameters
                if backtrack and attempts < max_attempts - 1:
                    attempts += 1
                    logger.info(f"Attempt {attempts}/{max_attempts} to find the image")

                    # Gradually lower the confidence
                    confidence = max(0.7, confidence - 0.05)
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                logger.error(f"Error searching for image: {e}")
                if not backtrack:
                    break

        return None

    @_records_in_session("image")
    def click_image(
        self,
        image_path,
        region=None,
        confidence=0.9,
        delay=0,
        mouse_button="left",
        max_attempts=3,
        backtrack=False,
        specific=True,
        sendtext=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
        occurrence=1,
        enumerate_all=False,
    ):
        """
        Find and click on an image with all the advanced features.

        Args:
            image_path (str): Path to the image
            region (tuple, optional): Search region (x, y, width, height)
            confidence (float): Confidence level (0.0-1.0)
            delay (float): Delay after the click in seconds
            mouse_button (str): Mouse click type:
                • "left" - Simple left click (default)
                • "right" - Right click
                • "double" or "double left" - Double left click
                • "move_to" - Just moves the mouse without clicking
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to use real backtracking between individual methods
            specific (bool): If True, exact search; if False, allows variations
            sendtext (str, optional): Text to type after the click
            show_overlay (bool, optional): Whether to show the red overlay before the click
                                         If None, uses the global configuration
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            bool: True if found and clicked, False otherwise
        """
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay

        image_path = self.image_map.resolve(image_path)

        # If backtrack is True, use the individual backtrack system
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_image",
                self._click_image_internal,
                image_path,
                region,
                confidence,
                delay,
                mouse_button,
                max_attempts,
                specific,
                sendtext,
                show_overlay,
                wait_until_found,
                wait_until_disappears,
                wait_timeout,
                occurrence,
                enumerate_all,
                backtrack=backtrack,
            )

        # Original behavior without backtrack
        return self._click_image_internal(
            image_path,
            region,
            confidence,
            delay,
            mouse_button,
            max_attempts,
            specific,
            sendtext,
            show_overlay,
            wait_until_found,
            wait_until_disappears,
            wait_timeout,
            occurrence,
            enumerate_all,
        )

    def _virtual_click_refused(self):
        """True when the last click was refused by a strict virtual mouse
        (``virtual_mouse_strict``): the window would not take a synthetic click
        and the real cursor was, on purpose, left alone."""
        mouse = getattr(getattr(self, "executor", None), "virtual_mouse", None)
        return getattr(mouse, "last_click", None) == "virtual-refused"

    @_records_in_session("click")
    def click_at(self, location, mouse_button="left", delay=0, show_overlay=None):
        """
        Click on specific screen coordinates.

        Args:
            location (tuple): (x, y, width, height) of the location
            mouse_button (str): Mouse button ("left", "right", "double", "move_to")
            delay (float): Delay after the click
            show_overlay (bool, optional): Whether to show the red overlay before the click
                                         If None, uses the global configuration

        Returns:
            bool: True if clicked successfully

        Examples:
            >>> bot.click_at((100, 200, 50, 30), mouse_button='left', delay=1)
        """
        try:
            # Use the global configuration if not specified
            if show_overlay is None:
                show_overlay = self.config.show_overlay

            # Build a temporary task to use the executor
            temp_task = {
                "mouse_button": mouse_button,
                "delay": delay,
                "show_overlay": show_overlay,
            }

            self.executor._perform_action(temp_task, location)
            return True

        except Exception as e:
            logger.error(f"Error clicking on coordinates {location}: {e}")
            return False

    def find_relative_image(
        self,
        anchor_image,
        target_image,
        max_distance=200,
        confidence=0.9,
        target_region=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """
        Find a target image near an anchor image.

        Args:
            anchor_image (str): Path to the anchor image (unique on screen)
            target_image (str): Path to the target image (there may be multiple)
            max_distance (int): Maximum distance in pixels from the anchor to the target
            confidence (float): Confidence level for detection (0.0-1.0)
            target_region (tuple, optional): Specific region to search for the target (x, y, width, height)
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            tuple: Location of the target image closest to the anchor, or None

        Examples:
            >>> location = bot.find_relative_image('anchor.png', 'target.png', max_distance=150)
            >>> if location:
            ...     print(f"Target found near the anchor: {location}")
        """
        # If there are wait parameters, build a task and use the executor with wait
        if wait_until_found or wait_until_disappears:
            # Build a search function for the wait manager
            def search_relative():
                try:
                    return self.executor.relative_detector.locate_relative_image(
                        anchor_image,
                        target_image,
                        confidence,
                        max_distance,
                        target_region,
                    )
                except Exception:
                    return None

            if wait_until_found:
                return self.executor.wait_manager.wait_until_found(
                    search_relative,
                    timeout=wait_timeout or self.config.get("wait_timeout", 30),
                    description=f"relative image '{target_image}' near '{anchor_image}'",
                )
            elif wait_until_disappears:
                # First find the image
                result = search_relative()
                if not result:
                    return None

                # Then wait for it to disappear
                disappeared = self.executor.wait_manager.wait_until_disappears(
                    search_relative,
                    timeout=wait_timeout or self.config.get("wait_timeout", 30),
                    description=f"relative image '{target_image}' near '{anchor_image}'",
                )
                return result if disappeared else None

        # Original behavior without wait
        try:
            return self.executor.relative_detector.locate_relative_image(
                anchor_image, target_image, confidence, max_distance, target_region
            )
        except Exception as e:
            logger.error(f"Error during relative image search: {e}")
            return None

    @_records_in_session("relative_image")
    def click_relative_image(
        self,
        anchor_image,
        target_image,
        max_distance=200,
        confidence=0.9,
        target_region=None,
        delay=0,
        mouse_button="left",
        backtrack=False,
        max_attempts=3,
        sendtext=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """
        Click on a target image near an anchor image.

        Args:
            anchor_image (str): Path to the anchor image
            target_image (str): Path to the target image
            max_distance (int): Maximum distance in pixels
            confidence (float): Confidence level (0.0-1.0)
            target_region (tuple, optional): Region to search for the target (x, y, width, height)
            delay (float): Delay after the click in seconds
            mouse_button (str): Mouse click type:
                • "left" - Simple left click (default)
                • "right" - Right click
                • "double" or "double left" - Double left click
                • "move_to" - Just moves the mouse without clicking
            backtrack (bool): Whether to use backtracking on failure
            max_attempts (int): Maximum number of attempts
            sendtext (str, optional): Text to type after the click
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            bool: True if found and clicked, False otherwise

        Examples:
            >>> # Simple left click (default)
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  max_distance=150, mouse_button="left")

            >>> # Right click
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  mouse_button="right", backtrack=True)

            >>> # Double left click
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  mouse_button="double", delay=1.0)

            >>> # Just move the mouse to the position (without clicking)
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  mouse_button="move_to", delay=0.5)

            >>> # Click and type text afterwards
            >>> success = bot.click_relative_image('anchor.png', 'input.png',
            ...                                  sendtext="Hello World", delay=1.0)
        """
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_relative_image",
                self._click_relative_image_internal,
                anchor_image,
                target_image,
                max_distance,
                confidence,
                target_region,
                delay,
                mouse_button,
                max_attempts,
                sendtext,
                wait_until_found,
                wait_until_disappears,
                wait_timeout,
                backtrack=backtrack,
            )

        return self._click_relative_image_internal(
            anchor_image,
            target_image,
            max_distance,
            confidence,
            target_region,
            delay,
            mouse_button,
            max_attempts,
            sendtext,
            wait_until_found,
            wait_until_disappears,
            wait_timeout,
        )

    def _click_relative_image_internal(
        self,
        anchor_image,
        target_image,
        max_distance,
        confidence,
        target_region,
        delay,
        mouse_button,
        max_attempts,
        sendtext=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """Internal implementation of the relative image click."""
        for attempt in range(max_attempts):
            # For click_relative_image, wait_until_disappears must wait AFTER the click, not before
            # So we pass only wait_until_found to find_relative_image
            location = self.find_relative_image(
                anchor_image,
                target_image,
                max_distance,
                confidence,
                target_region,
                wait_until_found,
                False,
                wait_timeout,
            )  # wait_until_disappears=False
            if location:
                temp_task = {
                    "mouse_button": mouse_button,
                    "delay": delay,
                    "sendtext": sendtext,
                    "wait_until_disappears": wait_until_disappears,
                    "wait_timeout": wait_timeout,
                    "image": target_image,  # So wait_until_disappears knows which image to wait for
                    "_wait_after_click": wait_until_disappears,
                    "_wait_timeout": wait_timeout,
                    "_image_path": target_image,
                }
                self.executor._perform_action(temp_task, location)
                return True

            if attempt < max_attempts - 1:
                time.sleep(0.5)

        return False

    @_records_in_session("click")
    def click_coordinates(self, x, y, delay=0, mouse_button="left", backtrack=False):
        """
        Click on specific screen coordinates.

        Args:
            x (int): X coordinate
            y (int): Y coordinate
            delay (float): Delay after the click
            mouse_button (str): Mouse button ("left", "right", "double", "move_to")
            backtrack (bool): Whether to use backtracking

        Returns:
            bool: True if clicked successfully

        Examples:
            >>> success = bot.click_coordinates(100, 200, delay=1, backtrack=True)
        """
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_coordinates",
                self._click_coordinates_internal,
                x,
                y,
                delay,
                mouse_button,
                backtrack=backtrack,
            )

        return self._click_coordinates_internal(x, y, delay, mouse_button)

    def _click_coordinates_internal(self, x, y, delay, mouse_button):
        """Internal implementation of the coordinate click."""
        try:
            location = (x, y, 1, 1)  # Create a small region
            temp_task = {"mouse_button": mouse_button, "delay": delay}
            self.executor._perform_action(temp_task, location)
            return True
        except Exception as e:
            logger.error(f"Error clicking on coordinates ({x}, {y}): {e}")
            return False

    def open_app(self, target, wait_window=None, timeout=30.0):
        """
        Open an app or a file as Windows Run does (``excel``, ``notepad``, a
        ``.xlsx``, a URL) and, with ``wait_window``, wait for that window to be
        ready and in front.

        Returns:
            dict: ``{"target", "window"}`` -- ``window`` is the ready window's title,
            or None when it did not show up in ``timeout`` seconds
        """
        from .core.process import open_app

        return open_app(target, wait_window=wait_window, timeout=timeout)

    @_records_in_session("type_text")
    def type_text(self, text, interval=0.02, delay=0, backtrack=False, window=None):
        """
        Type text with an interval between characters.

        Args:
            text (str): Text to type
            interval (float): Interval between characters in seconds
            delay (float): Delay after typing
            backtrack (bool): Whether to use backtracking
            window (str): Part of the title of the window that gets the text: it is
                brought to the front and CHECKED first -- with another window in
                front nothing is typed and this returns False

        Returns:
            bool: True if typed successfully

        Examples:
            >>> success = bot.type_text('Hello World!', interval=0.05, backtrack=True)
            >>> success = bot.type_text('{ctrl}a{del}New text', backtrack=True)
        """
        if window and not _window_in_front(window):
            return False
        if backtrack:
            return self._execute_with_individual_backtrack(
                "type_text",
                self._type_text_internal,
                text,
                interval,
                delay,
                backtrack=backtrack,
            )

        return self._type_text_internal(text, interval, delay)

    def _type_text_internal(self, text, interval, delay):
        """Internal implementation of text typing."""
        try:
            # Like a person at the keyboard: a key per character (accents included),
            # Tab/Enter and the {tab}/{enter}/... tokens anywhere in the text. The old
            # path lost accents (typewrite) and pasted mid-text tokens literally.
            from .core.human_typing import type_like_a_person

            type_like_a_person(text, interval)

            if delay > 0:
                time.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"Error typing text '{text}': {e}")
            return False

    @_records_in_session("keyboard_command")
    def keyboard_command(self, command, delay=0, backtrack=False, window=None):
        """
        Run a keyboard command: a catalog token, any chord (``Ctrl+Shift+S``), a key
        alone (``Alt``) or a comma sequence (``"Alt, H, O, I"``).

        Args:
            command (str): Name of the command to run
            delay (float): Delay after the command
            backtrack (bool): Whether to use backtracking
            window (str): The window that gets the key, brought to the front and
                checked first like ``type_text``'s

        Returns:
            bool: True if the command ran successfully

        Examples:
            >>> success = bot.keyboard_command('Ctrl+S', delay=1, backtrack=True)
            >>> success = bot.keyboard_command('F7', backtrack=True)  # Oracle Forms
        """
        if window and not _window_in_front(window):
            return False
        if backtrack:
            return self._execute_with_individual_backtrack(
                "keyboard_command",
                self._keyboard_command_internal,
                command,
                delay,
                backtrack=backtrack,
            )

        return self._keyboard_command_internal(command, delay)

    def _keyboard_command_internal(self, command, delay):
        """Internal implementation of the keyboard command."""
        try:
            success = self.executor.keyboard_commander.execute_command(command)
            if delay > 0:
                time.sleep(delay)
            return success
        except Exception as e:
            logger.error(f"Error running command '{command}': {e}")
            return False

    def get_available_keyboard_commands(self):
        """
        Return the list of available keyboard commands.

        Returns:
            list: List of all available commands

        Examples:
            >>> commands = bot.get_available_keyboard_commands()
            >>> print(f"Available commands: {len(commands)}")
            >>> for cmd in commands[:10]:  # Show the first 10
            ...     print(f"  - {cmd}")
        """
        return self.executor.keyboard_commander.get_available_commands()

    def _process_sendtext(self, sendtext):
        """
        Process special commands in sendtext and type the text.

        Args:
            sendtext (str): Text with special commands such as {ctrl}a, {del}, etc.
        """
        import time

        import pyautogui
        import pyperclip

        text_to_write = sendtext
        commands_processed = True

        while commands_processed:
            commands_processed = False
            lower_text = text_to_write.lower()

            if lower_text.startswith("{ctrl}a"):
                pyautogui.hotkey("ctrl", "a")
                text_to_write = text_to_write[7:]  # Remove '{ctrl}a'
                commands_processed = True
                time.sleep(0.1)

            elif lower_text.startswith("{del}"):
                pyautogui.press("delete")
                text_to_write = text_to_write[5:]  # Remove '{del}'
                commands_processed = True
                time.sleep(0.1)

            elif lower_text.startswith("{tab}"):
                pyautogui.press("tab")
                text_to_write = text_to_write[5:]  # Remove '{tab}'
                commands_processed = True
                time.sleep(0.1)

            elif lower_text.startswith("{enter}"):
                pyautogui.press("enter")
                text_to_write = text_to_write[7:]  # Remove '{enter}'
                commands_processed = True
                time.sleep(0.1)

        # Type the remaining text using the clipboard for greater reliability
        if text_to_write:
            try:
                pyperclip.copy(text_to_write)
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                # Fallback to direct typing
                pyautogui.write(text_to_write)
            time.sleep(0.1)

    def execute_with_backtrack_between_tasks(self, tasks_list):
        """
        Execute multiple individual tasks with real backtracking between them.

        When a task fails, it goes back to the previous one, runs it,
        and then returns to try the failed one again.

        Args:
            tasks_list (list): List of dictionaries with individual task settings
                              Each item must have: {'type': 'text'|'image', 'params': {...}}

        Returns:
            list: List of boolean results
        """
        if not tasks_list:
            return []

        results = []
        i = 0
        backtrack_stack = []
        task_failures = {}

        logger.info(
            f"🚀 Starting execution with backtracking across {len(tasks_list)} individual tasks"
        )

        while i < len(tasks_list):
            task_config = tasks_list[i]
            task_type = task_config.get("type")
            params = task_config.get("params", {})
            backtrack_enabled = params.get("backtrack", True)

            logger.info(
                f"📋 Running task {i + 1}/{len(tasks_list)} - Type: {task_type}"
            )

            success = False

            try:
                if task_type == "text":
                    # Remove backtrack from params to avoid recursion
                    text_params = params.copy()
                    text_params.pop("backtrack", None)
                    success = self.click_text(**text_params)

                elif task_type == "image":
                    # Remove backtrack from params to avoid recursion
                    image_params = params.copy()
                    image_params.pop("backtrack", None)
                    success = self.click_image(**image_params)

                else:
                    logger.error(f"Unknown task type: {task_type}")
                    success = False

            except Exception as e:
                logger.error(f"Error running task {i + 1}: {e}")
                success = False

            # Adjust the results list
            while len(results) <= i:
                results.append(False)
            results[i] = success

            if success:
                logger.info(f"✓ Task {i + 1}/{len(tasks_list)} executed successfully!")

                # Check whether there are pending backtracks on the stack
                if backtrack_stack:
                    # Pop the item from the stack and go back to the original task that failed
                    original_failed_task = backtrack_stack.pop()
                    logger.info(
                        f"🔄 Returning to task {original_failed_task + 1} that originally failed after backtrack"
                    )
                    i = original_failed_task
                    # Reset the failure attempts for the original task
                    if i in task_failures:
                        task_failures[i] = 0
                else:
                    # Normal behavior: advance to the next task
                    i += 1

            else:
                # Task failed, check backtracking
                if backtrack_enabled and i > 0:
                    # Manage backtracking
                    task_failures.setdefault(i, 0)
                    task_failures[i] += 1

                    if task_failures[i] <= 2:  # Limit backtrack attempts
                        # Add the current task to the backtrack stack (to return later)
                        if i not in backtrack_stack:  # Avoid duplicates
                            backtrack_stack.append(i)
                            logger.info(
                                f"📌 Task {i + 1} added to the backtrack stack for later re-execution"
                            )

                        prev_task_type = tasks_list[i - 1].get("type", "unknown")
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} ({task_type}) failed. "
                            f"BACKTRACKING to task {i}/{len(tasks_list)} ({prev_task_type})"
                        )
                        i -= 1  # Go back to the previous task (THIS IS THE KEY LINE!)
                    else:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} failed "
                            f"after multiple backtracking attempts. Advancing."
                        )
                        # Remove from the stack if it is there
                        if i in backtrack_stack:
                            backtrack_stack.remove(i)
                        i += 1
                else:
                    # No backtrack or first task
                    if backtrack_enabled:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} failed "
                            f"but it is the first task. Advancing."
                        )
                    else:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} failed "
                            f"and has 'backtrack': False. Advancing."
                        )
                    i += 1

        successful_tasks = sum(1 for r in results if r)
        logger.info(
            f"🏁 Execution finished: {successful_tasks}/{len(results)} successful tasks"
        )

        return results


# Backward-compatibility alias (previous branding: bot-vision-suite / import bot_vision)
BotVision = VisusBot


# NEW CONVENIENCE FUNCTIONS WITH INDIVIDUAL BACKTRACK


def start_individual_session(config=None):
    """
    Start an individual task session with backtracking.

    Args:
        config (dict, optional): Custom configuration

    Returns:
        VisusBot: Instance configured for individual backtracking
    """
    bot = VisusBot(config)
    bot.start_task_session()
    return bot


def run_individual_tasks_with_backtrack(task_functions, config=None):
    """
    Run a list of individual task functions with automatic backtracking.

    Args:
        task_functions (list): List of tuples (function, args, kwargs)
        config (dict, optional): Custom configuration

    Returns:
        tuple: (successes, total, bot_instance)

    Examples:
        >>> tasks = [
        ...     (lambda bot: bot.click_image('btn.png', backtrack=True), (), {}),
        ...     (lambda bot: bot.click_text('Save', backtrack=True), (), {}),
        ... ]
        >>> success, total, bot = run_individual_tasks_with_backtrack(tasks)
    """
    bot = VisusBot(config)
    bot.start_task_session()

    results = []
    for i, (func, args, kwargs) in enumerate(task_functions):
        try:
            result = func(bot, *args, **kwargs)
            results.append(result)
            logger.info(f"Task {i + 1}: {'✓ Success' if result else '✗ Failed'}")
        except Exception as e:
            logger.error(f"Error in task {i + 1}: {e}")
            results.append(False)

    successful, total = bot.end_task_session()
    return successful, total, bot


# Main function compatible with legacy code
def execute_tasks(tasks, config=None):
    """
    Main function to run a list of tasks.

    Supports both simple lists and lists of lists (multiple sets).
    This is the function that users migrated from the original code will use.

    Args:
        tasks (list): List of automation tasks or list of lists
        config (dict, optional): Custom configuration

    Returns:
        list: List of TaskResult or list of lists of TaskResult

    Examples:
        Simple list:
        >>> tasks = [{'text': 'Login', 'region': (100, 100, 500, 300)}]
        >>> results = execute_tasks(tasks)

        Multiple lists:
        >>> task_sets = [
        ...     [{'text': 'Login', 'region': (100, 100, 500, 300)}],
        ...     [{'text': 'Save', 'region': (200, 200, 600, 400)}]
        ... ]
        >>> results = execute_tasks(task_sets)
    """
    if not isinstance(tasks, list):
        logger.error(f"Tasks must be a list. Received type: {type(tasks)}")
        return []

    if not tasks:
        logger.info("Empty task list.")
        return []

    # Check whether it is a list of lists
    if isinstance(tasks[0], list):
        # Multiple task sets
        logger.info(
            f"Detected multiple task sets ({len(tasks)} sets). Running sequentially."
        )

        all_results = []
        for i, task_list in enumerate(tasks):
            if isinstance(task_list, list):
                logger.info(
                    f"--- Starting task set {i + 1}/{len(tasks)} ({len(task_list)} tasks) ---"
                )
                bot = VisusBot(config)
                results = bot.execute_tasks(task_list)
                all_results.append(results)
                logger.info(f"--- Finished task set {i + 1}/{len(tasks)} ---")
            else:
                logger.warning(
                    f"Item {i} in the main list is not a list of tasks. Skipping."
                )
                all_results.append([])

        return all_results
    else:
        # Simple list of tasks
        bot = VisusBot(config)
        return bot.execute_tasks(tasks)


# Additional function for full compatibility with the original click_images
def click_images(tasks, default_confidence=0.9, default_margin=50):
    """
    Function for full compatibility with legacy code.

    This function replicates exactly the behavior of the click_images function
    from the original bot_vision.py, including support for lists of lists.

    Args:
        tasks: List of tasks or list of lists of tasks
        default_confidence (float): Default confidence for image detection
        default_margin (int): Default margin (kept for compatibility)

    Returns:
        list: List of results
    """
    # Build a configuration with compatible default values
    config = {
        "default_confidence": default_confidence,
        "default_margin": default_margin,
        "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        "tessdata_path": r"C:\Program Files\Tesseract-OCR\tessdata",
    }

    return execute_tasks(tasks, config)


# Standalone functions for 100% compatibility with the original code
def locate_image_with_retry(
    image_path: str, region=None, confidence=0.9, max_attempts=3, scales=None
):
    """
    Standalone function that replicates exactly the original function from bot_vision.py.
    Tries to locate an image with different scales and confidence levels.
    """
    executor = TaskExecutor()
    return executor._locate_image_with_retry(
        image_path, region, confidence, max_attempts, scales
    )


# Standalone convenience functions - NEW FEATURES
def find_relative_image(
    anchor_image,
    target_image,
    max_distance=200,
    confidence=0.9,
    target_region=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Standalone function to find a relative image.

    Args:
        anchor_image (str): Path to the anchor image
        target_image (str): Path to the target image
        max_distance (int): Maximum distance in pixels
        confidence (float): Confidence level
        target_region (tuple, optional): Region to search for the target
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        tuple: Location of the image or None

    Examples:
        >>> location = find_relative_image('anchor.png', 'target.png')
    """
    bot = VisusBot()
    return bot.find_relative_image(
        anchor_image,
        target_image,
        max_distance,
        confidence,
        target_region,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
    )


def click_relative_image(
    anchor_image,
    target_image,
    max_distance=200,
    confidence=0.9,
    target_region=None,
    delay=0,
    mouse_button="left",
    backtrack=False,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Standalone function to click on a relative image.

    Args:
        anchor_image (str): Path to the anchor image
        target_image (str): Path to the target image
        max_distance (int): Maximum distance in pixels
        confidence (float): Confidence level (0.0-1.0)
        target_region (tuple, optional): Region to search for the target (x, y, width, height)
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        backtrack (bool): Whether to use backtracking on failure

    Returns:
        bool: True if clicked successfully, False otherwise

    Examples:
        >>> # Simple left click
        >>> success = click_relative_image('anchor.png', 'target.png')

        >>> # Right click
        >>> success = click_relative_image('anchor.png', 'target.png',
        ...                              mouse_button="right", backtrack=True)

        >>> # Double left click
        >>> success = click_relative_image('anchor.png', 'target.png',
        ...                              mouse_button="double", delay=1.0)

        >>> # Just move the mouse to the position (without clicking)
        >>> success = click_relative_image('anchor.png', 'target.png',
        ...                              mouse_button="move_to", delay=0.5)

        Additional args v1.3.0+:
            wait_until_found (bool): Waits for the image to appear automatically
            wait_until_disappears (bool): Waits for the image to disappear
            wait_timeout (int, optional): Specific timeout (overrides the global one)
    """
    bot = VisusBot()
    return bot.click_relative_image(
        anchor_image,
        target_image,
        max_distance,
        confidence,
        target_region,
        delay,
        mouse_button,
        backtrack,
        3,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
    )


def click_coordinates(x, y, delay=0, mouse_button="left", backtrack=False):
    """
    Standalone function to click on specific coordinates.

    Args:
        x (int): X coordinate
        y (int): Y coordinate
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        backtrack (bool): Whether to use backtracking on failure

    Returns:
        bool: True if clicked successfully, False otherwise

    Examples:
        >>> # Simple click
        >>> success = click_coordinates(100, 200, delay=1)

        >>> # Right click
        >>> success = click_coordinates(100, 200, mouse_button="right", backtrack=True)

        >>> # Just move the mouse to the position (without clicking)
        >>> success = click_coordinates(100, 200, mouse_button="move_to", delay=0.5)
    """
    bot = VisusBot()
    return bot.click_coordinates(x, y, delay, mouse_button, backtrack)


def type_text_standalone(text, interval=0.05, delay=0, backtrack=False):
    """
    Standalone function to type text.

    Args:
        text (str): Text to type
        interval (float): Interval between characters
        delay (float): Delay after typing
        backtrack (bool): Whether to use backtracking

    Returns:
        bool: True if typed successfully

    Examples:
        >>> success = type_text_standalone('Hello World!', backtrack=True)
        >>> success = type_text_standalone('{ctrl}a{del}New text', backtrack=True)
    """
    bot = VisusBot()
    return bot.type_text(text, interval, delay, backtrack)


def keyboard_command_standalone(command, delay=0, backtrack=False):
    """
    Standalone function to run a keyboard command.

    Args:
        command (str): Command to run
        delay (float): Delay after the command
        backtrack (bool): Whether to use backtracking

    Returns:
        bool: True if it ran successfully

    Examples:
        >>> success = keyboard_command_standalone('Ctrl+S', delay=1, backtrack=True)
        >>> success = keyboard_command_standalone('F7', backtrack=True)
    """
    bot = VisusBot()
    return bot.keyboard_command(command, delay, backtrack)


def get_available_keyboard_commands():
    """
    Standalone function to get the available keyboard commands.

    Returns:
        list: List of available commands

    Examples:
        >>> commands = get_available_keyboard_commands()
        >>> print(f"Total commands: {len(commands)}")
    """
    bot = VisusBot()
    return bot.get_available_keyboard_commands()


def extract_text_from_region_standalone(
    region=None,
    filter_type="both",
    confidence_threshold=50.0,
    return_full_data=False,
    max_attempts=3,
    backtrack=False,
    config=None,
):
    """
    Standalone function to extract text from a specific region of the screen.

    Args:
        region (tuple, optional): (x, y, width, height) of the region to extract text from.
                                If None, extracts from the whole screen
        filter_type (str): Filter type ("numbers", "letters", "both")
        confidence_threshold (float): Minimum confidence threshold (0-100)
        return_full_data (bool): If True, returns full data with coordinates
        max_attempts (int): Maximum number of attempts if backtrack=True
        backtrack (bool): Whether to try multiple times with adjustments
        config (dict or BotVisionConfig, optional): Custom configuration

    Returns:
        If return_full_data=False:
            list: List of strings with all the text found
        If return_full_data=True:
            list: List of dictionaries with full data

    Examples:
        Simple extraction:
        >>> texts = extract_text_from_region_standalone(region=(100, 100, 400, 300))
        >>> print("Texts found:", texts)

        Extraction with full data:
        >>> data = extract_text_from_region_standalone(
        ...     region=(100, 100, 400, 300),
        ...     return_full_data=True,
        ...     confidence_threshold=70.0,
        ...     backtrack=True
        ... )
        >>> for item in data:
        ...     print(f"'{item['text']}' - Confidence: {item['confidence']:.1f}%")

        Numbers only:
        >>> numbers = extract_text_from_region_standalone(
        ...     region=(50, 50, 200, 100),
        ...     filter_type="numbers"
        ... )
    """
    bot = VisusBot(config=config)
    return bot.extract_text_from_region(
        region=region,
        filter_type=filter_type,
        confidence_threshold=confidence_threshold,
        return_full_data=return_full_data,
        max_attempts=max_attempts,
        backtrack=backtrack,
    )


# Function for full compatibility - task execution with multiple-list support
def run_automation(tasks, default_confidence=0.9, default_margin=50):
    """
    Function that replicates the exact behavior of the if __name__ == '__main__' block of the original bot_vision.py.
    Supports both a simple list and a list of lists (multiple task sets).

    Args:
        tasks: List of tasks or list of lists of tasks (as in the original)
        default_confidence (float): Default confidence
        default_margin (int): Default margin
    """
    import logging

    # Check whether tasks is a list and not empty
    if isinstance(tasks, list) and tasks:
        # Check whether the first element is also a list (indicating a list of lists)
        if isinstance(tasks[0], list):
            logging.info(
                f"Detected multiple task lists ({len(tasks)} lists). Executing sequentially."
            )
            # Iterate through each task list
            for i, task_list in enumerate(tasks):
                if isinstance(task_list, list):
                    logging.info(
                        f"--- Starting task list {i + 1}/{len(tasks)} ({len(task_list)} tasks) ---"
                    )
                    click_images(
                        task_list, default_confidence, default_margin
                    )  # Pass the individual list to the function
                    logging.info(f"--- Finished task list {i + 1}/{len(tasks)} ---")
                else:
                    logging.warning(
                        f"Item {i} in the main list is not a list of tasks. Skipping."
                    )
        else:
            # Assume it is a single flat list of tasks
            logging.info("Detected a single task list. Executing.")
            click_images(tasks, default_confidence, default_margin)
    elif isinstance(tasks, list) and not tasks:
        logging.info("The imported 'tasks' list is empty. Nothing to execute.")
    else:
        logging.error(
            f"The imported 'tasks' is not a list. Type: {type(tasks)}. Cannot execute."
        )


# Initial library setup
def _setup_library():
    """Initial library setup."""
    try:
        # Configure logging if it is not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
            )

        # Try to configure the library with the default configuration
        get_default_config()
        logger.debug(f"visus.desktop v{__version__} initialized")

    except Exception as e:
        logger.warning(f"Warning during library initialization: {e}")


# Run the initial setup
_setup_library()


# Standalone convenience functions (create a temporary VisusBot instance)
def find_text(
    text,
    region=None,
    filter_type="both",
    confidence_threshold=75.0,
    occurrence=1,
    max_attempts=3,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Search for text on screen using a temporary VisusBot instance.

    Args:
        text (str): Text to find
        region (tuple, optional): Search region (x, y, width, height)
        filter_type (str): Filter type ("letters", "numbers", "both")
        confidence_threshold (float): OCR confidence threshold
        occurrence (int): Which occurrence to look for (1=first)
        max_attempts (int): Maximum number of attempts
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        tuple: Found coordinates or None
    """
    bot = VisusBot(config)
    return bot.find_text(
        text,
        region,
        filter_type,
        confidence_threshold,
        occurrence,
        max_attempts,
        wait_until_found=wait_until_found,
        wait_until_disappears=wait_until_disappears,
        wait_timeout=wait_timeout,
    )


def click_text(
    text,
    region=None,
    filter_type="both",
    delay=0,
    mouse_button="left",
    occurrence=1,
    max_attempts=3,
    sendtext=None,
    confidence_threshold=None,
    show_overlay=True,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Click on text using a temporary VisusBot instance.

    Args:
        text (str): Text to click on
        region (tuple, optional): Search region (x, y, width, height)
        filter_type (str): Filter type ("letters", "numbers", "both")
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        occurrence (int): Which occurrence to click (1=first)
        max_attempts (int): Maximum number of attempts
        sendtext (str, optional): Text to type after the click
        confidence_threshold (float, optional): Custom confidence threshold
        show_overlay (bool): Whether to show the red overlay before the click
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        bool: True if found and clicked, False otherwise
    """
    bot = VisusBot(config)
    return bot.click_text(
        text,
        region,
        filter_type,
        delay,
        mouse_button,
        occurrence,
        False,
        max_attempts,
        sendtext,
        confidence_threshold,
        show_overlay,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
    )


def find_image(
    image_path,
    region=None,
    confidence=0.9,
    max_attempts=3,
    specific=True,
    scales=None,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
    occurrence=1,
):
    """
    Search for an image on screen using a temporary VisusBot instance.

    Args:
        image_path (str): Path to the image
        region (tuple, optional): Search region
        confidence (float): Confidence level
        max_attempts (int): Maximum number of attempts
        specific (bool): If True, searches in the region; if False, searches the whole screen + variations
        scales (list, optional): List of scales to try
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)
        occurrence (int): Which match to return when the template appears more
            than once (1=first, reading order top→bottom/left→right)

    Returns:
        tuple: Coordinates of the image or None
    """
    bot = VisusBot(config)
    return bot.find_image(
        image_path,
        region,
        confidence,
        max_attempts,
        False,
        specific,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
        scales,
        occurrence=occurrence,
    )


def click_image(
    image_path,
    region=None,
    confidence=0.9,
    delay=0,
    mouse_button="left",
    max_attempts=3,
    specific=True,
    sendtext=None,
    show_overlay=True,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
    occurrence=1,
):
    """
    Click on an image using a temporary VisusBot instance.

    Args:
        image_path (str): Path to the image
        region (tuple, optional): Search region (x, y, width, height)
        confidence (float): Confidence level (0.0-1.0)
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        max_attempts (int): Maximum number of attempts
        specific (bool): If True, searches in the region; if False, searches the whole screen + variations
        sendtext (str, optional): Text to type after the click
        show_overlay (bool): Whether to show the red overlay before the click
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)
        occurrence (int): Which match to click when the template appears more
            than once (1=first, reading order top→bottom/left→right)

    Returns:
        bool: True if found and clicked, False otherwise
    """
    bot = VisusBot(config)
    return bot.click_image(
        image_path,
        region,
        confidence,
        delay,
        mouse_button,
        max_attempts,
        False,
        specific,
        sendtext,
        show_overlay,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
        occurrence=occurrence,
    )


def click_at(location, mouse_button="left", delay=0, show_overlay=True, config=None):
    """
    Click on specific coordinates using a temporary VisusBot instance.

    Args:
        location (tuple): (x, y, width, height) of the location
        mouse_button (str): Mouse button ("left", "right", "double", "move_to")
        delay (float): Delay after the click
        show_overlay (bool): Whether to show the red overlay before the click
        config (dict, optional): Custom configuration

    Returns:
        bool: True if clicked successfully
    """
    bot = VisusBot(config)
    return bot.click_at(location, mouse_button, delay, show_overlay)


def type_text(text, config=None):
    """
    Type text using a temporary VisusBot instance.

    Args:
        text (str): Text to type (supports special commands)
        config (dict, optional): Custom configuration

    Returns:
        bool: True if typed successfully
    """
    bot = VisusBot(config)
    return bot.type_text(text)


# PUBLIC EXPORTS
__all__ = [
    # Main class
    "VisusBot",
    "BotVision",  # backward-compatibility alias
    # Task execution functions
    "execute_tasks",
    "click_images",  # Full compatibility with legacy code
    "run_automation",  # Compatibility with if __name__ == '__main__'
    # Basic convenience functions
    "find_text",
    "click_text",
    "find_image",
    "click_image",
    "click_at",
    "type_text",
    # NEW FEATURES - Convenience functions for relative images
    "find_relative_image",
    "click_relative_image",
    # NEW FEATURES - Convenience functions for coordinates
    "click_coordinates",
    # NEW FEATURES - Convenience functions for the keyboard
    "type_text_standalone",
    "keyboard_command_standalone",
    "get_available_keyboard_commands",
    # NEW FEATURE - Text extraction
    "extract_text_from_region_standalone",
    # Individual backtrack functions
    "start_individual_session",
    "run_individual_tasks_with_backtrack",
    # Core classes (for advanced use)
    "TaskExecutor",
    "TaskResult",
    "OCREngine",
    "OCRResult",
    "ImageProcessor",
    "VisualOverlay",
    "RelativeImageDetector",  # NEW
    "KeyboardCommander",  # NEW
    # Utilities
    "BotVisionConfig",
    "get_default_config",
    "clean_text",
    "limpar_texto",
    "matches_filter",
    "retry",
    "Session",
    # Standalone processing functions (compatibility)
    "preprocess_image_for_ocr",
    "find_text_with_multiple_preprocessing",
    "show_overlay",
    "locate_image_with_retry",
    # Files / clipboard / screen / process / window / image map / mouse (BotCity parity)
    "wait_for_file",
    "wait_for_file_stable",
    "copy_to_clipboard",
    "paste",
    "get_clipboard",
    "capture_screen",
    "save_screenshot",
    "take_screenshot",
    "get_display_size",
    "get_monitors",
    "Monitor",
    "wait_for_stable_screen",
    "capture_element",
    "get_window",
    "smart_find",
    "smart_click",
    "launch",
    "open_app",
    "find_process",
    "is_process_running",
    "kill_process",
    "focus_window",
    "maximize_window",
    "minimize_window",
    "close_window",
    "ensure_window",
    "list_windows",
    "scroll",
    "drag",
    "triple_click",
    "move_random",
    "mouse_down",
    "mouse_up",
    "ImageMap",
    "find_all",
    "find_multiple",
    "Backend",
    "NativeError",
    # Exceptions
    "BotVisionError",
    "ImageNotFoundError",
    "TextNotFoundError",
    "TaskExecutionError",
    "ImageProcessingError",
    "OCRProcessingError",
    "TesseractNotFoundError",
    "InvalidRegionError",
    "ConfigurationError",
    "NotSupportedOnThisOS",
    # Library information
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]

# Changelog — visus-desktop

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Safer native automation for AI agents, with ideas from Vercel Labs' agent-desktop
(Apache-2.0) and its measured Windows findings.

### Added
- No-mouse UIA actions in the API, CLI and MCP: `native_toggle` / `native check|uncheck|toggle`
  (Toggle pattern, read back; nothing sent when already so; a toggle that changes nothing is
  never repeated), `native_select` / `native select N VALUE` (SelectionItem: expands a closed
  combo, scrolls lists that load as you scroll, refuses two options with the same name; a
  classic Win32 combo is set through its writable Value), `native_expand` /
  `native expand|collapse` and `native_scroll_into_view` / `native scroll-into-view`.
- Every native action reports delivery (`ActionOutcome`): `not_delivered` (safe to retry),
  `delivered`, `verified` (read back) or `uncertain` (may have landed — read the state first).
  `native_click_ex` / `native_set_text_ex`; the CLI prints it and `--json` returns
  `{ok, delivery, retry_safe, method, reason}`.
- `native snapshot` shows each control's state (`[disabled]`, `[checked]`, `[expanded]`,
  `[offscreen]`, `[password]`…) and numbers any element that announces an action (a clickable
  `Custom`/`Group` in WPF or Chromium). Under Chromium/Electron, anonymous wrapper groups no
  longer count as depth, so web content is reachable.

### Changed
- `native snapshot` numbers are per session (`VISUS_DESKTOP_SESSION`) and carry a snapshot id
  (`s1a2b3:3` pins one): two agents, or an agent and a bot, no longer overwrite each other's
  numbers and click the wrong window.
- An action by number first checks the control against the live window: when it is gone or
  another control like it appeared (so `found_index` could point elsewhere), the action is
  refused with nothing sent.
- `native_click` (`method="auto"`) tries the control's `LegacyIAccessible` default action after
  Invoke and before the real mouse; `retries` only repeat what never reached the app.
- A program that is not responding is detected up front (`SendMessageTimeout`) instead of
  waiting out the timeout and answering `False` with no reason.
- The window list (and every `--window` match) skips windows a person does not see: cloaked
  (suspended UWP, other virtual desktop), tool windows and zero-size windows.
- `native get-text N` never prints a password field.

## [0.4.8] - 2026-11-13

### Fixed
- Typing is right on ANY keyboard layout and language. `type_text` (and the native fill,
  the CLI and the no-clipboard fallbacks) presses the real key only when it is PROVEN on
  the layout of the window in front: that key, alone or with Shift, makes exactly that
  character there (`ToUnicodeEx`, with the current CapsLock). Everything else -- AltGr
  characters, dead keys, CapsLock flipping the case, characters the layout does not
  have -- goes as Unicode input (`KEYEVENTF_UNICODE`), independent of the layout.
  pyautogui pressed Ctrl+Alt+Q for "/" on a Brazilian ABNT2 keyboard, so the Calculator got
  "4422" for "44/22", and it built its key map on the script's layout, not the window's.
  Measured on a real window: before, "01/12/2026" arrived as "01Q12Q2026" on a US window,
  "?" as "W" and "~" as "^" on ABNT2, and "Ação" as "açãO" with CapsLock on; now the text
  arrives exactly, on ABNT2 and US, with and without CapsLock. Checked on the Russian,
  German, French and Japanese layouts too. Moving the mouse to a screen corner still
  stops the typing (pyautogui's fail-safe). Shortcuts, mouse and the rest of pyautogui are
  unchanged.

## [0.4.7] - 2026-11-13

### Fixed
- Keyboard and typing into the window `use_app` returned check that the PROGRAM is in front
  (its process), not the exact window title. A program switches windows and keeps being
  the same program: Excel 2013's start screen ("Microsoft Excel") becomes the workbook
  ("Book1 - Excel") after Escape, and `keyboard_command(..., window=excel)` used to stop with
  "is not the window in front -- nothing was sent". When another program is in front, the
  program's top visible window is brought forward first (`front_program`). A title typed by
  hand is still checked by title. Measured: a recorded Excel task stopped at step 3 before
  and ran 6/6 after.

## [0.4.6] - 2026-11-13

### Fixed
- The on-screen highlight no longer shows up in screen captures (`SetWindowDisplayAffinity`
  with `WDA_EXCLUDEFROMCAPTURE`): it is for the person watching, and in a capture it sat
  over the target -- the next step's image/OCR search and the step screenshot saw the
  green box. Measured on the library highlight: 1140 green px in a capture before, 0 now.

## [0.4.5] - 2026-11-13

### Added
- `AppWindow.region(x=0, y=0, width=None, height=None)` / `AppWindow.point(x, y)` — a
  region / point ON SCREEN from coordinates relative to the window's top-left corner,
  read at call time (the window may have moved since `use_app`). `region()` is the
  whole window.
- `use_app(..., maximized=True/False)` — leave the window maximized / restored, as it
  was when the steps were recorded (`None`, the default, leaves it alone).
- `bot.smart_click(...)` — ONE step of the report: the cascade (image → OCR by
  default) runs inside, so a failed first attempt no longer stops the run before the
  next one; it fails only when every method failed, saying what it tried. `smart_click`
  (function and MCP tool) gains `occurrence` and `double`.

## [0.4.4] - 2026-11-13

### Added
- `native_drag(window=..., start=(x, y), end=(x, y), ...)` — drag INSIDE a control
  located by selector: draw a shape on Paint's canvas, move a slider, select a
  range. `start` / `end` are offsets in pixels from the control's top-left corner,
  so the drag follows the control wherever the window is; a real mouse press, move
  over `duration` (0.4 s) and release. A step of the report inside `rpa()`; also an
  MCP tool (`native_drag`) and a CLI command (`visus native drag`).
- `native_click(..., at=(x, y))` — click THAT point inside the control (offset from
  its top-left corner) with the real mouse: a spot on a surface such as Paint's
  canvas (fill, pick a color). Also `at=` in the MCP tool and `--at X,Y` in the CLI.
- `native_scroll(window=..., amount=N, at=(x, y))` — turn the mouse wheel over a
  control (notches: + up, - down), at a point inside it or its center. Also an MCP
  tool (`native_scroll`) and a CLI command (`visus native scroll`).
- A left drag / point click on a control right after the mouse acted on ANOTHER
  control first clicks its start point: WinUI 3 surfaces (the Windows 11 Paint
  canvas) spend that first press only to activate themselves -- measured: tool click
  then drag drew nothing; with the activation click, the shape. Consecutive drags on
  the same control don't get it.

## [0.4.3] - 2026-11-13

One automation across several programs.

### Added
- `use_app(app=None, *, window=None, file=None, timeout=30.0)` — brings a program to
  the front and, only when it is closed, opens it (or `file`) and waits until its
  window is in front with a steady title. `app` is the exe path (the exe name is tried
  when the path does not exist on this machine), the exe name or a packaged app id
  (opened through `shell:AppsFolder` — the Calculator and the other Store apps, which
  run inside `ApplicationFrameHost.exe`, now open too). Matching by process is exact
  (`calc.exe` does not match `calcengine.exe`); among several windows the one with the
  `window` title wins, and any window of the program serves when none has it. As
  `bot.use_app` it is a step of the report (`opened: …` / `in front: …`); a failure is
  `UseAppError` (a `BotVisionError`). Also an MCP tool (`use_app`) and a CLI command
  (`visus use-app`).
- `AppWindow` — what `use_app` returns: the live title (a `str`) with `hwnd`, `pid`
  and `opened`. Passed as `window=` to the `native_*` calls they bind to that handle,
  so a workbook opened blank (`Pasta1 - Excel`) serves the steps captured on
  `vendas.xlsx - Excel`; a dead handle falls back to the title.
- `window_app_id(hwnd)` — the packaged app id (AUMID) of a window's app (`""` for a
  plain Win32 app).

## [0.4.2] - 2026-11-12

The highlight with the visus-studio look, and no more piling up in a fast run.

### Changed
- The highlight looks like the visus-studio one — brand green `#2ea043`, a 2 px
  rounded border, a translucent fill of the same color and a soft glow, a few pixels
  clear of the target — on screen AND on the report screenshots (same drawing, no
  more crosshair). On Windows it is a per-pixel-alpha click-through window
  (`UpdateLayeredWindow`); if that ever fails, the plain outline still shows.
  Defaults: `overlay_color="green"` (now the studio green, not pure `#00ff00`) and
  `overlay_width=2`; any other color keeps the same look in that color.

### Fixed
- The click highlight no longer piles up in a fast run. Each box used to stay its whole
  `overlay_duration` (1 s) no matter what, so a click every ~0.14 s stacked ~7 red boxes
  that lingered after the bot moved on and showed up on the next steps' report
  screenshots. The action highlight is now one at a time — a new one closes the
  previous at once — and every recorded step clears the previous step's box when it
  starts (a `native_wait`'s screenshot no longer shows the last click's box); the run's
  last box goes when `rpa()` ends. Numbered occurrence overlays
  (`show_text_occurrences`) still show together.

## [0.4.1] - 2026-11-12

Native actions in the run report, highlighted like every other click.

### Added
- Inside `rpa()` (any open task session) `native_click`, `native_set_text`,
  `native_get_text` and `native_wait` are steps of the report — called as they are,
  no wrapper: the control is highlighted on screen in the bot's overlay style
  (`show_overlay`, `overlay_color`, `overlay_width`, `overlay_duration`), boxed on the
  step screenshot, the text `native_get_text` read shows as the step output, and a
  `False` / `None` result stops the run with `ActionFailedError` ("num8Button in
  'Calculadora' was not found within 5.0s (or it did not take the click)").
  Outside a session they behave exactly as before (CLI, MCP, plain scripts).
- `native_set_text(..., secret=True)` — typed the same, masked in the report.

### MCP
- `start_recording(path, name=None, screenshots=True)` now records EVERY action tool
  called after it — `click_text`, `click_image`, `click_at`, `type_text`,
  `keyboard_command`, `open_app`, `extract_text_from_region`, `scroll`, `drag`,
  `triple_click`, the `native_*` actions — not only `execute_tasks`; the tools keep
  their normal return values (a failed step is recorded, it does not raise).
- `stop_recording(report_path=None)` returns `{saved, zip, report, steps, failures,
  timeline}` (was a bool) and can render the HTML report in the same call;
  `render_report(..., title=None)`.
- `type_text(secret=)` / `native_set_text(secret=)`; `configure` during a recording
  keeps recording into the same run; the instructions teach the `rpa()` script shape.

### CLI
- `new` scaffolds a `tasks.py` built on `rpa()` (report under `visus-runs/`, exit 1 on
  a failed step) and a README with `visus-desktop run`; `report --title`; `run` help
  explains the report and exit code.

### Docs / skills
- `docs/mcp.md`, `docs/cli.md`, the README tables, `docs/api_reference.md` and the
  skills checked against the code: 59 MCP tools (was "57"; `open_app`,
  `native_snapshot` were missing), 52 CLI commands (was "50"; `open`,
  `native snapshot` were missing), and the `window` / `virtual` / `word_box` /
  `backend` / `ocr_backend` parameters added in 0.3.0. `record-and-replay` rewritten
  for the live MCP recording and `rpa()`; the docs no longer say recording needs
  `log_format="json"`. The bundled `resources/cli.md` was out of sync with
  `docs/cli.md` — synced.

## [0.4.0] - 2026-11-12

The run report in one line, the same `rpa()` as visus.web.

### Added
- `rpa(name, *, config, app, window, timeout, outdir, report, summary, open_report,
  screenshots, stop_on_failure, reraise)` — a context manager that yields a ready
  `VisusBot`, records every action as a report step and, on exit (even when a step
  fails), writes `./visus-runs/<name>-<ts>/run.zip` + `report.html`, prints a summary
  and exits with code 1 on failure. `app=`/`window=` open the app and wait for its
  window as the first step.
- `ActionFailedError` — a failed action inside `rpa()` stops the run with it
  (`stop_on_failure=True`, the default) instead of returning `False`.
- `bot.step("label")` — records any block (a `native_click`, a `smart_click`, a check)
  as one step.
- `type_text(..., secret=True)` — typed as usual, shown as `••••••` in the report and logs.
- Recorded as steps too: `open_app`, `extract_text_from_region` (the text read shows in
  the report, also for `execute_tasks` `extract_text` tasks), `scroll`, `drag`,
  `triple_click`.
- Report: the run name as the headline (`manifest.json` in the zip), step titles that
  read "Click text · Login", "Type · Ada", and an `output` row.
- `Session.start_recording(zip, name=None)` yields a `Recording` (`.events`,
  `.summary()`); `zip_path=None` captures without writing.

### Changed
- `Session.start_recording` no longer needs `log_format="json"`: with the default text
  logs the events reach the recording directly (and no JSON is printed on the console).
- Inside a task session, `execute_tasks` keeps the session's run id, so direct calls
  and task lists show as ONE run in the report.
- Under `RUNPILOT_RUN_TOKEN` without `runpilot` installed (nothing streamed), the local
  zip is kept instead of being skipped.

### Fixed
- Under RunPilot, a step with a long field (a `type_text` of 2600 characters, an error
  message over 5000) was rejected whole by the orchestrator's step schema and vanished
  from the run timeline; streamed steps are now clipped to fit (name 500, target 2000,
  error 5000). The text an extraction read goes along as the `output` attribute.
- A failed direct call's screenshot no longer draws the PREVIOUS step's box.
- `backtrack=True` after a recorded direct call no longer crashes (report-only entries
  went into the backtrack history).

### CI
- Publishing requires the test matrix on Windows and Ubuntu (the supported platforms).
  macOS still runs on every push but no longer gates a release: GitHub's arm64 Mac
  queue cancelled the jobs before they ran, blocking a release with every test green.

## [0.3.1] - 2026-10-31

### Changed
- The agent playbooks (`skills/`) now ship INSIDE the package
  (`visus/desktop/skills/`), so `pip install visus-desktop` brings them — before,
  they lived only at the repository root and a pip install had none to give an
  agent.

## [0.3.0] - 2026-10-30

Use the PC like a person: open an app, look, type into the window that is really in
front, and act by the control's name — measured live in Excel (open, type a 5x10
table, format it and save it in ~47 s, CLI only).

### Added
- `visus-desktop open TARGET [--wait-window TITLE]` — opens an app, a document or a URL
  as Windows Run does (`excel`, `report.xlsx`) and waits until that window is ready and
  in front. Also `open_app()` in the API and the `open_app` MCP tool.
- Window guard: `type --window` / `key --window` (and `window=` on `VisusBot.type_text`,
  `keyboard_command` and the MCP tools) bring the window to the front and CHECK it first
  — with another window in front nothing is typed.
- Human typing: one key per character with accents, real Tab/Enter, and the
  `{tab}`/`{enter}`/`{ctrl}a` tokens anywhere in the text; 0.02 s per character.
- `key` takes ANY key or chord, no fixed list (`Ctrl+;`, `Ctrl++`, `Win+Shift+S`,
  `PrintScreen`), a key alone (`Alt`) and comma sequences (`"Alt, H, O, I"`).
- `native snapshot` numbered, and act by number (`native click 3`); depth 25 by default
  so it reaches the Office ribbon's buttons; `native_snapshot` MCP tool.
- Virtual keyboard: type in the background without stealing focus or the clipboard.
- Run report in the orchestrator's "Run report" look.
- The `visus-desktop` console script (the name that only ever means this tool).

### Changed
- `smart` finds the native name fast (exact, then case-insensitive) and clicks once;
  with `--window` the image/OCR steps read only that window, brought to the front.
- RapidOCR keeps ONNX Runtime's memory arena: the first read (the only one a CLI call
  makes) went from 7.8 s to 3.9 s.
- `native set-text` types for real and verifies the value; `get-text` returns the value.

### Fixed
- Scrolling on Windows really scrolls, at the point; negative numbers in the CLI.
- Strict virtual mouse, `--occurrence` = the #N of `find-all`, DPI and UTF-8 output.
- The `mcp` extra is capped `<2` and only installed on Python 3.10+.

## [0.2.0] - 2026-07-14

### Added
- **Visus CLI Pro** — the `visus` terminal CLI was rebuilt in
  [Click](https://click.palletsprojects.com/) as an agent-native interface
  that mirrors the MCP surface in the shell. Every command takes `--json`
  (human-readable by default, machine-readable on demand). Command groups:
  * `visus smart find|click` — the cascade (native → image → OCR → coordinates),
    with `--dry-run` to resolve a target without acting.
  * `visus native dump-tree|click|set-text|get-text|get-state|wait` — no-pixel
    RPA by directed selector.
  * `visus capture <label> --auto|--text|--native|--region` — coordinate-free
    element capture (saves template + annotated shot, optional `--click`).
  * `visus screenshot <path>` — disk PNG (the `find_image` template format).
  * `visus window focus|maximize|minimize|close|get` — window control
    (`close` is gated by a confirmation / `--yes`).
  * `visus process launch|find|kill` — process control (`kill` gated likewise).
  * `visus clipboard get|set`, `visus configure <json|@file>`,
    `visus doctor`, and the preserved `visus new|run|report`.
  * `visus repl` — an interactive shell over the same command group.

  Safety: action commands accept `--dry-run`; destructive `kill`/`close`
  require confirmation (or `--yes`, mandatory in `--json` mode). The CLI is a
  thin Click shell that reuses the already-tested library functions — no new
  automation logic. Adds `click>=8.1.0` as a core dependency. See
  [`docs/cli.md`](docs/cli.md).
- **Smart cascade** (`visus.desktop.smart_find` / `smart_click` + 2 MCP
  tools): one call tries every targeting technique in a configurable
  order, default **native → image → OCR → coordinates**, and reports
  which won (`{found|clicked, method, tried}`). Provide whatever you have
  — `query` (native title + OCR text), `image` (template PNG),
  `coordinates` ([x, y]), plus `window`/`control_type`/`auto_id` to
  sharpen the native match; a method is skipped when its input is absent.
  `order=["native"]` forces a single method; `order=["ocr","image"]`
  reorders. The most robust single "click this" / "find this" primitive.
  MCP surface: **41 tools**.
- **Screenshot-on-failure** (Phase 1, O1): when an `execute_tasks` step fails,
  the executor saves a PNG to `config['artifacts_dir']`
  (default `./visus-artifacts/`) and exposes the path on
  `TaskResult.failure_screenshot`. The filename pattern is
  `<run_id>__<task_id>__<timestamp>.png`. Disable with
  `config['screenshot_on_failure'] = False`.
- **Structured task events** (Phase 1, O2): set
  `config['log_format'] = 'json'` to emit one JSON object per task on the
  `visus.desktop.task_events` logger. Fields: `run_id`, `task_id`,
  `task_name`, `success`, `duration_ms`, `error`, `failure_screenshot`,
  `timestamp` (ISO 8601, UTC). Attach a handler to that logger to route
  events to a file, Loki, or any structured sink. The default `text`
  format keeps the existing human-readable `[INFO]` lines unchanged.
- **`@retry` decorator** (Phase 1, R1): `visus.desktop.retry` (also
  importable from `visus.desktop.utils.retry`) re-invokes a callable on
  transient failures with `fixed` or `expo` backoff and an exception
  allow-list. Complements `backtrack`, which only retries within a task
  list — `@retry` is the standalone primitive for arbitrary functions
  (HTTP calls, file I/O, third-party APIs).
- **`visus-doctor` health-check CLI** (Phase 1, R4): run
  `python -m visus.desktop.doctor` (or the `visus-doctor` console
  script) to verify Tesseract, required Python modules, the display, and
  `pywinauto` (Windows-only). Prints `[OK]`/`[FAIL]` per check and exits
  non-zero on any failure, suitable for CI gates. The Tesseract candidate
  paths now live in `visus.desktop.utils.config.get_tesseract_candidate_paths`
  and are shared by the doctor and `BotVisionConfig`.
- **Graceful SIGINT shutdown** (Phase 1, R5): a `KeyboardInterrupt` during
  `execute_tasks` is intercepted to release any held mouse buttons
  (`left`, `middle`, `right`) before the exception propagates. Prevents
  stuck buttons after an interrupted `drag` / `mouse_down`.
- **MCP server + Skills bundle**: new `visus-mcp` console script
  exposes 31 tools (find/click/screenshot/keyboard/process/window/
  task-list/session/report/doctor/configure) via FastMCP for any
  MCP-aware agent (Claude Desktop, Claude Code, Cursor, custom
  clients). Install with `pip install 'visus-desktop[mcp]'`. The
  `skills/` directory ships 7 agent-ready playbooks
  (using-visus-desktop, automate-form-login, extract-table-data,
  wait-for-download, solve-image-captcha, file-dialog-automation,
  record-and-replay) referenced by name in the host's settings.json.
  Full docs at `docs/mcp.md`.
- **`save_screenshot` tool/helper**: `core.screen.save_screenshot` now
  accepts `monitor=` (parity with `capture_screen`/`take_screenshot`)
  and auto-creates parent directories. Exposed as the MCP
  `save_screenshot(path, region?, monitor?)` tool — it writes a PNG to
  disk (returns `{path, width, height}`), closing the gap where
  `find_image`/`click_image` need a disk template but the MCP surface
  previously only offered base64 `take_screenshot`. The full
  capture → find_image → click_image flow now lives entirely inside MCP.
- **Native RPA** (`visus.desktop.core.native_rpa` + 6 MCP tools): no-pixel
  desktop automation through the accessibility tree (pywinauto UIA). Operate
  accessible apps (Win32 / WPF / WinUI / .NET) by control — immune to theme,
  DPI, resolution, language and window position. Functions:
  * `native_dump_tree(window|pid, max_depth)` — the agent *sees* the UI:
    a flat list of `{depth, control_type, title, auto_id, rect}` walked via
    `children()` to a depth cap (fast, not a full `descendants()` flood).
  * `native_click` / `native_set_text` / `native_get_text` /
    `native_get_state` / `native_wait` — act on a control located by a
    **directed** selector (`title` / `control_type` / `auto_id` /
    `found_index`) via `child_window` FindFirst. `native_click` supports
    `method=invoke|click|auto`; reads expose `get_state`
    (exists/visible/enabled/checked/value/rect).

  Every call is bounded by a worker-thread `timeout` (UIA can hang) and
  supports `retries` + `delay` — the native analogue of backtrack.
  Non-accessible UIs (Java Swing without the Access Bridge, some Electron)
  return empty/None/False, so callers fall back to OCR / `capture_element`.
  MCP surface: **39 tools**.
- **Layered precise locators** (`visus.desktop.core.locators` + MCP):
  precise element location beyond OCR. `capture_element(auto=...)` now
  tries **Win32 classic menu → OCR → UIA directed** in order:
  * Win32 menu (`GetMenu`/`GetMenuItemRect` + `GetMenuStringW`) returns a
    classic menu item's exact rect instantly — perfect for native menu
    bars.
  * OCR (the universal fallback — works on Java Swing, Electron, remote
    desktop, anything that renders text).
  * UIA *directed* (`Application.connect(process=pid).child_window(...)`
    FindFirst) — fast, unlike the old full `descendants()` walk; bounded
    by a worker-thread timeout so it can never hang.
  New `get_window(title)` resolves a window's rect/pid/hwnd via win32
  without requiring focus, and `capture_element(window=...)` scopes the
  Win32/UIA strategies to a named window even when it is behind others.
  `native=` now uses the fast directed UIA path. MCP surface: **33 tools**.
- **`capture_element`** (`visus.desktop.capture_element` + MCP tool):
  coordinate-free element capture. Locate a UI element by exactly one of
  `text=` (OCR), `native=` (UIA), or `region=`, then save a tight
  reusable template to `<elements_dir>/<label>.png`, save an annotated
  full-screen PNG (rectangle around the match) to
  `<elements_dir>/trace/`, and optionally `click=True` the center. Lets
  an agent build a robust click-by-image flow step-by-step (e.g.
  `text="Arquivo"` → `text="Salvar como"`) without guessing
  coordinates. On a miss returns `{"found": false}` with the annotated
  screenshot for diagnosis. MCP surface is now **32 tools**.
- **Pluggable OCR backend** (Phase 3, E5 — early): set
  `config['ocr_backend'] = 'rapidocr'` to swap Tesseract for the
  ONNX-runtime-based PP-OCR pipeline. Default stays `'tesseract'` so no
  existing user notices. Install the optional dep with
  `pip install 'visus-desktop[rapidocr]'`. `BotVisionConfig` no longer
  forces a Tesseract install when the RapidOCR backend is selected, so
  the library is usable on locked-down corporate Windows machines.
  `visus-doctor` now reports the active backend and checks the
  appropriate dependency chain.

### Documentation
- **Cookbook** (Phase 1, DOC1) — `docs/cookbook/` with a worked
  download-wait recipe and stubs for Oracle Forms, captcha, Excel input,
  and Windows file dialogs.
- **Migration guide** (Phase 1, DOC2) — `docs/migration.md` covers
  imports, renames (`BotVision` ↔ `VisusBot`, `limpar_texto` ↔
  `clean_text`), bug fixes inherited from the rebrand, and the new
  Phase 1 opt-ins.
- **Troubleshooting guide** (Phase 1, DOC3) — `docs/troubleshooting.md`
  with symptom → diagnosis → fix sections for OCR misses, DPI scaling,
  `pywinauto` connection issues, Tcl/Tk on Linux/WSL, stuck mouse
  buttons, and the `cv2 --cov` interaction.

### Changed
- `BotVisionConfig._get_tesseract_paths` was refactored to delegate to
  the shared `get_tesseract_candidate_paths()` helper. The Windows
  candidate list previously contained the same path three times; the
  helper deduplicates while preserving order.

### Fixed
- **B1 / TS4**: the `cv2` warm-up shim was moved into `tests/conftest.py` so
  `pytest --cov=visus.desktop` is reliable; the per-file duplicates were
  removed.

## [0.1.0] - 2026-05-27

First release under the **Visus** brand. This is a clean, professional repackaging of the
previously published `bot-vision-suite` library.

### Added
- `visus-desktop` distribution, importable as the namespace package `visus.desktop`.
- `py.typed` marker — the package now ships type information.
- Quality tooling: ruff (lint + format), mypy (gradual), and pre-commit hooks.
- Community docs: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`.
- A real, CI-safe test suite (environment-dependent tests are skipped with clear reasons).

### Changed
- **Rebrand of `bot-vision-suite`.** The main class `BotVision` is now `VisusBot`
  (the `BotVision` alias is kept for backward compatibility).
- `limpar_texto` is now `clean_text` (the `limpar_texto` alias is kept).
- Adopted a `src/` layout; configuration consolidated into `pyproject.toml`
  (removed `pytest.ini`, `requirements.txt`, and the stale `MANIFEST.in`).
- All human-readable text (docstrings, comments, messages, docs) translated to English.

### Fixed
- Repaired the test suite, which previously referenced a non-existent API.
- Removed dead/junk files (empty `overlay_new.py`, stray build output).
- Fixed a duplicate `__all__` and a `SyntaxWarning` in the package initializer.

### Migration
- Install with `pip install visus-desktop` and import via `from visus.desktop import VisusBot`.
- Existing code using `from bot_vision import BotVision` migrates by changing the import to
  `from visus.desktop import BotVision` — class behavior is unchanged.

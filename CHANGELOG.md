# Changelog — visus-desktop

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

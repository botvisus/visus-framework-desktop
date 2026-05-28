# Changelog — visus-desktop

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

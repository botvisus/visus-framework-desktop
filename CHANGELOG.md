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

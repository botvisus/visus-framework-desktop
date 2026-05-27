# Changelog — visus-desktop

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

# Contributing to Visus Desktop

Thanks for your interest in contributing! This document explains how to set up a development
environment and the conventions we follow.

## Project layout

`visus-desktop` uses a `src/` layout and is a PEP 420 namespace package under `visus.desktop`:

```
src/visus/desktop/   # library code (no __init__.py in src/visus/ — that creates the namespace)
tests/               # pytest test suite
examples/            # runnable usage examples
docs/                # documentation
scripts/             # maintenance/build helpers
```

## Development setup

Requires Python 3.8+ and [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
installed on your system.

```bash
# create and activate a virtual environment, then:
pip install -e ".[automation]"          # editable install with optional extras
pip install pytest pytest-cov ruff mypy pre-commit
pre-commit install                      # enable git hooks
```

(If you use `uv`, `uv sync` installs the `dev` dependency group defined in `pyproject.toml`.)

## Running checks

```bash
pytest                  # run the test suite (environment-dependent tests auto-skip)
ruff check .            # lint
ruff format .           # auto-format
mypy src                # type-check (gradual; not all code is fully typed yet)
```

All checks should pass (or tests skip with a clear reason) before you open a pull request.

## Conventions

- Code style and import sorting are handled by **ruff** (line length 88).
- All human-readable text (docstrings, comments, log/error messages) is written in **English**.
- Public API changes must keep backward-compatibility aliases where reasonable
  (e.g. `BotVision` aliases `VisusBot`).
- Add or update tests for any behavior change. Keep environment-dependent tests guarded with
  `@pytest.mark.skipif` so the suite stays green in CI.

## Pull requests

1. Create a feature branch from `main`.
2. Make focused commits with clear messages.
3. Ensure `pytest` and `ruff check` pass.
4. Open a PR describing the change and the motivation.

## Reporting issues

Use the GitHub issue tracker. For security issues, see [SECURITY.md](SECURITY.md).

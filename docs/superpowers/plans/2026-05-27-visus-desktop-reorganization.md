# visus-desktop Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the existing `bot-vision-suite` library into a clean, professional repository at `D:\bot_vision\visus-desktop\`, rebranded as `visus-desktop` (namespace `visus.desktop`), with src/ layout, unified config, quality tooling, fixed tests, and community files — without breaking functionality.

**Architecture:** Source of truth is `D:\bot_vision\new\bot_vision_suite\bot_vision_suite\` (package `bot_vision/`, plus tests/examples/docs/scripts/CI). We build a fresh git repo, copy the package into `src/visus/desktop/` (PEP 420 namespace — no `src/visus/__init__.py`), rebrand symbols with backward-compat aliases (`BotVision = VisusBot`, `limpar_texto = clean_text`), fix the broken test suite, and add ruff/mypy/pre-commit + community docs.

**Tech Stack:** Python 3.8+, setuptools (src layout), pytest, ruff, mypy, pre-commit. Verification venv: `D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe`.

---

## Conventions used in this plan

- **SRC** = `D:\bot_vision\new\bot_vision_suite\bot_vision_suite` (the existing library project root)
- **DST** = `D:\bot_vision\visus-desktop` (the new clean repo)
- **PY** = `D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe` (venv with runtime deps + pytest)
- All shell snippets are PowerShell. Run git commands from DST.

---

## Task 1: Initialize the clean repo

**Files:**
- Create: `D:\bot_vision\visus-desktop\.gitignore`
- Commit: the already-written spec under `docs/superpowers/specs/`

- [ ] **Step 1: Initialize git** (the `docs/` spec/plan already exist in DST)

```powershell
git -C "D:\bot_vision\visus-desktop" init
```

- [ ] **Step 2: Write `.gitignore`** at DST root (Python standard + ignore internal planning + build artifacts)

Content: standard Python `.gitignore` (byte-compiled, build/, dist/, *.egg-info/, .venv, .pytest_cache, .mypy_cache, .ruff_cache, htmlcov, .coverage) **plus** these lines so internal planning never ships:

```
# Internal planning docs (Claude/superpowers)
docs/superpowers/
```

- [ ] **Step 3: Commit scaffold**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "chore: init visus-desktop repo with design spec and plan"
```

Expected: one commit created. (`docs/superpowers/` is gitignored, so the spec/plan are kept locally but not tracked — that's intended; if you want them tracked, force-add. Default: untracked.)

> NOTE: Since `docs/superpowers/` is gitignored, force-add the spec+plan once for provenance: `git -C DST add -f docs/superpowers/specs docs/superpowers/plans` before the commit. Decide per preference; default in this plan = keep them tracked via force-add.

---

## Task 2: Copy package source into src/ layout

**Files:**
- Create: `DST\src\visus\desktop\` (copy of `SRC\bot_vision\`, minus dead files)
- Create: `DST\src\visus\desktop\py.typed`
- Delete (do not copy): `core/overlay_new.py` (0 bytes)
- Ensure NOT created: `DST\src\visus\__init__.py`

- [ ] **Step 1: Copy the package tree**

```powershell
New-Item -ItemType Directory -Force "D:\bot_vision\visus-desktop\src\visus" | Out-Null
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\bot_vision" "D:\bot_vision\visus-desktop\src\visus\desktop" -Recurse
```

- [ ] **Step 2: Remove dead/junk files from the copy**

```powershell
Remove-Item "D:\bot_vision\visus-desktop\src\visus\desktop\core\overlay_new.py" -Force
Remove-Item "D:\bot_vision\visus-desktop\src\visus\desktop\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem "D:\bot_vision\visus-desktop\src\visus\desktop" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

- [ ] **Step 3: Add `py.typed` marker** (empty file)

```powershell
New-Item -ItemType File "D:\bot_vision\visus-desktop\src\visus\desktop\py.typed" | Out-Null
```

- [ ] **Step 4: Verify NO `src\visus\__init__.py` exists** (namespace package requirement)

```powershell
Test-Path "D:\bot_vision\visus-desktop\src\visus\__init__.py"
```
Expected: `False`. If `True`, delete it.

- [ ] **Step 5: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "feat: import package source into src/visus/desktop namespace layout"
```

---

## Task 3: Rebrand symbols inside the package (with compat aliases)

**Files:**
- Modify: `DST\src\visus\desktop\__init__.py`
- Modify: `DST\src\visus\desktop\utils\text_filters.py`
- Modify: `DST\src\visus\desktop\utils\__init__.py` (if it re-exports `limpar_texto`)

- [ ] **Step 1: Rename main class `BotVision` → `VisusBot` + alias.** In `__init__.py`, change `class BotVision:` to `class VisusBot:`. After the class definition (and before/independent of `__all__`), add:

```python
# Backward-compatibility alias (previous brand: bot-vision-suite)
BotVision = VisusBot
```

Update internal references to `BotVision(` used by standalone helper functions in the same file (e.g. inside `execute_tasks`, `find_text`, `click_text`, etc.) to `VisusBot(` — search the file for `BotVision(` and replace constructor calls; keep the `BotVision` alias name available for external users.

- [ ] **Step 2: Rename `limpar_texto` → `clean_text` + alias.** In `text_filters.py`, rename `def limpar_texto(` to `def clean_text(`. At end of file add:

```python
# Backward-compatibility alias (Portuguese name)
limpar_texto = clean_text
```

- [ ] **Step 3: Update the import in `__init__.py`.** Change:

```python
from .utils.text_filters import limpar_texto, matches_filter
```
to:
```python
from .utils.text_filters import clean_text, limpar_texto, matches_filter
```
And in `utils/__init__.py`, if it imports/exports `limpar_texto`, add `clean_text` alongside.

- [ ] **Step 4: Fix the duplicate `__all__`.** `__init__.py` defines `__all__` twice (~line 2259 and ~line 2496). Merge into a single `__all__` at the end of the file containing all intended public symbols (include both `VisusBot` and `BotVision`, `clean_text`, `limpar_texto`, `matches_filter`, `execute_tasks`, `find_text`, `click_text`, `find_image`, `click_image`, `click_at`, `type_text`, and the other standalone helpers + exceptions). Remove the earlier duplicate.

- [ ] **Step 5: Fix `SyntaxWarning: invalid escape sequence '\P'`.** The module docstring at top of `__init__.py` contains an unescaped backslash (e.g. `C:\Program Files`). Make the module docstring a raw string: change the opening `"""` to `r"""`.

- [ ] **Step 6: Update branding strings.** In `__init__.py`, replace user-facing branding: log line `"Bot Vision Suite v1.3.0 inicializada"` → `"visus.desktop v0.1.0 inicializada"`; any `"Bot Vision Suite"` title in the module docstring → `"Visus Desktop"`. Update version references to `0.1.0`. Search the file for `Bot Vision Suite` and `1.3.0`.

- [ ] **Step 7: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "refactor: rebrand BotVision->VisusBot and limpar_texto->clean_text with aliases"
```

---

## Task 4: Write the unified `pyproject.toml`

**Files:**
- Create: `DST\pyproject.toml`
- Do NOT create: `pytest.ini`, `requirements.txt`, `MANIFEST.in`

- [ ] **Step 1: Write `pyproject.toml`** with this exact content:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "visus-desktop"
version = "0.1.0"
authors = [
    {name = "Matheus Pereira", email = "matheuszwilkdev@gmail.com"},
]
description = "Visus Desktop — automação de GUI desktop com OCR multi-técnica, detecção de imagem robusta, backtrack inteligente e mouse virtual não-intrusivo."
readme = "README.md"
license = "MIT"
requires-python = ">=3.8"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Software Development :: Testing",
    "Topic :: Desktop Environment",
]
keywords = ["automation", "gui", "ocr", "image-recognition", "rpa", "bot", "desktop-automation", "visus"]
dependencies = [
    "PyAutoGUI>=0.9.54",
    "pytesseract>=0.3.0",
    "opencv-python>=4.9.0",
    "Pillow>=10.0.0",
    "numpy>=1.24.0",
    "pyperclip>=1.8.2",
    "pywin32>=306; sys_platform=='win32'",
]

[project.optional-dependencies]
automation = ["keyboard>=0.13.5", "MouseInfo>=0.1.3", "pandas>=1.0.0"]
ai = ["openai>=1.0.0"]
web = ["webdriver-manager>=4.0.0"]

[dependency-groups]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.6.0",
    "mypy>=1.8.0",
    "pre-commit>=3.5.0",
]

[project.urls]
Homepage = "https://github.com/matheuszwilk/visus-desktop"
Documentation = "https://github.com/matheuszwilk/visus-desktop#readme"
Repository = "https://github.com/matheuszwilk/visus-desktop.git"
"Bug Tracker" = "https://github.com/matheuszwilk/visus-desktop/issues"

[tool.setuptools.packages.find]
where = ["src"]
include = ["visus*"]

[tool.setuptools.package-data]
"visus.desktop" = ["py.typed"]

[tool.ruff]
line-length = 88
target-version = "py38"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]  # line length handled by formatter; many PT docstrings are long

[tool.mypy]
python_version = "3.8"
ignore_missing_imports = true
warn_unused_ignores = false
# gradual typing: do not fail the build on every untyped def yet
disallow_untyped_defs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-ra --strict-markers"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests that may take longer to run",
]
```

Note: coverage flags are intentionally NOT in default `addopts` (keeps `pytest` runnable without the cov plugin); run coverage explicitly with `--cov=visus.desktop` when desired.

- [ ] **Step 2: Editable install into the verification venv**

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m pip install -e "D:\bot_vision\visus-desktop"
```
Expected: `Successfully installed visus-desktop-0.1.0`.

- [ ] **Step 3: Verify the namespace import + aliases work**

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -c "from visus.desktop import VisusBot, BotVision; from visus.desktop.utils.text_filters import clean_text, limpar_texto; print('OK', VisusBot is BotVision, clean_text is limpar_texto)"
```
Expected: `OK True True`

- [ ] **Step 4: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "build: add unified pyproject.toml (src layout, ruff, mypy, pytest)"
```

---

## Task 5: Copy and fix the test suite

**Files:**
- Create: `DST\tests\` (copy of `SRC\tests\`, minus dead/junk)
- Rename: `teste_cores_overlay.py` → `test_overlay_colors.py`
- Modify: every test file's imports (`bot_vision` → `visus.desktop`) and the 3 broken imports

- [ ] **Step 1: Copy tests**

```powershell
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\tests" "D:\bot_vision\visus-desktop\tests" -Recurse
Get-ChildItem "D:\bot_vision\visus-desktop\tests" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

- [ ] **Step 2: Rename the PT test file**

```powershell
Rename-Item "D:\bot_vision\visus-desktop\tests\teste_cores_overlay.py" "test_overlay_colors.py"
```

- [ ] **Step 3: Update ALL absolute imports** in every file under `tests/`: replace `bot_vision` with `visus.desktop` (e.g. `from bot_vision import ...` → `from visus.desktop import ...`, `from bot_vision.utils...` → `from visus.desktop.utils...`). Use Grep to find every occurrence first, then Edit each.

- [ ] **Step 4: Fix the 3 known-broken imports:**
  - `test_integration.py`: `from bot_visions0 import BotVision, execute_tasks, find_text, click_text` → `from visus.desktop import BotVision, execute_tasks, find_text, click_text`
  - `test_exceptions.py`: `OCRError` → `OCRProcessingError`. Verify every imported name exists in `exceptions.py` (`BotVisionError`, `TesseractNotFoundError`, `ImageNotFoundError`, `TextNotFoundError`, `InvalidRegionError`, `TaskExecutionError`, `ConfigurationError`, `OCRProcessingError`, `ImageProcessingError`); fix any other mismatches.
  - `test_utils.py`: `from bot_vision.utils.text_filters import clean_text, filter_text_by_keywords` → import the names that actually exist now: `from visus.desktop.utils.text_filters import clean_text, matches_filter`. If a test references `filter_text_by_keywords` (nonexistent), update the test to use `matches_filter` per its real signature, or remove that specific assertion if it has no real counterpart.

- [ ] **Step 5: Run the suite**

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m pytest "D:\bot_vision\visus-desktop\tests" -p no:cacheprovider
```
Expected: collection succeeds (no ImportErrors). Triage remaining failures: GUI/screen-dependent tests (overlay, pyautogui screenshot) may need `@pytest.mark.skipif` for headless/no-display or Tesseract-not-installed. Mark environment-dependent tests as `skip`/`skipif` with a clear reason rather than deleting them. Target: **no errors; passes or explicitly-skipped only.**

- [ ] **Step 6: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "test: port tests to visus.desktop and fix broken imports (suite green)"
```

---

## Task 6: Copy and normalize examples

**Files:**
- Create: `DST\examples\` (copy of `SRC\examples\`)
- Rename PT example file(s); update imports

- [ ] **Step 1: Copy examples**

```powershell
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\examples" "D:\bot_vision\visus-desktop\examples" -Recurse
Get-ChildItem "D:\bot_vision\visus-desktop\examples" -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

- [ ] **Step 2: Rename PT example files to EN**

```powershell
Rename-Item "D:\bot_vision\visus-desktop\examples\exemplo_overlay_config.py" "overlay_config_example.py"
```
Review `migration_guide.py`, `migration_guide_new_features.py`, `new_features_example.py` — keep names but ensure they're descriptive; rename `new_features_example.py` only if a clearer name is obvious (otherwise leave).

- [ ] **Step 3: Update imports** in every example: `bot_vision` → `visus.desktop`; update any `BotVision` usage doc text mentioning the old install/import (functionally `BotVision` still works via alias).

- [ ] **Step 4: Smoke-check examples import-parse** (do not execute GUI actions; just byte-compile)

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m py_compile (Get-ChildItem "D:\bot_vision\visus-desktop\examples\*.py" | ForEach-Object { $_.FullName })
```
Expected: no syntax errors.

- [ ] **Step 5: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "docs: port examples to visus.desktop and normalize names"
```

---

## Task 7: Move helper scripts into scripts/

**Files:**
- Create: `DST\scripts\` with `build_package.py`, `check_dependencies.py`, `update_pypi.ps1`, `validate_package.py`

- [ ] **Step 1: Copy scripts**

```powershell
New-Item -ItemType Directory -Force "D:\bot_vision\visus-desktop\scripts" | Out-Null
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\build_package.py"     "D:\bot_vision\visus-desktop\scripts\"
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\check_dependencies.py" "D:\bot_vision\visus-desktop\scripts\"
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\update_pypi.ps1"       "D:\bot_vision\visus-desktop\scripts\"
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\validate_package.py"   "D:\bot_vision\visus-desktop\scripts\"
```

- [ ] **Step 2: Update references in scripts** — any hardcoded `bot-vision-suite`, `bot_vision`, version `1.3.1`, or relative paths assuming root-level files. Update to `visus-desktop` / `visus.desktop` / `0.1.0`, and adjust paths for the `src/` layout (e.g. building from project root still works; `--cov=visus.desktop`). Grep these files for `bot_vision`, `bot-vision`, `1.3.1`.

- [ ] **Step 3: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "chore: move helper scripts into scripts/ and update for visus-desktop"
```

---

## Task 8: Documentation — README, docs/, CHANGELOG, LICENSE

**Files:**
- Create: `DST\README.md`, `DST\CHANGELOG.md`, `DST\LICENSE`
- Create: `DST\docs\` (api_reference.md, installation.md, README.md)

- [ ] **Step 1: Copy LICENSE as-is**

```powershell
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\LICENSE" "D:\bot_vision\visus-desktop\LICENSE"
```

- [ ] **Step 2: Copy README + docs, then rebrand**

```powershell
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\README.md" "D:\bot_vision\visus-desktop\README.md"
Copy-Item "D:\bot_vision\new\bot_vision_suite\bot_vision_suite\docs" "D:\bot_vision\visus-desktop\docs\" -Recurse -Force
```
Then in `README.md` and every file under `docs/` (api_reference.md, installation.md, README.md): replace `pip install bot-vision-suite` → `pip install visus-desktop`; `from bot_vision import BotVision` → `from visus.desktop import VisusBot` (mention `BotVision` alias for migration); `import bot_vision` → `import visus.desktop`; `bot-vision-suite`/`Bot Vision Suite` → `visus-desktop`/`Visus Desktop`. Add a short "Migrating from bot-vision-suite" note near the top of the README.

- [ ] **Step 3: Write a fresh `CHANGELOG.md`** starting with:

```markdown
# Changelog — visus-desktop

## [0.1.0] - 2026-05-27

### Added
- First release under the **Visus** brand as `visus-desktop` (namespace package `visus.desktop`).
- `py.typed` marker (the package now ships type information).
- Quality tooling: ruff (lint+format), mypy (gradual), pre-commit.
- Community docs: CONTRIBUTING, SECURITY, CODE_OF_CONDUCT.

### Changed
- **Rebrand of `bot-vision-suite`.** Main class `BotVision` is now `VisusBot` (alias `BotVision` kept for backward compatibility).
- `limpar_texto` is now `clean_text` (alias `limpar_texto` kept).
- Adopted `src/` layout; configuration consolidated into `pyproject.toml` (removed `pytest.ini`, `requirements.txt`, stale `MANIFEST.in`).

### Fixed
- Repaired the test suite (broken imports) — now green.
- Removed dead/junk files (`overlay_new.py`, stray build output).
- Fixed duplicate `__all__` and a `SyntaxWarning` in the package init.

### Migration
- `pip install visus-desktop` and `from visus.desktop import VisusBot`.
- Existing code using `from bot_vision import BotVision` migrates by changing the import to `from visus.desktop import BotVision` (class behavior unchanged).
```

- [ ] **Step 4: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "docs: rebrand README/docs and add 0.1.0 changelog"
```

---

## Task 9: Tooling configs + community files

**Files:**
- Create: `DST\.pre-commit-config.yaml`, `DST\CONTRIBUTING.md`, `DST\SECURITY.md`, `DST\CODE_OF_CONDUCT.md`

- [ ] **Step 1: Write `.pre-commit-config.yaml`**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

- [ ] **Step 2: Write `CONTRIBUTING.md`** (English): how to set up dev env (`pip install -e ".[dev]"` / `uv sync`), run tests (`pytest`), lint/format (`ruff check`, `ruff format`), type-check (`mypy src`), install hooks (`pre-commit install`), branch/PR conventions, and that the package lives under `src/visus/desktop/`.

- [ ] **Step 3: Write `SECURITY.md`** (English): supported versions table (0.1.x), how to report a vulnerability privately (email `matheuszwilkdev@gmail.com`), expected response window.

- [ ] **Step 4: Write `CODE_OF_CONDUCT.md`** — Contributor Covenant v2.1 standard text, contact `matheuszwilkdev@gmail.com`.

- [ ] **Step 5: Run ruff and verify (or capture baseline)**

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m ruff check "D:\bot_vision\visus-desktop\src" "D:\bot_vision\visus-desktop\tests"
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m ruff format --check "D:\bot_vision\visus-desktop\src"
```
Expected: either clean, or apply `ruff check --fix` and `ruff format` (then re-run pytest to confirm still green) and commit the formatting. Do not let auto-format change behavior — run tests after.

- [ ] **Step 6: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "chore: add pre-commit, ruff/format pass, and community docs"
```

---

## Task 10: CI workflows

**Files:**
- Create: `DST\.github\workflows\test.yml`, `DST\.github\workflows\publish.yml`

- [ ] **Step 1: Copy workflows**

```powershell
New-Item -ItemType Directory -Force "D:\bot_vision\visus-desktop\.github\workflows" | Out-Null
Copy-Item "D:\bot_vision\new\bot_vision_suite\.github\workflows\test.yml"    "D:\bot_vision\visus-desktop\.github\workflows\"
Copy-Item "D:\bot_vision\new\bot_vision_suite\.github\workflows\publish.yml" "D:\bot_vision\visus-desktop\.github\workflows\"
```

- [ ] **Step 2: Update workflows** — install via `pip install -e ".[dev]"` (or `pip install .[automation] pytest`), run `ruff check` + `pytest`, set coverage to `--cov=visus.desktop`, and any package-name references (`bot-vision-suite` → `visus-desktop`) in build/publish steps. Verify the Python matrix still matches `requires-python = ">=3.8"`.

- [ ] **Step 3: Commit**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "ci: add test and publish workflows for visus-desktop"
```

---

## Task 11: Final verification (acceptance criteria)

- [ ] **Step 1: Clean reinstall + import check**

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m pip install -e "D:\bot_vision\visus-desktop" --force-reinstall --no-deps
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -c "import visus.desktop as d; from visus.desktop import VisusBot, BotVision, execute_tasks, find_text, click_text, find_image, click_image; print('import OK', d.__file__)"
```
Expected: prints `import OK` and a path under `...\visus-desktop\src\visus\desktop\__init__.py`.

- [ ] **Step 2: Full test run**

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m pytest "D:\bot_vision\visus-desktop\tests" -p no:cacheprovider -ra
```
Expected: no errors; all passed or explicitly skipped (skips have reasons).

- [ ] **Step 3: Build sanity (sdist/wheel)**

```powershell
& "D:\bot_vision\new\bot_vision_suite\.venv\Scripts\python.exe" -m build "D:\bot_vision\visus-desktop"
```
Expected: builds `visus_desktop-0.1.0.tar.gz` and `.whl` under `dist/` (gitignored). If `build` missing, `pip install build` first. Confirm the wheel contains `visus/desktop/py.typed`.

- [ ] **Step 4: Confirm namespace hygiene + no junk**

```powershell
Test-Path "D:\bot_vision\visus-desktop\src\visus\__init__.py"   # expect False
Test-Path "D:\bot_vision\visus-desktop\0.37.0"                  # expect False
Test-Path "D:\bot_vision\visus-desktop\pytest.ini"              # expect False
Test-Path "D:\bot_vision\visus-desktop\requirements.txt"        # expect False
```
Expected: all `False`.

- [ ] **Step 5: Final commit + summary**

```powershell
git -C "D:\bot_vision\visus-desktop" add -A
git -C "D:\bot_vision\visus-desktop" commit -m "chore: final verification pass for visus-desktop 0.1.0"
git -C "D:\bot_vision\visus-desktop" log --oneline
```

---

## Self-review notes (coverage of spec)

- Brand strategy / namespace → Tasks 2, 4 (no `visus/__init__.py`, `where=["src"]`).
- Rebrand class + clean_text + aliases → Task 3. Compat for `a.py` → alias in Task 3 + README note in Task 8.
- Junk removal (`0.37.0`, `overlay_new.py`, build/dist/egg-info) → not copied (Tasks 2, 5, 6) + verified Task 11.
- Config unification (no pytest.ini/requirements.txt/MANIFEST.in) → Task 4 + verified Task 11.
- Dedup dependency groups → Task 4.
- Tooling (ruff/mypy/pre-commit/py.typed) → Tasks 2, 4, 9.
- Test fixes (3 broken imports) + green suite → Task 5, verified Task 11.
- PT→EN file names → Tasks 5, 6.
- `__all__` dup + `\P` warning → Task 3.
- Community files + docs → Tasks 8, 9.
- Version 0.1.0, no PyPI publish → Tasks 4, 8 (publish workflow added but not run).
- CI → Task 10.
```

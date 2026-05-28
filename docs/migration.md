# Migration — from `bot-vision-suite` to `visus-desktop`

`visus-desktop` is the clean repackaging of the previously published
`bot-vision-suite` library. The runtime behaviour of the **public API**
is unchanged; only the distribution name, the namespace, and a handful
of renamed entry points have moved. Backwards-compatible aliases are in
place so you can migrate in two phases (imports first, then names) if
that suits your codebase better.

> This is the formal migration guide. The runnable counterpart lives in
> [`examples/migration_guide.py`](../examples/migration_guide.py) and
> shows the patterns side-by-side.

## TL;DR

```diff
- pip install bot-vision-suite
+ pip install visus-desktop

- from bot_vision import BotVision
+ from visus.desktop import VisusBot
```

Everything else (task-list format, `execute_tasks`, OCR confidence,
backtrack, etc.) keeps the same shape and defaults.

## Install

```bash
pip uninstall bot-vision-suite -y       # optional, but recommended
pip install visus-desktop
```

Optional extras:

```bash
pip install "visus-desktop[native]"      # pywinauto (Windows-only)
pip install "visus-desktop[automation]"  # keyboard, MouseInfo, pandas
pip install "visus-desktop[ai]"          # openai
pip install "visus-desktop[web]"         # webdriver-manager
```

Verify the install in one command:

```bash
python -m visus.desktop.doctor
# or, after install:
visus-doctor
```

## Imports

| Old (`bot-vision-suite`) | New (`visus-desktop`) |
|---|---|
| `from bot_vision import BotVision` | `from visus.desktop import VisusBot` |
| `from bot_vision import execute_tasks` | `from visus.desktop import execute_tasks` |
| `from bot_vision import limpar_texto` | `from visus.desktop import clean_text` |
| `from bot_vision import BotVisionConfig` | `from visus.desktop import BotVisionConfig` |
| `from bot_vision.exceptions import ...` | `from visus.desktop.exceptions import ...` |

**Aliases kept for backwards compatibility:**

```python
from visus.desktop import BotVision      # alias for VisusBot
from visus.desktop import limpar_texto   # alias for clean_text
```

You can migrate the import paths first and keep using the old class
name; the aliases will not be removed.

## Renames in detail

| Old name | New canonical name | Reason |
|---|---|---|
| `BotVision` | `VisusBot` | Aligns with the **Visus** product family. |
| `limpar_texto` | `clean_text` | All public identifiers are English. |

The behaviour of both pairs is identical.

## Task-list format — unchanged

Task dictionaries have the same shape:

```python
tasks = [
    {"image": "button.png", "region": (0, 0, 800, 600),
     "confidence": 0.9, "backtrack": True},
    {"text": "Login", "region": (50, 50, 300, 100),
     "char_type": "letters"},
    {"type": "type_text", "text": "hello"},
    {"type": "keyboard_command", "command": "Ctrl+S"},
]
```

The new task types added since the rename are pure **additions** —
they do not break any old task dict.

| Task type | When added | Notes |
|---|---|---|
| `click` (with `x`/`y`) | bot-vision-suite 1.3 | Click absolute coordinates. |
| `type_text` | bot-vision-suite 1.3 | Type text directly. |
| `keyboard_command` | bot-vision-suite 1.3 | Send shortcut. |
| `relative_image` | bot-vision-suite 1.3 | Anchor + target image. |
| `extract_text` | visus-desktop 0.1 | Extract OCR text into `last_extracted_text`. |

## Bug fixes you get for free

The rebrand bundled the following fixes — if you hit any of them on the
old package, the migration is also the cure:

* `type_text` task dispatch (the OCR branch could intercept tasks with a
  `"text"` key when `"type": "type_text"` was explicitly set).
* Overlay fallback `UnboundLocalError` when Tk was unavailable.
* Virtual-mouse DPI scaling on high-DPI Windows displays.
* Duplicate `__all__` and a `SyntaxWarning` in the package initializer.
* Coverage was unreliable due to a `cv2.gapi.wip.draw.Text` lazy-import;
  the warm-up shim now lives in `tests/conftest.py`.

## New in visus-desktop (Phase 1, unreleased)

These are pure additions — opt-in via config:

* **Screenshot-on-failure** — `config['artifacts_dir']`,
  `config['screenshot_on_failure']`. Failed tasks save a PNG named
  `<run_id>__<task_id>__<timestamp>.png` and the path lands on
  `TaskResult.failure_screenshot`.
* **Structured JSON task events** — set `config['log_format'] = 'json'`
  to receive one JSON object per task on the
  `visus.desktop.task_events` logger.
* **`@retry` decorator** — `from visus.desktop import retry` for
  arbitrary callables (HTTP, file I/O, third-party APIs).
* **`visus-doctor` CLI** — `python -m visus.desktop.doctor` /
  `visus-doctor` checks Tesseract, deps, display, pywinauto.
* **Graceful SIGINT** — Ctrl+C during `execute_tasks` releases any held
  mouse buttons before propagating.

See [`CHANGELOG.md`](../CHANGELOG.md) for the authoritative list.

## Step-by-step checklist

1. `pip install visus-desktop`.
2. Update imports: `bot_vision` → `visus.desktop`.
3. Run `visus-doctor` and resolve any `[FAIL]` lines.
4. Run your existing test suite. The aliases (`BotVision`,
   `limpar_texto`) should keep everything green.
5. Rename `BotVision` → `VisusBot` and `limpar_texto` → `clean_text`
   in your own code (optional, but recommended).
6. Adopt one of the new opt-ins (screenshot-on-failure is the highest
   ROI quick win).
7. Remove `bot-vision-suite` from your environment and CI image.

## See also

* [API reference](api_reference.md)
* [Installation](installation.md)
* [Cookbook](cookbook/README.md)
* [Troubleshooting](troubleshooting.md)
* Runnable example: [`examples/migration_guide.py`](../examples/migration_guide.py)

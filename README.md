<div align="center">

# Visus Desktop

**Desktop GUI automation that *sees* the screen — multi-technique OCR, robust image detection, smart backtracking, and a non-intrusive virtual mouse.**

[![PyPI](https://img.shields.io/pypi/v/visus-desktop.svg)](https://pypi.org/project/visus-desktop/)
[![Python](https://img.shields.io/pypi/pyversions/visus-desktop.svg)](https://pypi.org/project/visus-desktop/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/matheuszwilk/visus-desktop/actions/workflows/test.yml/badge.svg)](https://github.com/matheuszwilk/visus-desktop/actions/workflows/test.yml)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230.svg)](https://github.com/astral-sh/ruff)

</div>

Visus Desktop automates desktop applications the way a person does: it **reads on‑screen text** with
OCR (Tesseract), **locates UI elements by image** template matching, and **clicks, types, or sends
keyboard shortcuts** to drive the app — even when there is no API to hook into. It is built for RPA
and end‑to‑end UI automation on Windows, Linux, and macOS.

> **Part of the Visus family.** `visus-desktop` (import root `visus.desktop`) is the first module of
> the planned **Visus** automation ecosystem, designed to sit alongside future `visus.web` (browser
> automation) and a cloud RPA orchestrator under one namespace.

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage guide](#usage-guide)
  - [Find & click text (OCR)](#find--click-text-ocr)
  - [Find & click images](#find--click-images)
  - [Relative images](#relative-images)
  - [Coordinates, typing & keyboard](#coordinates-typing--keyboard)
  - [Text extraction](#text-extraction)
  - [Task‑list automation](#task-list-automation)
  - [Backtracking sessions](#backtracking-sessions)
  - [Wait parameters](#wait-parameters)
  - [Virtual mouse](#virtual-mouse)
  - [Visual overlay](#visual-overlay)
  - [Standalone functions](#standalone-functions)
  - [Text helpers](#text-helpers)
- [Configuration](#configuration)
- [Error handling](#error-handling)
- [Migrating from `bot-vision-suite`](#migrating-from-bot-vision-suite)
- [Project layout](#project-layout)
- [Development & testing](#development--testing)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **🔎 OCR text search & click** — find on‑screen text with Tesseract and click it, with character
  filtering (`letters` / `numbers` / `both`) and occurrence selection.
- **🖼️ Image detection & click** — locate UI elements by template image, with adjustable confidence
  and optional automatic scale variations for resolution‑independent matching.
- **🎯 Relative‑image detection** — find a target image *near* a unique anchor image (great when many
  identical buttons exist on screen).
- **⌨️ Typing & keyboard commands** — type text (with special sequences like `{ctrl}a`, `{del}`,
  `{tab}`, `{enter}`) and send named shortcuts such as `Ctrl+S`, `F7`, `Alt+Tab`.
- **📋 Task‑list automation** — describe a whole workflow as a list of dictionaries and run it with a
  single `execute_tasks` call.
- **↩️ Smart backtracking** — when a step fails, re‑run the previous step and retry, both inside task
  lists and between individual method calls.
- **⏳ Wait parameters** — wait for an element to appear or disappear (`wait_until_found`,
  `wait_until_disappears`, `wait_timeout`).
- **🖱️ Virtual mouse** — perform clicks **without moving the physical cursor** (`use_virtual_mouse`),
  so automations don't fight you for the mouse.
- **🟥 Visual overlay** — draw a colored rectangle over the target before clicking — perfect for
  debugging and demos.
- **🧠 Multi‑technique OCR** — a preprocessing pipeline (HSV/LAB, masking, thresholding, and more)
  improves recognition on tricky UIs.
- **♻️ Backward compatible** — drop‑in aliases (`BotVision`, `limpar_texto`) for code written against
  `bot-vision-suite`.
- **🏷️ Typed** — ships a `py.typed` marker for type checkers.

---

## Requirements

- **Python 3.8+**
- **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed on the system** — this
  is a hard requirement; Visus Desktop shells out to the Tesseract binary for OCR.
- Core Python dependencies are installed automatically: `PyAutoGUI`, `pytesseract`, `opencv-python`,
  `Pillow`, `numpy`, `pyperclip` (plus `pywin32` on Windows).

### Install Tesseract OCR

| OS | Command / link |
|----|----------------|
| **Windows** | Download the installer from <https://github.com/UB-Mannheim/tesseract/wiki> |
| **Linux** (Debian/Ubuntu) | `sudo apt-get install tesseract-ocr` |
| **macOS** | `brew install tesseract` |

On Windows, the default location `C:\Program Files\Tesseract-OCR\tesseract.exe` is detected
automatically. You can also add Tesseract to your `PATH`, or set `tesseract_path` in the
[configuration](#configuration). Verify with:

```bash
tesseract --version
```

---

## Installation

```bash
pip install visus-desktop
```

Optional extras:

```bash
pip install "visus-desktop[automation]"   # keyboard, MouseInfo, pandas
pip install "visus-desktop[ai]"           # openai
pip install "visus-desktop[web]"          # webdriver-manager
```

See [docs/installation.md](docs/installation.md) for detailed, per‑OS instructions and
troubleshooting.

---

## Quickstart

```python
from visus.desktop import VisusBot

bot = VisusBot()

bot.click_text("Login")              # find on-screen text via OCR and click it
bot.click_image("save_button.png")   # find a UI element by template image and click it
bot.type_text("hello world")         # type into the focused field
```

Restricting the search to a screen `region` (faster and more reliable):

```python
from visus.desktop import VisusBot

bot = VisusBot()

# region is (x, y, width, height) — x, y is the top-left corner
if bot.find_text("Username", region=(100, 100, 500, 300), filter_type="letters"):
    bot.click_text("Username", region=(100, 100, 500, 300), sendtext="admin")
```

---

## Usage guide

The library can be used through the **`VisusBot`** class (recommended) or through
[standalone functions](#standalone-functions) that create a temporary bot internally.

Conventions:

- **`region`** = `(x, y, width, height)`; `x, y` is the top‑left corner.
- **locations** returned by `find_*` are `(x, y, width, height)` tuples, or `None` if nothing matched.
- **`mouse_button`** = `"left"` | `"right"` | `"double"` | `"move_to"`.
- **`filter_type` / `char_type`** = `"letters"` | `"numbers"` | `"both"`.
- **`confidence`** (image matching) is `0.0–1.0`; **`confidence_threshold`** (OCR) is `0–100`.

### Find & click text (OCR)

```python
bot = VisusBot()

# find_text -> (x, y, width, height) or None
location = bot.find_text("Confirm", region=(0, 0, 800, 600), filter_type="both")

# click_text -> True / False
bot.click_text(
    "Confirm",
    region=(0, 0, 800, 600),
    filter_type="letters",   # "letters" | "numbers" | "both"
    occurrence=1,            # which match to click (1 = first)
    mouse_button="left",
    delay=1,                 # seconds to pause after the click
    sendtext="my text",      # optional: type after clicking
)
```

### Find & click images

```python
bot = VisusBot()

location = bot.find_image("button.png", region=(100, 100, 300, 200), confidence=0.9)

bot.click_image(
    "button.png",
    confidence=0.9,        # 0.0–1.0
    specific=True,         # True: search the region; False: full screen + scale variations
    mouse_button="double",
    delay=1,
)
```

`specific=False` also tries scaled versions of the template, which helps when the UI renders at a
different resolution/DPI. You can pass an explicit `scales=[1.0, 0.95, 1.05]` list too.

### Relative images

Find a target image positioned near a unique anchor — ideal when several identical targets exist:

```python
bot = VisusBot()

# Click the "OK" closest to the warning icon
bot.click_relative_image(
    anchor_image="warning_icon.png",
    target_image="ok_button.png",
    max_distance=200,                  # max pixels between anchor and target
    confidence=0.9,
    target_region=(0, 0, 800, 600),    # optional region to search the target
)
```

### Coordinates, typing & keyboard

```python
bot = VisusBot()

bot.click_coordinates(500, 300, mouse_button="right", delay=0.5)
bot.click_at((500, 300, 0, 0))                     # click using a location tuple

bot.type_text("{ctrl}a{del}New value{enter}")      # special key sequences supported
bot.keyboard_command("Ctrl+S")                     # named shortcut

print(bot.get_available_keyboard_commands())       # list supported command names
```

### Text extraction

```python
bot = VisusBot()

# Plain list of strings
lines = bot.extract_text_from_region(region=(0, 0, 800, 200), filter_type="both")

# Rich data: text + confidence + bounding boxes
data = bot.extract_text_from_region(region=(0, 0, 800, 200), return_full_data=True)
for item in data:
    print(item["text"], item["confidence"], item["absolute_box"])
```

### Task‑list automation

Describe an entire workflow as a list of dictionaries and run it with one call. Each task is
dispatched by its keys:

| Task | Identifying key(s) | Common fields |
|------|--------------------|---------------|
| Text (OCR) click | `text` | `region`, `char_type`, `occurrence`, `confidence`, `backtrack`, `delay`, `sendtext` |
| Image click | `image` | `region`, `confidence`, `specific`, `mouse_button`, `backtrack`, `delay` |
| Relative image | `type: "relative_image"` | `anchor_image`, `target_image`, `max_distance`, `confidence`, `target_region` |
| Coordinate click | `type: "click"` | `x`, `y`, `mouse_button`, `delay` |
| Type text | `type: "type_text"` | `text`, `interval`, `delay` |
| Keyboard command | `type: "keyboard_command"` | `command`, `delay` |
| Extract text | `type: "extract_text"` | `region`, `filter_type`, `confidence_threshold`, `return_full_data` |

```python
from visus.desktop import VisusBot

bot = VisusBot()

tasks = [
    # 1) OCR text search + click, then type into the field
    {
        "text": "Username",
        "region": (100, 100, 500, 300),
        "char_type": "letters",
        "occurrence": 1,
        "backtrack": True,
        "delay": 0.5,
        "sendtext": "admin{tab}secret{enter}",
    },
    # 2) Image search + click
    {"image": "login_button.png", "confidence": 0.9, "specific": False, "delay": 1},
    # 3) Relative image
    {
        "type": "relative_image",
        "anchor_image": "warning_icon.png",
        "target_image": "ok_button.png",
        "max_distance": 200,
        "confidence": 0.9,
    },
    # 4) Click at coordinates
    {"type": "click", "x": 500, "y": 300, "mouse_button": "left", "delay": 0.5},
    # 5) Type text
    {"type": "type_text", "text": "Hello World!", "interval": 0.05, "delay": 1},
    # 6) Keyboard command
    {"type": "keyboard_command", "command": "Ctrl+S", "delay": 1},
]

results = bot.execute_tasks(tasks)            # -> list[TaskResult]
for r in results:
    print(r.task_name, r.success)
```

The module‑level `execute_tasks(tasks, config=None)` works without instantiating the class and
accepts either a single list of tasks or a list of task lists run sequentially.

### Backtracking sessions

When a step fails, backtracking re‑runs the previous step and retries the failed one:

```python
bot = VisusBot()

bot.start_task_session()
bot.click_image("step1.png", backtrack=True)
bot.click_text("Next", backtrack=True)        # if it fails, step1 is re-run, then retried
successful, total = bot.end_task_session()
print(f"{successful}/{total} steps succeeded")
```

Using `backtrack=True` without an active session starts one automatically.

### Wait parameters

Synchronize with a changing UI on most `find_*` / `click_*` methods:

```python
bot = VisusBot()

# Wait until the button appears (up to wait_timeout seconds), then click it
bot.click_image("submit.png", wait_until_found=True, wait_timeout=15)

# Wait until a loading spinner disappears before continuing
bot.find_image("loading.png", wait_until_disappears=True, wait_timeout=60)
```

`wait_timeout` defaults to the global config value (30s) and can be overridden per call.

### Virtual mouse

Perform clicks **without moving the physical cursor** — the automation won't steal the mouse:

```python
from visus.desktop import VisusBot

bot = VisusBot(config={"use_virtual_mouse": True})
bot.click_image("save_button.png")   # cursor stays where it is
```

### Visual overlay

Draw a colored rectangle over the target before clicking — great for debugging:

```python
bot = VisusBot(config={"show_overlay": True, "overlay_color": "blue"})

bot.configure_overlay(color="green", duration=800, width=3)
print(bot.get_overlay_config())
print(VisusBot.get_available_overlay_colors())
# red, blue, green, yellow, purple, orange, cyan, magenta, white, black
```

### Standalone functions

Prefer not to manage an instance? Import functions directly — each creates a temporary bot:

```python
from visus.desktop import find_text, click_text, click_image, execute_tasks, type_text

click_text("Login", region=(0, 0, 800, 600))
click_image("submit.png", confidence=0.9)
execute_tasks([{"text": "OK"}, {"type": "keyboard_command", "command": "Enter"}])
```

> **Note:** the standalone `type_text(text, config=None)` takes only those two arguments. For
> `interval` / `delay` / `backtrack`, use the `VisusBot.type_text` method or `type_text_standalone`.

### Text helpers

```python
from visus.desktop import clean_text, matches_filter

clean_text("  123abc!  ", "numbers")   # "123"
clean_text("  123abc!  ", "letters")   # "abc"
clean_text("  123abc!  ", "both")      # "123abc"

matches_filter("15", "numbers")        # True  (integers 1–31)
matches_filter("32", "numbers")        # False
```

---

## Configuration

`BotVisionConfig` takes a **dictionary** (not keyword arguments). You can pass a dict straight to
`VisusBot(config=...)` or build a `BotVisionConfig` explicitly.

```python
from visus.desktop import BotVisionConfig, VisusBot

config = BotVisionConfig({
    "confidence_threshold": 80.0,   # OCR threshold (0–100)
    "overlay_color": "blue",
    "use_virtual_mouse": True,
    "wait_timeout": 45,
    "default_mouse_button": "left",
})

bot = VisusBot(config=config)
```

Recognized keys (with defaults):

| Key | Default | Description |
|-----|---------|-------------|
| `tesseract_path` | auto | Path to the Tesseract executable. |
| `tesseract_data_path` | auto | Path to the `tessdata` directory. |
| `confidence_threshold` | `75.0` | Default OCR confidence (0–100). |
| `retry_attempts` | `3` | Default retry attempts. |
| `default_delay` | `1.0` | Default pause (s) between actions. |
| `overlay_duration` | `1000` | Overlay display time (ms). |
| `overlay_color` | `"red"` | red/blue/green/yellow/purple/orange/cyan/magenta/white/black. |
| `overlay_width` | `4` | Overlay line width. |
| `show_overlay` | `True` | Show overlay before clicks. |
| `overlay_enabled` | `True` | Overlay system active. |
| `default_mouse_button` | `"left"` | left/right/double/move_to. |
| `log_level` | `"INFO"` | Logging level. |
| `ocr_languages` | `["eng"]` | Tesseract language(s). |
| `image_processing_methods` | `"all"` | OCR preprocessing methods. |
| `click_duration` | `0.1` | Click duration (s). |
| `movement_duration` | `0.1` | Mouse movement duration (s). |
| `use_virtual_mouse` | `False` | Click without moving the cursor. |
| `wait_timeout` | `30` | Global wait timeout (s). |
| `screenshot_delay` | `0.1` | Delay before screen capture (s). |

Full reference: [docs/api_reference.md](docs/api_reference.md).

---

## Error handling

All exceptions live in `visus.desktop.exceptions` and subclass `BotVisionError`:

```python
from visus.desktop import VisusBot
from visus.desktop.exceptions import TesseractNotFoundError, TaskExecutionError

try:
    bot = VisusBot()
    bot.click_text("Login")
except TesseractNotFoundError:
    print("Please install Tesseract OCR.")
except TaskExecutionError as e:
    print(f"Automation step failed: {e}")
```

| Exception | Raised when |
|-----------|-------------|
| `BotVisionError` | Base class for all Visus Desktop errors. |
| `TesseractNotFoundError` | Tesseract OCR is not found on the system. |
| `ImageNotFoundError` | An image is not found on screen. |
| `TextNotFoundError` | Text is not found in the specified region. |
| `InvalidRegionError` | An invalid region was specified. |
| `TaskExecutionError` | An error occurred while executing a task. |
| `ConfigurationError` | A configuration error (e.g. a missing dependency). |
| `OCRProcessingError` | An error during OCR processing. |
| `ImageProcessingError` | An error during image processing. |

---

## Migrating from `bot-vision-suite`

Visus Desktop is the rebrand of the previously published `bot-vision-suite`. Migration is a one‑line
import change — behavior is unchanged and aliases are kept.

```diff
- pip install bot-vision-suite
+ pip install visus-desktop
```

```diff
- from bot_vision import BotVision
+ from visus.desktop import VisusBot          # BotVision still works as an alias
```

| Old | New | Notes |
|-----|-----|-------|
| `pip install bot-vision-suite` | `pip install visus-desktop` | new distribution name |
| `import bot_vision` | `import visus.desktop` | namespace package |
| `BotVision` | `VisusBot` | `BotVision` kept as an alias |
| `limpar_texto` | `clean_text` | `limpar_texto` kept as an alias |

---

## Project layout

```
visus-desktop/
├── src/visus/desktop/    # library code (PEP 420 namespace: no __init__.py in src/visus/)
│   ├── core/             # OCR, image processing, overlay, task executor, virtual mouse, ...
│   └── utils/            # config, text filters
├── tests/                # pytest suite
├── examples/             # runnable usage examples
├── docs/                 # installation & API reference
└── scripts/              # build / validation helpers
```

---

## Development & testing

```bash
git clone https://github.com/matheuszwilk/visus-desktop.git
cd visus-desktop

python -m venv .venv && . .venv/Scripts/activate   # Windows; use . .venv/bin/activate on Unix
pip install -e ".[automation]"
pip install pytest pytest-cov ruff mypy pre-commit
pre-commit install
```

Run the checks:

```bash
pytest            # test suite (environment-dependent tests auto-skip)
ruff check .      # lint
ruff format .     # format
mypy src          # type-check (gradual)
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for the development
workflow and conventions, and note our [Code of Conduct](CODE_OF_CONDUCT.md). For security reports,
see [SECURITY.md](SECURITY.md).

---

## License

Released under the [MIT License](LICENSE).

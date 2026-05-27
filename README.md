# Visus Desktop

**Desktop GUI automation with multi-technique OCR, robust image detection, smart backtracking, and a non-intrusive virtual mouse.**

Visus Desktop lets you automate desktop applications by *seeing* the screen the way a person does: it reads on-screen text with OCR (Tesseract), locates UI elements by image template matching, and clicks, types, or sends keyboard shortcuts to drive the application — even when there is no programmatic API to hook into.

> **Part of the Visus family** — Visus Desktop (`visus.desktop`) is the first module of the planned **Visus** automation family. The distribution is `visus-desktop` and the import root is the PEP 420 namespace `visus.desktop`.

---

## Features

- **OCR text search and click** — find on-screen text with Tesseract and click it, with character filtering and occurrence selection.
- **Image detection and click** — locate UI elements by template image, with adjustable confidence and optional scale variations.
- **Relative-image detection** — find a target image *near* a unique anchor image (useful when many identical buttons exist on screen).
- **Coordinate clicks and typing** — click at exact coordinates and type text (with special key sequences like `{ctrl}a`, `{del}`, `{tab}`, `{enter}`).
- **Keyboard commands** — send named shortcuts such as `Ctrl+S`, `F7`, `Alt+Tab`, and many more.
- **Task-list automation** — describe a whole workflow as a list of dictionaries and run it with `execute_tasks`.
- **Smart backtracking** — when a step fails, re-run the previous step and retry, both inside task lists and between individual method calls.
- **Wait parameters** — wait for an element to appear or disappear (`wait_until_found`, `wait_until_disappears`, `wait_timeout`).
- **Visual overlay** — draw a colored rectangle over the target before clicking, helpful for debugging.
- **Virtual mouse** — perform clicks without moving the physical cursor (`use_virtual_mouse`).
- **Backward compatible** — drop-in aliases for code written against `bot-vision-suite`.

---

## Requirements

- **Python 3.8+**
- **Tesseract OCR installed on the system** (this is a hard requirement — Visus Desktop shells out to the Tesseract binary).
- Core Python dependencies are installed automatically: `PyAutoGUI`, `pytesseract`, `opencv-python`, `Pillow`, `numpy`, `pyperclip` (and `pywin32` on Windows).

### Installing Tesseract OCR

| OS | Command / link |
|----|----------------|
| Windows | Download and install from <https://github.com/UB-Mannheim/tesseract/wiki> |
| Linux (Debian/Ubuntu) | `sudo apt-get install tesseract-ocr` |
| macOS | `brew install tesseract` |

After installing on Windows, the default location `C:\Program Files\Tesseract-OCR\tesseract.exe` is detected automatically. You can also add Tesseract to your `PATH`, or set `tesseract_path` in the configuration (see [Configuration](#configuration)).

Verify the install:

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

See [docs/installation.md](docs/installation.md) for detailed, per-OS instructions.

---

## Quickstart

```python
from visus.desktop import VisusBot

bot = VisusBot()

# Click on-screen text found by OCR
bot.click_text("Login")

# Click a UI element located by template image
bot.click_image("save_button.png")

# Type into the focused field
bot.type_text("hello world")
```

Restricting the search to a screen region (faster and more reliable):

```python
from visus.desktop import VisusBot

bot = VisusBot()

# region is (x, y, width, height)
location = bot.find_text("Username", region=(100, 100, 500, 300), filter_type="letters")
if location:
    bot.click_text("Username", region=(100, 100, 500, 300), sendtext="admin")
```

---

## API overview

The library can be used through the `VisusBot` class (recommended) or through standalone convenience functions that create a temporary bot instance.

### Find and click text (OCR)

```python
bot = VisusBot()

# find_text returns (x, y, width, height) or None
location = bot.find_text("Confirm", region=(0, 0, 800, 600), filter_type="both")

# click_text returns True/False
bot.click_text(
    "Confirm",
    region=(0, 0, 800, 600),
    filter_type="letters",   # "letters" | "numbers" | "both"
    occurrence=1,            # which match to click (1 = first)
    mouse_button="left",     # "left" | "right" | "double" | "move_to"
    delay=1,                 # pause (seconds) after the click
    sendtext="my text",      # optional: type after clicking
)
```

### Find and click images

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

### Relative image (target near an anchor)

```python
bot = VisusBot()

# Click the "OK" that is closest to the warning icon
bot.click_relative_image(
    anchor_image="warning_icon.png",
    target_image="ok_button.png",
    max_distance=200,          # max pixels between anchor and target
    confidence=0.9,
    target_region=(0, 0, 800, 600),   # optional region to search the target
)
```

### Coordinates, typing, and keyboard commands

```python
bot = VisusBot()

bot.click_coordinates(500, 300, mouse_button="right", delay=0.5)
bot.type_text("{ctrl}a{del}New value{enter}")   # special key sequences supported
bot.keyboard_command("Ctrl+S")

# Inspect supported keyboard command names
print(bot.get_available_keyboard_commands())
```

### Task-list automation (`execute_tasks`)

Describe a workflow as a list of dictionaries. Each task is one of several types:

```python
from visus.desktop import VisusBot

bot = VisusBot()

tasks = [
    # OCR text search + click, then type into the field
    {
        "text": "Username",
        "region": (100, 100, 500, 300),
        "char_type": "letters",
        "occurrence": 1,
        "backtrack": True,
        "delay": 0.5,
        "sendtext": "admin{tab}secret{enter}",
    },
    # Image search + click
    {
        "image": "login_button.png",
        "confidence": 0.9,
        "specific": False,
        "mouse_button": "left",
        "delay": 1,
    },
    # Relative image
    {
        "type": "relative_image",
        "anchor_image": "warning_icon.png",
        "target_image": "ok_button.png",
        "max_distance": 200,
        "confidence": 0.9,
    },
    # Click at coordinates
    {"type": "click", "x": 500, "y": 300, "mouse_button": "left", "delay": 0.5},
    # Type text
    {"type": "type_text", "text": "Hello World!", "interval": 0.05, "delay": 1},
    # Keyboard command
    {"type": "keyboard_command", "command": "Ctrl+S", "delay": 1},
]

results = bot.execute_tasks(tasks)
```

You can also call the module-level `execute_tasks(tasks, config=None)` without instantiating the class. It accepts a single list of tasks, or a list of task lists that run sequentially.

### Wait parameters

Most find/click methods accept wait parameters so you can synchronize with a loading UI:

```python
bot = VisusBot()

# Block until the text appears (up to wait_timeout seconds), then click
bot.click_text("Dashboard", wait_until_found=True, wait_timeout=60)

# Wait for a spinner image to disappear
bot.find_image("loading_spinner.png", wait_until_disappears=True, wait_timeout=120)
```

`wait_timeout` overrides the global `wait_timeout` config value (default 30 seconds) for that call.

### Virtual mouse

Enable the virtual mouse so clicks are dispatched without moving the physical cursor — useful when you want to keep working while automation runs:

```python
bot = VisusBot(config={"use_virtual_mouse": True})
bot.click_text("Submit")   # the on-screen cursor does not move
```

### Backtracking between individual methods

When `backtrack=True`, a failed step re-runs the previous step and retries. You can let it auto-manage a session, or control it explicitly:

```python
from visus.desktop import VisusBot, start_individual_session

# Auto session: backtrack=True starts a session on first use
bot = VisusBot()
bot.click_image("step1.png", backtrack=True)
bot.click_text("Next", backtrack=True)        # if it fails, step1 is re-run, then retried

# Manual session control
bot = start_individual_session()               # or bot.start_task_session()
bot.click_image("step1.png", backtrack=True)
bot.click_text("Next", backtrack=True)
successful, total = bot.end_task_session()
```

---

## Configuration

Pass configuration either as a `BotVisionConfig` instance or as a plain dict to `VisusBot(config=...)`. `BotVisionConfig` takes a **dictionary** (not keyword arguments).

```python
from visus.desktop import VisusBot, BotVisionConfig

config = BotVisionConfig({
    "confidence_threshold": 80.0,          # default OCR threshold, 0–100 (default 75.0)
    "retry_attempts": 5,                   # default retry attempts
    "default_delay": 1.0,                  # default pause between actions (seconds)
    "show_overlay": True,                  # draw the visual overlay before clicking
    "overlay_color": "blue",               # red/blue/green/yellow/purple/orange/cyan/magenta/white/black
    "default_mouse_button": "left",        # left/right/double/move_to
    "use_virtual_mouse": False,            # click without moving the physical cursor
    "wait_timeout": 30,                    # default timeout (seconds) for wait_* parameters
    "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # optional override
})

bot = VisusBot(config=config)

# Equivalent: pass the dict directly
bot = VisusBot(config={"confidence_threshold": 80.0, "overlay_color": "green"})
```

See [docs/api_reference.md](docs/api_reference.md#botvisionconfig) for the full list of configuration keys.

---

## Migrating from `bot-vision-suite`

Visus Desktop is the successor to `bot-vision-suite`. Migration is minimal because the public API is preserved and the old names remain available as aliases.

| | Old (`bot-vision-suite`) | New (`visus-desktop`) |
|---|---|---|
| Install | `pip install bot-vision-suite` | `pip install visus-desktop` |
| Import | `from bot_vision import BotVision` | `from visus.desktop import VisusBot` |

```python
# Old code
from bot_vision import BotVision
bot = BotVision()

# New code
from visus.desktop import VisusBot
bot = VisusBot()
```

The `BotVision` class name and the `limpar_texto` text-helper alias still work:

```python
from visus.desktop import BotVision, limpar_texto   # both still supported
bot = BotVision()                                    # alias for VisusBot
limpar_texto("  abc123!  ", "numbers")               # alias for clean_text -> "123"
```

---

## Documentation and examples

- [docs/](docs/) — full documentation index
  - [docs/installation.md](docs/installation.md) — installation and Tesseract setup
  - [docs/api_reference.md](docs/api_reference.md) — public API reference
- [examples/](examples/) — runnable example scripts

---

## License

Released under the MIT License.

# API Reference

Reference for the public API of `visus.desktop`. All examples assume:

```python
from visus.desktop import VisusBot
```

Conventions used throughout:

- **`region`** is a tuple `(x, y, width, height)` describing a rectangular screen area. `x, y` is the top-left corner.
- **`location`** values returned by `find_*` methods are tuples `(x, y, width, height)`, or `None` if nothing was found.
- **`mouse_button`** accepts `"left"`, `"right"`, `"double"` (double left-click), or `"move_to"` (move the cursor without clicking).
- **`filter_type` / `char_type`** accepts `"letters"`, `"numbers"`, or `"both"`.
- **`confidence`** for image matching is a float `0.0–1.0`; **`confidence_threshold`** for OCR is a float `0–100`.

---

## Table of contents

- [`VisusBot`](#visusbot)
  - [Text (OCR)](#text-ocr)
  - [Images](#images)
  - [Relative images](#relative-images)
  - [Coordinates, typing, keyboard](#coordinates-typing-keyboard)
  - [Text extraction](#text-extraction)
  - [Task lists](#task-lists)
  - [Backtracking sessions](#backtracking-sessions)
  - [Overlay control](#overlay-control)
- [Standalone convenience functions](#standalone-convenience-functions)
- [`BotVisionConfig`](#botvisionconfig)
- [Text helpers](#text-helpers)
- [Exceptions](#exceptions)
- [Backward-compatibility aliases](#backward-compatibility-aliases)

---

## `VisusBot`

```python
VisusBot(config=None)
```

The main entry point. `config` may be a `dict`, a `BotVisionConfig` instance, or `None` (use defaults). Passing a `dict` constructs a `BotVisionConfig` internally.

`BotVision` is a backward-compatibility alias for `VisusBot`.

### Text (OCR)

#### `find_text`

```python
find_text(text, region=None, filter_type="both", confidence_threshold=75.0,
          occurrence=1, max_attempts=3, backtrack=False, wait_until_found=False,
          wait_until_disappears=False, wait_timeout=None)
```

Locate `text` on screen using OCR. Returns the location tuple of the requested `occurrence`, or `None`.

- `occurrence` — which match to return (1 = first).
- `backtrack` — when `True`, retries up to `max_attempts` times, gradually lowering the confidence threshold.
- `wait_until_found` / `wait_until_disappears` / `wait_timeout` — see [wait parameters](#wait-parameters).

#### `click_text`

```python
click_text(text, region=None, filter_type="both", delay=0, mouse_button="left",
           occurrence=1, backtrack=False, max_attempts=3, sendtext=None,
           confidence_threshold=None, show_overlay=None, wait_until_found=False,
           wait_until_disappears=False, wait_timeout=None)
```

Find `text` and click it. Returns `True` on success, `False` otherwise.

- `delay` — seconds to pause after the click.
- `sendtext` — optional text to type after clicking (supports special key sequences, see [`type_text`](#type_text)).
- `confidence_threshold` — overrides the configured OCR threshold for this call; `None` uses the config value.
- `show_overlay` — `True`/`False` to force the visual overlay on/off; `None` uses the global config value.
- `backtrack` — when `True`, integrates with the individual-method [backtracking session](#backtracking-sessions).

### Images

#### `find_image`

```python
find_image(image_path, region=None, confidence=0.9, max_attempts=3,
           backtrack=False, specific=True, wait_until_found=False,
           wait_until_disappears=False, wait_timeout=None, scales=None)
```

Locate the template image `image_path` on screen. Returns the location tuple or `None`.

- `specific` — `True` searches within `region`; `False` searches the full screen and also tries scale variations.
- `scales` — optional list of scale factors to try (e.g. `[1.0, 0.95, 1.05]`). Defaults are chosen automatically based on `specific`.
- `backtrack` — when `True`, retries up to `max_attempts`, gradually lowering `confidence`.

#### `click_image`

```python
click_image(image_path, region=None, confidence=0.9, delay=0, mouse_button="left",
            max_attempts=3, backtrack=False, specific=True, sendtext=None,
            show_overlay=None, wait_until_found=False, wait_until_disappears=False,
            wait_timeout=None)
```

Find an image and click it. Returns `True`/`False`.

### Relative images

Locate a target image positioned near a unique anchor image. Useful when several identical targets exist on screen and you want the one closest to a distinctive reference point.

#### `find_relative_image`

```python
find_relative_image(anchor_image, target_image, max_distance=200,
                    confidence=0.9, target_region=None, wait_until_found=False,
                    wait_until_disappears=False, wait_timeout=None)
```

Returns the location of the target image nearest the anchor (within `max_distance` pixels), or `None`.

#### `click_relative_image`

```python
click_relative_image(anchor_image, target_image, max_distance=200, confidence=0.9,
                     target_region=None, delay=0, mouse_button="left", backtrack=False,
                     max_attempts=3, sendtext=None, wait_until_found=False,
                     wait_until_disappears=False, wait_timeout=None)
```

Find the relative target and click it. Returns `True`/`False`.

### Coordinates, typing, keyboard

#### `click_at`

```python
click_at(location, mouse_button="left", delay=0, show_overlay=None)
```

Click at a `location` tuple `(x, y, width, height)`. Returns `True`/`False`.

#### `click_coordinates`

```python
click_coordinates(x, y, delay=0, mouse_button="left", backtrack=False)
```

Click directly at pixel coordinates `(x, y)`. Returns `True`/`False`.

#### `type_text`

```python
type_text(text, interval=0.05, delay=0, backtrack=False)
```

Type `text` at the current cursor position. Returns `True`/`False`.

- `interval` — seconds between characters.
- Special key sequences are recognized when present in `text`: `{ctrl}a` (select all), `{del}`, `{tab}`, `{enter}`. Plain text is sent via the clipboard for reliability.

#### `keyboard_command`

```python
keyboard_command(command, delay=0, backtrack=False)
```

Execute a named keyboard command (e.g. `"Ctrl+S"`, `"F7"`, `"Alt+Tab"`). Returns `True`/`False`.

#### `get_available_keyboard_commands`

```python
get_available_keyboard_commands()
```

Return the list of supported keyboard command names.

### Text extraction

#### `extract_text_from_region`

```python
extract_text_from_region(region=None, filter_type="both", confidence_threshold=50.0,
                         return_full_data=False, max_attempts=3, backtrack=False)
```

Extract all OCR text from `region` (or the whole screen if `region=None`).

- With `return_full_data=False` (default): returns a `list[str]`.
- With `return_full_data=True`: returns a `list[dict]`, each with keys `text`, `confidence`, `box` (relative to the region) and `absolute_box` (absolute screen coordinates).

#### `get_last_extracted_text`

```python
get_last_extracted_text()
```

Return the result of the most recent `extract_text` task run via [`execute_tasks`](#task-lists), or `None`.

### Task lists

#### `execute_tasks`

```python
execute_tasks(tasks)
```

Run a list of task dictionaries sequentially. Returns a list of `TaskResult` objects.

Each task dictionary is dispatched by its keys. Supported task shapes:

| Task | Identifying keys | Common fields |
|------|------------------|---------------|
| Text (OCR) click | `text` | `region`, `char_type`, `occurrence`, `confidence`/`confidence_threshold`, `backtrack`, `delay`, `sendtext` |
| Image click | `image` | `region`, `confidence`, `specific`, `mouse_button`, `backtrack`, `delay` |
| Relative image | `type: "relative_image"` | `anchor_image`, `target_image`, `max_distance`, `confidence`, `target_region`, `specific`, `backtrack`, `delay`, `mouse_button` |
| Coordinate click | `type: "click"` | `x`, `y`, `mouse_button`, `delay`, `backtrack` |
| Type text | `type: "type_text"` | `text`, `interval`, `delay` |
| Keyboard command | `type: "keyboard_command"` | `command`, `delay` |
| Extract text | `type: "extract_text"` | `region`, `filter_type`, `confidence_threshold`, `return_full_data`, `backtrack`, `delay` |

```python
bot = VisusBot()
results = bot.execute_tasks([
    {"text": "Login", "region": (100, 100, 500, 300), "char_type": "letters"},
    {"image": "submit.png", "confidence": 0.9, "delay": 1},
    {"type": "keyboard_command", "command": "Ctrl+S"},
])
```

### Backtracking sessions

When a step fails, backtracking re-runs the previous step and retries the failed step.

#### `start_task_session` / `end_task_session`

```python
start_task_session()
end_task_session()   # returns (successful_count, total_count)
```

Begin and end a session in which individual methods called with `backtrack=True` cooperate. If `backtrack=True` is used without an active session, a session is started automatically.

```python
bot = VisusBot()
bot.start_task_session()
bot.click_image("step1.png", backtrack=True)
bot.click_text("Next", backtrack=True)        # if it fails, step1 is re-run then retried
successful, total = bot.end_task_session()
```

### Overlay control

The visual overlay draws a colored rectangle over the target before a click.

#### `configure_overlay`

```python
configure_overlay(enabled=None, color=None, duration=None, width=None)
```

Convenience setter. `color` must be one of: `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `cyan`, `magenta`, `white`, `black`. `duration` is in milliseconds; `width` is the line width. Invalid values raise `ValueError`.

#### `get_overlay_config`

```python
get_overlay_config()   # -> dict with enabled, show_overlay, color, duration, width
```

#### `get_available_overlay_colors` (static)

```python
VisusBot.get_available_overlay_colors()   # -> list of color names
```

#### Properties

- `overlay_enabled` (bool) — whether the overlay system is active.
- `show_overlay` (bool) — whether the overlay is shown before clicks.

### Wait parameters

The find/click methods accept these to synchronize with a changing UI:

- `wait_until_found` (bool) — block until the element appears.
- `wait_until_disappears` (bool) — block until the element disappears.
- `wait_timeout` (int, optional) — timeout in seconds for this call; overrides the global `wait_timeout` config (default 30).

---

## Standalone convenience functions

These module-level functions create a temporary `VisusBot` internally, so you can use the library without managing an instance. Import them from `visus.desktop`.

```python
find_text(text, region=None, filter_type="both", confidence_threshold=75.0,
          occurrence=1, max_attempts=3, config=None, wait_until_found=False,
          wait_until_disappears=False, wait_timeout=None)

click_text(text, region=None, filter_type="both", delay=0, mouse_button="left",
           occurrence=1, max_attempts=3, sendtext=None, confidence_threshold=None,
           show_overlay=True, config=None, wait_until_found=False,
           wait_until_disappears=False, wait_timeout=None)

find_image(image_path, region=None, confidence=0.9, max_attempts=3, specific=True,
           scales=None, config=None, wait_until_found=False,
           wait_until_disappears=False, wait_timeout=None)

click_image(image_path, region=None, confidence=0.9, delay=0, mouse_button="left",
            max_attempts=3, specific=True, sendtext=None, show_overlay=True,
            config=None, wait_until_found=False, wait_until_disappears=False,
            wait_timeout=None)

click_at(location, mouse_button="left", delay=0, show_overlay=True, config=None)

type_text(text, config=None)

find_relative_image(anchor_image, target_image, max_distance=200, confidence=0.9,
                    target_region=None, wait_until_found=False,
                    wait_until_disappears=False, wait_timeout=None)

click_relative_image(anchor_image, target_image, max_distance=200, confidence=0.9,
                     target_region=None, delay=0, mouse_button="left", backtrack=False,
                     wait_until_found=False, wait_until_disappears=False, wait_timeout=None)

click_coordinates(x, y, delay=0, mouse_button="left", backtrack=False)

type_text_standalone(text, interval=0.05, delay=0, backtrack=False)

keyboard_command_standalone(command, delay=0, backtrack=False)

get_available_keyboard_commands()

extract_text_from_region_standalone(region=None, filter_type="both",
                                    confidence_threshold=50.0, return_full_data=False,
                                    max_attempts=3, backtrack=False, config=None)

execute_tasks(tasks, config=None)
```

`execute_tasks` accepts either a single list of task dictionaries or a list of task lists (each list runs sequentially with its own bot).

### Session helpers

```python
start_individual_session(config=None)   # -> VisusBot with a backtracking session started
run_individual_tasks_with_backtrack(task_functions, config=None)
    # task_functions: list of (callable, args, kwargs); callable receives the bot as first arg
    # returns (successful_count, total_count, bot_instance)
```

> **Note:** `type_text` (the standalone function) takes only `(text, config=None)`. For the `interval` / `delay` / `backtrack` parameters, use the `VisusBot.type_text` method or the `type_text_standalone` function.

---

## `BotVisionConfig`

```python
BotVisionConfig(config_dict=None)
```

Configuration container. It takes a **dictionary** (not keyword arguments). On construction it auto-detects Tesseract, validates dependencies, and validates the overlay/mouse settings. Unknown Tesseract installations raise `TesseractNotFoundError`; missing Python dependencies raise `ConfigurationError`.

Recognized keys and their defaults:

| Key | Default | Description |
|-----|---------|-------------|
| `tesseract_path` | `None` (auto-detected) | Path to the Tesseract executable. |
| `tesseract_data_path` | `None` (auto-detected) | Path to the `tessdata` directory. |
| `confidence_threshold` | `75.0` | Default OCR confidence threshold (0–100). |
| `retry_attempts` | `3` | Default number of retry attempts. |
| `default_delay` | `1.0` | Default pause (seconds) between actions. |
| `overlay_duration` | `1000` | Overlay display time in milliseconds. |
| `overlay_color` | `"red"` | Overlay color (see [colors](#overlay-control)). |
| `overlay_width` | `4` | Overlay line width. |
| `show_overlay` | `True` | Show the visual overlay before clicks. |
| `overlay_enabled` | `True` | Whether the overlay system is active. |
| `default_mouse_button` | `"left"` | `left` / `right` / `double` / `move_to`. |
| `log_level` | `"INFO"` | Logging level. |
| `ocr_languages` | `["eng"]` | Tesseract language(s). |
| `image_processing_methods` | `"all"` | OCR preprocessing methods to apply. |
| `click_duration` | `0.1` | Click duration (seconds). |
| `movement_duration` | `0.1` | Mouse movement duration (seconds). |
| `use_virtual_mouse` | `False` | Click without moving the physical cursor. |
| `wait_timeout` | `30` | Global timeout (seconds) for wait parameters. |
| `screenshot_delay` | `0.1` | Delay before screen capture (seconds). |

Methods: `get(key, default=None)`, `set(key, value)`, `update(config_dict)`, `to_dict()`, `setup_tesseract()`, `setup_logging()`. Configuration values are also accessible as attributes (e.g. `config.confidence_threshold`).

Related helpers:

```python
get_default_config()                      # -> shared default BotVisionConfig (singleton)
create_config_from_file(config_path)      # load config from a .json / .yaml / .yml file
```

```python
from visus.desktop import BotVisionConfig, VisusBot

config = BotVisionConfig({
    "confidence_threshold": 80.0,
    "overlay_color": "blue",
    "use_virtual_mouse": True,
})
bot = VisusBot(config=config)
```

---

## Text helpers

#### `clean_text`

```python
clean_text(text, filter_type="both")
```

Filter characters of `text` by type. It does **not** normalize whitespace.

- `"numbers"` — keep only digits.
- `"letters"` — keep only letters (including accented).
- `"both"` — keep letters and digits.
- any other value — strip only leading/trailing special characters.

```python
from visus.desktop import clean_text

clean_text("  123abc!  ", "numbers")   # "123"
clean_text("  123abc!  ", "letters")   # "abc"
clean_text("  123abc!  ", "both")      # "123abc"
```

`limpar_texto` is a backward-compatibility alias for `clean_text`.

#### `matches_filter`

```python
matches_filter(word, filter_type)
```

Return `True` if `word` matches the given filter type. For `"numbers"`, the word must be a single integer in the range 1–31.

---

## Exceptions

All exceptions live in `visus.desktop.exceptions` and are re-exported from `visus.desktop`.

| Exception | Raised when |
|-----------|-------------|
| `BotVisionError` | Base class for all Visus Desktop errors. |
| `TesseractNotFoundError` | Tesseract OCR is not found on the system. |
| `ImageNotFoundError` | An image is not found on screen. |
| `TextNotFoundError` | Text is not found in the specified region. |
| `InvalidRegionError` | An invalid region was specified. |
| `TaskExecutionError` | An error occurred while executing a task. |
| `ConfigurationError` | A configuration error occurred (e.g. missing dependency). |
| `OCRProcessingError` | An error occurred during OCR processing. |
| `ImageProcessingError` | An error occurred during image processing. |

```python
from visus.desktop import VisusBot
from visus.desktop.exceptions import TesseractNotFoundError

try:
    bot = VisusBot()
except TesseractNotFoundError:
    print("Please install Tesseract OCR.")
```

---

## Backward-compatibility aliases

| Alias | Canonical name |
|-------|----------------|
| `BotVision` | `VisusBot` |
| `limpar_texto` | `clean_text` |

These are kept for code migrating from `bot-vision-suite`. See the README's *Migrating from `bot-vision-suite`* section.

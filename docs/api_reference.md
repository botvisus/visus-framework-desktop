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

- [Platform support](#platform-support)
- [`VisusBot`](#visusbot)
  - [Text (OCR)](#text-ocr)
  - [Images](#images)
  - [Find all / find multiple](#find-all--find-multiple)
  - [Image map](#image-map)
  - [Relative images](#relative-images)
  - [Coordinates, typing, keyboard](#coordinates-typing-keyboard)
  - [Named keyboard shortcuts](#named-keyboard-shortcuts)
  - [Mouse extras](#mouse-extras)
  - [Coordinate helpers](#coordinate-helpers)
  - [Text extraction](#text-extraction)
  - [Task lists](#task-lists)
  - [Backtracking sessions](#backtracking-sessions)
  - [Overlay control](#overlay-control)
  - [Native (accessibility) automation](#native-accessibility-automation)
  - [Process management](#process-management)
  - [Window management](#window-management)
  - [Screen capture](#screen-capture)
  - [Clipboard](#clipboard)
  - [Files](#files)
  - [Web](#web)
- [Module-level capability functions](#module-level-capability-functions)
- [Standalone convenience functions](#standalone-convenience-functions)
- [`BotVisionConfig`](#botvisionconfig)
- [Text helpers](#text-helpers)
- [Exceptions](#exceptions)
- [Backward-compatibility aliases](#backward-compatibility-aliases)

---

## Platform support

The library targets **Windows** and **Linux**. Most of the API is cross‑platform; two areas are
Windows‑only for now and raise `NotSupportedOnThisOS` elsewhere:

- **Native (accessibility) automation** — `connect_to_app`, `find_app_window`, `find_app_element`
  (pywinauto). A Linux backend via AT‑SPI is planned.
- **Window management** — `focus_window`, `maximize_window`, `minimize_window`, `close_window`
  (pywin32). A Linux backend via xdotool/wmctrl is planned.

The non‑intrusive **virtual mouse** (`use_virtual_mouse`) performs clicks without moving the cursor on
Windows and automatically falls back to a physical click on other platforms.

On Linux, install the system tools the cross‑platform features rely on:

```bash
sudo apt-get install tesseract-ocr scrot xclip python3-tk
```

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

For both `find_image` and `click_image`, `image_path` may be a **registered label** (see
[Image map](#image-map)) or a direct file path.

### Find all / find multiple

#### `find_all`

```python
find_all(image, region=None, confidence=0.9, grayscale=False)
```

Return **every** on‑screen match of a template `image` (a registered label or a path). Returns a
`list[tuple]` of `(left, top, width, height)` boxes — an empty list if nothing matched. `confidence`
requires OpenCV; if OpenCV is unavailable the search is retried without it. `grayscale=True` performs a
faster grayscale match.

#### `find_multiple`

```python
find_multiple(images, region=None, confidence=0.9, grayscale=False)
```

Locate the first match of **several** templates at once. `images` is either a list of labels/paths
(keyed by the path in the result) or a dict `{key: label_or_path}` (keyed by your keys). Returns a
`dict` mapping each key to its first match box, or `None` for images that were not found.

```python
bot.find_all("checkbox.png", region=(0, 0, 1920, 1080))
bot.find_multiple({"ok": "ok.png", "cancel": "cancel.png"})
```

### Image map

A per‑bot registry mapping friendly labels to image file paths. Once registered, a label can be used
anywhere an image path is accepted (`find_image`, `click_image`, `find_all`, `find_multiple`).

```python
register_image(label, path)        # register one label -> path (validates the path exists)
register_images(mapping)           # register a {label: path} dict at once
get_image(label)                   # -> the path registered for label (KeyError if unknown)
```

Registration raises `FileNotFoundError` if a path does not exist and `ValueError` if a label is empty.
The registry is also exposed as the `bot.image_map` property (an `ImageMap` instance).

```python
bot = VisusBot()
bot.register_image("save", "assets/save.png")
bot.register_images({"login": "assets/login.png", "logout": "assets/logout.png"})
bot.click_image("save")            # label resolved to its path
```

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

#### `click_relative`

```python
click_relative(image, x_offset=0, y_offset=0, region=None, confidence=0.9,
               mouse_button="left", delay=0, centered=False)
```

Find a single `image` (registered label or path) and click at a fixed coordinate offset from it:
the image's top-left `+ (x_offset, y_offset)`, or its center `+` the offset when `centered=True`.
This is the "image + coordinate" relative click (as opposed to `click_relative_image`, which is
anchor-image → target-image). Returns `True` if found and clicked, `False` otherwise.

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

### Named keyboard shortcuts

`VisusBot` also exposes named, self‑documenting keyboard methods. Each is **sugar** that delegates to
`keyboard_command("<Command>")` (the command map is the single source of truth), so `bot.control_c()`
is equivalent to `bot.keyboard_command("Ctrl+C")`. All take no arguments and return whatever
`keyboard_command` returns.

| Group | Methods |
|-------|---------|
| Navigation / editing | `enter`, `tab`, `shift_tab`, `esc`, `space`, `backspace`, `delete`, `key_up`, `key_down`, `key_left`, `key_right`, `page_up`, `page_down`, `home`, `end` |
| Function keys | `key_f1` … `key_f12` |
| Shortcuts | `control_c`, `control_v`, `control_x`, `control_a`, `control_s`, `control_z`, `control_y`, `control_f`, `control_p`, `alt_tab`, `alt_f4` |

Low‑level **primitives** call `pyautogui` directly (they are *not* in the command map):

```python
type_key(key)        # press a single key by its pyautogui name (e.g. "a", "f5")
key_combo(*keys)     # press an arbitrary combination, e.g. key_combo("ctrl", "alt", "del")
hold_shift()         # press and hold Shift (release later)
release_shift()      # release Shift held with hold_shift()
hold_ctrl()          # press and hold Ctrl
release_ctrl()       # release Ctrl held with hold_ctrl()
```

### Mouse extras

Thin wrappers over `pyautogui`.

```python
scroll(amount, x=None, y=None)
    # scroll the wheel `amount` clicks (positive = up, negative = down);
    # optionally move to (x, y) first.

drag(start_x, start_y, end_x, end_y, duration=0.5, button="left")
    # move to the start point, then drag to the end point while holding `button`.

triple_click(x=None, y=None, interval=0.05)
    # triple-click at (x, y), or at the current cursor position when omitted.

move_random(x, y, max_offset=3, duration=0.2)
    # move to (x, y) with a small random jitter, then settle exactly on the target.
```

### Coordinate helpers

Static helpers that convert a `(x, y, width, height)` location into a point.

```python
VisusBot.get_element_coords(location)            # -> (x, y) top-left corner
VisusBot.get_element_coords_centered(location)   # -> (x, y) center of the box
```

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

### Native (accessibility) automation

> **Windows‑only.** Backed by [pywinauto](https://pywinauto.readthedocs.io) (install the `[native]`
> extra). On other platforms these raise `NotSupportedOnThisOS`. `Backend` and `NativeError` are
> importable from `visus.desktop`.

Selectors (`**selectors`) are forwarded directly to pywinauto — for example `title`, `title_re`,
`auto_id`, `control_type`, `class_name`, `process`, `handle`, `path`.

#### `connect_to_app`

```python
connect_to_app(backend=Backend.UIA, timeout=60.0, poll_interval=0.5, **selectors)
```

Connect to an already‑running application, retrying every `poll_interval` seconds until it appears or
`timeout` elapses. `backend` is a `Backend` member or its string value: `Backend.UIA` (`"uia"`, for
modern WPF/WinForms/Qt/UWP apps) or `Backend.WIN32` (`"win32"`, for classic Win32 controls). The
connected application is stored on `bot.app` and returned. Raises `NativeError` if it cannot connect
within `timeout`.

#### `find_app_window`

```python
find_app_window(timeout=10.0, **selectors)
```

Return a top‑level window of the connected application (or `None` if none appears within `timeout`).
Requires a prior `connect_to_app`, otherwise raises `NativeError`.

#### `find_app_element`

```python
find_app_element(from_parent_window=None, timeout=10.0, **selectors)
```

Return a control of the connected application (or `None`). When `from_parent_window` is provided, the
lookup drills into that window's descendants (`child_window`); when omitted, it behaves like
`find_app_window`. Requires a prior `connect_to_app`.

```python
from visus.desktop import VisusBot, Backend

bot = VisusBot()
bot.connect_to_app(backend=Backend.UIA, title_re=".*Notepad")
window = bot.find_app_window(title_re=".*Notepad")
edit = bot.find_app_element(from_parent_window=window, control_type="Edit")
edit.set_edit_text("Hello")
```

### Process management

Cross‑platform helpers powered by `psutil`.

```python
launch(path)
    # open an application or file via the OS default handler (os.startfile on
    # Windows; subprocess.Popen elsewhere).

find_process(name=None, pid=None)
    # -> the first running psutil.Process whose name contains `name`
    #    (case-insensitive) or whose pid == `pid`, else None.

is_process_running(name)
    # -> True if a process whose name contains `name` is running.

kill_process(target)
    # terminate a process by psutil.Process, pid (int), or name substring (str);
    # tries terminate() then kill(). -> True if a match was found and stopped.
```

### Window management

> **Windows‑only.** Backed by pywin32; matching is by a case‑insensitive substring of the window
> title. On other platforms these raise `NotSupportedOnThisOS`.

```python
focus_window(title_substring)      # bring the first matching window to the foreground
maximize_window(title_substring)
minimize_window(title_substring)
close_window(title_substring)      # posts WM_CLOSE
```

Each returns `True` if a matching window was found (and the action issued), `False` otherwise.

### Screen capture

Capture prefers `mss` (fast, multi‑monitor) and falls back to `pyautogui` on any failure.

```python
take_screenshot(region=None)
    # -> a PIL.Image of the full primary screen, or of `region` = (x, y, width, height).

save_screenshot(path, region=None)
    # capture and save to `path`; returns `path`.

get_display_size()
    # -> the primary display size as (width, height) in pixels.
```

### Clipboard

Thin wrappers over `pyperclip`.

```python
copy(text)            # place `text` on the system clipboard
paste()               # -> current clipboard text
get_clipboard()       # -> current clipboard text (alias of paste())
```

### Files

Helpers for synchronizing with files produced externally (e.g. downloads).

```python
wait_for_file(path, timeout=10.0, poll_interval=0.5)
    # -> True once `path` exists and is readable; False on timeout.

wait_for_file_stable(path, timeout=30.0, stable_for=1.0, poll_interval=0.5)
    # -> True once `path` exists and its size has not changed for `stable_for`
    #    seconds (download finished); False on timeout.
```

### Web

```python
browse(url)           # open `url` in the system default web browser
```

---

## Module-level capability functions

The capability helpers above are also re‑exported as module‑level functions, so they can be used
without a `VisusBot` instance. Import them from `visus.desktop`.

```python
# Image location
find_all(image_path, region=None, confidence=0.9, grayscale=False)
find_multiple(images, region=None, confidence=0.9, grayscale=False)

# Screen
capture_screen(region=None)                 # module-level name for VisusBot.take_screenshot
save_screenshot(path, region=None)
get_display_size()

# Clipboard
copy_to_clipboard(text)                     # module-level alias of VisusBot.copy
paste()
get_clipboard()

# Process
launch(path)
find_process(name=None, pid=None)
is_process_running(name)
kill_process(target)

# Window (Windows-only; raise NotSupportedOnThisOS elsewhere)
focus_window(title_substring)
maximize_window(title_substring)
minimize_window(title_substring)
close_window(title_substring)

# Mouse extras
scroll(amount, x=None, y=None)
drag(start_x, start_y, end_x, end_y, duration=0.5, button="left")
triple_click(x=None, y=None, interval=0.05)
move_random(x, y, max_offset=3, duration=0.2)

# Files
wait_for_file(path, timeout=10.0, poll_interval=0.5)
wait_for_file_stable(path, timeout=30.0, stable_for=1.0, poll_interval=0.5)
```

The `ImageMap` class, plus `Backend` and `NativeError`, are also importable from `visus.desktop`.

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
| `NotSupportedOnThisOS` | A feature (native automation, window management) is not available on the current OS. |

`NativeError` is raised by the native‑automation helpers (`connect_to_app`, `find_app_*`) when a
connection or element lookup fails. It is importable from `visus.desktop` (and from
`visus.desktop.core.native`) but does **not** subclass `BotVisionError`.

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

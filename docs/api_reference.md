# Python API reference

Everything is importable from the top-level package:

```python
from visus.desktop import VisusBot, BotVisionConfig, ensure_window
```

The recommended entry point is **`VisusBot`** (stateful, reuses one OCR engine).
Standalone functions create a temporary bot internally — handy for one-shots.
Every method/function has a complete docstring (params, defaults, return shape)
— this page is the map; hover or `help()` for the fine print.

Conventions: `region = (x, y, width, height)`; find tools return `(x, y, width,
height)` or `None`; `mouse_button` ∈ `left|right|double|move_to`; `filter_type /
char_type` ∈ `letters|numbers|both`; image `confidence` is `0.0–1.0`, OCR
`confidence_threshold` is `0–100`.

## `VisusBot` — find / click

| Method | Returns | Notes |
|---|---|---|
| `find_text(text, region=None, filter_type="both", confidence_threshold=75.0, occurrence=1, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None)` | box or `None` | First match (or Nth via `occurrence`). |
| `find_all_text(text, region=None, filter_type="both", confidence_threshold=None)` | `[(x,y,w,h,confidence), …]` | **Every** match, reading order. |
| `show_text_occurrences(text, region=None, filter_type="both", confidence_threshold=None, color="red", duration_ms=3000, width=3)` | same list | Also draws a numbered click-through overlay. |
| `click_text(text, region=None, filter_type="both", delay=0, mouse_button="left", occurrence=1, backtrack=False, max_attempts=3, sendtext=None, confidence_threshold=None, show_overlay=None, wait_until_found=False, wait_until_disappears=False, wait_timeout=None)` | bool | |
| `find_image(image_path, region=None, confidence=0.9, …)` | box or `None` | Accepts a registered label or a path. |
| `click_image(image_path, region=None, confidence=0.9, delay=0, mouse_button="left", max_attempts=3, backtrack=False, specific=True, sendtext=None, show_overlay=None, wait_until_found=False, wait_until_disappears=False, wait_timeout=None)` | bool | `specific=False` searches the whole screen + scale variations. |
| `find_relative_image(anchor_image, target_image, max_distance=200, confidence=0.9, target_region=None, …)` | box or `None` | Target near a unique anchor. |
| `click_relative_image(anchor_image, target_image, max_distance=200, confidence=0.9, target_region=None, delay=0, mouse_button="left", backtrack=False, max_attempts=3, sendtext=None, …)` | bool | |
| `click_at(location, mouse_button="left", delay=0, show_overlay=None)` | bool | `location = (x, y, w, h)`. |
| `click_coordinates(x, y, delay=0, mouse_button="left", backtrack=False)` | bool | |
| `hybrid_find(name, …)` | box or `None` | native → OCR → image cascade. |

## `VisusBot` — keyboard / text

| Method | Returns |
|---|---|
| `type_text(text, interval=0.05, delay=0, backtrack=False)` | bool |
| `keyboard_command(command, delay=0, backtrack=False)` | bool |
| `extract_text_from_region(region, filter_type="both", return_full_data=False, confidence_threshold=50)` | list |

## `VisusBot` — mouse extras (from `CapabilitiesMixin`)

`scroll(amount, x=None, y=None, delay=0)`, `drag(start_x, start_y, end_x, end_y,
duration=0.5, button="left", delay=0, show_overlay=None)`, `triple_click(x=None,
y=None, interval=0.05, delay=0, show_overlay=None)`, `move_random(...)`,
`mouse_down(...)`, `mouse_up(...)`.

## `VisusBot` — overlay control

`configure_overlay(enabled=None, color=None, duration=None, width=None)`,
`get_overlay_config()`, `get_available_overlay_colors()`, the `show_overlay`
property. See [`config.md`](config.md) for the overlay keys.

## `VisusBot` — task lists & sessions

`execute_tasks(tasks, resume=False)` → `list[TaskResult]`. Task dict shapes are
documented in [`mcp.md`](mcp.md#task-lists--sessions) (identical schema).
`start_task_session()` / `end_task_session()` open a manual scope in which direct
`click_*` / `type_text` / `keyboard_command` calls also emit structured events
(so a `Session` recording captures them).

## Smart cascade & capture

`smart_find(...)`, `smart_click(...)`, `capture_element(label, auto=…, text=…,
native=…, region=…, window=…, click=False, …)`. Same params as the
[MCP tools](mcp.md#smart-cascade).

## Native RPA — `from visus.desktop.core.native_rpa import …`

`native_dump_tree`, `native_click`, `native_set_text`, `native_get_text`,
`native_get_state`, `native_wait`. Same selectors/params as the
[MCP native tools](mcp.md#native-rpa-accessibility-tree).

## Windows / processes / screen / files / clipboard

`ensure_window`, `list_windows`, `get_window`, `focus_window`,
`maximize_window`, `minimize_window`, `close_window`; `launch`, `find_process`,
`is_process_running`, `kill_process`; `take_screenshot`, `save_screenshot`,
`capture_screen`, `get_display_size`, `get_monitors`, `wait_for_stable_screen`;
`wait_for_file`, `wait_for_file_stable`; `get_clipboard`, `copy_to_clipboard`,
`paste`; `find_all`, `find_multiple`.

## Sessions / reports — `from visus.desktop.core.session import Session`

```python
from visus.desktop.core.session import Session
from visus.desktop.core.report import write_report

with Session.start_recording("run.zip"):
    bot.execute_tasks([...])          # or direct calls inside start_task_session()
events = Session.replay("run.zip")    # read back (does not re-run)
write_report("run.zip", "run.html")   # styled single-file HTML
```

## Config & exceptions

`BotVisionConfig` ([config.md](config.md)), `get_default_config()`. Exceptions:
`BotVisionError` (base), `ImageNotFoundError`, `TextNotFoundError`,
`TaskExecutionError`, `ImageProcessingError`, `OCRProcessingError`,
`TesseractNotFoundError`, `InvalidRegionError`, `ConfigurationError`,
`NotSupportedOnThisOS`, `NativeError`.

---

## Coverage matrix — Python API vs CLI vs MCP

Every capability is now first-class (✓) in **both** the CLI and the MCP server.
The library method, its CLI command, and its MCP tool expose the same parameter
set (verified by an automated audit of the find/click/keyboard/relative
primitives — all robustness knobs included).

| Capability | Python | CLI | MCP |
|---|---|---|---|
| `find_text` | ✓ | ✓ `text find` | ✓ |
| `find_all_text` | ✓ | ✓ `text find-all` | ✓ |
| `show_text_occurrences` | ✓ | ✓ `text show` | — *(on-screen overlay; n/a headless)* |
| `click_text` | ✓ | ✓ `text click` | ✓ |
| `find_image` / `click_image` | ✓ | ✓ `image find` / `image click` | ✓ |
| `find_all` / `find_multiple` | ✓ | ✓ `image find-all` / `image find-multiple` | ✓ |
| `find_relative_image` / `click_relative_image` | ✓ | ✓ `image relative` | ✓ |
| `click_at` / `click_coordinates` | ✓ | ✓ `mouse click` (+ `smart --coords`) | ✓ `click_at` |
| `hybrid_find` | ✓ | `smart find` | ✓ |
| `type_text` | ✓ | ✓ `type` | ✓ |
| `keyboard_command` | ✓ | ✓ `key` | ✓ |
| `get_available_keyboard_commands` | ✓ | ✓ `keys` | — *(static list)* |
| mouse extras (`scroll`/`drag`/`triple_click`/`move_random`/`mouse_down`/`mouse_up`) | ✓ | ✓ `mouse …` | ✓ |
| `smart_find` / `smart_click` | ✓ | ✓ `smart` | ✓ |
| `capture_element` | ✓ | ✓ `capture` | ✓ |
| native RPA (6) | ✓ | ✓ `native` | ✓ |
| `ensure_window` / `list_windows` / `get_window` | ✓ | ✓ `window` | ✓ |
| `focus`/`maximize`/`minimize`/`close_window` | ✓ | ✓ `window` | ✓ |
| `launch` / `find_process` / `kill_process` | ✓ | ✓ `process` | ✓ |
| `is_process_running` | ✓ | ✓ `process is-running` | ✓ |
| `take_screenshot` (base64) | ✓ | ✓ `screenshot --base64` | ✓ |
| `save_screenshot` | ✓ | ✓ `screenshot` | ✓ |
| `get_monitors` / `get_display_size` | ✓ | ✓ `monitors` / `display-size` | ✓ |
| `wait_for_stable_screen` | ✓ | *(via record/report flow)* | ✓ |
| `wait_for_file` / `wait_for_file_stable` | ✓ | *(used in task scripts)* | ✓ |
| `get_clipboard` / `copy_to_clipboard` | ✓ | ✓ `clipboard` | ✓ |
| `extract_text_from_region` | ✓ | *(via `text`/scripts)* | ✓ |
| `execute_tasks` | ✓ | ✓ `run` (script) | ✓ |
| record / replay / report | ✓ | ✓ `report` (render) | ✓ |
| `configure` / `doctor` | ✓ | ✓ | ✓ |

Totals: **56 MCP tools**, **50 CLI leaf commands**.

The few non-first-class cells are deliberate: `show_text_occurrences` draws an
on-screen overlay (meaningless to a headless MCP agent); the file/screen *wait*
helpers are single-call utilities used from task scripts rather than standalone
CLI verbs (the MCP server exposes them directly because agents call them
between steps).

See also: [`cli.md`](cli.md) · [`mcp.md`](mcp.md) · [`config.md`](config.md).

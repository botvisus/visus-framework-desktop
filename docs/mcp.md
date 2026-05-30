# Visus Desktop MCP server — complete tool reference (for AI agents)

This is the authoritative, exhaustive reference for the **56 MCP tools** exposed
by the `visus-mcp` server. Every tool, every parameter, every default, and every
return shape is listed. If you are an agent driving this server, you should be
able to act with **zero guessing** from this page alone.

## Install & run

```bash
pip install "visus-desktop[mcp]"
visus-mcp                              # stdio transport (what hosts expect)
```

Host config (Claude Desktop / Code `settings.json`):

```json
{ "mcpServers": { "visus-desktop": { "command": "visus-mcp" } } }
```

The bot is a lazily-built module-level singleton, so config, the open recording,
and the last extracted text persist across calls within one server lifetime.

## Reading this reference

- **Types**: `int`, `float`, `str`, `bool`, `list[int]`, `list[str]`, `dict`.
- **`region` / `target_region` / `search_region`** are always `[x, y, w, h]`
  (JSON array of 4 ints). `coordinates` is `[x, y]`.
- **Confidence scales differ**: image `confidence` is **0.0–1.0**; OCR
  `confidence_threshold` is **0–100**. Do not mix them up.
- **Boxes** returned by find tools are `{x, y, width, height}` or `null`.
- **`mouse_button`** accepts `left`, `right`, `double`, `move_to` (the OCR/image
  click tools) or `left`/`right`/`middle` (native/coordinate tools) — each
  tool states which.
- A parameter shown as `name=value` has that default; omit it to accept the
  default.

## The 6-step playbook (follow in order)

1. **`ensure_window(process="app.exe")`** — open/focus the app, get its `rect`.
   Always first. Prefer `process` over `title`.
2. **`native_dump_tree(window="App")`** — if it returns controls, drive the app
   natively (most robust). If `[]`, use the pixel path.
3. **`capture_element(label="save", auto="Save", window="App", click=True)`** —
   the coordinate-free click. Or `smart_click(query="Save", window="App")`.
4. **Scope every search** — pass `region` = the window `rect` so a match can't
   land on the wrong window.
5. **Wait, don't sleep** — `wait_for_stable_screen` after a UI change;
   `wait_for_file_stable` for downloads; `native_wait` for a control.
6. **Record** — `start_recording` → `execute_tasks`/clicks → `stop_recording` →
   `render_report` for an auditable HTML artifact.

---

# Targeting (call first)

### `ensure_window(title=None, process=None, show=True, foreground=True) -> dict`
**Call FIRST.** Fast win32 probe + raise-to-front. Match by `title` (substring)
and/or `process` (name like `"notepad.exe"`). `show=False` = read-only probe
(don't restore/raise). Returns `{found, running, hwnd, pid, title, minimized,
maximized, foreground, rect, shown, matches}`. `rect` is `null` while minimized;
`matches > 1` = ambiguous (narrow with `process`).

### `list_windows(title=None, process=None) -> list[dict]`
Read-only. `[{hwnd, title, pid, minimized, maximized, foreground, rect}, …]`.

### `get_window(title_substring) -> dict | null`
One window's `{title, pid, hwnd, x, y, width, height}`; no focus.

---

# Find / click — text (OCR)

### `find_text(text, region=None, filter_type="both", confidence_threshold=75.0, occurrence=1, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> dict | null`
Find on-screen text; return its box, no click.
- `filter_type`: `"letters"` | `"numbers"` | `"both"`.
- `occurrence`: Nth match, 1-based.
- `confidence_threshold`: 0–100 (lower to ~50 to debug a miss).
- `wait_until_found`: poll until it appears (≤ `wait_timeout` s).
- `wait_until_disappears`: wait until it's gone.
- `backtrack` + `max_attempts`: retry with adjusted thresholds.

### `find_all_text(text, region=None, filter_type="both", confidence_threshold=None) -> list[dict]`
**Every** occurrence, reading order. Returns `[{occurrence, x, y, width, height,
confidence}, …]`. Use to disambiguate repeats, then `click_text(occurrence=N)`.
`confidence_threshold=None` uses the config default.

### `click_text(text, region=None, filter_type="both", delay=0, mouse_button="left", occurrence=1, sendtext=None, confidence_threshold=None, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> bool`
Find text and click its center. `sendtext` types a string right after the click
(fill a field you just clicked). `mouse_button`: left|right|double|move_to.
Wait/backtrack knobs as in `find_text`.

---

# Find / click — image (template PNG)

### `find_image(image_path, region=None, confidence=0.9, specific=True, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> dict | null`
Find a template PNG; return its box. `confidence`: 0–1 (lower to ~0.7 on a
miss). `specific=True` = search `region`; `specific=False` = whole screen +
scale variations (helps across resolutions). Template must match the live
DPI/scale.

### `click_image(image_path, region=None, confidence=0.9, delay=0, mouse_button="left", specific=True, sendtext=None, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> bool`
Find a template PNG and click its center.

### `find_relative_image(anchor_image, target_image, max_distance=200, confidence=0.9, target_region=None, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> dict | null`
Find a target template **near** a unique anchor template (no click). Use when
the target alone is ambiguous but a unique anchor sits nearby. `max_distance` =
max px between anchor and target (keep small to reject a far twin).

### `click_relative_image(anchor_image, target_image, max_distance=200, confidence=0.9, target_region=None, delay=0, mouse_button="left", sendtext=None, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> bool`
Find the target near the anchor and click it.

### `find_all(image_path, region=None, confidence=0.9) -> list[dict]`
**Every** occurrence of one template. Returns `[{x, y, width, height}, …]`.

### `find_multiple(images: list[str], region=None, confidence=0.9) -> dict`
First match of several templates in one call. Returns `{path: {x, y, width,
height} | null}` per input path. (Probe which of several elements is on screen.)

### `hybrid_find(name, region=None) -> dict | null`
Find `name` trying native → OCR → image, in order (no click). For clicking
prefer `smart_click`.

### `click_at(x, y, width=0, height=0, mouse_button="left", delay=0) -> bool`
Click absolute coordinates — **last resort** (no find step). Clicks the box
center if `width`/`height` given. `mouse_button`: left|right|middle.

---

# Smart cascade (native → image → OCR → coordinates)

### `smart_find(query=None, image=None, coordinates=None, window=None, pid=None, control_type=None, auto_id=None, search_region=None, confidence=0.9, confidence_threshold=75.0, order=None, timeout=5.0) -> dict`
Locate by cascading. A method is skipped when its input is missing. `order`
overrides the cascade (e.g. `["native"]` to force one, `["ocr","image"]` to
reorder; default `["native","image","ocr","coordinates"]`). Returns `{found,
box, method, tried}`.

### `smart_click(query=None, image=None, coordinates=None, window=None, pid=None, control_type=None, auto_id=None, search_region=None, button="left", confidence=0.9, confidence_threshold=75.0, order=None, timeout=5.0, retries=0, delay=0.3) -> dict`
Same inputs; each layer uses its own click action. Returns `{clicked, method,
tried}`.

---

# Coordinate-free capture

### `capture_element(label, auto=None, text=None, native=None, region=None, window=None, search_region=None, click=False, mouse_button="left", padding=0, confidence_threshold=75.0, native_timeout=5.0, elements_dir="./visus-elements") -> dict`
Locate an element, save `<elements_dir>/<label>.png` + an annotated screenshot,
optionally click. Provide **exactly one** locator: `auto` (recommended: Win32
menu → OCR → UIA directed), `text` (OCR), `native` (directed UIA), or `region`.
`window` scopes Win32/UIA to a title even when not focused. Returns `{found,
label, located_by, box, template_path, annotated_path, clicked}`.

---

# Native RPA (accessibility tree, no pixels)

All select a control via `window` / `pid` / `title` / `control_type` /
`auto_id` / `found_index`. Empty/`false`/`null` on non-accessible UIs.

### `native_dump_tree(window=None, pid=None, max_depth=3, timeout=5.0) -> list[dict]`
`[{depth, control_type, title, auto_id, rect}, …]`. How an agent *sees* a native
UI. `[]` for non-accessible apps (Java Swing w/o Access Bridge, some Electron).

### `native_click(window=None, pid=None, title=None, control_type=None, auto_id=None, found_index=None, button="left", double=False, method="auto", timeout=5.0, retries=0, delay=0.3) -> bool`
`method`: `invoke` (UIA, no mouse) | `click` (real mouse) | `auto` (invoke then
click). `button`: left|right|middle.

### `native_set_text(text, window=None, pid=None, title=None, control_type=None, auto_id=None, found_index=None, timeout=5.0, retries=0, delay=0.3) -> bool`
Set an editable control's text (UIA value pattern).

### `native_get_text(window=None, pid=None, title=None, control_type=None, auto_id=None, found_index=None, timeout=5.0) -> str | null`
Read a control's text/value.

### `native_get_state(window=None, pid=None, title=None, control_type=None, auto_id=None, found_index=None, timeout=5.0) -> dict | null`
`{exists, visible, enabled, checked, value, control_type, rect}`.

### `native_wait(window=None, pid=None, title=None, control_type=None, auto_id=None, found_index=None, state="exists", timeout=10.0, poll_interval=0.3) -> bool`
`state`: `exists` | `visible` | `enabled` | `ready` (= exists+visible+enabled).

---

# Keyboard

### `type_text(text, interval=0.05, delay=0, backtrack=False) -> bool`
Type into the **currently focused** field (focus it first). Inline tokens
expand: `{ctrl}a`, `{tab}`, `{enter}`, `{escape}`. `interval` = per-char delay.

### `keyboard_command(command, delay=0, backtrack=False) -> bool`
Press a key/chord — tokens **case-sensitive**: `Enter`, `Escape`, `Tab`,
`Delete`, `F1`–`F12`, `Up`/`Down`/`Left`/`Right`, `Ctrl+S`, `Ctrl+C`, `Ctrl+V`,
`Ctrl+A`, `Ctrl+Z`, `Alt+F4`, `Alt+Tab`, `Shift+Tab`, `Ctrl+T`, `Ctrl+W`.

---

# Mouse gestures (low-level, coordinate-based)

### `scroll(amount, x=None, y=None) -> bool`
Scroll the wheel; positive = up, negative = down. Optionally move to `(x, y)`
first.

### `drag(start_x, start_y, end_x, end_y, duration=0.5, button="left") -> bool`
Drag holding `button` (left|middle|right). Sliders, reordering, drag-and-drop.

### `triple_click(x=None, y=None, interval=0.05) -> bool`
Triple-click (select a whole line/paragraph).

### `move_random(x, y, max_offset=3, duration=0.2) -> bool`
Move with a light human-like jitter, settling exactly on `(x, y)`.

### `mouse_down(x=None, y=None, button="left") -> bool` / `mouse_up(x=None, y=None, button="left") -> bool`
Press / release without the other — press-and-hold patterns `drag` doesn't
cover. `button`: left|middle|right.

---

# Screen / monitors / waits

### `take_screenshot(region=None, monitor=None) -> dict`
Base64 PNG: `{mime_type, data_base64, width, height}`.

### `save_screenshot(path, region=None, monitor=None) -> dict`
Write a PNG to disk (the `find_image` template format). Returns `{path, width,
height}` (absolute path).

### `get_monitors() -> list[dict]`
`[{index, x, y, width, height, is_primary}]`. `index` is the 1-based value the
screenshot tools' `monitor=` expects.

### `get_display_size() -> dict`
Primary display `{width, height}` in pixels.

### `wait_for_stable_screen(region=None, stable_for=0.5, timeout=15.0, poll_interval=0.1) -> bool`
Block until the screen stops changing — use instead of sleeping after a UI
transition. Narrow `region` for speed; raise `stable_for` (~0.8) for animations.

---

# Files / clipboard

### `wait_for_file(path, timeout=10.0, poll_interval=0.5) -> bool`
Block until `path` exists & is readable.

### `wait_for_file_stable(path, timeout=30.0, stable_for=1.0, poll_interval=0.5) -> bool`
Block until `path` exists **and** its size stops growing — for downloads.

### `get_clipboard() -> str` / `copy_to_clipboard(text) -> bool`
Read / write the system clipboard. (Copy then `keyboard_command("Ctrl+V")` is
more reliable than typing long/Unicode text.)

### `extract_text_from_region(region, filter_type="both", return_full_data=False, confidence_threshold=50.0) -> list`
OCR all text in `region`. `return_full_data=True` → `[{text, confidence, box,
absolute_box}, …]`; otherwise a flat string list.

---

# Process / window control

### `launch(command, args=None) -> dict`
Start a process. Returns `{pid, command}`.

### `find_process(name) -> list[dict]`
`[{pid, name}, …]` (case-insensitive substring).

### `is_process_running(name) -> bool`
Quick boolean: is any process whose name contains `name` running?

### `kill_process(pid) -> bool`
Terminate by PID. **DESTRUCTIVE** — confirm with the user first.

### `focus_window / maximize_window / minimize_window / close_window(title_substring) -> bool`
Window actions by title substring. `close_window` is destructive — confirm.

---

# Task lists & sessions

### `execute_tasks(tasks: list[dict], resume=False) -> list[dict]`
Run a sequence of task dicts with retry. The action is chosen by an explicit
`type` key, or inferred from a `text` / `image` key. Returns one result per
task: `{task_index, task_name, success, attempts, duration_ms, error,
failure_screenshot}`.

**Task shapes** (the action is chosen by `type`, or inferred from `text`/`image`):

```jsonc
// IMAGE — find a template PNG and click its center
{"image": "save.png", "region": [x,y,w,h], "confidence": 0.8,
 "specific": true, "mouse_button": "left"}

// TEXT (OCR) — region recommended
{"text": "Save", "region": [x,y,w,h], "char_type": "both",
 "occurrence": 1, "sendtext": "admin"}

// TYPE_TEXT — into the focused field (tokens: {ctrl}a {tab} {enter} {escape})
{"type": "type_text", "text": "hello", "interval": 0.05}

// KEYBOARD_COMMAND — case-sensitive token
{"type": "keyboard_command", "command": "Ctrl+S"}

// CLICK — absolute coords (only if the user gave them)
{"type": "click", "x": 100, "y": 200, "mouse_button": "left"}

// EXTRACT_TEXT — OCR a region, no click
{"type": "extract_text", "region": [x,y,w,h], "char_type": "both",
 "return_full_data": false}

// RELATIVE_IMAGE — target template NEAR a unique anchor, click target
{"type": "relative_image", "anchor_image": "cancel.png",
 "target_image": "save.png", "max_distance": 180, "confidence": 0.8,
 "specific": true, "target_region": [x,y,w,h]}
```

**Common options** (any task): `mouse_button` left|right|double|move_to,
`delay` (s after the action), `region` `[x,y,w,h]` (always scope it).

**Wait & retry knobs**: `backtrack: true` (on failure, re-run earlier step(s)
then retry); `wait_until_found: true` (poll until the image/text appears, then
act); `wait_until_disappears: true` (click, then wait until target is gone —
confirm a dialog closed); `wait_timeout` (seconds for those waits, default 30).

### `start_recording(path) -> str`
Begin capturing task events + per-step/failure screenshots + `visus.*` logs into
a session zip. Returns the path.

### `stop_recording() -> bool`
Finalize and write the zip.

### `replay_session(zip_path) -> list[dict]`
Read recorded events back (does NOT re-run). Each: `{run_id, task_id,
task_name, success, duration_ms, error, failure_screenshot, timestamp, logs}`.
`logs` = the `visus.*` log lines captured during that task (verbosity follows
the recorded `log_level`).

### `render_report(zip_path, html_path) -> str`
Render a session zip into a styled single-file HTML report (timeline,
durations/attempts, embedded screenshots, collapsible per-task logs). Returns
the absolute HTML path.

---

# Configuration & diagnostics

### `configure(config: dict) -> dict`
Rebuild the bot with new config; persists for the server session. Any
`BotVisionConfig` key — see [`config.md`](config.md). Common: `ocr_backend`
(`tesseract`|`rapidocr`), `matcher` (`cv2`|`pyscreeze`), `confidence_threshold`,
`show_overlay`, `log_format`, `screenshot_steps`. Returns the active config dict.

### `doctor() -> dict`
`{exit_code, checks: [{name, ok, detail}], output}`. `exit_code != 0` = a check
failed (e.g. Tesseract missing).

---

See also: [`cli.md`](cli.md) (the `visus` CLI, 1:1 with these tools),
[`config.md`](config.md) (every config key), [`api_reference.md`](api_reference.md)
(Python API + a Python↔CLI↔MCP coverage matrix).

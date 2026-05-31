# Visus Desktop MCP server — complete tool reference (for AI agents)

This is the authoritative, exhaustive reference for the **57 MCP tools** exposed
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

**This reference ships with the server.** The MCP server exposes two resources —
`visus://docs/mcp` (this page) and `visus://docs/cli` (the full CLI reference) —
so any MCP client can read them on demand after `pip install`, no repo needed.
The whole toolbox is also a `visus …` shell command (`--json` everywhere); drive
a step from the shell whenever that is simpler.

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

## All 57 tools at a glance

Full per-parameter detail is in the sections below. A `?` marks an optional parameter.

| Tool | Parameters | What it does |
|---|---|---|
| `configure` | config | Change global behavior by rebuilding the bot with new config. |
| `find_text` | text, region?, filter_type?, confidence_threshold?, occurrence?, max_attempts?, backtrack?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find visible on-screen `text` via OCR; return its box (do not click). |
| `click_text` | text, region?, filter_type?, delay?, mouse_button?, occurrence?, sendtext?, confidence_threshold?, max_attempts?, backtrack?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find on-screen `text` via OCR and click its center. |
| `find_all_text` | text, region?, filter_type?, confidence_threshold? | List EVERY on-screen occurrence of `text` via OCR (do not click). |
| `show_text_occurrences` | text, region?, filter_type?, confidence_threshold?, color?, duration_ms?, width?, annotate_screenshot? | Find every occurrence of `text` and SHOW them numbered 1, 2, 3 …. |
| `find_image` | image_path, region?, confidence?, specific?, occurrence?, max_attempts?, backtrack?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find a template PNG on screen; return its box (do not click). |
| `click_image` | image_path, region?, confidence?, delay?, mouse_button?, specific?, occurrence?, sendtext?, max_attempts?, backtrack?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find a template PNG on screen and click its center. |
| `click_at` | x, y, width?, height?, mouse_button?, delay? | Click at absolute screen coordinates -- no find step. LAST RESORT. |
| `hybrid_find` | name, region? | Find `name` trying native -> OCR -> image template, in order (no click). |
| `find_relative_image` | anchor_image, target_image, max_distance?, confidence?, target_region?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find a target template NEAR a unique anchor template (no click). |
| `click_relative_image` | anchor_image, target_image, max_distance?, confidence?, target_region?, delay?, mouse_button?, sendtext?, max_attempts?, backtrack?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find a target template near a unique anchor and click it. |
| `find_all` | image_path, region?, confidence? | Find EVERY occurrence of one template PNG on screen (no click). |
| `find_multiple` | images, region?, confidence? | Locate the first match of SEVERAL template PNGs in one call (no click). |
| `type_text` | text, interval?, delay?, backtrack? | Type `text` into the CURRENTLY FOCUSED field (click/focus it first). |
| `keyboard_command` | command, delay?, backtrack? | Press a named key or shortcut. Tokens are CASE-SENSITIVE. |
| `scroll` | amount, x?, y? | Scroll the mouse wheel. Positive = up, negative = down. |
| `drag` | start_x, start_y, end_x, end_y, duration?, button? | Drag from `(start_x, start_y)` to `(end_x, end_y)` holding `button`. |
| `triple_click` | x?, y?, interval? | Triple-click at `(x, y)` (or the current cursor position). |
| `move_random` | x, y, max_offset?, duration? | Move the cursor to `(x, y)` with a light human-like jitter. |
| `mouse_down` | x?, y?, button? | Press a mouse button at `(x, y)` (or current position) WITHOUT releasing. |
| `mouse_up` | x?, y?, button? | Release a previously-pressed mouse button at `(x, y)` (or current position). |
| `take_screenshot` | region?, monitor? | Capture the screen and return a base64-encoded PNG. |
| `save_screenshot` | path, region?, monitor? | Capture the screen and save it to `path` on disk as a PNG. |
| `get_window` | title_substring | Resolve a window by title substring; no focus required. |
| `capture_element` | label, auto?, text?, native?, region?, window?, search_region?, click?, mouse_button?, padding?, confidence_threshold?, native_timeout?, elements_dir? | Locate a UI element, save a reusable template + annotated shot, click. |
| `smart_find` | query?, image?, coordinates?, window?, pid?, control_type?, auto_id?, search_region?, confidence?, confidence_threshold?, order?, timeout? | Locate a target by cascading native -> image -> ocr -> coordinates. |
| `smart_click` | query?, image?, coordinates?, window?, pid?, control_type?, auto_id?, search_region?, button?, confidence?, confidence_threshold?, order?, timeout?, retries?, delay? | Click a target by cascading native -> image -> ocr -> coordinates. |
| `native_dump_tree` | window?, pid?, max_depth?, timeout? | Return the accessibility control tree of a window (no pixel). |
| `native_click` | window?, pid?, title?, control_type?, auto_id?, found_index?, button?, double?, method?, timeout?, retries?, delay? | Click a control by selector -- no coordinates, no image (UIA). |
| `native_set_text` | text, window?, pid?, title?, control_type?, auto_id?, found_index?, timeout?, retries?, delay? | Set the text of an editable control by selector (UIA value pattern). |
| `native_get_text` | window?, pid?, title?, control_type?, auto_id?, found_index?, timeout? | Read a control's text/value by selector. Returns the string or None. |
| `native_get_state` | window?, pid?, title?, control_type?, auto_id?, found_index?, timeout? | Snapshot a control's state by selector. |
| `native_wait` | window?, pid?, title?, control_type?, auto_id?, found_index?, state?, timeout?, poll_interval? | Wait until a control reaches `state` by selector. |
| `get_monitors` | — | List connected monitors so you can target one in a multi-screen setup. |
| `get_display_size` | — | Return the primary display size as `{width, height}` (pixels). |
| `wait_for_stable_screen` | region?, stable_for?, timeout?, poll_interval? | Block until the screen stops changing -- use INSTEAD of sleeping. |
| `wait_for_file` | path, timeout?, poll_interval? | Block until `path` exists and is readable, or `timeout` elapses. |
| `wait_for_file_stable` | path, timeout?, stable_for?, poll_interval? | Block until `path` exists AND its size stops growing -- for downloads. |
| `get_clipboard` | — | Read the system clipboard text. |
| `copy_to_clipboard` | text | Put `text` on the system clipboard (e.g. to paste with Ctrl+V). |
| `extract_text_from_region` | region, filter_type?, return_full_data?, confidence_threshold? | OCR-extract all text from `region`. |
| `launch` | command, args? | Start an application/process. Returns its pid. |
| `find_process` | name | List running processes whose name contains `name` (no windows needed). |
| `is_process_running` | name | Return True if any running process's name contains `name`. |
| `kill_process` | pid | Terminate a process by pid. DESTRUCTIVE -- confirm with the user first. |
| `focus_window` | title_substring | Bring a window (matched by title substring) to the foreground. |
| `maximize_window` | title_substring | Maximize a window matched by title substring. |
| `minimize_window` | title_substring | Minimize a window matched by title substring. |
| `close_window` | title_substring | Gracefully close a window (posts WM_CLOSE). Confirm with the user first. |
| `ensure_window` | title?, process?, show?, foreground? | **Call this FIRST** before automating any app -- fast, reliable targeting. |
| `list_windows` | title?, process? | List visible windows (read-only) matching `title` and/or `process`. |
| `execute_tasks` | tasks, resume? | Run a sequence of task dicts (find / click / type / keys) with retry. |
| `start_recording` | path | Start recording task events into a session zip at `path`. |
| `stop_recording` | — | Finalize the active recording and write the session zip to disk. |
| `replay_session` | zip_path | Read back the recorded task events from a session zip. |
| `render_report` | zip_path, html_path | Render a session zip into a styled single-file HTML report. |
| `doctor` | — | Verify the environment is healthy (Tesseract, display, deps, pywinauto). |

## The 6-step playbook (follow in order)

1. **`ensure_window(process="app.exe")`** — open/focus the app, get its `rect`.
   Always first. Prefer `process` over `title`.
2. **`native_dump_tree(window="App")`** — if it returns controls, drive the app
   natively (most robust). If `[]`, use the pixel path.
3. **`capture_element(label="save", auto="Save", window="App", click=True)`** —
   locate by native/OCR and **save a reusable `save.png` from that exact box**.
   **OCR/native are your *eyes* at build time, not the runtime.** The automation
   you hand to the user should click the captured templates with **`click_image`
   / `click_relative_image`** — template matching is far faster than re-running
   OCR every run, and deterministic. Re-locate with OCR/native only when the
   label/layout is dynamic or to anchor a relative click. `visus text find
   "Save" --ocr rapidocr --json` (CLI) quickly "gives you eyes" on a coordinate.
   **Never eyeball a pixel crop** for `save_screenshot`; the template must come
   FROM a located box. If a locator misses, FIX it (widen/scope `search_region`,
   lower `confidence_threshold`, try `auto=`) — don't guess coordinates. If a
   word repeats (e.g. "Salvar" is in both the button and the title "Salvar
   como"), scope `search_region` to the button strip or use `find_all_text` +
   occurrence.
4. **Scope every search** — pass `region` = the window `rect` so a match can't
   land on the wrong window. With leftover look-alike windows, disambiguate via
   `list_windows` (foreground/largest rect), not title alone.
5. **Wait, don't sleep** — `wait_for_stable_screen` after a UI change;
   `wait_for_file_stable` for downloads; `native_wait` for a control.
6. **Record** — `start_recording` → `execute_tasks`/clicks → `stop_recording` →
   `render_report` for an auditable HTML artifact.

> **Save As / Open / overwrite dialogs.** The Windows 11 file picker often
> returns an **empty `native_dump_tree`** — go straight to OCR. Type the full
> path into the name field, then click the button by **text scoped to the
> bottom button row**. The dialog's **default button fires on `Enter`**; an
> overwrite confirm (**"Sim"/"Não"**) **defaults to "Não"**, so `Enter` cancels
> the overwrite — click **"Sim"** explicitly (focus that dialog first) or send
> `Left` then `Enter`. **Verify a save by the file's mtime/size**, not just that
> the path exists.

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

### `show_text_occurrences(text, region=None, filter_type="both", confidence_threshold=None, color="red", duration_ms=3000, width=3, annotate_screenshot=True) -> dict`
The **visual** sibling of `find_all_text`: SEE which copy is which before
picking an `occurrence`. Draws a numbered click-through overlay (1, 2, 3 …) on
the real screen **and** (with `annotate_screenshot=True`) returns a base64 PNG
of the screen with each match boxed and numbered — read the numbers straight
from the image, no separate `take_screenshot`, no timing race. Returns
`{count, matches: [{occurrence, x, y, width, height, confidence}], image:
{mime_type, data_base64, width, height} | null}`. Numbers are the same
`occurrence` you pass to `click_text` / `click_image`.

### `click_text(text, region=None, filter_type="both", delay=0, mouse_button="left", occurrence=1, sendtext=None, confidence_threshold=None, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> bool`
Find text and click its center. `sendtext` types a string right after the click
(fill a field you just clicked). `mouse_button`: left|right|double|move_to.
Wait/backtrack knobs as in `find_text`.

---

# Find / click — image (template PNG)

### `find_image(image_path, region=None, confidence=0.9, specific=True, occurrence=1, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> dict | null`
Find a template PNG; return its box. `confidence`: 0–1 (lower to ~0.7 on a
miss). `specific=True` = search `region`; `specific=False` = whole screen +
scale variations (helps across resolutions). `occurrence`: when the template
appears more than once, the Nth match in reading order (top-to-bottom,
left-to-right); `occurrence>1` enumerates every match and picks the Nth — the
image counterpart of `click_text(occurrence=N)`. Template must match the live
DPI/scale.

### `click_image(image_path, region=None, confidence=0.9, delay=0, mouse_button="left", specific=True, occurrence=1, sendtext=None, max_attempts=3, backtrack=False, wait_until_found=False, wait_until_disappears=False, wait_timeout=None) -> bool`
Find a template PNG and click its center. `occurrence=N` clicks the Nth copy
(reading order) when the template repeats.

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

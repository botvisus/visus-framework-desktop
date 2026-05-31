---
name: using-visus-desktop
description: Entry-point skill for driving visus-desktop via MCP. Use whenever the user asks you to automate a desktop app, scrape on-screen text, or replay a UI flow through the visus-desktop tools.
when_to_use: Activate at the start of any visus-desktop automation task to ground yourself in the available tools, safety conventions, and the recommended flow.
---

# Using Visus Desktop

You have access to the visus-desktop MCP server (`visus-mcp`). It exposes **57 tools** that cover desktop GUI automation, OCR, image matching, native (Win32/UIA) targeting, **no-pixel native RPA**, a **smart cascade** (`smart_click`/`smart_find` — try native → image → OCR → coordinates, configurable order), low-level mouse gestures, process / window management, clipboard, file waits, session record/replay, and HTML reporting. The full per-parameter reference is `docs/mcp.md`.

## What this MCP gives you

| Group | Tools |
|---|---|
| **Find / click (text)** | `find_text`, `find_all_text` *(every occurrence, reading order — to disambiguate repeats, then `click_text(occurrence=N)`)*, `click_text` |
| **Find / click (image)** | `find_image`, `click_image`, `find_all` *(every match of one template)*, `find_multiple` *(first match of several templates)*, `find_relative_image`, `click_relative_image` *(target near a unique anchor)*, `click_at` *(absolute coords, last resort)*, `hybrid_find` |
| **Keyboard** | `type_text`, `keyboard_command` |
| **Mouse (low-level)** | `scroll`, `drag`, `triple_click`, `move_random`, `mouse_down`, `mouse_up` |
| **Screen / monitors** | `take_screenshot` (base64), `save_screenshot` (to disk — for find_image templates), `capture_element` (locate-by-text/native/region → save template + annotated → optional click), `get_monitors`, `get_display_size`, `wait_for_stable_screen` |
| **Files / clipboard** | `wait_for_file`, `wait_for_file_stable`, `get_clipboard`, `copy_to_clipboard`, `extract_text_from_region` *(use `return_full_data=true` for boxes + scores)* |
| **Process / window** | `launch`, `find_process`, `is_process_running`, `kill_process`, `ensure_window` *(★ call first)*, `list_windows`, `get_window`, `focus_window`, `maximize_window`, `minimize_window`, `close_window` |
| **Smart cascade** | `smart_click` / `smart_find` — one call tries **native → image → OCR → coordinates** in order (pass `order=[...]` to force/reorder). The simplest robust way to click something when you're not sure which technique fits. |
| **Native RPA (no pixel)** | `native_dump_tree` (read the UI structure), `native_click`, `native_set_text`, `native_get_text`, `native_get_state`, `native_wait` — operate accessible apps by control, immune to theme/DPI/resolution/language. Falls flat on non-accessible UIs (Java Swing) → use OCR there. |
| **Task lists** | `execute_tasks` |
| **Sessions / reports** | `start_recording`, `stop_recording`, `replay_session`, `render_report` |
| **Diagnostics / config** | `doctor`, `configure` |

The find/click primitives also take the robustness knobs `wait_until_found`, `wait_until_disappears`, `wait_timeout`, `backtrack`, `max_attempts`, plus `sendtext` (type right after a click) and `filter_type` / `specific` where relevant — see `docs/mcp.md` for the exact per-tool parameter list.

## Every tool (57) at a glance

`?` marks an optional parameter. Full per-parameter detail is in `docs/mcp.md`.

| Tool | Parameters | What it does |
|---|---|---|
| `configure` | config | Change global behavior by rebuilding the bot with new config. |
| `find_text` | text, region?, filter_type?, confidence_threshold?, occurrence?, max_attempts?, backtrack?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find visible on-screen `text` via OCR; return its box (do not click). |
| `click_text` | text, region?, filter_type?, delay?, mouse_button?, occurrence?, sendtext?, confidence_threshold?, max_attempts?, backtrack?, wait_until_found?, wait_until_disappears?, wait_timeout? | Find on-screen `text` via OCR and click its center. |
| `find_all_text` | text, region?, filter_type?, confidence_threshold? | List EVERY on-screen occurrence of `text` via OCR (do not click). |
| `show_text_occurrences` | text, region?, filter_type?, confidence_threshold?, color?, duration_ms?, width?, save_image?, image_path? | Find every occurrence of `text` and SHOW them numbered 1, 2, 3 …. |
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

## The mental model

0. **Native RPA first when the app is accessible.** Before any pixel work, try `native_dump_tree(window=...)` to *see* the control tree. If it returns controls, prefer `native_click` / `native_set_text` / `native_get_text` / `native_wait` — operating by control (no pixel) is the most robust automation: immune to theme, DPI, resolution, language, window position, and overlapping windows. If `native_dump_tree` returns `[]` (non-accessible UI: Java Swing, some Electron), fall back to the pixel path below.
1. **Targeting (pixel path)**: prefer `hybrid_find(name=…)` — it tries native (pywinauto), then OCR, then template image, transparently. Only drop to the specific layer (`find_text`, `find_image`) when you know which one fits.
2. **Prefer `capture_element(auto=...)` for click steps**: instead of guessing a screenshot region and eyeballing coordinates (error-prone — you can grab the wrong button), call `capture_element(label="...", auto="Salvar", click=True)`. `auto=` tries **Win32 menu → OCR → UIA directed** in order: native apps get the instant pixel-exact Win32/UIA rect; anything else (Java Swing, Electron, remote desktop) falls back to OCR automatically. It saves a reusable template to `visus-elements/<label>.png` + an annotated screenshot showing exactly what matched, and clicks the center. `located_by` in the result tells you which strategy won. Pass `window="App Title"` to scope to a specific window even when it's not focused. Walk a menu step-by-step this way (`auto="Arquivo"` → `auto="Salvar como"`). Never hand-crop a region just to find a button.

   **OCR/native are your *eyes* to capture the template — the script you hand off runs on images.** When you BUILD a reusable automation/script for the user, use `capture_element(auto=/text=)` (or `find_text`/`native_*`) to *locate* each element and save its template once; the delivered script then clicks with `click_image` / `click_relative_image`, because template matching is far faster than re-running OCR on every run and is deterministic. Re-locate with OCR/native only when the label/layout is dynamic or to anchor a relative click. CLI to "get eyes" on a coordinate fast: `visus text find "Sim" --ocr rapidocr --json`.
3. **Verify before clicking** (when not using `capture_element`): call a find tool, inspect the returned `{x, y, width, height}` dict, then click. Never blind-click coordinates unless the user gave them to you. When a label repeats on screen, call `find_all_text` first — it lists every match in reading order with a 1-based `occurrence` — then click the right one with `click_text(occurrence=N)`.
3. **Wait deliberately**: between any visible change and the next find, call `wait_for_stable_screen` (UI redraw) or `wait_for_file_stable` (downloads). Hard-coded `sleep` is a smell.
4. **Record troublesome flows**: `start_recording('out.zip')` → `execute_tasks([...])` → `stop_recording()` → `render_report('out.zip', 'report.html')`. The HTML report has timing + screenshots and is the right artifact to send a human when a flow fails.

## Recommended sequence for any new task

1. `ensure_window(process="app.exe")` — **call this first**. Opens/restores/focuses the target and returns its `rect`; prefer `process=` over `title=`. Scope later searches to that `rect`.
2. `doctor()` — verify Tesseract, display, pywinauto, dependencies are healthy (once per session).
3. `take_screenshot()` once — orient yourself; you have the dimensions and current state.
4. Plan the smallest task list possible:
   * One `find_*` / `hybrid_find` per ambiguous target.
   * One `wait_for_stable_screen` per UI transition you cannot predict.
   * `keyboard_command` over typing whenever a shortcut exists.
5. Either send the steps as a `execute_tasks(tasks=[…])` list (best when the user wants atomic backtrack/retry behaviour) **or** call each tool individually if you need to inspect intermediate state.

## Safety guardrails

* **Confirm destructive actions** (closing windows, killing processes, replacing files) with the user before invoking them, unless the user has already authorized the operation explicitly in this turn.
* **Never enter credentials** unless the user provided them in this conversation.
* **Honour `wait_timeout`** when calling find tools that block (`wait_for_file`, `wait_for_stable_screen`). 30 seconds is the sane upper bound for a UI redraw; 5 minutes is the upper bound for a download.
* **Use absolute coordinates only when given by the user.** Otherwise resolve targets through `find_*` / `hybrid_find`.

## Common failure modes and how to react

| Symptom | Diagnosis | Fix |
|---|---|---|
| `find_text` returns `null` | OCR could not match | Re-`take_screenshot` and inspect the region; lower `confidence_threshold` to ~50 to see what OCR actually read. |
| `click_image` returns `false` | Template not on screen / wrong DPI | Re-capture a fresh template; `configure({"matcher": "pyscreeze"})` if cv2 is too strict. |
| `wait_for_stable_screen` returns `false` (timeout) | Animation never settled | Narrow the `region` to the area you care about; bump `stable_for` to 0.8 s. |
| `execute_tasks` shows a `failure_screenshot` path | A specific step failed | Take that screenshot and decide whether it's an unexpected modal / network error / wrong target. |

## Cookbook reference

When the user describes a recipe pattern, prefer the matching skill rather than improvising:

* **Login forms** → `automate-form-login.md`
* **Table scraping** → `extract-table-data.md`
* **Downloads** → `wait-for-download.md`
* **Captchas** → `solve-image-captcha.md`
* **File dialogs** → `file-dialog-automation.md`
* **Session capture for reporting** → `record-and-replay.md`

When in doubt, re-read this skill before invoking tools — it overrides whatever you "remember" about visus-desktop from training data.

---
name: using-visus-desktop
description: Entry-point skill for driving visus-desktop via MCP. Use whenever the user asks you to automate a desktop app, scrape on-screen text, or replay a UI flow through the visus-desktop tools.
when_to_use: Activate at the start of any visus-desktop automation task to ground yourself in the available tools, safety conventions, and the recommended flow.
---

# Using Visus Desktop

You have access to the visus-desktop MCP server (`visus-mcp`). It exposes **41 tools** that cover desktop GUI automation, OCR, image matching, native (Win32/UIA) targeting, **no-pixel native RPA**, a **smart cascade** (`smart_click`/`smart_find` — try native → image → OCR → coordinates, configurable order), process / window management, clipboard, file waits, session record/replay, and HTML reporting.

## What this MCP gives you

| Group | Tools |
|---|---|
| **Find / click** | `find_text`, `click_text`, `find_image`, `click_image`, `click_at`, `hybrid_find` |
| **Keyboard** | `type_text`, `keyboard_command` |
| **Screen / monitors** | `take_screenshot` (base64), `save_screenshot` (to disk — for find_image templates), `capture_element` (locate-by-text/native/region → save template + annotated → optional click), `get_monitors`, `wait_for_stable_screen` |
| **Files / clipboard** | `wait_for_file`, `wait_for_file_stable`, `get_clipboard`, `copy_to_clipboard`, `extract_text_from_region` *(use `return_full_data=true` for boxes + scores)* |
| **Process / window** | `launch`, `find_process`, `kill_process`, `focus_window`, `maximize_window`, `minimize_window`, `close_window` |
| **Smart cascade** | `smart_click` / `smart_find` — one call tries **native → image → OCR → coordinates** in order (pass `order=[...]` to force/reorder). The simplest robust way to click something when you're not sure which technique fits. |
| **Native RPA (no pixel)** | `native_dump_tree` (read the UI structure), `native_click`, `native_set_text`, `native_get_text`, `native_get_state`, `native_wait` — operate accessible apps by control, immune to theme/DPI/resolution/language. Falls flat on non-accessible UIs (Java Swing) → use OCR there. |
| **Task lists** | `execute_tasks` |
| **Sessions / reports** | `start_recording`, `stop_recording`, `replay_session`, `render_report` |
| **Diagnostics** | `doctor` |
| **Configuration** | `configure` |

## The mental model

0. **Native RPA first when the app is accessible.** Before any pixel work, try `native_dump_tree(window=...)` to *see* the control tree. If it returns controls, prefer `native_click` / `native_set_text` / `native_get_text` / `native_wait` — operating by control (no pixel) is the most robust automation: immune to theme, DPI, resolution, language, window position, and overlapping windows. If `native_dump_tree` returns `[]` (non-accessible UI: Java Swing, some Electron), fall back to the pixel path below.
1. **Targeting (pixel path)**: prefer `hybrid_find(name=…)` — it tries native (pywinauto), then OCR, then template image, transparently. Only drop to the specific layer (`find_text`, `find_image`) when you know which one fits.
2. **Prefer `capture_element(auto=...)` for click steps**: instead of guessing a screenshot region and eyeballing coordinates (error-prone — you can grab the wrong button), call `capture_element(label="...", auto="Salvar", click=True)`. `auto=` tries **Win32 menu → OCR → UIA directed** in order: native apps get the instant pixel-exact Win32/UIA rect; anything else (Java Swing, Electron, remote desktop) falls back to OCR automatically. It saves a reusable template to `visus-elements/<label>.png` + an annotated screenshot showing exactly what matched, and clicks the center. `located_by` in the result tells you which strategy won. Pass `window="App Title"` to scope to a specific window even when it's not focused. Walk a menu step-by-step this way (`auto="Arquivo"` → `auto="Salvar como"`). Never hand-crop a region just to find a button.
3. **Verify before clicking** (when not using `capture_element`): call a find tool, inspect the returned `{x, y, width, height}` dict, then click. Never blind-click coordinates unless the user gave them to you.
3. **Wait deliberately**: between any visible change and the next find, call `wait_for_stable_screen` (UI redraw) or `wait_for_file_stable` (downloads). Hard-coded `sleep` is a smell.
4. **Record troublesome flows**: `start_recording('out.zip')` → `execute_tasks([...])` → `stop_recording()` → `render_report('out.zip', 'report.html')`. The HTML report has timing + screenshots and is the right artifact to send a human when a flow fails.

## Recommended sequence for any new task

1. `doctor()` — verify Tesseract, display, pywinauto, dependencies are healthy.
2. `take_screenshot()` once — orient yourself; you have the dimensions and current state.
3. If the user named a specific window: `focus_window(title)` so subsequent finds operate on the right surface.
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

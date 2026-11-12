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
and end‑to‑end UI automation on **Windows** and **Linux** (see [Platform support](#platform-support)
for the few Windows‑only features).

> **Part of the Visus family.** `visus-desktop` (import root `visus.desktop`) is the first module of
> the planned **Visus** automation ecosystem, designed to sit alongside future `visus.web` (browser
> automation) and a cloud RPA orchestrator under one namespace.

---

## Table of contents

- [Features](#features)
- [Platform support](#platform-support)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage guide](#usage-guide)
  - [Run report (`rpa`)](#run-report-rpa)
  - [Find & click text (OCR)](#find--click-text-ocr)
  - [Find & click images](#find--click-images)
  - [Find all / find multiple](#find-all--find-multiple)
  - [Image map (register images by name)](#image-map-register-images-by-name)
  - [Relative images](#relative-images)
  - [Coordinates, typing & keyboard](#coordinates-typing--keyboard)
  - [Named keyboard shortcuts](#named-keyboard-shortcuts)
  - [Mouse extras (scroll, drag, triple‑click)](#mouse-extras-scroll-drag-triple-click)
  - [Coordinate helpers](#coordinate-helpers)
  - [Text extraction](#text-extraction)
  - [Task‑list automation](#task-list-automation)
  - [Backtracking sessions](#backtracking-sessions)
  - [Wait parameters](#wait-parameters)
  - [Virtual mouse](#virtual-mouse)
  - [Visual overlay](#visual-overlay)
  - [Native (accessibility) automation](#native-accessibility-automation)
  - [Process management](#process-management)
  - [Window management](#window-management)
  - [Screen capture](#screen-capture)
  - [Clipboard](#clipboard)
  - [Waiting for files](#waiting-for-files)
  - [Opening a browser](#opening-a-browser)
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

- **🎯 Fast window targeting** — `ensure_window(process="app.exe")` answers, in
  milliseconds, "is the app open / minimized / where?" and brings it to the
  front. Match by **process** (no title false‑positives). Always the first
  step of a reliable automation. Plus `list_windows` / `get_window`.
- **🧠 Smart cascade** — `smart_find` / `smart_click` try **native → image →
  OCR → coordinates** in a single call (order configurable) and report which
  technique won. The simplest robust way to "find/click this".
- **📸 Coordinate‑free capture** — `capture_element(auto="Save", window=...)`
  locates an element (Win32 menu → OCR → UIA), saves a **reusable PNG
  template + an annotated screenshot**, and can click it — build an
  image‑based flow without ever eyeballing coordinates.
- **🌳 Native RPA (no pixels)** *(Windows)* — read the accessibility tree
  (`native_dump_tree`) and act by control (`native_click`, `native_set_text`,
  `native_get_text`, `native_get_state`, `native_wait`). Immune to
  theme/DPI/resolution/language; degrades to OCR on non‑accessible UIs.
- **🎬 Run report in one line** — `with rpa("name", open_report=True) as bot:`
  records every action (duration, OK/FAILED + reason, a screenshot with the
  target boxed, its logs) and writes `run.zip` + a single‑file `report.html`,
  even when a step fails — the same `rpa()` as `visus.web`. For manual control:
  `Session.start_recording` + `Session.write_report`. See [Run report](#run-report-rpa).
- **🤖 MCP server** — expose all 57 tools to AI agents (Claude Code/Desktop,
  Cursor) via the `visus-mcp` command. See [Drive it from any MCP agent](#drive-it-from-any-mcp-agent).
- **⌨️ Visus CLI Pro** — the `visus` command mirrors the whole surface in the
  shell (`--json` everywhere, interactive `repl`). See [docs/cli.md](docs/cli.md).
- **🔎 OCR text search & click** — find on‑screen text with Tesseract and click it, with character
  filtering (`letters` / `numbers` / `both`) and occurrence selection.
- **🖼️ Image detection & click** — locate UI elements by template image, with adjustable confidence
  and optional automatic scale variations for resolution‑independent matching. Find a *single* match,
  *all* matches (`find_all`), or *several* templates at once (`find_multiple`).
- **🏷️ Image map** — register images under friendly labels once (`register_image`) and refer to them
  by name everywhere; `find_image` / `click_image` accept either a label or a path.
- **🎯 Relative‑image detection** — find a target image *near* a unique anchor image (great when many
  identical buttons exist on screen).
- **⌨️ Typing & keyboard commands** — type text (with special sequences like `{ctrl}a`, `{del}`,
  `{tab}`, `{enter}`), send named shortcuts such as `Ctrl+S`, `F7`, `Alt+Tab`, and use expressive
  named methods (`enter()`, `control_c()`, `key_f5()`, …) plus modifier primitives (`hold_shift`,
  `key_combo`).
- **🖱️ Mouse extras** — `scroll`, `drag`, `triple_click`, and a lightly humanized `move_random`.
- **📋 Task‑list automation** — describe a whole workflow as a list of dictionaries and run it with a
  single `execute_tasks` call.
- **↩️ Smart backtracking** — when a step fails, re‑run the previous step and retry, both inside task
  lists and between individual method calls.
- **⏳ Wait parameters** — wait for an element to appear or disappear (`wait_until_found`,
  `wait_until_disappears`, `wait_timeout`).
- **🪟 Native (accessibility) automation** *(Windows)* — connect to a running app and drive its
  windows and controls through UIA/Win32 (`connect_to_app`, `find_app_window`, `find_app_element`).
- **🧩 Process & window control** — launch apps, find/kill processes, and focus/maximize/minimize/close
  windows (window management is Windows‑only for now).
- **🖼️ Screen capture** — fast multi‑monitor screenshots via `mss` (`take_screenshot`,
  `save_screenshot`, `get_display_size`) with an automatic `pyautogui` fallback.
- **📋 Clipboard & file waits** — read/write the clipboard (`copy`, `paste`) and wait for files to
  appear or finish downloading (`wait_for_file`, `wait_for_file_stable`).
- **🖱️ Virtual mouse** — perform clicks **without moving the physical cursor** (`use_virtual_mouse`),
  so automations don't fight you for the mouse (best on Windows; falls back to a physical click
  elsewhere).
- **🟥 Visual overlay** — draw a colored rectangle over the target before clicking — perfect for
  debugging and demos.
- **🧠 Multi‑technique OCR** — a preprocessing pipeline (HSV/LAB, masking, thresholding, and more)
  improves recognition on tricky UIs.
- **♻️ Backward compatible** — drop‑in aliases (`BotVision`, `limpar_texto`) for code written against
  `bot-vision-suite`.
- **🏷️ Typed** — ships a `py.typed` marker for type checkers.

---

## Platform support

Visus Desktop runs on **Windows** and **Linux**. Most capabilities are cross‑platform; a small number
of features are Windows‑only for now.

| Capability | Windows | Linux | Notes |
|------------|:-------:|:-----:|-------|
| OCR (text search/extract) | ✅ | ✅ | Requires Tesseract OCR. |
| Image matching (`find_image`, `find_all`, `find_multiple`, relative images) | ✅ | ✅ | |
| Mouse & keyboard input, typing, named shortcuts | ✅ | ✅ | |
| Screen capture (`take_screenshot`, `save_screenshot`, `get_display_size`) | ✅ | ✅ | Uses `mss` (multi‑monitor) with a `pyautogui` fallback. |
| Clipboard (`copy`, `paste`, `get_clipboard`) | ✅ | ✅ | On Linux needs `xclip` (or `xsel`). |
| Process management (`launch`, `find_process`, `kill_process`, …) | ✅ | ✅ | Uses `psutil`. |
| File waits (`wait_for_file`, `wait_for_file_stable`) | ✅ | ✅ | |
| Task lists, backtracking, wait parameters | ✅ | ✅ | |
| Visual overlay | ✅ | ✅ | Needs a Tk display (`python3-tk` on Linux). |
| Virtual mouse (`use_virtual_mouse`) | ✅ | ⚠️ | Non‑intrusive (no cursor movement) on Windows; **falls back to a physical click** elsewhere. |
| Native / accessibility automation (`connect_to_app`, `find_app_window`, `find_app_element`) | ✅ | ❌ | Windows‑only (pywinauto). Raises `NotSupportedOnThisOS` on other platforms; a Linux backend via AT‑SPI is planned. |
| Window management (`focus_window`, `maximize_window`, `minimize_window`, `close_window`) | ✅ | ❌ | Windows‑only (pywin32). Raises `NotSupportedOnThisOS` on other platforms; a Linux backend via xdotool/wmctrl is planned. |

> **Linux system dependencies.** Beyond the Python packages, install the OS tools the cross‑platform
> features rely on:
>
> ```bash
> sudo apt-get install tesseract-ocr scrot xclip python3-tk
> ```
>
> Native automation and window management are not available on Linux yet — they raise
> `NotSupportedOnThisOS` so you can branch on platform with a clear, actionable error.

---

## Requirements

- **Python 3.8+**
- **[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed on the system** — this
  is a hard requirement; Visus Desktop shells out to the Tesseract binary for OCR.
- Core Python dependencies are installed automatically: `PyAutoGUI`, `pytesseract`, `opencv-python`,
  `Pillow`, `numpy`, `pyperclip`, `psutil`, `mss` (plus `pywin32` on Windows).

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
pip install "visus-desktop[native]"       # pywinauto (native/accessibility + native RPA, Windows)
pip install "visus-desktop[mcp]"          # MCP server for AI agents (the visus-mcp command)
pip install "visus-desktop[rapidocr]"     # ONNX OCR backend (no Tesseract install needed)
```

The `visus` command-line tool (**Visus CLI Pro**) is installed with the core
package — no extra needed. The MCP server needs the `[mcp]` extra.

On **Linux**, also install the system tools the cross‑platform features need:

```bash
sudo apt-get install tesseract-ocr scrot xclip python3-tk
```

See [docs/installation.md](docs/installation.md) for detailed, per‑OS instructions and
troubleshooting.

---

## Quickstart

```python
from visus.desktop import rpa

with rpa("login", open_report=True) as bot:
    bot.click_text("Login")              # find on-screen text via OCR and click it
    bot.click_image("save_button.png")   # find a UI element by template image and click it
    bot.type_text("hello world")         # type into the focused field
```

On exit you get `./visus-runs/login-<timestamp>/run.zip` + `report.html` (opened in
the browser), and a summary on the console. Without the report, use the bot directly:

```python
from visus.desktop import VisusBot

bot = VisusBot()
bot.click_text("Login")
```

Restricting the search to a screen `region` (faster and more reliable):

```python
from visus.desktop import VisusBot

bot = VisusBot()

# region is (x, y, width, height) — x, y is the top-left corner
if bot.find_text("Username", region=(100, 100, 500, 300), filter_type="letters"):
    bot.click_text("Username", region=(100, 100, 500, 300), sendtext="admin")
```

### Drive it from any MCP agent

`visus-desktop` ships a **Model Context Protocol** server exposing **57 tools**. Install the extra and wire it into Claude Desktop / Code / Cursor — your agent can drive desktop apps end to end. The server also ships an `instructions` preamble and per‑tool docstrings that teach the agent *when and how* to use each tool, so it never has to read source.

```bash
pip install 'visus-desktop[mcp]'
```

**Tool groups:**

| Group | Tools |
|---|---|
| Targeting | `ensure_window` ★, `list_windows`, `get_window` |
| Find / click | `find_text`, `click_text`, `find_all_text`, `find_image`, `click_image`, `find_all`, `find_multiple`, `find_relative_image`, `click_relative_image`, `click_at`, `hybrid_find` |
| Smart / capture | `smart_find`, `smart_click`, `capture_element` |
| Native RPA | `native_dump_tree`, `native_click`, `native_set_text`, `native_get_text`, `native_get_state`, `native_wait` |
| Keyboard | `type_text`, `keyboard_command` |
| Mouse | `drag`, `scroll`, `triple_click`, `move_random`, `mouse_down`, `mouse_up` |
| Screen | `take_screenshot`, `save_screenshot`, `get_monitors`, `get_display_size`, `wait_for_stable_screen` |
| Files / clipboard | `wait_for_file`, `wait_for_file_stable`, `get_clipboard`, `copy_to_clipboard`, `extract_text_from_region` |
| Process / window | `launch`, `find_process`, `is_process_running`, `kill_process`, `focus_window`, `maximize_window`, `minimize_window`, `close_window` |
| Task lists | `execute_tasks` |
| Sessions | `start_recording`, `stop_recording`, `replay_session`, `render_report` |
| Diagnostics | `doctor`, `configure` |

**Recommended agent flow:** `ensure_window(process=…)` → `native_dump_tree` (if accessible, act natively) **or** `capture_element(auto=…, click=True)` / `smart_click` → wrap in `start_recording` / `stop_recording` → `render_report`.

```jsonc
// claude_desktop_config.json (or ~/.claude/settings.json for Claude Code)
{
  "mcpServers": {
    "visus-desktop": { "command": "visus-mcp" }
  }
}
```

See [`docs/mcp.md`](docs/mcp.md) for the full tool reference (all 57 tools, every parameter), and [`skills/`](src/visus/desktop/skills/) for ready-to-use playbooks (login forms, table scraping, captchas, downloads, file dialogs, record/replay). The agent-facing playbook is [`skills/using-visus-desktop.md`](src/visus/desktop/skills/using-visus-desktop.md).

### Or drive it from the shell — Visus CLI Pro

The `visus` command mirrors the automation surface in the terminal (great for
scripting, cron, and CI). Every command takes `--json` for machine-readable
output:

```bash
visus smart click --query "Login" --dry-run     # resolve target, no input
visus text find-all "Total" --ocr rapidocr --json # every OCR match, pick a backend
visus native dump-tree --window "Notepad" --json # see the control tree
visus capture save --auto "Salvar" --click       # coordinate-free capture+click
visus repl                                        # interactive shell
```

Run `visus --help` (or `visus <group> --help`) for inline help. The agent-facing
playbook lives in [`skills/using-visus-cli.md`](src/visus/desktop/skills/using-visus-cli.md) and the
full reference in [`docs/cli.md`](docs/cli.md).

<details>
<summary><b>Full command reference — all 50 commands</b> (click to expand)</summary>

Notation: `ARG` = required positional · `ARG?` = optional · `ARG…` = variadic ·
`--flag` = boolean · `--opt=<type>` = takes a value. Nearly every command also
accepts `--json` (machine-readable output); exit code is `0` on success, `1` on
a failed operation, `2` on a usage error.

### All commands at a glance (50)

| Command | Parameters | What it does |
|---|---|---|
| `visus smart find` | `--query=<text> --image=<text> --coords=<text> --window=<text> --pid=<int> --control-type=<text> --auto-id=<text> --region=<text> --confidence=<float> --confidence-threshold=<float> --order=<text> --timeout=<float> --json` | Locate a target via the cascade (native→image→OCR→coords); report which won. |
| `visus smart click` | *(smart find opts)* `--button=<choice> --retries=<int> --delay=<float> --dry-run --json` | Same cascade, then click the winner. |
| `visus text find` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --occurrence=<int> --word --max-attempts=<int> --backtrack --wait-until-found --wait-until-disappears --wait-timeout=<int> --ocr=<choice> --json` | Find on-screen text via OCR; print its box (no click). |
| `visus text click` | *(text find opts)* `--word --button=<choice> --delay=<float> --sendtext=<text> --json` | Find on-screen text via OCR and click its center. |
| `visus text find-all` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --overlay/--no-overlay --color=<text> --duration=<int> --width=<int> --word --ocr=<choice> --json` | List EVERY occurrence of the text (reading order) + draw a numbered overlay (`--word` = just the word's box). |
| `visus text show` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --color=<text> --duration=<int> --width=<int> --word --ocr=<choice> --json` | Overlay every occurrence on screen, numbered. |
| `visus image find` | `IMAGE_PATH --region=<text> --confidence=<float> --specific/--no-specific --occurrence=<int> --backtrack --max-attempts=<int> --wait-until-found --wait-until-disappears --wait-timeout=<int> --json` | Find a template PNG; print its box (no click). |
| `visus image click` | *(image find opts)* `--button=<choice> --delay=<float> --sendtext=<text> --json` | Find a template PNG and click its center. |
| `visus image find-all` | `IMAGE_PATH --region=<text> --confidence=<float> --json` | Find EVERY occurrence of one template PNG. |
| `visus image find-multiple` | `IMAGE_PATHS… --region=<text> --confidence=<float> --json` | First match of several templates in one call. |
| `visus image relative` | `ANCHOR_IMAGE TARGET_IMAGE --max-distance=<int> --confidence=<float> --target-region=<text> --click --button=<choice> --delay=<float> --sendtext=<text> --backtrack --max-attempts=<int> --wait-until-found --wait-until-disappears --wait-timeout=<int> --json` | Find/click a target template near a unique anchor. |
| `visus mouse click` | `X Y --width=<int> --height=<int> --button=<choice> --delay=<float> --json` | Click at absolute coordinates (last resort). |
| `visus mouse scroll` | `AMOUNT --x=<int> --y=<int> --json` | Scroll the wheel (positive = up, negative = down). |
| `visus mouse drag` | `X1 Y1 X2 Y2 --duration=<float> --button=<choice> --json` | Drag from (X1,Y1) to (X2,Y2). |
| `visus mouse triple-click` | `--x=<int> --y=<int> --interval=<float> --json` | Triple-click (select a line/paragraph). |
| `visus mouse move` | `X Y --max-offset=<int> --duration=<float> --json` | Move the cursor with a light human jitter. |
| `visus mouse down` | `--x=<int> --y=<int> --button=<choice> --json` | Press a button without releasing (pair with `up`). |
| `visus mouse up` | `--x=<int> --y=<int> --button=<choice> --json` | Release a held button. |
| `visus type` | `TEXT --interval=<float> --delay=<float> --backtrack --json` | Type into the focused field (`{ctrl}a {tab} {enter}` tokens). |
| `visus key` | `COMMAND --delay=<float> --backtrack --json` | Press a key/chord (case-sensitive, e.g. `Ctrl+S`). |
| `visus keys` | `--json` | List every valid `key` token. |
| `visus native dump-tree` | `--window=<text> --pid=<int> --max-depth=<int> --timeout=<float> --backend=<choice> --json` | Print the accessibility control tree. |
| `visus native click` | `--window=<text> --pid=<int> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<int> --backend=<choice> --button=<text> --double --method=<choice> --timeout=<float> --retries=<int> --delay=<float> --dry-run --json` | Click a control by selector (no pixels). |
| `visus native set-text` | `TEXT --window=<text> --pid=<int> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<int> --backend=<choice> --timeout=<float> --retries=<int> --delay=<float> --dry-run --json` | Set an editable control's text. |
| `visus native get-text` | `--window=<text> --pid=<int> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<int> --backend=<choice> --timeout=<float> --json` | Read a control's text/value. |
| `visus native get-state` | *(native selectors)* `--timeout=<float> --json` | Snapshot exists/visible/enabled/checked/value/rect. |
| `visus native wait` | *(native selectors)* `--state=<choice> --timeout=<float> --poll-interval=<float> --json` | Wait until a control reaches a state. |
| `visus capture` | `LABEL --auto=<text> --text=<text> --native=<text> --region=<text> --window=<text> --search-region=<text> --click --mouse-button=<text> --padding=<int> --confidence-threshold=<float> --native-timeout=<float> --elements-dir=<text> --dry-run --json` | Locate an element → save template + annotated → optional click. |
| `visus screenshot` | `PATH? --region=<text> --monitor=<int> --base64 --json` | Capture the screen to a PNG (or base64 with `--base64`). |
| `visus monitors` | `--json` | List connected monitors (the `--monitor` index). |
| `visus display-size` | `--json` | Print the primary display size. |
| `visus window ensure` | `--title=<text> --process=<text> --no-show --no-foreground --json` | **Call first**: is the app open/minimized? + bring to front. |
| `visus window list` | `--title=<text> --process=<text> --json` | List visible windows (read-only). |
| `visus window get` | `TITLE --json` | Resolve a window's rect/pid/hwnd (no focus). |
| `visus window focus` | `TITLE --json` | Bring a window to the foreground. |
| `visus window maximize` | `TITLE --json` | Maximize a window. |
| `visus window minimize` | `TITLE --json` | Minimize a window. |
| `visus window close` | `TITLE --yes --json` | Close a window (destructive — needs `--yes`). |
| `visus process launch` | `COMMAND ARGS…? --json` | Launch a process; returns `{pid, command}`. |
| `visus process find` | `NAME --json` | List processes whose name contains NAME. |
| `visus process is-running` | `NAME --json` | Boolean: is any matching process running? |
| `visus process kill` | `PID --yes --json` | Terminate by PID (destructive — needs `--yes`). |
| `visus clipboard get` | `--json` | Read the clipboard text. |
| `visus clipboard set` | `TEXT --json` | Put TEXT on the clipboard. |
| `visus configure` | `CONFIG? --set=<KEY=VALUE>… --dry-run --reset --json` | Show / set+persist / reset the CLI config. |
| `visus doctor` | `--json` | Check the environment (Tesseract, display, deps, pywinauto). |
| `visus new` | `PATH --force` | Scaffold a new bot project. |
| `visus run` | `SCRIPT` | Run a Python script with the active interpreter. |
| `visus report` | `ZIP_PATH --html=<file>` | Render a recorded session zip to HTML. |
| `visus repl` | — | Open the interactive Visus CLI Pro shell. |

</details>

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

### Run report (`rpa`)

`rpa()` is the same contract as `visus.web`'s: you write only the automation, it
handles the bot, the recording, the HTML report and the summary.

```python
from visus.desktop import rpa

with rpa("pedido", app="notepad", window="Bloco de notas", open_report=True) as bot:
    bot.type_text("Pedido 123")
    bot.type_text(senha, secret=True)          # typed, shown as •••••• in the report
    total = bot.extract_text_from_region(region=(1196, 507, 109, 20))
    bot.keyboard_command("Ctrl+S")
```

- **Every action is a step** — `click_text`, `click_image`, `click_at`,
  `click_coordinates`, `click_relative_image`, `type_text`, `keyboard_command` (and
  `enter()`, `tab()`…), `open_app`, `extract_text_from_region` (the text read shows
  in the report), `scroll`, `drag`, `triple_click` and every task of `execute_tasks`:
  its duration, OK/FAILED with the reason, a screenshot right after it (target boxed)
  and the logs it produced. One run id for all of them.
- **Anything else** — wrap it in `with bot.step("label"):` (a `native_click`, a
  `smart_click`, your own check) and it becomes one step too.
- **A failed action stops the run** (`stop_on_failure=True`): the step is in the
  report with a failure screenshot, the summary says why, and the script exits with
  code 1 (`reraise=True` raises `ActionFailedError` instead). An `assert` or an
  unexpected error in your script is added as the last FAILED step. For an "is it on
  screen?" check use `find_text` / `find_image` — they never stop the run — or pass
  `stop_on_failure=False` to get the old `True`/`False` returns.
- **Options** — `config=` (the usual `VisusBot` settings), `app=` / `window=` /
  `timeout=` (open the app and wait for its window as the first step), `outdir=`
  (default `./visus-runs/<name>-<timestamp>/`), `report=`, `summary=`,
  `open_report=`, `screenshots=` (a screenshot per step; failures always get one).
- **Under RunPilot** (`RUNPILOT_RUN_TOKEN`) every step streams live to the
  orchestrator instead, and no local files are written.

Manual control (several bots, your own paths) — no `log_format="json"` needed anymore:

```python
from visus.desktop import Session, VisusBot

bot = VisusBot()
with Session.start_recording("run.zip", name="pedido") as rec:
    bot.start_task_session()          # direct calls are recorded from here
    bot.click_text("Login")
    bot.end_task_session()
print(rec.summary())
Session.write_report("run.zip", "report.html")
```

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

When the same label appears more than once, list **every** occurrence (instead
of just the first) and pick the right one by index:

```python
# find_all_text -> [(x, y, width, height, confidence), ...] in reading order
for i, (x, y, w, h, conf) in enumerate(bot.find_all_text("Delete"), start=1):
    print(f"#{i} at ({x}, {y}) conf={conf:.0f}%")

bot.click_text("Delete", occurrence=2)   # click the second match

# show_text_occurrences -> same list, plus a numbered click-through overlay
# (1, 2, 3 …) drawn on screen for `duration_ms`. Great for debugging a miss.
bot.show_text_occurrences("Delete", duration_ms=4000, color="green")
```

### Find & click images

```python
bot = VisusBot()

location = bot.find_image("button.png", region=(100, 100, 300, 200), confidence=0.9)

bot.click_image(
    "button.png",
    confidence=0.9,        # 0.0–1.0
    specific=True,         # True: search the region; False: full screen + scale variations
    occurrence=1,          # which match to act on (1 = first), reading order top→bottom/left→right
    mouse_button="double",
    delay=1,
)
```

`specific=False` also tries scaled versions of the template, which helps when the UI renders at a
different resolution/DPI. You can pass an explicit `scales=[1.0, 0.95, 1.05]` list too.

When the **same template appears more than once** on screen (grid rows, a toolbar of identical
icons), list every match first and pick the right one by index with `occurrence` — exactly like
`click_text`:

```python
# find_all -> every box, in reading order (empty list if none found)
for i, box in enumerate(bot.find_all("row_icon.png"), start=1):
    print(f"#{i} at {box}")

bot.find_image("row_icon.png", occurrence=2)    # box of the second match
bot.click_image("row_icon.png", occurrence=2)   # click the second match
```

`find_image` / `click_image` accept either a **registered label** or a **file path** for the image —
see [Image map](#image-map-register-images-by-name).

### Find all / find multiple

Locate *every* occurrence of one template, or the first match of *several* templates in a single call.
Both return plain `(left, top, width, height)` boxes and accept registered labels or paths.

```python
bot = VisusBot()

# Every match of one template -> list of boxes (empty list if none found)
boxes = bot.find_all("checkbox.png", region=(0, 0, 1920, 1080), confidence=0.9, grayscale=False)
for box in boxes:
    bot.click_at(box)

# First match of several templates at once
# - pass a list -> keyed by path; or a dict -> keyed by your labels
results = bot.find_multiple(["ok.png", "cancel.png"], confidence=0.9)
results = bot.find_multiple({"ok": "ok.png", "cancel": "cancel.png"})
if results["ok"]:
    bot.click_at(results["ok"])   # value is a box tuple, or None when not found
```

### Image map (register images by name)

Register each template once under a friendly label and refer to it by name throughout your script.
Registration validates that the file exists.

```python
bot = VisusBot()

bot.register_image("save", "assets/save_button.png")
bot.register_images({
    "login": "assets/login.png",
    "logout": "assets/logout.png",
})

bot.get_image("save")             # -> "assets/save_button.png"

# A label works anywhere an image path is accepted
bot.click_image("save")
bot.find_all("login")
```

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

To click at a fixed **coordinate offset** from a single found image (image + coordinate, rather
than two images), use `click_relative`:

```python
bot = VisusBot()

# Find "label.png", then click 60px to its right and 5px down (from its top-left)
bot.click_relative("label.png", x_offset=60, y_offset=5)

# Offset from the image's center instead, with a right-click
bot.click_relative("icon.png", x_offset=0, y_offset=40, centered=True, mouse_button="right")
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

### Named keyboard shortcuts

In addition to the `keyboard_command("Ctrl+C")` string API, `VisusBot` exposes expressive, named
methods. The named methods are **sugar** over `keyboard_command` (the same command map is the single
source of truth), so they read like intentions:

```python
bot = VisusBot()

# Navigation & editing
bot.enter(); bot.tab(); bot.shift_tab(); bot.esc(); bot.space()
bot.backspace(); bot.delete()
bot.key_up(); bot.key_down(); bot.key_left(); bot.key_right()
bot.page_up(); bot.page_down(); bot.home(); bot.end()

# Function keys F1–F12
bot.key_f1(); bot.key_f5(); bot.key_f12()

# Shortcuts
bot.control_c(); bot.control_v(); bot.control_x(); bot.control_a()
bot.control_s(); bot.control_z(); bot.control_y()
bot.control_f(); bot.control_p()
bot.alt_tab(); bot.alt_f4()
```

Low‑level primitives talk to `pyautogui` directly (they are not part of the named command map):

```python
bot.type_key("a")                 # press a single key by its pyautogui name
bot.key_combo("ctrl", "alt", "del")  # press an arbitrary key combination

# Hold/release a modifier across several presses
bot.hold_shift()
bot.key_down(); bot.key_down()
bot.release_shift()

bot.hold_ctrl(); bot.type_key("a"); bot.release_ctrl()
```

### Mouse extras (scroll, drag, triple‑click)

```python
bot = VisusBot()

bot.scroll(3)                          # scroll up 3 clicks (negative = down)
bot.scroll(-3, x=400, y=300)           # move to (400, 300) first, then scroll down

bot.drag(100, 100, 400, 300, duration=0.5, button="left")   # press, drag, release
bot.triple_click(250, 180, interval=0.05)                   # e.g. select a whole line
bot.move_random(640, 480, max_offset=3, duration=0.2)       # lightly "human" move

# Separate press/release for custom press-and-hold patterns (drag is atomic):
bot.mouse_down(200, 200)         # press the left button at (200, 200)
# ... do other things while holding ...
bot.mouse_up()                   # release at the current cursor position
```

### Coordinate helpers

Turn a `(x, y, width, height)` location (as returned by `find_*`) into a click point:

```python
loc = bot.find_image("button.png")    # -> (x, y, width, height) or None
if loc:
    VisusBot.get_element_coords(loc)            # top-left (x, y)
    VisusBot.get_element_coords_centered(loc)   # center (x, y)
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

### Native (accessibility) automation

> **Windows‑only (for now).** These methods drive an application through the Windows accessibility
> layers (UIA/Win32) via [pywinauto](https://pywinauto.readthedocs.io). Install the extra with
> `pip install "visus-desktop[native]"`. On non‑Windows platforms they raise `NotSupportedOnThisOS`.

Unlike OCR/image matching, native automation finds controls by their accessibility properties — so it
keeps working even if the UI repaints or moves. Selectors are passed straight through to pywinauto
(`title`, `title_re`, `auto_id`, `control_type`, `class_name`, `process`, …).

```python
from visus.desktop import VisusBot, Backend

bot = VisusBot()

# Connect to an already-running application (retries until it appears or times out)
bot.connect_to_app(backend=Backend.UIA, timeout=60.0, title_re=".*Notepad")

# Find a top-level window of the connected app
window = bot.find_app_window(timeout=10.0, title_re=".*Notepad")

# Find a child control inside that window by accessibility selectors
edit = bot.find_app_element(from_parent_window=window, control_type="Edit")

# Interact with the control via pywinauto's own API
edit.set_edit_text("Hello from Visus")
```

- `connect_to_app(backend=Backend.UIA, timeout=60.0, **selectors)` — connect and store the app on
  `bot.app`. `backend` is `Backend.UIA` (modern WPF/WinForms/Qt/UWP) or `Backend.WIN32` (classic
  Win32). Raises `NativeError` if the connection cannot be made within `timeout`.
- `find_app_window(timeout=10.0, **selectors)` — return a top‑level window (or `None`). Requires a
  prior `connect_to_app`, otherwise raises `NativeError`.
- `find_app_element(from_parent_window=None, timeout=10.0, **selectors)` — return a control. With
  `from_parent_window` it drills into that window's children; without it, it behaves like
  `find_app_window`.

### Process management

Cross‑platform process helpers (powered by `psutil`):

```python
bot = VisusBot()

bot.launch("notepad.exe")              # open an app or file via the OS default handler

proc = bot.find_process(name="notepad")   # first match by name substring (or pid=...)
bot.is_process_running("notepad")          # -> True / False
bot.kill_process("notepad")                # by name substring, pid, or Process object -> True / False
```

### Window management

> **Windows‑only (for now)** (pywin32). Matching is by a case‑insensitive substring of the window
> title. On non‑Windows platforms these raise `NotSupportedOnThisOS`.

```python
bot = VisusBot()

bot.focus_window("Notepad")      # bring the first matching window to the foreground
bot.maximize_window("Notepad")
bot.minimize_window("Notepad")
bot.close_window("Notepad")      # each returns True if a matching window was found
```

### Screen capture

Fast, multi‑monitor screenshots via `mss`, with an automatic `pyautogui` fallback:

```python
bot = VisusBot()

img = bot.take_screenshot()                          # full primary screen -> PIL.Image
img = bot.take_screenshot(region=(0, 0, 800, 600))   # a region (x, y, width, height)

bot.save_screenshot("shot.png")                      # capture + save -> returns the path
bot.save_screenshot("region.png", region=(0, 0, 800, 600))

width, height = bot.get_display_size()               # primary display size in pixels
```

### Clipboard

```python
bot = VisusBot()

bot.copy("text to place on the clipboard")
text = bot.paste()              # current clipboard contents
text = bot.get_clipboard()      # alias of paste()
```

### Waiting for files

Useful for downloads or output produced by other processes:

```python
bot = VisusBot()

# Wait until the file exists and is readable (polls until timeout)
if bot.wait_for_file("report.pdf", timeout=30, poll_interval=0.5):
    ...

# Wait until the file exists AND its size stops changing (download finished)
if bot.wait_for_file_stable("download.zip", timeout=60, stable_for=1.0):
    ...
```

### Opening a browser

```python
bot = VisusBot()
bot.browse("https://example.com")   # open a URL in the system default browser
```

### Standalone functions

Prefer not to manage an instance? Import functions directly — each creates a temporary bot:

```python
from visus.desktop import find_text, click_text, click_image, execute_tasks, type_text

click_text("Login", region=(0, 0, 800, 600))
click_image("submit.png", confidence=0.9)
click_image("row_icon.png", occurrence=2)   # nth copy when the template repeats
execute_tasks([{"text": "OK"}, {"type": "keyboard_command", "command": "Enter"}])
```

Several capability helpers are also re‑exported at the module level so you can call them as plain
functions without a `VisusBot` instance:

```python
from visus.desktop import (
    find_all, find_multiple,                       # image location
    capture_screen, save_screenshot, get_display_size,  # screen
    copy_to_clipboard, paste, get_clipboard,       # clipboard
    launch, find_process, is_process_running, kill_process,  # process
    focus_window, maximize_window, minimize_window, close_window,  # window (Windows)
    scroll, drag, triple_click, move_random,       # mouse extras
    mouse_down, mouse_up,                          # press-and-hold primitives
    wait_for_file, wait_for_file_stable,           # files
)
```

> **Note:** `copy_to_clipboard` is the module‑level alias of `VisusBot.copy`, and `capture_screen` is
> the module‑level name for `VisusBot.take_screenshot`.

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
| `show_overlay` | `True` | Show overlay before clicks (master toggle). |
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
| `NotSupportedOnThisOS` | A feature (native automation, window management) is not available on the current OS. |

`NativeError` (importable from `visus.desktop`) is raised by the native‑automation helpers when a
connection or element lookup fails. It does **not** subclass `BotVisionError`.

```python
from visus.desktop import VisusBot
from visus.desktop.exceptions import NotSupportedOnThisOS

bot = VisusBot()
try:
    bot.focus_window("Notepad")
except NotSupportedOnThisOS:
    print("Window management is Windows-only for now.")
```

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

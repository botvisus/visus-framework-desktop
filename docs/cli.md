# Visus CLI Pro — full command reference

`visus-desktop` installs the **`visus`** console command (and `visus-doctor`,
`visus-mcp`). It mirrors the automation surface in the shell — ideal for
scripting, cron, and CI. Every command is a thin wrapper over the same library
functions exposed by `from visus.desktop import ...`.

```bash
pip install visus-desktop
visus --help                 # top-level groups
visus <group> --help         # a group's subcommands
visus <group> <cmd> --help   # a command's full flag list
```

## Global conventions

- **`--json`** — every command prints human-readable text by default and a
  machine-readable JSON document when `--json` is passed. **Always pass it when
  parsing output.**
- **Exit codes** — `0` success, `1` operation failed (not found / returned
  false), `2` usage error (bad flags). Branch your scripts on `$?` or
  `$LASTEXITCODE`.
- **`--dry-run`** — on `smart click`, `native click`, `native set-text` and
  `capture` it resolves/locates the target and reports what it *would* do
  without sending any real mouse/keyboard input.
- **`--yes` / `-y`** — destructive commands (`process kill`, `window close`)
  prompt for confirmation interactively and **refuse to run in `--json` mode
  without `--yes`**.
- **`--region X,Y,W,H`** and **`--coords X,Y`** — passed as comma-separated
  integers (no brackets, no spaces): `--region 0,0,1920,1080`.
- **Confidence scales** — image matching uses `--confidence` `0.0–1.0`; OCR uses
  `--confidence-threshold` `0–100`.

---

## All commands at a glance (50)

| Command | Parameters | What it does |
|---|---|---|
| `visus smart find` | `--query=<text> --image=<text> --coords=<text> --window=<text> --pid=<int> --control-type=<text> --auto-id=<text> --region=<text> --confidence=<float> --confidence-threshold=<float> --order=<text> --timeout=<float> --json` | Locate a target via the cascade (native→image→OCR→coords); report which won. |
| `visus smart click` | *(smart find opts)* `--button=<choice> --retries=<int> --delay=<float> --dry-run --json` | Same cascade, then click the winner. |
| `visus text find` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --occurrence=<int> --max-attempts=<int> --backtrack --wait-until-found --wait-until-disappears --wait-timeout=<int> --ocr=<choice> --json` | Find on-screen text via OCR; print its box (no click). |
| `visus text click` | *(text find opts)* `--button=<choice> --delay=<float> --sendtext=<text> --json` | Find on-screen text via OCR and click its center. |
| `visus text find-all` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --ocr=<choice> --json` | List EVERY occurrence of the text (reading order). |
| `visus text show` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --color=<text> --duration=<int> --width=<int> --ocr=<choice> --json` | Overlay every occurrence on screen, numbered. |
| `visus image find` | `IMAGE_PATH --region=<text> --confidence=<float> --specific/--no-specific --backtrack --max-attempts=<int> --wait-until-found --wait-until-disappears --wait-timeout=<int> --json` | Find a template PNG; print its box (no click). |
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
| `visus native dump-tree` | `--window=<text> --pid=<int> --max-depth=<int> --timeout=<float> --json` | Print the accessibility control tree. |
| `visus native click` | `--window=<text> --pid=<int> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<int> --button=<text> --double --method=<choice> --timeout=<float> --retries=<int> --delay=<float> --dry-run --json` | Click a control by selector (no pixels). |
| `visus native set-text` | `TEXT --window=<text> --pid=<int> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<int> --timeout=<float> --retries=<int> --delay=<float> --dry-run --json` | Set an editable control's text. |
| `visus native get-text` | `--window=<text> --pid=<int> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<int> --timeout=<float> --json` | Read a control's text/value. |
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

The sections below document each group in detail (defaults + examples).

---

## `visus smart` — the cascade (native → image → OCR → coordinates)

The "do whatever works" group. Provide whatever you have; each layer is skipped
when its input is missing.

### `visus smart find`
Locate a target and report which method won (no click).

### `visus smart click`
Same cascade, but clicks the winner.

**Shared options** (both subcommands):

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--query` | str | — | Text/title to match (native title + OCR text). |
| `--image` | str | — | Template PNG path. |
| `--coords X,Y` | int,int | — | Fallback absolute coordinates. |
| `--window` | str | — | Window title substring (sharpens native). |
| `--pid` | int | — | Process id (native). |
| `--control-type` | str | — | UIA control type (native). |
| `--auto-id` | str | — | UIA automation id (native). |
| `--region X,Y,W,H` | int×4 | — | Search region for image/OCR. |
| `--confidence` | float | `0.9` | Image-match confidence (0–1). |
| `--confidence-threshold` | float | `75.0` | OCR confidence threshold (0–100). |
| `--order` | csv | — | Override cascade order, e.g. `native,ocr`. |
| `--timeout` | float | `5.0` | Per-method timeout (s). |
| `--json` | flag | off | JSON output. |

`smart click` adds: `--button left\|right\|middle` (default `left`),
`--retries` (int, `0`), `--delay` (float, `0.3`), `--dry-run`.

```bash
visus smart find  --query "Login" --json
visus smart click --query "Salvar" --image btn_salvar.png --window "Bloco" --dry-run
visus smart click --query "OK" --order native,ocr
```

---

## `visus text` — OCR find / click / discovery

| Command | What it does |
|---|---|
| `text find QUERY` | Find text via OCR; print its box (no click). |
| `text click QUERY` | Find text via OCR and click its center. |
| `text find-all QUERY` | List **every** match in reading order (no click). |
| `text show QUERY` | List every match + draw a numbered click-through overlay. |

**Shared options** (all four): `--region X,Y,W,H` (else whole screen),
`--filter letters|numbers|both` (default `both`), `--ocr tesseract|rapidocr`
(default `tesseract`), `--json`.

`find` / `click` add: `--confidence-threshold` (float, 0–100; `find` default
`75`, `click` default = config), `--occurrence N` (int, `1`), and the
**robustness knobs** `--max-attempts` (int, `3`), `--backtrack`,
`--wait-until-found`, `--wait-until-disappears`, `--wait-timeout` (s).

`click` also adds: `--button left|right|double|move_to` (default `left`),
`--delay` (s), `--sendtext TEXT` (type right after clicking).

`find-all` adds `--confidence-threshold` (default = config); `show` adds
`--color` (`red`), `--duration` ms (`3000`), `--width` px (`3`).

JSON: `find` → `{x,y,width,height}`; `find-all`/`show` →
`[{occurrence,x,y,width,height,confidence}, …]`.

```bash
visus text find  "Login" --region 0,0,1920,1080 --json
visus text click "Save"  --occurrence 2 --sendtext "report.xlsx" --ocr rapidocr
visus text click "Next"  --wait-until-found --wait-timeout 10
visus text find-all "Total" --ocr rapidocr --filter numbers --json
visus text show "Login" --duration 4000 --color green
```

---

## `visus image` — template-image find / click / relative

| Command | What it does |
|---|---|
| `image find PATH` | Find a template PNG; print its box (no click). |
| `image click PATH` | Find a template PNG and click its center. |
| `image find-all PATH` | List **every** occurrence of a template PNG. |
| `image find-multiple PATH…` | First match of several templates in one call. |
| `image relative ANCHOR TARGET` | Find/click a target template near a unique anchor. |

`find` / `click` options: `--region X,Y,W,H`, `--confidence` (float 0–1, `0.9`),
`--specific/--no-specific` (default `--specific`: region only; `--no-specific`:
whole screen + scale variations), `--max-attempts` (`3`),
`--wait-until-found`, `--wait-until-disappears`, `--wait-timeout`, `--json`.
`click` adds `--button left|right|double|move_to`, `--delay`, `--sendtext`,
`--backtrack`. `find` adds `--backtrack`.

`relative` options: `--max-distance` (int, `200`), `--confidence` (0–1, `0.9`),
`--target-region X,Y,W,H`, `--click` (else just locate),
`--button`, `--delay`, `--sendtext`, `--backtrack`, `--max-attempts`,
`--wait-until-found`, `--wait-until-disappears`, `--wait-timeout`, `--json`.

`find-all` / `find-multiple` options: `--region`, `--confidence`, `--json`.
`find-multiple` takes one or more PATH args and returns `{path: box|null}`.

```bash
visus image find  save.png --region 0,0,1920,1080 --json
visus image click save.png --confidence 0.85 --button double
visus image find-all row_delete.png --json
visus image find-multiple accept.png decline.png --json
visus image relative cancel.png save.png --max-distance 180 --click
```

---

## `visus mouse` — low-level coordinate gestures

| Command | Args | Key options |
|---|---|---|
| `mouse click X Y` | x, y | `--width`, `--height`, `--button left\|right\|double\|move_to`, `--delay` |
| `mouse scroll AMOUNT` | amount | `--x`, `--y` (move there first) |
| `mouse drag X1 Y1 X2 Y2` | 4 ints | `--duration` (`0.5`), `--button left\|middle\|right` |
| `mouse triple-click` | — | `--x`, `--y`, `--interval` (`0.05`) |
| `mouse move X Y` | x, y | `--max-offset` (`3`), `--duration` (`0.2`) — human jitter |
| `mouse down` / `mouse up` | — | `--x`, `--y`, `--button left\|middle\|right` |

```bash
visus mouse click 640 480 --button double
visus mouse scroll -5 --x 960 --y 540
visus mouse drag 100 200 400 200 --duration 0.8
```

---

## `visus type` / `visus key` / `visus keys` — keyboard

| Command | What it does |
|---|---|
| `type TEXT` | Type into the focused field. `--interval` (`0.05`), `--delay`, `--backtrack`, `--json`. Inline tokens: `{ctrl}a {tab} {enter} {escape}`. |
| `key TOKEN` | Press a key/chord (case-sensitive). `--delay`, `--backtrack`, `--json`. |
| `keys` | List every valid `key` token. `--json`. |

```bash
visus type "admin" --interval 0.02
visus key "Ctrl+S"
visus keys --json
```

---

## `visus native` — no-pixel RPA (accessibility tree)

Operate controls directly through UIA — immune to theme/DPI/resolution/
language. Returns nothing on non-accessible UIs (Java Swing without the Access
Bridge, some Electron); fall back to OCR/image there.

**Selector options** (shared by `click`, `set-text`, `get-text`, `get-state`,
`wait`):

| Option | Type | Meaning |
|---|---|---|
| `--window` | str | Window title substring (else foreground). |
| `--pid` | int | Process id (else foreground). |
| `--title` | str | Control title/name. |
| `--control-type` | str | Button, MenuItem, Edit, … |
| `--auto-id` | str | UIA automation id. |
| `--found-index` | int | Disambiguate multiple matches (0-based). |

### `visus native dump-tree`
Print the control tree. Options: `--window`, `--pid`, `--max-depth` (int, `3`),
`--timeout` (float, `5.0`), `--json`. Each node: `{depth, control_type, title,
auto_id, rect}`.

### `visus native click`
Selector options + `--button` (str, `left`), `--double` (flag),
`--method invoke|click|auto` (default `auto`), `--timeout` (`5.0`),
`--retries` (`0`), `--delay` (`0.3`), `--dry-run`, `--json`.

### `visus native set-text TEXT`
Selector options + `--timeout` (`5.0`), `--retries` (`0`), `--delay` (`0.3`),
`--dry-run`, `--json`.

### `visus native get-text`
Selector options + `--timeout` (`5.0`), `--json`. Prints the control's text.

### `visus native get-state`
Selector options + `--timeout` (`5.0`), `--json`. Returns `{exists, visible,
enabled, checked, value, control_type, rect}`.

### `visus native wait`
Selector options + `--state exists|visible|enabled|ready` (default `exists`),
`--timeout` (`10.0`), `--poll-interval` (`0.3`), `--json`.

```bash
visus native dump-tree --window "Notepad" --json
visus native click --window "Notepad" --control-type MenuItem --title "File"
visus native set-text "hello" --window "Notepad" --control-type Edit
visus native wait --window "Notepad" --control-type Edit --state ready
```

---

## `visus capture` — coordinate-free element capture

Locate a UI element, save a reusable PNG template + an annotated screenshot, and
optionally click it. Provide **exactly one** locator.

```
visus capture LABEL  (one of --auto / --text / --native / --region)
```

| Option | Type | Default | Meaning |
|---|---|---|---|
| `--auto` | str | — | **Recommended.** Win32 menu → OCR → UIA directed. |
| `--text` | str | — | Locate by OCR text only. |
| `--native` | str | — | Locate by directed UIA only. |
| `--region X,Y,W,H` | int×4 | — | You already know the box. |
| `--window` | str | — | Scope to a window title (no focus needed). |
| `--search-region X,Y,W,H` | int×4 | — | Restrict the search area. |
| `--click` | flag | off | Click the located center. |
| `--mouse-button` | str | `left` | Mouse button for `--click`. |
| `--padding` | int | `0` | Padding added around the saved template. |
| `--confidence-threshold` | float | `75.0` | OCR threshold (0–100). |
| `--native-timeout` | float | `5.0` | UIA lookup timeout (s). |
| `--elements-dir` | str | `./visus-elements` | Where templates are written. |
| `--dry-run` | flag | off | Locate only, don't click. |
| `--json` | flag | off | JSON output. |

Returns `{found, label, located_by, box, template_path, annotated_path,
clicked}`.

```bash
visus capture save --auto "Salvar" --window "Bloco de Notas" --click
visus capture total --text "Total" --search-region 0,0,800,600
```

---

## `visus screenshot [PATH]` — capture the screen

Save a PNG to disk (the `find_image` / `capture` template format), or print a
base64 PNG. Options: `--region X,Y,W,H`, `--monitor N` (1-based physical
monitor), `--base64` (print base64 to stdout instead of saving — `PATH`
optional then), `--json`.

```bash
visus screenshot btn.png --region 740,589,78,30
visus screenshot full.png --monitor 2
visus screenshot --base64 --region 0,0,800,600 --json
```

## `visus monitors` / `visus display-size`

- `visus monitors [--json]` — list connected monitors `[{index, x, y, width,
  height, is_primary}]` (the `index` is what `--monitor` expects).
- `visus display-size [--json]` — primary display `{width, height}`.

---

## `visus window` — window management

| Command | Args | Options | Returns |
|---|---|---|---|
| `focus TITLE` | title | `--json` | bool |
| `maximize TITLE` | title | `--json` | bool |
| `minimize TITLE` | title | `--json` | bool |
| `close TITLE` | title | `--yes/-y`, `--json` | bool (destructive) |
| `ensure` | — | `--title`, `--process`, `--no-show`, `--no-foreground`, `--json` | state dict |
| `list` | — | `--title`, `--process`, `--json` | list of windows |
| `get TITLE` | title | `--json` | `{title, pid, hwnd, x, y, width, height}` |

`ensure` is the **fast targeting call** — answers "is the app open / minimized /
where?" and brings it to the front in one go. Prefer `--process` over `--title`
to avoid false-positives. `--no-show` makes it a read-only probe.

```bash
visus window ensure --process notepad.exe --json
visus window list --process chrome.exe --json
visus window close "Untitled - Notepad" --yes
```

---

## `visus process` — process management

| Command | Args | Options | Notes |
|---|---|---|---|
| `launch COMMAND [ARGS…]` | command + varargs | `--json` | Returns `{pid, command}`. |
| `find NAME` | name substring | `--json` | Returns `[{pid, name}, …]`. |
| `is-running NAME` | name substring | `--json` | Boolean; exit 0 if running. |
| `kill PID` | pid (int) | `--yes/-y`, `--json` | Destructive. |

```bash
visus process launch notepad.exe --json
visus process find chrome --json
visus process is-running notepad.exe --json
visus process kill 12345 --yes
```

---

## `visus clipboard` — read / write the clipboard

| Command | Args | Options |
|---|---|---|
| `get` | — | `--json` |
| `set TEXT` | text | `--json` |

```bash
visus clipboard set "hello"
visus clipboard get --json
```

---

## Root commands

### `visus configure [CONFIG] [--set KEY=VALUE]… [--dry-run] [--reset]`
Read, set, or reset the persisted CLI config.

- **`visus configure`** (no input) — print the active config (read-only).
- **`visus configure --set KEY=VALUE`** — set it **and persist it** (no
  separate save step); later commands pick it up. Repeatable; quote-free
  (best on Windows cmd.exe / PowerShell). Values are typed
  (`true`/`false`/`null`/numbers/JSON arrays), else kept as a string.
- **`CONFIG`** — a JSON object, or `@path` to a file (also persisted). Merges
  onto the saved config; `--set` wins over `CONFIG`.
- **`--dry-run`** — preview the result without saving.
- **`--reset`** — delete the saved config (back to library defaults).

Anything you pass is **persisted by default** — each `visus` call is a separate
process, so persistence is the only way settings reach later commands. A
per-command flag (e.g. `text --ocr tesseract`) still overrides the saved value
for that call. Options: `--json`.

The config is saved to a per-user, OS-appropriate location (never the project
folder) — overridable with `$VISUS_CONFIG`:
- **Windows:** `%APPDATA%\visus\config.json`
- **macOS:** `~/Library/Application Support/visus/config.json`
- **Linux:** `$XDG_CONFIG_HOME/visus/config.json` (else `~/.config/visus/config.json`)

```bash
visus configure                                          # show active config
visus configure --set ocr_backend=rapidocr              # set + persist (one step)
visus text find-all "Total"                              # now uses rapidocr
visus configure --set ocr_languages='["eng","por"]'
visus configure @config.json                             # load a file and persist it
visus configure --set show_overlay=false --dry-run       # preview, don't save
visus configure --reset                                  # back to defaults
```

### `visus doctor`
Run environment health checks (Tesseract, display, deps, pywinauto). Options:
`--json`. Non-zero exit means at least one check failed. (Also installed as the
standalone `visus-doctor` command.)

### `visus new PATH`
Scaffold a new bot project (`tasks.py`, `README.md`, `.gitignore`). Option:
`--force` to overwrite an existing directory.

### `visus run SCRIPT`
Run a Python script with the active interpreter (propagates its exit code).

### `visus report ZIP_PATH --html OUT.html`
Render a recorded session zip to a single-file HTML report.

### `visus repl`
Interactive shell over the same commands.

```bash
visus new ./mybot
visus run mybot/tasks.py
visus report run.zip --html run.html
```

---

## Scripting example

```bash
#!/usr/bin/env bash
set -euo pipefail
visus window ensure --process notepad.exe --json
visus native wait --window "Notepad" --control-type Edit --state ready --json
visus native set-text "hello world" --window "Notepad" --control-type Edit
visus capture save --auto "Save" --window "Notepad" --click
```

See also: the MCP reference at [`mcp.md`](mcp.md) and the agent playbook at
[`../skills/using-visus-cli.md`](../skills/using-visus-cli.md).

---
name: using-visus-cli
description: Drive visus-desktop from the shell with the Visus CLI Pro (`visus`) command. Use for scripting, cron, CI, or any time you want shell commands instead of the MCP server.
when_to_use: Activate when the user wants to automate a desktop app from a terminal/script (not interactively via MCP), or asks how to use the `visus` command.
---

# Using Visus CLI Pro

`visus-desktop` ships **Visus CLI Pro** — the `visus` command. It mirrors the
MCP tool surface in the shell, as a thin Click wrapper over the same library
functions. Prefer it for **scripting, cron, and CI**; prefer the **MCP server**
when an agent is driving interactively.

## The one rule: `--json`

Every command prints human text by default and machine JSON with `--json`.
**Always pass `--json` when you will parse the output.** Exit codes: `0`
success, `1` operation failed (not found / false), `2` usage error.

```bash
visus smart find --query "Login" --json   # {"found": true, "box": {...}, "method": "native", "tried": [...]}
```

## Command groups (mirror of the MCP tools)

50 commands total; `visus <group> <cmd> --help` shows every flag. Full
reference: `docs/cli.md`.

| Group | Commands |
|---|---|
| `visus smart` | `find`, `click` — cascade native → image → OCR → coordinates (`--order` to force/reorder; `--dry-run` to resolve only) |
| `visus text` | `find`, `click`, `find-all`, `show` — OCR find/click a label, list every occurrence, or overlay them numbered (`--ocr tesseract\|rapidocr`) |
| `visus image` | `find`, `click`, `find-all`, `find-multiple`, `relative` — template-PNG targeting |
| `visus native` | `dump-tree`, `click`, `set-text`, `get-text`, `get-state`, `wait` — no-pixel RPA by directed selector |
| `visus mouse` | `click`, `scroll`, `drag`, `triple-click`, `move`, `down`, `up` — coordinate gestures |
| `visus type` / `key` / `keys` | type text into the focused field / press a key chord / list valid tokens |
| `visus capture` | coordinate-free capture by `--auto`/`--text`/`--native`/`--region` → saves template + annotated, optional `--click` |
| `visus window` | `ensure` (★ call first), `list`, `get`, `focus`, `maximize`, `minimize`, `close` |
| `visus process` | `launch`, `find`, `is-running`, `kill` |
| `visus clipboard` | `get`, `set` |
| `visus` (root) | `screenshot` (`--base64`), `monitors`, `display-size`, `configure`, `doctor`, `new`, `run`, `report`, `repl` |

Find/click commands (`text`/`image`) share the robustness flags
`--wait-until-found`, `--wait-until-disappears`, `--wait-timeout`,
`--backtrack`, `--max-attempts`, plus `--sendtext`/`--occurrence`/`--filter`
where relevant.

### `visus text` — find all OCR matches / overlay them

When the same label appears more than once, list every match first, then act
on the right one by index. Choose the OCR engine with `--ocr`.

```bash
# List every occurrence (reading order, top-to-bottom). --json for scripts.
visus text find-all "Confirm" --region 0,0,1920,1080 --json
#  [{"occurrence": 1, "x": 980, "y": 384, "width": 70, "height": 22, "confidence": 96.0}, ...]

# Pick the OCR backend: 'tesseract' (needs the binary) or 'rapidocr' (bundled ONNX).
visus text find-all "Total" --ocr rapidocr --filter numbers

# Draw a numbered, click-through overlay over every match (debug / demo).
visus text show "Login" --duration 4000 --color green --ocr rapidocr
```

Shared options: `--region X,Y,W,H`, `--filter letters|numbers|both`,
`--confidence-threshold 0-100`, `--ocr tesseract|rapidocr`. `show` adds
`--color`, `--duration` (ms), `--width` (px). The overlay is a Win32
click-through window, so it never blocks a subsequent click.

## Every command (50) at a glance

`?` marks an optional argument; `…` a variadic one. Nearly every command also takes `--json`. Full reference: `docs/cli.md`.

| Command | Parameters | What it does |
|---|---|---|
| `visus capture` | `LABEL --auto=<text> --text=<text> --native=<text> --region=<text> --window=<text> --search-region=<text> --click --mouse-button=<text> --padding=<integer> --confidence-threshold=<float> --native-timeout=<float> --elements-dir=<text> --dry-run --json` | Capture a UI element: locate -> save template + annotated -> optional click. |
| `visus clipboard get` | `--json` | Read the clipboard text. |
| `visus clipboard set` | `TEXT --json` | Put TEXT on the clipboard. |
| `visus configure` | `CONFIG? --set=<text> --dry-run --reset --save --json` | Read, set (persisted), or reset the CLI config. |
| `visus display-size` | `--json` | Print the primary display size. |
| `visus doctor` | `--json` | Run environment health checks (Tesseract, display, deps). |
| `visus image click` | `IMAGE_PATH --region=<text> --confidence=<float> --specific --button=<choice> --delay=<float> --sendtext=<text> --backtrack --occurrence=<integer> --wait-timeout=<integer> --wait-until-disappears --wait-until-found --max-attempts=<integer> --json` | Find a template PNG and click its center. |
| `visus image find` | `IMAGE_PATH --region=<text> --confidence=<float> --specific --backtrack --occurrence=<integer> --wait-timeout=<integer> --wait-until-disappears --wait-until-found --max-attempts=<integer> --json` | Find a template PNG; print its box (no click). |
| `visus image find-all` | `IMAGE_PATH --region=<text> --confidence=<float> --json` | Find EVERY occurrence of a template PNG (no click). |
| `visus image find-multiple` | `IMAGE_PATHS... --region=<text> --confidence=<float> --json` | Find the first match of SEVERAL template PNGs. |
| `visus image relative` | `ANCHOR_IMAGE TARGET_IMAGE --max-distance=<integer> --confidence=<float> --target-region=<text> --click --button=<choice> --delay=<float> --sendtext=<text> --backtrack --max-attempts=<integer> --wait-until-found --wait-until-disappears --wait-timeout=<integer> --json` | Find/click a target template NEAR a unique anchor. |
| `visus key` | `COMMAND --delay=<float> --backtrack --json` | Press a key or chord (token is CASE-SENSITIVE). |
| `visus keys` | `--json` | List the valid keyboard_command tokens (case-sensitive). |
| `visus monitors` | `--json` | List connected monitors (for the --monitor index). |
| `visus mouse click` | `X Y --width=<integer> --height=<integer> --button=<choice> --delay=<float> --json` | Click at absolute coordinates (X,Y). Last resort. |
| `visus mouse down` | `--x=<integer> --y=<integer> --button=<choice> --json` | Press a mouse button without releasing (pair with 'up'). |
| `visus mouse drag` | `X1 Y1 X2 Y2 --duration=<float> --button=<choice> --json` | Drag from (X1,Y1) to (X2,Y2). |
| `visus mouse move` | `X Y --max-offset=<integer> --duration=<float> --json` | Move the cursor to (X,Y) with a light human jitter. |
| `visus mouse scroll` | `AMOUNT --x=<integer> --y=<integer> --json` | Scroll the wheel (positive = up, negative = down). |
| `visus mouse triple-click` | `--x=<integer> --y=<integer> --interval=<float> --json` | Triple-click at (X,Y) (or current cursor). |
| `visus mouse up` | `--x=<integer> --y=<integer> --button=<choice> --json` | Release a previously-pressed mouse button. |
| `visus native click` | `--window=<text> --pid=<integer> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<integer> --button=<text> --double --method=<choice> --timeout=<float> --retries=<integer> --delay=<float> --dry-run --json` | Click a control by selector. |
| `visus native dump-tree` | `--window=<text> --pid=<integer> --max-depth=<integer> --timeout=<float> --json` | Print the accessibility control tree. |
| `visus native get-state` | `--window=<text> --pid=<integer> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<integer> --timeout=<float> --json` | Snapshot a control's state. |
| `visus native get-text` | `--window=<text> --pid=<integer> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<integer> --timeout=<float> --json` | Read a control's text/value. |
| `visus native set-text` | `TEXT --window=<text> --pid=<integer> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<integer> --timeout=<float> --retries=<integer> --delay=<float> --dry-run --json` | Set the text of an editable control. |
| `visus native wait` | `--window=<text> --pid=<integer> --title=<text> --control-type=<text> --auto-id=<text> --found-index=<integer> --state=<choice> --timeout=<float> --poll-interval=<float> --json` | Wait until a control reaches a state. |
| `visus new` | `PATH --force` | Scaffold a new visus-desktop bot project. |
| `visus process find` | `NAME --json` | Find processes whose name contains NAME. |
| `visus process is-running` | `NAME --json` | Check whether any process name contains NAME. |
| `visus process kill` | `PID --yes --json` | Terminate a process by PID (destructive -- requires confirmation). |
| `visus process launch` | `COMMAND ARGS...? --json` | Launch a process. Returns {pid, command}. |
| `visus repl` | `—` | Start the interactive Visus CLI Pro shell. |
| `visus report` | `ZIP_PATH --html=<text>` | Render a session zip to HTML. |
| `visus run` | `SCRIPT` | Run a Python script via the active interpreter. |
| `visus screenshot` | `PATH? --region=<text> --monitor=<integer> --base64 --json` | Capture the screen to a PNG on disk (the find_image template format). |
| `visus smart click` | `--query=<text> --image=<text> --coords=<text> --window=<text> --pid=<integer> --control-type=<text> --auto-id=<text> --region=<text> --confidence=<float> --confidence-threshold=<float> --order=<text> --timeout=<float> --button=<choice> --retries=<integer> --delay=<float> --dry-run --json` | Click a target using the smart cascade. |
| `visus smart find` | `--query=<text> --image=<text> --coords=<text> --window=<text> --pid=<integer> --control-type=<text> --auto-id=<text> --region=<text> --confidence=<float> --confidence-threshold=<float> --order=<text> --timeout=<float> --json` | Find a target using the smart cascade. |
| `visus text click` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --occurrence=<integer> --button=<choice> --delay=<float> --sendtext=<text> --wait-timeout=<integer> --wait-until-disappears --wait-until-found --backtrack --max-attempts=<integer> --ocr=<choice> --json` | Find on-screen text via OCR and click its center. |
| `visus text find` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --occurrence=<integer> --wait-timeout=<integer> --wait-until-disappears --wait-until-found --backtrack --max-attempts=<integer> --ocr=<choice> --json` | Find on-screen text via OCR; print its box (no click). |
| `visus text find-all` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --ocr=<choice> --json` | List EVERY on-screen occurrence of TEXT (no click). |
| `visus text show` | `QUERY --region=<text> --filter=<choice> --confidence-threshold=<float> --color=<text> --duration=<integer> --width=<integer> --ocr=<choice> --json` | Overlay every occurrence of TEXT on screen, numbered. |
| `visus type` | `TEXT --interval=<float> --delay=<float> --backtrack --json` | Type TEXT into the currently focused field. |
| `visus window close` | `TITLE --yes --json` | Close a window (destructive -- requires confirmation). |
| `visus window ensure` | `--title=<text> --process=<text> --no-show --no-foreground --json` | Fast: is the app open/minimized? -- and bring it to the front. |
| `visus window focus` | `TITLE --json` | Bring a window to the foreground. |
| `visus window get` | `TITLE --json` | Resolve a window's rect/pid/hwnd (no focus). |
| `visus window list` | `--title=<text> --process=<text> --json` | List visible windows (read-only). |
| `visus window maximize` | `TITLE --json` | Maximize a window. |
| `visus window minimize` | `TITLE --json` | Minimize a window. |

## Mental model (same as the MCP skill)

**Core idea — locate with your eyes, run on images.** Native tree + OCR are how
you SEE the screen while *building* a flow (they find WHERE a thing is).
`visus capture` turns a sighting into a reusable PNG template. The **script you
ship** then clicks those templates with `visus image click` /
`visus image relative` — template matching is fast and deterministic; re-running
OCR every execution is slow and brittle. Accessible apps are the exception (act
by control, no templates).

1. **Target first**: `visus window ensure --process app.exe --json` — opens/
   focuses and returns the `rect`. Scope later searches to it (`--region`).
2. **See the UI**: `visus native dump-tree --window "App" --json`. Controls
   returned → accessible app: act with `visus native click/set-text/wait`
   (no pixels, most robust, **no templates needed**). Returns `[]` (Win11 file
   pickers, Java Swing, some Electron) → see by OCR.
3. **Capture each target (build time)**: `visus capture save --auto "Salvar"
   --window "App" --search-region X,Y,W,H --click` saves `save.png` cropped from
   the box it located. **Never guess coordinates / eyeball a crop**; if a
   locator misses, FIX it (scope `--search-region`, lower
   `--confidence-threshold`, try `--text`/`--native`). When unsure which layer
   fits, `visus smart click --query "Salvar" --window "App" --dry-run`.
4. **Assemble the runtime flow (image-based)**: `visus image click save.png
   --region X,Y,W,H`. Scope to the window rect so a look-alike elsewhere can't
   match. Re-run OCR/native at runtime only for dynamic text or relative anchors.
5. **Verify by EFFECT, not just exit code**: a `0`/`clicked:true` ≠ the action
   worked. Confirm the real outcome — file mtime/size changed, `visus native
   get-text/get-state` changed, screen settled (`visus` exit code + the actual
   side effect).

### Dialogs (Save As / Open / overwrite confirm)

The Win11 file picker usually gives an **empty `native dump-tree`** → go OCR.
Type the **full path** into the name field (`visus type` after focusing it) —
it saves anywhere regardless of the dialog's current folder. The default button
fires on `Enter`, **but an overwrite confirm ("Sim"/"Não", "Yes"/"No") defaults
to "Não"** — so `Enter` cancels it; click "Sim" (focus that dialog first) or
send `Left` then `Enter`. Locate by text scoped to the **bottom button row**
(the word may also be in the title). **Verify the save by the file's
mtime/size.**

## Safety guardrails

- **Destructive commands need `--yes`**: `visus process kill <pid>` and
  `visus window close <title>` prompt for confirmation; in `--json`/non-interactive
  mode they refuse without `--yes`. Only pass `--yes` when the user authorized it.
- **Use `--dry-run`** on `smart click` / `native click` / `native set-text` /
  `capture --click` to resolve the target before committing to real input.
- **Coordinates only when given**: resolve targets through `smart`/`native`/
  `capture`; don't hard-code `--coords` unless the user provided them.

## Scripting example

**Build once** — let OCR/native be your eyes and capture the templates the
runtime will click (run with each dialog open):

```bash
# Save As button (file picker has no native tree → OCR, scoped to the button row)
visus capture btn_salvar --text "Salvar" --window "Salvar como" \
  --search-region 84,528,960,90 --click
# overwrite-confirm "Sim" button
visus capture btn_sim --text "Sim" --window "Confirmar Salvar como" --padding 8 --click
```

**Run** — fast, image-based, deterministic:

```bash
#!/usr/bin/env bash
set -euo pipefail
OUT="$HOME/Downloads/demo.txt"
before=$(stat -c %Y "$OUT" 2>/dev/null || echo 0)

visus window ensure --process notepad.exe --json
visus type "hello world"
visus key "Ctrl+S"
visus window get "Salvar como" --json            # wait for the dialog, grab its rect
visus type "{ctrl}a$OUT"                          # full path → saves to Downloads
visus image click visus-elements/btn_salvar.png --region 84,78,960,540

# overwrite confirm defaults to "Não" → click "Sim" by image (don't press Enter)
if visus window get "Confirmar Salvar como" --json >/dev/null 2>&1; then
  visus image click visus-elements/btn_sim.png --region 769,415,366,140
fi

after=$(stat -c %Y "$OUT")                         # verify by EFFECT (mtime grew)
[ "$after" -gt "$before" ] && echo "saved" || { echo "not written"; exit 1; }
```

When in doubt, re-read this skill before invoking `visus` — it overrides
whatever you "remember" about the CLI from training data. The companion MCP
skill is `using-visus-desktop.md`.

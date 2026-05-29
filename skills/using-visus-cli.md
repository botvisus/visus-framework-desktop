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

| Group | Commands |
|---|---|
| `visus smart` | `find`, `click` — cascade native → image → OCR → coordinates (`--order` to force/reorder; `--dry-run` to resolve only) |
| `visus native` | `dump-tree`, `click`, `set-text`, `get-text`, `get-state`, `wait` — no-pixel RPA by directed selector |
| `visus capture` | coordinate-free capture by `--auto`/`--text`/`--native`/`--region` → saves template + annotated, optional `--click` |
| `visus screenshot` | save a PNG to disk (the `find_image` template format) |
| `visus window` | `focus`, `maximize`, `minimize`, `close`, `get` |
| `visus process` | `launch`, `find`, `kill` |
| `visus clipboard` | `get`, `set` |
| `visus` (root) | `configure`, `doctor`, `new`, `run`, `report`, `repl` |

## Mental model (same as the MCP skill)

1. **Native first when accessible**: `visus native dump-tree --window "App" --json`
   to *see* the control tree. If it returns controls, act with
   `visus native click/set-text/wait` — no pixels, most robust.
2. **Otherwise prefer `visus smart click`**: it tries native → image → OCR →
   coordinates and tells you which won. `--dry-run` first if unsure.
3. **Build click-by-image with `visus capture`**: `visus capture save --auto
   "Salvar" --window "App" --click` instead of guessing coordinates.
4. **Verify exit codes**: `0` = success. Branch your script on `$?` or parse
   the `--json` payload.

## Safety guardrails

- **Destructive commands need `--yes`**: `visus process kill <pid>` and
  `visus window close <title>` prompt for confirmation; in `--json`/non-interactive
  mode they refuse without `--yes`. Only pass `--yes` when the user authorized it.
- **Use `--dry-run`** on `smart click` / `native click` / `native set-text` /
  `capture --click` to resolve the target before committing to real input.
- **Coordinates only when given**: resolve targets through `smart`/`native`/
  `capture`; don't hard-code `--coords` unless the user provided them.

## Scripting example

```bash
#!/usr/bin/env bash
set -euo pipefail
visus process launch notepad.exe --json
visus native wait --window "Notepad" --control-type Edit --state ready --json
visus native set-text "hello world" --window "Notepad" --control-type Edit
visus capture save --auto "Save" --window "Notepad" --click
```

When in doubt, re-read this skill before invoking `visus` — it overrides
whatever you "remember" about the CLI from training data. The companion MCP
skill is `using-visus-desktop.md`.

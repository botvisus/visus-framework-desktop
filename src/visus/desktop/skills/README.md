# Visus Desktop — Skills

These are agent-ready playbooks for driving the [visus-desktop MCP server](../resources/mcp.md) (`visus-mcp`) and the `visus` CLI. Each `*.md` file is a single skill: a self-contained markdown document with frontmatter (`name`, `description`, `when_to_use`) followed by step-by-step guidance written for an agent (Claude Code, Claude Desktop, Cursor, custom MCP clients). They ship inside the package (`visus/desktop/skills/`).

## How agents discover these

Skills are language-agnostic — they're plain markdown. For Claude Code, install each one as a personal skill folder — `~/.claude/skills/<name>/SKILL.md` (e.g. `~/.claude/skills/record-and-replay/SKILL.md`) — and it becomes invokable by name. Re-copy them after upgrading `visus-desktop` so the agent sees the current API.

To use them outside a skill framework, just paste the body of the skill into the agent's system prompt; the steps reference the `visus-mcp` tool names directly so they remain executable.

## Catalogue

| Skill | When to invoke |
|---|---|
| [`using-visus-desktop`](using-visus-desktop.md) | Entry-point skill — establishes the toolset, conventions, and safety guidelines. |
| [`using-visus-cli`](using-visus-cli.md) | Driving visus-desktop from the shell (`visus …` commands, `--json`), scripting/CI, and `new` → `run` for a run with a report. |
| [`automate-form-login`](automate-form-login.md) | Filling out a login / sign-in form in a desktop or browser app. |
| [`extract-table-data`](extract-table-data.md) | OCR-scraping a table or list on screen into structured rows. |
| [`wait-for-download`](wait-for-download.md) | Triggering a download and blocking the agent until the file lands. |
| [`solve-image-captcha`](solve-image-captcha.md) | Reading old-style image captchas with OCR + character whitelisting. |
| [`file-dialog-automation`](file-dialog-automation.md) | Skipping the "Open File" dialog by typing the absolute path. |
| [`record-and-replay`](record-and-replay.md) | A step-by-step HTML report of a run — live through the MCP (`start_recording` / `stop_recording`) or in a delivered script (`rpa()`). |

## Authoring conventions

* Frontmatter is YAML, comma-separated tags, plain markdown body.
* Every step says **which MCP tool to call** and **what to inspect** before proceeding.
* Skills assume `visus-mcp` is running (or attached via host config); they never instruct the agent to invent its own automation primitives.
* The skills only call public tools (the 59 registered in `mcp_server.py` — `tests/test_skills.py` checks it); they never reach into private internals.

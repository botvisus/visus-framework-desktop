# Visus Desktop — Skills

These are agent-ready playbooks for driving the [visus-desktop MCP server](../docs/mcp.md) (`visus-mcp`). Each `*.md` file is a single skill: a self-contained markdown document with frontmatter (`name`, `description`, `when_to_use`) followed by step-by-step guidance written for an MCP-aware agent (Claude Code, Claude Desktop, Cursor, custom MCP clients).

## How agents discover these

Skills are language-agnostic — they're plain markdown. Agents that support local skill libraries (Claude Code, the `superpowers` plugin family, the `claude-skills` CLI) point at this directory and the files become invokable by name.

To enable inside Claude Code, add this directory to your skill path:

```jsonc
// ~/.claude/settings.json
{
  "skillPaths": [
    "C:\\path\\to\\visus-desktop\\skills"
  ]
}
```

To use them outside a skill framework, just paste the body of the skill into the agent's system prompt; the steps reference the `visus-mcp` tool names directly so they remain executable.

## Catalogue

| Skill | When to invoke |
|---|---|
| [`using-visus-desktop`](using-visus-desktop.md) | Entry-point skill — establishes the toolset, conventions, and safety guidelines. |
| [`automate-form-login`](automate-form-login.md) | Filling out a login / sign-in form in a desktop or browser app. |
| [`extract-table-data`](extract-table-data.md) | OCR-scraping a table or list on screen into structured rows. |
| [`wait-for-download`](wait-for-download.md) | Triggering a download and blocking the agent until the file lands. |
| [`solve-image-captcha`](solve-image-captcha.md) | Reading old-style image captchas with OCR + character whitelisting. |
| [`file-dialog-automation`](file-dialog-automation.md) | Skipping the "Open File" dialog by typing the absolute path. |
| [`record-and-replay`](record-and-replay.md) | Recording a manual run to a session zip and rendering the HTML report. |

## Authoring conventions

* Frontmatter is YAML, comma-separated tags, plain markdown body.
* Every step says **which MCP tool to call** and **what to inspect** before proceeding.
* Skills assume `visus-mcp` is running (or attached via host config); they never instruct the agent to invent its own automation primitives.
* The skills only call public tools (the 30 registered in `mcp_server.py`); they never reach into private internals.

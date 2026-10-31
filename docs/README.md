# Visus Desktop documentation

Reference and guides for [`visus-desktop`](https://github.com/matheuszwilk/visus-desktop).

## Reference

- [**CLI reference**](cli.md) — every `visus` command and flag.
- [**MCP reference**](mcp.md) — all 44 MCP tools and their parameters.
- [**Python API reference**](api_reference.md) — `VisusBot` methods, standalone
  functions, and a Python ↔ CLI ↔ MCP coverage matrix.
- [**Configuration reference**](config.md) — every `BotVisionConfig` key.

## Guides

- [**Installation & troubleshooting**](installation.md) — install, OCR engine
  choice, per-OS setup.
- [**Troubleshooting**](troubleshooting.md) — focused symptom → fix table
  (OCR, DPI, pywinauto, Tcl/Tk).
- [**Migration guide**](migration.md) — moving from the old `BotVision` to
  `visus-desktop` / `VisusBot`.
- [**Cookbook**](cookbook/README.md) — worked, copy-pasteable recipes.

## Playbooks (agent-facing)

The [`skills/`](../src/visus/desktop/skills/) directory holds task playbooks for AI agents:
login forms, table scraping, captchas, downloads, file dialogs, record/replay,
and the CLI/MCP usage skills.

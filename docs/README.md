# Visus Desktop Documentation

Documentation for **Visus Desktop** (`visus-desktop`) — desktop GUI automation with multi-technique OCR, robust image detection, smart backtracking, and a non-intrusive virtual mouse. Part of the **Visus** automation family.

## Contents

- **[Installation](installation.md)** — installing the package, setting up Tesseract OCR (Windows / Linux / macOS), the Linux system dependencies, verifying the install, and the optional extras (`[native]`, `[automation]`, `[ai]`, `[web]`).
- **[API Reference](api_reference.md)** — the public API: the `VisusBot` class and its methods (OCR, images, image map, relative images, keyboard/mouse, native accessibility automation, process/window control, screen capture, clipboard, file waits), the module‑level capability functions, standalone convenience functions, `BotVisionConfig`, text helpers, and exceptions.
- **[Cookbook](cookbook/README.md)** — end-to-end recipes for common automation patterns (download wait, file dialogs, captcha, Excel input, Oracle Forms).
- **[Migration guide](migration.md)** — from `bot-vision-suite` to `visus-desktop` (imports, renames, new opt-ins, step-by-step checklist).
- **[Troubleshooting](troubleshooting.md)** — symptom → diagnosis → fix for OCR misses, DPI issues, `pywinauto` connection failures, Tcl/Tk on Linux/WSL, and more.
- **[MCP server](mcp.md)** — drive `visus-desktop` from any MCP-aware agent (Claude Desktop, Claude Code, Cursor). 30 tools + bundled Skills.

## Quick links

- Project overview and quickstart: [../README.md](../README.md)
- Runnable examples: [../examples/](../examples/)

## At a glance

```python
from visus.desktop import VisusBot

bot = VisusBot()
bot.click_text("Login")
bot.click_image("submit_button.png")
bot.type_text("hello world")
```

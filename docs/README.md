# Visus Desktop Documentation

Documentation for **Visus Desktop** (`visus-desktop`) — desktop GUI automation with multi-technique OCR, robust image detection, smart backtracking, and a non-intrusive virtual mouse. Part of the **Visus** automation family.

## Contents

- **[Installation](installation.md)** — installing the package, setting up Tesseract OCR (Windows / Linux / macOS), verifying the install, and the optional extras (`[automation]`, `[ai]`, `[web]`).
- **[API Reference](api_reference.md)** — the public API: the `VisusBot` class and its methods, standalone convenience functions, `BotVisionConfig`, text helpers, and exceptions.

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

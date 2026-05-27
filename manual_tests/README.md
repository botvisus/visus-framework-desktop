# Manual tests / playground

Runnable scripts to try Visus Desktop features by hand. Unlike the automated suite in `tests/`
(which is CI-safe and never touches your real screen), these scripts **interact with your actual
screen, mouse, and keyboard** — run them yourself and watch what happens.

Run any script with the project's Python (after `pip install -e .`):

```bash
python manual_tests/00_environment_check.py
```

Or use the interactive menu:

```bash
python manual_tests/06_menu.py
```

## Scripts, by how intrusive they are

| Script | What it does | Safety |
|--------|--------------|--------|
| `00_environment_check.py` | Imports, version, Tesseract detection, config defaults, keyboard commands, overlay colors. | ✅ Safe — no screen actions |
| `01_text_helpers.py` | Exercises `clean_text` / `matches_filter` / `validate_text_input` / extractors. | ✅ Safe — pure functions |
| `02_overlay_demo.py` | Draws colored overlay rectangles in the center of your screen. | 🟡 Visual only — no clicks |
| `03_screen_ocr.py` | Captures a region (or full screen) and prints the OCR text it reads. | 🟡 Read-only — reads the screen |
| `04_find_on_screen.py` | Searches your screen for text and/or an image and reports the location. | 🟡 Read-only by default (`--click` to actually click) |
| `05_typing_keyboard.py` | After a countdown, types text and sends a keyboard shortcut into the focused window. | 🔴 Sends real keystrokes — focus a safe text field first |

> **Requirement:** Tesseract OCR must be installed (see the project README). Scripts that use OCR
> will tell you clearly if it is missing.

# Cookbook — Windows "Open File" dialogs (stub)

> 🚧 **Stub.** Recipe planned for an upcoming release.

## What this recipe will cover

The standard Windows "Open File" / "Save As" dialog accepts a full path
in its **filename** field — typing the full path then pressing **Enter**
skips the entire folder-tree navigation.

```python
from visus.desktop import VisusBot

bot = VisusBot()

# After clicking "Open" / "Upload" on the host app, the dialog opens.
# Focus its filename field, type the absolute path, then Enter.
bot.execute_tasks([
    {"text": "File name", "region": (0, 600, 1920, 100)},  # focus the field
    {"type": "type_text", "text": r"C:\Users\me\Documents\report.csv"},
    {"type": "keyboard_command", "command": "Enter"},
])
```

## Patterns to expand

* Detect the dialog by finding the title bar text ("Abrir", "Open"…).
* Handle the "File name:" label in localized Windows builds (use OCR
  rather than hard-coded strings).
* Pair with `wait_for_file_stable` for the *result* of a "Save As".

## See also

* [Cookbook index](README.md)
* [Download wait](download-wait.md) — for the after-Save-As case.

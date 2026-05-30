# Fill a native file dialog (Save / Open)

The Windows common file dialog is **accessible**, so drive it natively — type the
full path into its *File name* edit and click the action button. No pixels.

```python
from visus.desktop import VisusBot, ensure_window
from visus.desktop.core.native_rpa import (
    native_set_text, native_click, native_wait,
)

bot = VisusBot()

# Trigger the dialog from your app (e.g. Ctrl+S), then wait for it to render.
bot.keyboard_command("Ctrl+S")
native_wait(title="File name:", control_type="Edit", state="ready", timeout=10)

# Type the absolute path into the "File name" edit and confirm.
native_set_text(
    r"C:\Users\me\Documents\output.txt",
    title="File name:", control_type="Edit",
)
native_click(title="Save", control_type="Button")
```

If the dialog is **not** accessible (some custom/legacy dialogs), fall back to
OCR + keyboard:

```python
bot = VisusBot()
bot.click_text("File name:", region=(0, 0, 1920, 1080))   # focus the edit
bot.type_text(r"C:\Users\me\Documents\output.txt")
bot.keyboard_command("Enter")
```

**Notes**

- Use `ensure_window(...)` on the host app first so the dialog opens on a visible
  window.
- Prefer typing the **absolute** path — it sidesteps the dialog's current folder.
- An "overwrite?" confirmation may follow: `native_click(title="Yes",
  control_type="Button")` or `bot.keyboard_command("Enter")`.

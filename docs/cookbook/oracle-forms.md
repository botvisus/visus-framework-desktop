# Oracle Forms / legacy apps (non-accessible UIs)

Oracle Forms, Java Swing without the Access Bridge, old Delphi/VB apps, and some
Electron windows expose **no accessibility tree** — `native_dump_tree` returns
`[]`. Drive them with the pixel path: OCR for text, template images for icons,
and the keyboard for field navigation.

```python
from visus.desktop import VisusBot, ensure_window
from visus.desktop.core.native_rpa import native_dump_tree
from visus.desktop.core.window import get_window

ensure_window(process="frmweb.exe")     # Oracle Forms runtime, for example
bot = VisusBot()

# Confirm it's non-accessible before committing to pixels.
if not native_dump_tree(window="Oracle"):
    win = get_window("Oracle")
    region = (win["x"], win["y"], win["width"], win["height"]) if win else None

    # Label-driven: click the field's label, then Tab into the input and type.
    bot.click_text("Username", region=region)
    bot.keyboard_command("Tab")
    bot.type_text("scott")

    bot.click_text("Password", region=region)
    bot.keyboard_command("Tab")
    bot.type_text("tiger")

    # Icon toolbar buttons have no text -> match a saved template image.
    bot.click_image("save_icon.png", region=region, confidence=0.85)
```

**Notes**

- Forms toolbars are icon-only — capture each button once
  (`bot.find_image`/`capture_element`) and reuse the template; scope the search
  to the window `region` so an identical icon elsewhere can't match.
- Field order is stable in Forms: it's often faster to `Tab` between fields than
  to OCR every label.
- Function keys matter in Forms (`F8` execute-query, `F10` commit):
  `bot.keyboard_command("F8")`. (Tokens are case-sensitive.)
- When the same label appears more than once (e.g. repeated "OK"), use
  `bot.find_all_text("OK", region=region)` to list every match and click the
  right one with `bot.click_text("OK", occurrence=2)`.

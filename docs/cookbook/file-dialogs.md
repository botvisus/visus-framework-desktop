# Cookbook — Windows "Open File" dialogs

**Problem.** Your bot clicks a button that opens the standard Windows
"Open File" / "Save As" dialog. Navigating that dialog with arrow keys
and OCR is fragile — folders move, locale changes the labels, scroll
position drifts.

**Solution.** Type the **full path** into the filename field and press
Enter. Windows dialogs accept an absolute path in the filename input
and skip the entire tree-navigation problem.

## Minimal example

```python
from visus.desktop import VisusBot

bot = VisusBot()

tasks = [
    # 1. Click the host app's "Open" or "Upload" button -> dialog opens.
    {"image": "open_button.png", "region": (1200, 80, 60, 30),
     "delay": 0.5},
    # 2. Focus the dialog's "File name" field. The field label varies by
    #    locale -- match by image or by the "Open" / "Save" button area.
    {"text": "File name", "region": (0, 600, 1920, 100)},
    # 3. Type the absolute path.
    {"type": "type_text",
     "text": r"C:\Users\me\Documents\report.csv"},
    # 4. Submit.
    {"type": "keyboard_command", "command": "Enter"},
]

bot.execute_tasks(tasks)
```

## After "Save As" -- wait for the file to actually land

```python
from pathlib import Path
from visus.desktop import wait_for_file_stable

# The user/bot triggered Save As above; here we wait until the file
# stops growing on disk before continuing.
saved = Path(r"C:\Users\me\Documents\report.csv")
assert wait_for_file_stable(str(saved), timeout=30, stable_for=1.5), \
    "Save As did not complete in time"
print(saved.read_text())
```

## Localized dialogs

If your Windows is set to Portuguese, the label is `Nome do arquivo`
rather than `File name`. Use the language-agnostic shortcut: the
focus tabs onto the filename field as the default control. So if the
dialog just opened, you can usually skip the OCR step:

```python
tasks = [
    {"image": "open_button.png", "delay": 0.5},
    {"type": "type_text",
     "text": r"C:\Users\me\Documents\report.csv"},
    {"type": "keyboard_command", "command": "Enter"},
]
```

## When the path is wrong

Windows shows a "The system cannot find the file" dialog on a bad
path. Pair the open call with a `screenshot_on_failure` config so the
PNG of that error dialog ends up on disk for diagnosis:

```python
bot = VisusBot({
    "artifacts_dir": "./visus-artifacts",
    "screenshot_on_failure": True,
})
```

See [`docs/troubleshooting.md`](../troubleshooting.md) for how to
trace the failure back to the dialog.

## See also

* [`wait_for_file_stable`](download-wait.md) -- pairs with Save As.
* [`type_text` task](../api_reference.md) -- the keyboard primitive
  used above.

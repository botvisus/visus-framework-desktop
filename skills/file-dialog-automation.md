---
name: file-dialog-automation
description: Skip Windows "Open File" / "Save As" tree navigation by typing the absolute path into the filename field and pressing Enter. Use whenever the user wants the bot to open a specific file in an app's standard dialog.
when_to_use: Activate whenever the host app pops a Windows file dialog (Open / Save As) and the user has given you the absolute path of the target file.
---

# Drive a Windows file dialog by absolute path

## Why this works

The "Open File" / "Save As" dialog accepts a **fully qualified path** in the filename field. Typing the path then pressing Enter bypasses every folder-tree navigation step — no more clicking through `C:\` → `Users` → `me` → `Documents`. It works regardless of how scrolled the side-pane is, and it survives locale changes.

## Steps

1. The dialog must already be visible (your previous step clicked "Open" / "Upload" / "Save As").
2. `take_screenshot()` once to confirm — file dialogs differ slightly between Windows versions. You're looking for a filename field near the bottom labeled "File name:" or its localized equivalent.
3. Focus the filename field. Two reliable paths:
   * **Localized-safe (preferred)**: most dialogs already have the field focused when they open. Skip straight to `type_text` if you can.
   * **Explicit**: `click_text(text="File name", region=[0, 500, 1920, 600])`. Adjust the `region` to the bottom strip of the dialog.
4. Clear whatever's there: `keyboard_command(command="Ctrl+A")` then `keyboard_command(command="Delete")`.
5. Type the absolute path:

   ```text
   type_text(text="C:\\\\Users\\\\me\\\\Documents\\\\report.csv")
   ```

   Note the double-escaped backslashes — these are JSON string escapes; the path that reaches the field is `C:\Users\me\Documents\report.csv`.
6. Submit: `keyboard_command(command="Enter")`.
7. Verify the dialog closed:
   * `wait_for_stable_screen(stable_for=0.5, timeout=5)`.
   * `find_text(text="File name")` should now return `None`.

## When the path is wrong

If the path does not exist, Windows shows "The system cannot find the file" or similar. After step 6, if the dialog stays open, capture the screen and surface the error message:

```text
take_screenshot()  # attach to your reply for the user
```

## When the dialog is "Save As"

Save the file, then call the `wait-for-download` skill on the same path to confirm it landed and stopped growing before the next step.

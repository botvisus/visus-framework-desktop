---
name: wait-for-download
description: Trigger a download from a UI button and block until the file has finished writing to disk, using wait_for_file_stable so partially-written files are never returned.
when_to_use: Activate whenever the user wants to click an "Export" / "Download" / "Save report" button and then operate on the resulting file.
---

# Wait for a download to finish

## Steps

1. Resolve the download target before clicking: ask the user **where** the file will land (typical: `%USERPROFILE%\Downloads\<name>.<ext>`). Save that path in your context.
2. Click the download trigger:
   * `click_text(text="Export")` — most apps label the trigger in plain text.
   * Fall back to `click_image(image_path=<button.png>)` when the trigger is an icon.
3. Capture the click confirmation: `wait_for_stable_screen(stable_for=0.5, timeout=5)` so the next step does not race a "Generating…" dialog.
4. Block on the file:

   ```text
   wait_for_file_stable(path="<absolute path>", timeout=60, stable_for=2, poll_interval=0.5)
   ```

   * `stable_for=2` covers slow OneDrive / Dropbox sync touches.
   * `timeout=60` is the right default; bump to 600 for genuinely large exports.
5. Verify the file is non-empty before reporting success — `wait_for_file_stable` returns `True` even for a zero-byte file. If you can read the file in this conversation, do; otherwise note the size from the OS.

## Quirks

* **Browser staging files**: Chrome writes `<name>.crdownload`, Firefox writes `<name>.part`, then renames on completion. `wait_for_file_stable` on the **final** name handles this transparently — the final name does not exist until the rename completes.
* **Dialog confirming the download**: some apps pop a "Save as…" dialog. Switch to the `file-dialog-automation` skill to fill in the path.
* **Timeout**: when the wait returns `false`, do **not** retry the click silently — re-`take_screenshot()` first. A second click often re-opens a "file in use" modal.

## Compact task-list version

```text
execute_tasks(tasks=[
    {"text": "Export", "region": [800, 100, 400, 80], "delay": 0.5},
])
# Then in plain MCP:
wait_for_file_stable(path="<absolute path>", timeout=60, stable_for=2)
```

The task list does not include the wait because `wait_for_file_stable` is a single-call tool, not a task type.

# Wait for a download to finish

Click an **Export** / **Download** button, then block until the file has fully
finished writing — `wait_for_file_stable` only returns once the size stops
growing, so a partially-written `.crdownload` / `.part` never counts as done.

```python
import os
from visus.desktop import VisusBot, ensure_window
from visus.desktop.core.window import get_window

ensure_window(process="chrome.exe")
bot = VisusBot()

# Where will the file land? Resolve the absolute path up front.
target = os.path.expandvars(r"%USERPROFILE%\Downloads\report.xlsx")

# Click the export trigger (text label; fall back to a template if it's an icon).
win = get_window("Downloads")          # or scope to your app's window
region = (win["x"], win["y"], win["width"], win["height"]) if win else None
bot.click_text("Export", region=region)

# Don't race a "Generating…" dialog.
from visus.desktop import wait_for_stable_screen
wait_for_stable_screen(stable_for=0.5, timeout=5)

# Block until the download is COMPLETE (size stable for 2s; bump timeout for big files).
from visus.desktop import wait_for_file_stable
ok = wait_for_file_stable(target, timeout=60, stable_for=2, poll_interval=0.5)
print("downloaded" if ok and os.path.getsize(target) > 0 else "download failed/empty")
```

**Notes**

- Browsers write a staging file (`.crdownload` / `.part`) then rename to the
  final name on completion — wait on the **final** name; it won't exist until the
  rename happens.
- `wait_for_file_stable` returns `True` even for a zero-byte file, so verify the
  size before reporting success.
- If the app pops a native *Save as…* dialog instead, see
  [Fill a file dialog](file-dialogs.md).

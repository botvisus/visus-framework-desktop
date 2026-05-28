# Cookbook — Wait for a download to finish

**Problem.** You click a button that triggers a download (a CSV report,
a PDF invoice, a build artifact). The next step of your bot needs the
file on disk *and* finished writing — clicking "Open" while the browser
is still flushing bytes is a recipe for a zero-byte file.

**Solution.** Use `wait_for_file_stable` to block until the file exists
and its size has not changed for `stable_for` seconds.

## Minimal example

```python
from pathlib import Path
from visus.desktop import VisusBot
from visus.desktop import wait_for_file_stable

bot = VisusBot()
downloads = Path.home() / "Downloads"
target = downloads / "report.csv"

# 1. Trigger the download.
bot.click_text("Export", region=(800, 200, 200, 80))

# 2. Wait until the file appears AND its size stops changing.
ok = wait_for_file_stable(
    str(target),
    timeout=60,        # give up after 60 s
    stable_for=2,      # size must be unchanged for 2 s
    poll_interval=0.5, # check twice a second
)
if not ok:
    raise RuntimeError(f"Download did not complete: {target}")

# 3. Now it's safe to read or open the file.
print(target.read_text())
```

## When to use `wait_for_file` vs `wait_for_file_stable`

| Helper | Waits until… | Use it when… |
|---|---|---|
| `wait_for_file(path)` | The path **exists** and is readable. | The target is written **atomically** (e.g. via `os.replace`) — the file appears already complete. |
| `wait_for_file_stable(path)` | Size has been unchanged for `stable_for`. | The writer flushes incrementally (browsers, FTP, slow disks). |

## As a task list step

The same wait fits in `execute_tasks` via Python — wrap it in a function
and call it between tasks. (A dedicated `wait_for_file` task type is on
the roadmap.)

```python
def step_wait_download():
    return wait_for_file_stable(str(target), timeout=60, stable_for=2)

bot.execute_tasks([
    {"type": "click", "x": 850, "y": 240, "delay": 0.5},  # Export
])
assert step_wait_download(), "download stalled"
bot.execute_tasks([
    {"text": "Open", "region": (0, 0, 1920, 200)},
])
```

## Production tips

* **Pick a generous `stable_for`.** Cloud-synced folders (OneDrive,
  Dropbox) periodically touch files. Two seconds is a safe floor.
* **Always set a `timeout`.** Bots that block forever on a missing file
  are the #1 cause of stuck pipelines.
* **Combine with `screenshot_on_failure`.** If the wait times out the
  failure screenshot tells you whether the browser actually started the
  download.
* **Watch the download directory, not the final destination.** Browsers
  often write to `<filename>.crdownload` (Chrome) or `<filename>.part`
  (Firefox) and rename on completion. `wait_for_file_stable` on the
  final name handles the rename transparently because the final name
  doesn't exist until the rename completes.

## See also

* [`wait_for_file` / `wait_for_file_stable`](../api_reference.md#files)
* [Screenshot-on-failure](../../CHANGELOG.md#unreleased) — pairs well
  with timeout debugging.

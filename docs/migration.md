# Migration guide — `BotVision` → `visus-desktop` / `VisusBot`

The library was renamed to **`visus-desktop`** and the main class to
**`VisusBot`**. The old `BotVision` name is kept as a backward-compatibility
alias, so existing scripts keep working, but new code should use the new names.

## What changed

| Old | New |
|---|---|
| package `bot_vision` | `visus-desktop` (PyPI) / `from visus.desktop import …` |
| class `BotVision` | `VisusBot` (`BotVision` still aliased) |
| config `BotVisionConfig` | `BotVisionConfig` (unchanged) |
| — | `visus` CLI, `visus-mcp` MCP server, `visus-doctor` |

## Import changes

```python
# Old
from bot_vision import BotVision
bot = BotVision()

# New
from visus.desktop import VisusBot
bot = VisusBot()
```

`from visus.desktop import BotVision` also works (alias of `VisusBot`).

## New opt-ins worth adopting

- **`visus doctor`** — verify Tesseract / display / deps / pywinauto before a
  run (also the `doctor` MCP tool).
- **Failure screenshots** — `screenshot_on_failure=True` (default) writes a PNG
  to `artifacts_dir` on any failed task; `screenshot_steps=True` also captures
  successful steps; `screenshot_annotate=True` draws the click target on them.
- **RapidOCR backend** — `ocr_backend="rapidocr"` removes the external Tesseract
  dependency entirely (`pip install "visus-desktop[rapidocr]"`).
- **Record & report** — wrap a run in `Session.start_recording(...)` and render
  a single-file HTML report; see the [cookbook](cookbook/README.md).
- **Single overlay flag** — the old `overlay_enabled` is folded into
  `show_overlay` (they were redundant). Set `show_overlay=False` to disable.

## Behavior notes

- `find_text` / `click_text` with no `region` now fall back to the whole screen
  in both the direct calls **and** `execute_tasks` task dicts (previously a
  task without a region raised).
- The click overlay is now a Win32 click-through window, so it no longer
  intercepts the click that follows it.

See the [configuration reference](config.md) for every key and the
[API reference](api_reference.md) for the full method list.

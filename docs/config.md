# Configuration reference — every `BotVisionConfig` key

Pass any subset of these keys when building a bot. Missing keys use the defaults
below. Unknown keys are accepted silently (forward-compatible).

```python
from visus.desktop import BotVisionConfig, VisusBot

cfg = BotVisionConfig({"ocr_backend": "rapidocr", "show_overlay": False})
bot = VisusBot(config=cfg)
# or, equivalently, pass the dict straight to VisusBot:
bot = VisusBot(config={"ocr_backend": "rapidocr"})
```

From the CLI: `visus configure '{...}'`. From MCP: the `configure` tool.

## OCR / Tesseract

| Key | Default | Meaning |
|---|---|---|
| `tesseract_path` | `None` (auto) | Path to the Tesseract binary. Leave `None` to auto-detect standard install paths. |
| `tesseract_data_path` | `None` (auto) | Path to the `tessdata` directory. |
| `ocr_languages` | `["eng"]` | Tesseract language codes (e.g. `["eng","por"]`). |
| `ocr_backend` | `"rapidocr"` | `"rapidocr"` (default; bundled ONNX models, no external binary, more robust on styled text) or `"tesseract"` (needs the binary). `rapidocr` ships with the `visus-desktop[rapidocr]` extra; if it isn't installed the OCR engine **falls back to Tesseract** automatically (with a warning). When `rapidocr` is active, Tesseract auto-detection is skipped. |
| `image_processing_methods` | `"all"` | OCR preprocessing pipeline. `"all"` runs every method; or a list to restrict. |

## Matching / detection

| Key | Default | Meaning |
|---|---|---|
| `confidence_threshold` | `75.0` | Default OCR confidence cutoff (0–100). |
| `matcher` | `"cv2"` | Image-template backend: `"cv2"` (fast, falls back to pyscreeze) or `"pyscreeze"` (legacy). |
| `retry_attempts` | `3` | Default retry attempts for find/click. |

## Mouse / click

| Key | Default | Meaning |
|---|---|---|
| `default_mouse_button` | `"left"` | `"left"` / `"right"` / `"double"` / `"move_to"`. |
| `click_duration` | `0.1` | Seconds the click takes. |
| `movement_duration` | `0.1` | Seconds to move the cursor to the target. |
| `use_virtual_mouse` | `False` | Click via `PostMessage` so the physical cursor doesn't move (Windows; falls back to physical if unsupported). |
| `default_delay` | `1.0` | Default pause (s) between actions in higher-level flows. |

## Overlay (visual feedback)

| Key | Default | Meaning |
|---|---|---|
| `show_overlay` | `True` | Master toggle. When on, every click first paints a **click-through** overlay around the target (Win32 `WS_EX_LAYERED \| WS_EX_TRANSPARENT` — the click passes through to the host below: native, Java, Electron, browsers). Can also be set per-task via `{"show_overlay": false}`. |
| `overlay_color` | `"red"` | `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `cyan`, `magenta`, `white`, `black`. |
| `overlay_duration` | `1000` | How long the overlay stays on screen (ms). |
| `overlay_width` | `4` | Outline thickness (px). |

> The legacy `overlay_enabled` key is deprecated; it is folded into
> `show_overlay` (logical AND) for back-compat.

## Waits / timeouts

| Key | Default | Meaning |
|---|---|---|
| `wait_timeout` | `30` | Default timeout (s) for `wait_until_found` / `wait_until_disappears`. |
| `screenshot_delay` | `0.1` | Pause before capturing the screen (lets late repaints settle). |

## Diagnostics / artifacts

| Key | Default | Meaning |
|---|---|---|
| `log_level` | `"INFO"` | `DEBUG` / `INFO` / `WARNING` / `ERROR`. Applied immediately on construction and whenever changed at runtime (`cfg.log_level = "DEBUG"` or `cfg.set("log_level", ...)`). |
| `log_format` | `"text"` | `"text"` (human `[INFO]` lines) or `"json"` (one JSON event per task on logger `visus.desktop.task_events` — **required** for `Session` recordings to capture events). |
| `artifacts_dir` | `"./visus-artifacts"` | Folder for failure screenshots / diagnostic dumps. |
| `screenshot_on_failure` | `True` | Save a screenshot when a task fails. |
| `screenshot_steps` | *(unset)* | When truthy, also save a screenshot after each **successful** step (so the HTML report shows every step, not just failures). |
| `screenshot_annotate` | `True` | Draw the matched `(x,y,w,h)` box + crosshair on saved step/failure screenshots, in the `overlay_color` / `overlay_width` style — independent of the on-screen overlay's timing. |

## Reading / mutating after construction

```python
cfg = BotVisionConfig({"confidence_threshold": 85.0})
cfg.confidence_threshold        # attribute proxy -> 85.0
cfg.get("overlay_duration")     # dict-style -> 1000
cfg.config["log_level"] = "DEBUG"   # in-place; logging re-applies on log_level
cfg.set("ocr_backend", "rapidocr")
```

Note: `VisusBot` builds its OCR engine once at construction. Changing
`ocr_backend` on an existing bot's config does **not** swap the active engine —
build a new `VisusBot`, or use the MCP `configure` tool / `visus configure`.

See also: [`cli.md`](cli.md), [`mcp.md`](mcp.md), [`api_reference.md`](api_reference.md).

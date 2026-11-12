# Installation & troubleshooting

## Install

```bash
pip install visus-desktop                 # core + the `visus` CLI
pip install "visus-desktop[native]"       # + pywinauto (native RPA, Windows)
pip install "visus-desktop[mcp]"          # + MCP server (the `visus-mcp` command)
pip install "visus-desktop[rapidocr]"     # + ONNX OCR backend (no Tesseract binary)
```

Extras compose: `pip install "visus-desktop[native,mcp,rapidocr]"`.

Console commands installed with the core package: `visus` (CLI),
`visus-doctor` (health check), `visus-mcp` (MCP server, needs `[mcp]`).

Python: 3.8+. Primary platform: Windows 10/11. The cross-platform paths
(OCR, screenshots, clipboard, image matching) also run on Linux/macOS; native
RPA (`native_*`) and the click-through overlay are Windows-only.

## OCR engine — two options

Visus needs an OCR engine for the text features (`find_text`, `click_text`,
`find_all_text`, `extract_text_from_region`, and the OCR layer of the cascade).

### Option A — Tesseract (default)

Requires the external Tesseract binary.

- **Windows**: download from <https://github.com/UB-Mannheim/tesseract/wiki>,
  install to `C:\Program Files\Tesseract-OCR\`, add it to `PATH`. Visus
  auto-detects the standard install paths.
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

Verify: `tesseract --version`, then `visus doctor`.

Extra languages: install the language data (e.g. `tesseract-ocr-por`) and set
`ocr_languages=["eng","por"]` in the config.

### Option B — RapidOCR (no external binary)

```bash
pip install "visus-desktop[rapidocr]"
```

Then select it: `BotVisionConfig({"ocr_backend": "rapidocr"})`, or
`visus text find-all "..." --ocr rapidocr`, or the MCP `configure` tool. The
ONNX models ship with the package — no Tesseract install, and Tesseract
auto-detection is skipped. First call is a little slower (models load once);
subsequent calls are fast.

## Linux system dependencies

The cross-platform features need a few system tools:

```bash
sudo apt-get install tesseract-ocr scrot xclip python3-tk
```

(`scrot` for screenshots, `xclip` for the clipboard, `python3-tk` only if you
use the legacy Tk overlay fallback.)

## Verify the environment

```bash
visus doctor            # human-readable [OK]/[FAIL] checks
visus doctor --json     # machine-readable; exit code != 0 means a check failed
```

`doctor` checks Tesseract, the display, the optional deps, and pywinauto.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `TesseractNotFoundError` / OCR errors | Tesseract not installed or not on `PATH` | Install it (above) and re-run `visus doctor`; or switch to `ocr_backend="rapidocr"`. |
| `find_text` / `find_all_text` returns nothing | OCR couldn't read the text, or wrong region | Lower `confidence_threshold` to ~50 to see what OCR read; widen/scope the `region`; try the other `ocr_backend`. |
| `click_image` returns `False` | Template not on screen, or DPI/scale mismatch | Re-capture the template at the live resolution; try `specific=False` (whole-screen + scale variations); or `matcher="pyscreeze"` if cv2 is too strict. |
| Click "doesn't land" / hits the overlay | (Fixed) the overlay is now a Win32 click-through window | Ensure you're on the current version; the overlay no longer intercepts clicks. |
| `log_level="DEBUG"` shows nothing extra | Logging configured before the value applied | It now applies on `BotVisionConfig` construction and whenever `log_level` changes. Noisy `PIL`/`RapidOCR` DEBUG lines: `logging.getLogger("PIL").setLevel("WARNING")`. |
| Report empty / direct calls missing | Direct calls are recorded only inside a task session | Use `rpa()` (it opens one), or `bot.start_task_session()` inside `Session.start_recording`. `log_format` no longer matters (0.4.0+). |
| No screenshots of successful steps | A manual `Session` captures only failures by default | `rpa()` takes one per step; with a manual `Session`, set `screenshot_steps=True`. |
| `native_dump_tree` returns `[]` | Non-accessible UI (Java Swing without Access Bridge, some Electron) | Fall back to OCR / image / `capture_element`. |
| Wrong window captured | Targeted by ambiguous title | Use `ensure_window(process="app.exe")` and pass `process`/longer `title`; check `matches` in its result. |
| `wait_for_stable_screen` times out | Animation never settles | Narrow `region`; raise `stable_for` to ~0.8s. |

See also: [`config.md`](config.md) for every config key, [`cli.md`](cli.md),
[`mcp.md`](mcp.md), [`api_reference.md`](api_reference.md).

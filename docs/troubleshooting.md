# Troubleshooting — Visus Desktop

Common symptoms and the smallest diagnostic that resolves them. If a
section's fix does not work, run `visus-doctor` first — its
`[OK]`/`[FAIL]` report often pinpoints the layer that is actually
broken.

```bash
visus-doctor              # console script, after install
python -m visus.desktop.doctor   # equivalent
```

---

## "I can't / don't want to install Tesseract"

Switch to the RapidOCR backend:

```bash
pip install 'visus-desktop[rapidocr]'
```

```python
bot = VisusBot({"ocr_backend": "rapidocr"})
```

No `.exe` install, no `tessdata/` folder. The first call downloads the
PP-OCR ONNX models (~10 MB) into your user cache. Caveats:

* Portuguese has no dedicated model — the `latin` model handles Latin
  scripts generically. If your bot reads accented Portuguese, keep
  Tesseract for now.
* No equivalent of `tessedit_char_whitelist=0123456789` — numeric-only
  fields may have lower accuracy than with Tesseract.

Run `visus-doctor` to confirm the backend is wired up correctly.

---

## OCR cannot find text that is clearly on screen

**Symptoms**

* `find_text("Login", region=(...))` returns `None` even though the
  word is visible.
* `bot.click_text(...)` raises `TextNotFoundError` (or
  `EarlyConfidenceNotReachedError`).

**Likely causes & fixes**

1. **Tesseract not installed or not on PATH.**
   `visus-doctor` reports `[FAIL] Tesseract OCR: …`. Install it:
   * Windows: [UB-Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki)
   * Linux: `sudo apt-get install tesseract-ocr`
   * macOS: `brew install tesseract`

2. **Wrong language pack.**
   Tesseract returns gibberish if you pass an unsupported language. The
   default is `eng`. For Portuguese forms:
   ```python
   bot = VisusBot({"ocr_languages": ["por"]})
   ```
   Make sure the corresponding `.traineddata` file exists in your
   tessdata folder (Windows install includes English only by default).

3. **Region too tight / too loose.**
   A region of 5 px is almost never enough — Tesseract needs context.
   Capture the region with `bot.save_screenshot("debug.png", region=...)`
   and inspect it. Aim for at least a 20-px padding around the text.

4. **Confidence threshold too high.**
   `BotVisionConfig` defaults to `confidence_threshold=75.0`. Lower it
   temporarily to see the raw candidates:
   ```python
   bot = VisusBot({"confidence_threshold": 30.0})
   bot.find_text("Login", region=(...))
   ```
   If the text suddenly appears, the OCR was already finding it but
   below your threshold. Improve image quality (contrast, scaling)
   rather than living at 30.

5. **Anti-aliasing / sub-pixel rendering.**
   Greyscale fonts on a dark theme often fail. Switch the target app
   to a light theme for testing, or pre-process the region in your bot
   (see the planned `image_processing` helpers).

---

## DPI / scaling wrong — clicks land in the wrong place

**Symptoms**

* The cursor lands several hundred pixels off target.
* `find_image` succeeds but the click misses.

**Cause.** Windows reports logical (pre-scaling) coordinates by
default to Python, while the actual pixel grid is at the system DPI
setting. `pyautogui` is DPI-unaware out of the box.

**Fix.** Ensure your Python interpreter is marked as **Per-Monitor V2**
DPI-aware. The simplest one-time fix on Windows:

```powershell
# In an admin PowerShell:
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers" `
  -Name "C:\path\to\python.exe" `
  -Value "~ HIGHDPIAWARE"
```

Or, programmatically at the top of your bot (Windows only):

```python
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
```

Then **restart the bot** — DPI awareness is locked at process start.

---

## `pywinauto` cannot connect to the app

**Symptoms**

* `bot.find_app_window(...)` raises `NotSupportedOnThisOS` or returns
  `None`.
* `pywinauto.findwindows.ElementNotFoundError` in the traceback.

**Likely causes & fixes**

1. **Not on Windows.** Native automation (`pywinauto`) is Windows-only.
   Linux/macOS support is on the roadmap (see X1 / X2 / X3 in the
   [improvements catalog](research/2026-05-28-improvements-catalog.md)).

2. **`pywinauto` not installed.**
   ```bash
   pip install "visus-desktop[native]"
   ```

3. **Wrong backend.** Some apps require `uia` (modern WPF / WinUI /
   .NET) while others only expose `win32`. Try both:
   ```python
   bot.connect_to_app(process_id=pid, backend="uia")
   bot.connect_to_app(process_id=pid, backend="win32")
   ```

4. **App not visible.** Minimized windows often refuse to enumerate
   their children. Call `bot.focus_window(...)` first.

5. **Admin elevation mismatch.** A non-elevated Python cannot
   introspect a window opened by an elevated process. Run Python as
   admin or relaunch the app non-elevated.

---

## Tcl/Tk error on overlay show

**Symptoms**

* `_tkinter.TclError: no display name and no $DISPLAY environment variable`
  on Linux/WSL.
* Overlay never appears on Windows; logs say `UnboundLocalError`.

**Likely causes & fixes**

1. **Headless environment.** Disable the overlay:
   ```python
   bot = VisusBot({"show_overlay": False})
   ```

2. **Missing `python3-tk` on Linux.**
   ```bash
   sudo apt-get install python3-tk
   ```

3. **WSL without an X server.** Either install
   [VcXsrv](https://sourceforge.net/projects/vcxsrv/) /
   [WSLg](https://github.com/microsoft/wslg) and export `DISPLAY`, or
   set `show_overlay=False`.

The `UnboundLocalError` regression was fixed in the v0.1 rebrand; if
you still hit it, you are running an older `bot-vision-suite`. Migrate
following [`migration.md`](migration.md).

---

## `KeyboardInterrupt` left a mouse button stuck

**Symptoms**

* After pressing Ctrl+C the mouse acts as if a button is held — clicks
  trigger drags, etc.

**Fix.** This was a real bug in `bot-vision-suite`; in `visus-desktop`
Phase 1 the executor releases `left`, `middle` and `right` on
interrupt automatically. If you still see it, your code is calling
`pyautogui.mouseDown` directly outside `execute_tasks` — either
rewrite to use `drag` (which is atomic) or wrap your loop in
`try/finally: pyautogui.mouseUp(button=…)`.

---

## Coverage runs explode with `cv2.gapi.wip.draw.Text`

**Symptom.** `pytest --cov` collects nothing; tracebacks reference
`cv2.typing` and a missing `Text` attribute.

**Fix.** Update to the current `visus-desktop`; the warm-up shim now
lives in `tests/conftest.py`. If you're on an older fork, copy the
top-of-file block from `tests/conftest.py` into your own conftest.

---

## Still stuck?

* Run `visus-doctor` and paste the output into your bug report.
* Set `config['log_format'] = 'json'` and attach the JSON log — every
  failed task carries a `failure_screenshot` path and a `duration_ms`.
* Open an issue at <https://github.com/matheuszwilk/visus-desktop/issues>
  with the failure screenshot and the task list that triggered it.

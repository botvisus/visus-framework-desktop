# Troubleshooting

Symptom → fix for the most common issues. Run `visus doctor` first — it checks
Tesseract, the display, the optional deps, and pywinauto in one go.

## OCR

- **`TesseractNotFoundError` / OCR raises** — the Tesseract binary isn't
  installed or isn't on `PATH`. Install it (see
  [installation.md](installation.md)) and re-run `visus doctor`, or switch to
  the bundled engine with `ocr_backend="rapidocr"` (no binary needed).
- **`find_text` / `find_all_text` returns nothing** — OCR couldn't read the
  text. Lower `confidence_threshold` to ~50 to see what OCR actually read,
  scope/normalize the `region`, set `filter_type` correctly
  (`letters`/`numbers`/`both`), or try the other `ocr_backend`.
- **Confidence looks wrong (>100)** — the Tesseract backend adds a small
  method bonus to its score; treat the threshold comparison as relative, not an
  absolute percentage.

## DPI / scaling

- **Clicks land slightly off, or image matches miss on a scaled display** — the
  template was captured at a different **DPI**/resolution than the live screen.
  Re-capture the template at the current scale, or use `specific=False` on
  `click_image` to allow scale variations. For coordinate clicks, prefer
  resolving the target through `smart_*` / `native_*` / OCR instead of
  hard-coded coordinates, which break on any DPI/layout change.
- **High-DPI virtual mouse** — `use_virtual_mouse=True` posts to client
  coordinates and does not apply manual DPI scaling, which is correct for
  per-monitor-DPI-aware hosts; if a click is misplaced, fall back to the
  physical mouse (the default).

## pywinauto / native RPA

- **`native_dump_tree` returns `[]`** — the UI isn't accessible (Java Swing
  without the Access Bridge, some Electron apps). Fall back to OCR / image /
  `capture_element`.
- **`native_*` import or backend errors** — install the extra:
  `pip install "visus-desktop[native]"` (pywinauto, Windows only).
- **Wrong control matched** — disambiguate with `found_index`, a more specific
  `control_type`/`auto_id`, or scope to a `window` title.

## Tcl/Tk (legacy overlay fallback)

- **`TclError` / Tk overlay won't open on Linux/macOS** — the click-through
  overlay is Win32-only; on other platforms Visus falls back to a Tk overlay,
  which needs Tk installed: `sudo apt-get install python3-tk`. The overlay is
  purely visual — if it can't open, automation still proceeds. To skip it
  entirely set `show_overlay=False`.

## Windows / capture

- **Wrong or minimized window captured** — call `ensure_window(process="…")`
  first; prefer `process` over `title` to avoid false-positives, and check the
  `matches` count in its result (`> 1` means ambiguous).
- **`wait_for_stable_screen` times out** — an animation never settled; narrow
  the `region` and raise `stable_for` to ~0.8s.

## Logging / reports

- **`log_level="DEBUG"` shows nothing new** — it applies on `BotVisionConfig`
  construction and whenever changed. Silence noisy third-party DEBUG with
  `logging.getLogger("PIL").setLevel("WARNING")` /
  `logging.getLogger("RapidOCR").setLevel("WARNING")`.
- **Session zip empty / no screenshots in the report** — set
  `log_format="json"` (so events are captured) and `screenshot_steps=True` (so
  successful steps are captured, not just failures).

See also: [installation.md](installation.md), [config.md](config.md),
[cli.md](cli.md), [mcp.md](mcp.md).

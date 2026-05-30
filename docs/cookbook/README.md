# Cookbook

Worked, copy-pasteable recipes for common automations. Each is plain
`from visus.desktop import VisusBot` Python; the same flows translate directly to
the [CLI](../cli.md) and [MCP](../mcp.md) surfaces.

| Recipe | What it shows |
|---|---|
| [Wait for a download](download-wait.md) | Click an export button, block until the file finishes writing. |
| [Fill a file dialog](file-dialogs.md) | Drive a native Save/Open dialog by path. |
| [Excel / grid input](excel-input.md) | Type values into a spreadsheet/grid cell by cell. |
| [Solve an image captcha](captcha.md) | OCR a captcha region and submit the text. |
| [Oracle Forms / legacy apps](oracle-forms.md) | Target non-accessible UIs with OCR + image. |

General pattern for every recipe:

1. `ensure_window(process="app.exe")` — open/focus, get the rect.
2. Prefer native (`native_*`) → capture/image → OCR, scoping every search to the
   window rect.
3. Wait deliberately (`wait_for_stable_screen`, `wait_for_file_stable`) instead
   of sleeping.
4. Optionally wrap in `Session.start_recording(...)` + `write_report(...)` for an
   auditable HTML artifact.

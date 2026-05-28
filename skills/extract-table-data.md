---
name: extract-table-data
description: OCR-scrape a table or list on screen into structured rows using extract_text_from_region with full_data so each cell carries its bounding box.
when_to_use: Activate when the user wants to read data off a visible grid / table / list (Excel-like, legacy ERP, report viewer) without exporting it.
---

# Extract a table into structured rows

## Steps

1. `take_screenshot()` — see the table; identify the bounding box of the entire grid area.
2. `extract_text_from_region(region=[x, y, w, h], full_data=true)` — returns every detected text fragment with its absolute box and confidence.
3. Group the fragments into rows: items whose `y` is within ~½ row height belong to the same row.
4. Within each row, sort by `x` to recover the column order.
5. If columns are misaligned, use the table header bounding boxes as anchors: read the headers first, then bucket each fragment whose `x` overlaps the header column into that column name.

## When the table is paged / scrollable

* Read the visible page.
* `keyboard_command(command="PageDown")` (or `click_image(scrollbar.png)`).
* `wait_for_stable_screen(region=<grid box>, stable_for=0.4, timeout=10)` — wait for the redraw to settle so OCR sees the new rows.
* Re-extract. Stop when the first row of the new page equals the last row of the previous page (no new content).

## When confidence is low

* Constrain `filter_type`: `"numbers"` for a column you know is numeric (drops "O" → "0" mistakes).
* Capture a tighter `region` (one column at a time) so OCR has less ambiguity.
* Snapshot the region for later inspection: `take_screenshot(region=…)` and attach to the report.

## Output shape to deliver to the user

```json
{
  "headers": ["Date", "Customer", "Amount"],
  "rows": [
    {"Date": "2026-05-01", "Customer": "ACME", "Amount": "1234.56"},
    ...
  ]
}
```

If the user asked for CSV, format yourself — do not call out to any extra MCP tool for the CSV step.

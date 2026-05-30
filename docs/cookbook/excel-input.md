# Excel / grid input — type values cell by cell

For a spreadsheet or data grid, navigate with the keyboard and type each value;
`Tab` moves right, `Enter` commits and moves down. This works on Excel, web
grids, and most table widgets without needing per-cell coordinates.

```python
from visus.desktop import VisusBot, ensure_window

ensure_window(process="EXCEL.EXE")
bot = VisusBot()

rows = [
    ["Name", "Qty", "Price"],
    ["Widget", "10", "2.50"],
    ["Gadget", "4", "9.99"],
]

# Click the first cell (or use the Name Box to jump to A1), then fill the grid.
bot.click_text("A1", region=(0, 0, 400, 200))   # adjust to your sheet

for row in rows:
    for value in row:
        bot.type_text(value)
        bot.keyboard_command("Tab")      # next column
    bot.keyboard_command("Enter")        # next row (Excel returns to col A)
```

**Notes**

- In Excel, pressing `Enter` after a run of `Tab`s returns to the column where
  the row started — so you don't need to count `Left` presses.
- For exact placement, jump via the Name Box: `bot.click_text("Name Box", ...)`
  or click it, then `bot.type_text("B5"); bot.keyboard_command("Enter")`.
- Paste is faster and more reliable than typing for large/Unicode values:

  ```python
  from visus.desktop import copy_to_clipboard
  copy_to_clipboard("a long\tvalue")          # \t and \n paste across cells
  bot.keyboard_command("Ctrl+V")
  ```
- To read values back, OCR the grid region with
  `bot.extract_text_from_region(region=(x, y, w, h), return_full_data=True)`.

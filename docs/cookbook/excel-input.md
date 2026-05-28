# Cookbook — Drive Excel from a CSV without COM

**Problem.** You have a CSV with 200 rows that need to land in cells
of an Excel workbook that's already open (e.g. a corporate template
with locked-down macros). COM / `openpyxl` are blocked; you have to
drive the UI directly.

**Solution.** Open the CSV with `csv.DictReader`, click into the first
cell with absolute coordinates, then type-Tab-Tab-Enter the row out.
Repeat. Use `keyboard_command` for `Tab` / `Enter` to avoid Excel's
auto-complete interference.

## Minimal example

```python
import csv
from visus.desktop import VisusBot

bot = VisusBot({
    "default_delay": 0.05,        # slow Excel down enough to keep up
    "show_overlay": False,        # avoid flashing the cursor outline
})

ROW_HEIGHT = 18         # pixels between rows in the visible grid
COL_WIDTH = 80          # pixels between columns
ANCHOR = (320, 220)     # screen coords of cell A2 (under the header row)

with open("input.csv", newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))

for row_index, row in enumerate(rows):
    x = ANCHOR[0]
    y = ANCHOR[1] + row_index * ROW_HEIGHT
    bot.execute_tasks([
        {"type": "click", "x": x, "y": y, "delay": 0.05},
        {"type": "type_text", "text": row["A"]},
        {"type": "keyboard_command", "command": "Tab"},
        {"type": "type_text", "text": row["B"]},
        {"type": "keyboard_command", "command": "Tab"},
        {"type": "type_text", "text": row["C"]},
        {"type": "keyboard_command", "command": "Enter"},
    ])
```

## Wait for the workbook to refresh before reading back

If a formula in column D recalculates after each row, give Excel a
moment to settle before sampling the result. ``wait_for_stable_screen``
shines here -- it waits until the formula bar stops repainting.

```python
from visus.desktop import wait_for_stable_screen

bot.execute_tasks([
    {"type": "click", "x": ANCHOR[0] + 3 * COL_WIDTH,
     "y": ANCHOR[1] + row_index * ROW_HEIGHT},
])
assert wait_for_stable_screen(
    region=(ANCHOR[0], ANCHOR[1] - 30, COL_WIDTH * 4, ROW_HEIGHT * 2),
    stable_for=0.4,
    timeout=5,
), "Excel did not finish recalculating"
```

## Production tips

* **COM is always better when available.** This recipe is the
  "corporate Excel is locked down, drive the UI" fallback. If you can
  use ``openpyxl`` or ``win32com.client``, do.
* **Anchor the start cell with `find_text`** rather than hard-coding
  pixel coordinates -- Excel's grid shifts with zoom, frozen panes
  and font scaling. Find the header text, then offset down/right by
  one row/column.
* **Disable the cursor overlay** (`show_overlay=False`) and **set
  `screen_cache_ms=0`** while clicking back-to-back cells -- the
  cache would otherwise return the pre-click frame.

## Caveats

* Excel may pop a Smart Tag or auto-fill suggestion after every
  Enter. Press `Escape` between rows to dismiss it.
* If you type a number that starts with `0`, Excel strips the
  leading zero. Prefix with an apostrophe (`"'0123"`) to keep it as
  text.

## See also

* [`wait_for_stable_screen`](download-wait.md) -- waits for the grid
  to settle.
* [Cookbook index](README.md)

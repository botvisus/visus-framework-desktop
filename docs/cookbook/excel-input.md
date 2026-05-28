# Cookbook — Driving Excel from a CSV (stub)

> 🚧 **Stub.** Recipe planned for an upcoming release.

## What this recipe will cover

* Open Excel via `launch` (or assume it's already open).
* Read rows from a CSV with `csv.DictReader`.
* For each row: click the target cell, type the value, press `Tab` or
  `Enter` to advance.
* Use the `sendtext` task-list field to skip the OCR step and just type
  after a cell is focused.

## Sketch

```python
import csv
from visus.desktop import VisusBot

bot = VisusBot()

with open("input.csv", newline="", encoding="utf-8") as fh:
    rows = list(csv.DictReader(fh))

for row in rows:
    bot.execute_tasks([
        {"type": "click", "x": 320, "y": 220},   # cell A2
        {"type": "type_text", "text": row["A"]},
        {"type": "keyboard_command", "command": "Tab"},
        {"type": "type_text", "text": row["B"]},
        {"type": "keyboard_command", "command": "Enter"},
    ])
```

## Caveats

* The native Excel automation API (COM / `openpyxl`) is **always** more
  reliable than UI driving — use this recipe only when COM is locked
  down. The planned `I2` integration will wrap `openpyxl` directly.
* Excel's cell-coordinate system shifts with frozen panes and zoom
  level; capture screenshots before commit to anchor the click targets.

## See also

* [Cookbook index](README.md)

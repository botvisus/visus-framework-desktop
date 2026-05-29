#!/usr/bin/env python
"""Produce a session report that INCLUDES failed steps, to show what the HTML
report renders for an error (detailed reason + failure screenshot + telemetry).

No keyboard/mouse input is used (so PyAutoGUI's fail-safe can't interfere):
  * step 1 succeeds  -> extract_text (an OCR read of a screen region)
  * step 2 fails     -> a real template that is NOT in the given region
  * step 3 fails     -> OCR text that does not exist on screen

Run:  python simulate_error.py
"""

from __future__ import annotations

from pathlib import Path

from visus.desktop import VisusBot
from visus.desktop.core.session import Session

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
TEMPLATE = str(HERE / "elements" / "btn_salvar.png")  # exists, but won't be there


def main() -> int:
    bot = VisusBot(config={"log_format": "json", "screenshot_steps": True})
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    zip_path = ARTIFACTS / "error_demo.zip"
    html_path = ARTIFACTS / "error_demo.html"

    tasks = [
        # 1) SUCCESS — read text from a region (no click, no input).
        {"type": "extract_text", "region": [0, 0, 400, 60]},
        # 2) FAIL — the template exists on disk but is not in this tiny region.
        {"image": TEMPLATE, "region": [0, 0, 120, 120], "confidence": 0.95},
        # 3) FAIL — OCR text that simply is not on screen.
        {"text": "ZZ_NAO_EXISTE_ZZ", "region": [0, 0, 600, 300]},
    ]

    with Session.start_recording(zip_path):
        results = bot.execute_tasks(tasks)

    for r in results:
        print(
            f"[{'OK' if r.success else 'FAIL'}] task {r.task_index} "
            f"attempts={r.attempts} error={r.error!r} shot={bool(r.failure_screenshot)}"
        )
    Session.write_report(zip_path, html_path)
    print(f"report -> {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

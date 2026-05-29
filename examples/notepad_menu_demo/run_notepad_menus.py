#!/usr/bin/env python
"""Click each Notepad menu (Arquivo -> Editar -> Formatar -> Exibir -> Ajuda)
in sequence, driven entirely by the templates captured with
``capture_element`` (saved under ``elements/``), and record the run as a
session zip + HTML report.

Runs standalone, no AI in the loop::

    python run_notepad_menus.py

What it demonstrates (the recommended robust flow):
  1. ``ensure_window(process="notepad.exe")`` -- open/restore/focus the right
     window FIRST (launches Notepad if it is not running). Matching by
     *process* avoids title false-positives (e.g. an editor showing a file
     named ``notepad_*.py``).
  2. Scope every image search to that window's rectangle (``region=``) so a
     template can never match a look-alike on another window.
  3. ``Session.start_recording(zip)`` around ``bot.execute_tasks([...])`` --
     each step is an image task that finds + clicks the menu; an ``Esc``
     keyboard command closes the opened menu before the next one.
  4. ``Session.replay`` + ``Session.write_report`` -- inspect the run and
     produce a single-file HTML report.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from visus.desktop import VisusBot, ensure_window
from visus.desktop.core.session import Session

HERE = Path(__file__).resolve().parent
ELEMENTS = HERE / "elements"
ARTIFACTS = HERE / "artifacts"
MENUS = ["arquivo", "editar", "formatar", "exibir", "ajuda"]


def ensure_notepad() -> dict:
    """Open/restore/focus Notepad and return its window state."""
    state = ensure_window(process="notepad.exe")
    if not state["found"]:
        subprocess.Popen(["notepad.exe"])  # noqa: S607 - demo launcher
        for _ in range(20):
            time.sleep(0.25)
            state = ensure_window(process="notepad.exe")
            if state["found"]:
                break
    if not state["found"]:
        sys.exit("Could not find or open Notepad.")
    return state


def main() -> int:
    state = ensure_notepad()
    rect = state["rect"]
    region = (rect["x"], rect["y"], rect["width"], rect["height"])
    print(f"Notepad pid={state['pid']} at {region} (foreground={state['foreground']})")

    # log_format='json' is what Session records on the task_events logger.
    bot = VisusBot(config={"log_format": "json"})

    tasks: list[dict] = []
    for name in MENUS:
        # Image task: find the template inside the Notepad rect, then click it.
        tasks.append(
            {"image": str(ELEMENTS / f"{name}.png"), "region": region, "confidence": 0.8}
        )
        # Close the menu we just opened before moving to the next one.
        # NOTE: command tokens are case-sensitive -- it is "Escape", not "Esc".
        tasks.append({"type": "keyboard_command", "command": "Escape"})

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    zip_path = ARTIFACTS / "notepad_menus.zip"
    html_path = ARTIFACTS / "notepad_menus.html"

    with Session.start_recording(zip_path):
        results = bot.execute_tasks(tasks)

    ok = sum(1 for r in results if r.success)
    print(f"{ok}/{len(results)} steps succeeded")
    for r in results:
        print(f"  [{'OK' if r.success else 'FAIL'}] {r.task_name}")

    events = Session.replay(zip_path)
    print(f"recorded {len(events)} events -> {zip_path}")
    Session.write_report(zip_path, html_path)
    print(f"report -> {html_path}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
"""End-to-end demo: open Notepad, type a name, and "Save As" into Downloads —
recorded as a session zip + HTML report. Runs standalone, no AI in the loop::

    python run_notepad_save.py            # saves Matheus.txt
    python run_notepad_save.py Joao       # saves Joao.txt

Flow (the recommended robust pattern):
  1. ensure_window(process="notepad.exe") — launch/restore/focus the RIGHT
     window first (matching by process avoids title false-positives).
  2. Record with Session.start_recording around bot.execute_tasks([...]):
       - type the name
       - Ctrl+S  -> opens the "Save As" dialog
       - select the filename field (Ctrl+A) and type the FULL target path
         (typing a full path overrides the dialog's current folder, so the
         file always lands in Downloads regardless of where it opened)
       - Enter   -> save
  3. wait_for_file_stable — confirm the file is written.
  4. Session.write_report — produce the HTML report.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from visus.desktop import VisusBot, ensure_window, wait_for_file_stable
from visus.desktop.core.screen import wait_for_stable_screen
from visus.desktop.core.session import Session

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DOWNLOADS = Path(os.environ["USERPROFILE"]) / "Downloads"


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


def main(name: str = "Matheus") -> int:
    target = DOWNLOADS / f"{name}.txt"
    # Start clean so the "Save As" never hits a "replace?" prompt.
    if target.exists():
        target.unlink()

    state = ensure_notepad()
    print(f"Notepad pid={state['pid']} foreground={state['foreground']}")

    # log_format='json' is what Session records; screenshot_steps captures a
    # screenshot after each successful step for the report timeline.
    bot = VisusBot(config={"log_format": "json", "screenshot_steps": True})

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    zip_path = ARTIFACTS / "notepad_save.zip"
    html_path = ARTIFACTS / "notepad_save.html"

    with Session.start_recording(zip_path):
        # 1) Select-all (replace any pre-existing content), type the name,
        #    then open the Save As dialog.
        bot.execute_tasks(
            [
                {"type": "keyboard_command", "command": "Ctrl+A"},
                {"type": "type_text", "text": name},
                {"type": "keyboard_command", "command": "Ctrl+S"},
            ]
        )
        # 2) Wait for the dialog to appear (the blinking caret keeps the screen
        #    from ever being perfectly "stable", so don't rely on the return).
        wait_for_stable_screen(stable_for=0.4, timeout=5)
        time.sleep(0.8)
        # 3) Select the filename field, type the full target path, save.
        bot.execute_tasks(
            [
                {"type": "keyboard_command", "command": "Ctrl+A"},
                {"type": "type_text", "text": str(target)},
                {"type": "keyboard_command", "command": "Enter"},
            ]
        )

    saved = wait_for_file_stable(str(target), timeout=10)
    print(f"saved={saved} -> {target}")
    if saved:
        print(f"content: {target.read_text(encoding='utf-8')!r}")

    events = Session.replay(zip_path)
    print(f"recorded {len(events)} events -> {zip_path}")
    Session.write_report(zip_path, html_path)
    print(f"report -> {html_path}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "Matheus"))

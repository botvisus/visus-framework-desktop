"""Typing & keyboard demo — sends REAL keystrokes to the focused window.

It waits for you to focus a safe text field (e.g. open Notepad / a text editor),
then types a sentence (including special key sequences) and sends a shortcut.

Run:  python manual_tests/05_typing_keyboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import time

from visus.desktop import VisusBot

COUNTDOWN = 6  # seconds to switch to your target window


def main() -> int:
    print(__doc__)
    print("!! This will type into whatever window is focused. Open a blank text editor now.")
    try:
        input("Press Enter when you're ready (then switch to the text field)... ")
    except EOFError:
        pass  # allow running non-interactively

    try:
        bot = VisusBot()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Could not create VisusBot(): {exc}")
        return 1

    for remaining in range(COUNTDOWN, 0, -1):
        print(f"  typing in {remaining}s — focus your text field now...", end="\r")
        time.sleep(1)
    print(" " * 60, end="\r")

    print("Typing a plain sentence ...")
    bot.type_text("Hello from Visus Desktop! ")

    print("Typing with special sequences ({enter}, {ctrl}a) ...")
    bot.type_text("Line 1{enter}Line 2 — select-all next{enter}")
    bot.type_text("{ctrl}a")  # selects all text in the field

    print("Sending a keyboard command (right arrow to deselect) ...")
    # Use a harmless command so we don't delete the user's content.
    if "Right" in bot.get_available_keyboard_commands():
        bot.keyboard_command("Right")

    print("\nDone. [OK]  Check your text field to see the result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

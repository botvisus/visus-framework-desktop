"""Interactive menu — pick a manual test to run.

Run:  python manual_tests/06_menu.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCRIPTS = [
    ("00_environment_check.py", "Environment check (safe, no screen actions)"),
    ("01_text_helpers.py", "Text helpers: clean_text / matches_filter (safe)"),
    ("02_overlay_demo.py", "Overlay demo: draw colored boxes (visual only)"),
    ("03_screen_ocr.py", "Screen OCR: read text from the screen (read-only)"),
    ("04_find_on_screen.py", "Find text/image on screen (read-only by default)"),
    ("05_typing_keyboard.py", "Typing & keyboard (REAL keystrokes!)"),
]


def main() -> int:
    while True:
        print("\n" + "=" * 60)
        print("Visus Desktop — manual test menu")
        print("=" * 60)
        for i, (_, desc) in enumerate(SCRIPTS):
            print(f"  {i}. {desc}")
        print("  q. quit")

        try:
            choice = input("\nChoose a script: ").strip().lower()
        except EOFError:
            return 0

        if choice in ("q", "quit", "exit"):
            return 0
        if not choice.isdigit() or not (0 <= int(choice) < len(SCRIPTS)):
            print("  invalid choice")
            continue

        script = SCRIPTS[int(choice)][0]
        extra: list[str] = []
        if script == "04_find_on_screen.py":
            text = input("  text to find (blank to skip): ").strip()
            if text:
                extra += ["--text", text]
            image = input("  image path to find (blank to skip): ").strip()
            if image:
                extra += ["--image", image]
            if not extra:
                print("  nothing to search; back to menu")
                continue

        print(f"\n>>> running {script} {' '.join(extra)}\n")
        subprocess.run([sys.executable, str(HERE / script), *extra], check=False)


if __name__ == "__main__":
    raise SystemExit(main())

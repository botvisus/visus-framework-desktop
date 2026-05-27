"""Overlay demo — draws colored rectangles on your screen (no clicks).

Cycles through every available overlay color, drawing a box in the center of the
primary monitor. Purely visual; nothing is clicked or typed.

Run:  python manual_tests/02_overlay_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import time

import pyautogui

from visus.desktop import VisusBot
from visus.desktop.core.overlay import show_overlay


def main() -> int:
    screen_w, screen_h = pyautogui.size()
    box_w, box_h = 360, 140
    region = (
        (screen_w - box_w) // 2,
        (screen_h - box_h) // 2,
        box_w,
        box_h,
    )

    colors = VisusBot.get_available_overlay_colors()
    print(f"Drawing a {box_w}x{box_h} overlay in the center of your "
          f"{screen_w}x{screen_h} screen.")
    print(f"Cycling through {len(colors)} colors — watch the screen...\n")

    for color in colors:
        print(f"  overlay color: {color}")
        show_overlay(region, duration=900, color=color, width=5)
        time.sleep(1.1)

    print("\nDone. [OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

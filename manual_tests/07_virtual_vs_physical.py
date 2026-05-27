"""Virtual vs physical mouse — do they target the SAME position? (no GUI needed)

Hover your mouse over the on-screen element you want to test. After a short countdown
the script captures that point and:

  1) PROVES the position is correct by comparing the client coordinates the virtual
     mouse computes against the OS ground truth (win32 ScreenToClient). If they match,
     the virtual click targets the exact same pixel as a physical click.
  2) Fires a PHYSICAL click (moves the real cursor) and a VIRTUAL click (cursor stays)
     at that point, so you can watch whether both activate the same element.

This uses only the Win32 API (no Tkinter), so it works even if your Python's Tcl/Tk
is broken.

Run:  python manual_tests/07_virtual_vs_physical.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import time

from visus.desktop.core.virtual_mouse import VirtualMouse
from visus.desktop.utils.config import BotVisionConfig

COUNTDOWN = 5


def main() -> int:
    print(__doc__)

    try:
        import pyautogui
        import win32gui
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] missing runtime dependency: {exc}")
        print("       Install with: pip install pyautogui pywin32")
        return 1

    try:
        config = BotVisionConfig(
            {"use_virtual_mouse": True, "click_duration": 0, "movement_duration": 0}
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Could not build config: {exc}")
        print("       Is Tesseract OCR installed? See the project README.")
        return 1

    vm = VirtualMouse(config)
    print(f"virtual mouse available on this system: {vm.is_virtual_available()}")
    if not vm.is_virtual_available():
        print("  -> win32 not available; virtual clicks FALL BACK to physical "
              "(pip install pywin32).")

    print(f"\nHover your mouse over the element to test. Capturing in {COUNTDOWN}s...")
    for remaining in range(COUNTDOWN, 0, -1):
        print(f"  {remaining}...", end="\r")
        time.sleep(1)
    print(" " * 40, end="\r")

    pos = pyautogui.position()
    px, py = int(pos[0]), int(pos[1])
    target = (px, py)
    print(f"Target screen point: {target}")

    hwnd = win32gui.WindowFromPoint(target)
    if not hwnd:
        print("[FAIL] No window found under that point.")
        return 1
    title = win32gui.GetWindowText(hwnd) or "(no title)"

    # --- Position proof: our computed client coords must equal the OS ground truth ---
    our_client = vm._resolve_client_coordinates(hwnd, target)[:2]
    os_client = tuple(win32gui.ScreenToClient(hwnd, target))
    match = tuple(our_client) == os_client

    print("\n" + "=" * 64)
    print("POSITION PROOF")
    print("=" * 64)
    print(f"  window under point        : {title!r} (hwnd={hwnd})")
    print(f"  VirtualMouse client coords : {tuple(our_client)}  <- what the click posts")
    print(f"  OS ScreenToClient (truth)  : {os_client}")
    print(f"  MATCH: {match}  -> "
          f"{'virtual click targets the correct pixel' if match else 'OFF — coordinate bug!'}")
    print("=" * 64)

    # --- Live clicks so you can watch the behavior ---------------------------
    print("\nFiring PHYSICAL click (the real cursor moves)...")
    r_phys = vm.click(px, py, button="left", use_virtual=False)
    print(f"  physical click() -> {r_phys}")
    time.sleep(0.8)

    print("Firing VIRTUAL click (the real cursor should NOT move)...")
    r_virt = vm.click(px, py, button="left", use_virtual=True)
    print(f"  virtual click()  -> {r_virt}")

    print("\nDone. [OK]")
    print("If both clicks activated the same element, position is correct (proof above).")
    print("If the virtual click did nothing, this target ignores posted mouse messages")
    print("(common in Chrome/Electron/Java/Oracle Forms) — use the physical mouse there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

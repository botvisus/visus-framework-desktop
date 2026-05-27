"""Virtual vs physical mouse — do they click the same spot? Does the virtual click register?

This opens a small target window that RECORDS every click it receives (and the exact
client coordinates). It then fires a PHYSICAL click and a VIRTUAL click at the *same*
screen point and reports, side by side, what the window actually received.

Why this matters: the virtual mouse on Windows clicks by POSTING WM_LBUTTONDOWN/UP
messages to the window under the point (it never moves the real cursor). Many apps
(Chrome/Electron, Java/Oracle Forms, games, custom-drawn UIs) IGNORE posted mouse
messages — so the virtual click silently does nothing. This test shows whether your
environment honors it, and whether the position matches the physical click.

Run:  python manual_tests/07_virtual_vs_physical.py

Note: this moves the real mouse (for the physical click) and briefly forces the target
window on top. Don't fight it for the mouse during the ~4 seconds it runs.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import threading
import time
import tkinter as tk

from visus.desktop.core.virtual_mouse import VirtualMouse
from visus.desktop.utils.config import BotVisionConfig

# Shared state between the click handler (main/Tk thread) and the worker thread.
received: list[dict] = []
phase = {"name": "idle"}


def main() -> int:
    print(__doc__)

    # Build a config + the virtual mouse. (BotVisionConfig needs Tesseract installed.)
    try:
        config = BotVisionConfig(
            {"use_virtual_mouse": True, "click_duration": 0, "movement_duration": 0}
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Could not build config: {exc}")
        print("       Is Tesseract OCR installed? See the project README.")
        return 1

    vm = VirtualMouse(config)
    print(f"\nvirtual mouse available on this system: {vm.is_virtual_available()}")
    if not vm.is_virtual_available():
        print("  -> win32 not available; virtual clicks will FALL BACK to physical.")
        print("     Install with: pip install pywin32")

    # --- Target window that records what it receives -------------------------
    root = tk.Tk()
    root.title("Visus mouse test — click target")
    root.geometry("640x460+200+200")
    root.attributes("-topmost", True)  # keep it frontmost so both clicks land here

    canvas = tk.Canvas(root, width=640, height=400, bg="white", highlightthickness=0)
    canvas.pack()
    status = tk.Label(root, text="Preparing...", font=("Segoe UI", 11))
    status.pack(fill="x")

    def on_click(event: tk.Event, button: str) -> None:
        rec = {
            "phase": phase["name"],
            "button": button,
            "client": (event.x, event.y),
            "screen": (event.x_root, event.y_root),
        }
        received.append(rec)
        color = "#1e88e5" if phase["name"] == "PHYSICAL" else "#e53935"
        canvas.create_oval(
            event.x - 8, event.y - 8, event.x + 8, event.y + 8, outline=color, width=3
        )
        canvas.create_text(
            event.x, event.y - 16, text=phase["name"], fill=color, font=("Segoe UI", 9)
        )
        status.config(text=f"Received {phase['name']} {button} click at client {rec['client']}")

    canvas.bind("<Button-1>", lambda e: on_click(e, "left"))
    canvas.bind("<Button-3>", lambda e: on_click(e, "right"))

    # --- Worker thread that fires the two clicks -----------------------------
    def worker() -> None:
        time.sleep(1.0)  # let the window render and come to front
        root.update_idletasks()
        target_x = canvas.winfo_rootx() + canvas.winfo_width() // 2
        target_y = canvas.winfo_rooty() + canvas.winfo_height() // 2
        expected_client = (canvas.winfo_width() // 2, canvas.winfo_height() // 2)

        print(f"\nTarget screen point: ({target_x}, {target_y})")
        print(f"Expected client point inside the canvas: {expected_client}\n")

        phase["name"] = "PHYSICAL"
        print(f"-> Firing PHYSICAL click at screen ({target_x}, {target_y}) ...")
        ok_phys = vm.click(target_x, target_y, button="left", use_virtual=False)
        print(f"   physical click() returned: {ok_phys}")
        time.sleep(1.0)

        phase["name"] = "VIRTUAL"
        print(f"-> Firing VIRTUAL click at screen ({target_x}, {target_y}) ...")
        ok_virt = vm.click(target_x, target_y, button="left", use_virtual=True)
        print(f"   virtual click() returned: {ok_virt}")
        time.sleep(1.0)

        phase["name"] = "done"
        root.after(0, lambda: report(expected_client))

    def report(expected_client: tuple[int, int]) -> None:
        phys = [r for r in received if r["phase"] == "PHYSICAL"]
        virt = [r for r in received if r["phase"] == "VIRTUAL"]

        print("\n" + "=" * 64)
        print("RESULT")
        print("=" * 64)
        print(f"  expected client point : {expected_client}")
        print(f"  PHYSICAL clicks received: {len(phys)}  "
              f"{phys[0]['client'] if phys else '(none)'}")
        print(f"  VIRTUAL  clicks received: {len(virt)}  "
              f"{virt[0]['client'] if virt else '(none)'}")

        if phys and virt:
            same = phys[0]["client"] == virt[0]["client"]
            print(f"\n  Same client position? {'YES' if same else 'NO'} "
                  f"(physical {phys[0]['client']} vs virtual {virt[0]['client']})")
            print("  => Virtual mouse WORKS here and lands at the same spot.")
        elif phys and not virt:
            print("\n  => The PHYSICAL click registered but the VIRTUAL click did NOT.")
            print("     This is the 'it wasn't clicking' symptom: this target ignores")
            print("     posted WM_LBUTTONDOWN messages. The virtual mouse cannot drive it.")
            print("     Use the physical mouse (use_virtual_mouse=False) for such apps.")
        elif not phys:
            print("\n  => Even the PHYSICAL click did not register on the window.")
            print("     The window may not have been focused/on top. Try running again.")

        print("=" * 64)
        root.after(3000, root.destroy)

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

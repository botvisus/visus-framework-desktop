#!/usr/bin/env python
"""End-to-end demo (IMAGE version): open Notepad, type a name, and "Save As"
into Downloads by CLICKING the dialog elements via template images instead of
typing a path. Runs standalone, recorded as a session zip + HTML report::

    python run_notepad_save_by_image.py            # saves Matheus.txt
    python run_notepad_save_by_image.py Joao       # saves Joao.txt

Templates used (captured once with `capture_element`, saved under elements/):
  * elements/nav_downloads.png  — the "Downloads" item in the dialog sidebar
  * elements/btn_salvar.png     — the "Salvar" button text
  * elements/btn_cancelar.png   — the "Cancelar" button (a UNIQUE anchor)

Flow:
  1. ensure_window(process="notepad.exe") — launch/focus a FRESH (untitled)
     Notepad so Ctrl+S opens the "Save As" dialog.
  2. type the name, Ctrl+S -> dialog.
  3. wait for the "Salvar como" window and read its rect (retry — the window
     takes a beat to appear; querying too early returns nothing).
  4. set the filename in the focused "Nome" field (Ctrl+A + type), then
     CLICK BY IMAGE:
       - Downloads sidebar item — search scoped to the LEFT sidebar sub-region
         only, so it can't match the "Downloads" word in the top address bar.
       - Salvar button — located RELATIVE to the unique "Cancelar" anchor
         (`relative_image` with a small `max_distance`), so it can't match the
         word "Salvar" in the dialog TITLE far above the buttons.
     (Both fixes address template-matching that otherwise grabs the wrong
     same-text occurrence.)
  5. wait_for_file_stable -> confirm; Session.write_report -> HTML.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from visus.desktop import VisusBot, ensure_window, get_window, wait_for_file_stable
from visus.desktop.core.session import Session

HERE = Path(__file__).resolve().parent
ELEMENTS = HERE / "elements"
ARTIFACTS = HERE / "artifacts"
DOWNLOADS = Path(os.environ["USERPROFILE"]) / "Downloads"
NAV_DOWNLOADS = str(ELEMENTS / "nav_downloads.png")
BTN_SALVAR = str(ELEMENTS / "btn_salvar.png")
BTN_CANCELAR = str(ELEMENTS / "btn_cancelar.png")


def _park_cursor() -> None:
    """Move the cursor to screen center so PyAutoGUI's corner fail-safe can't
    trip before we start (uses ctypes so it works even if the cursor is
    already parked in a corner, which pyautogui.moveTo would refuse)."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        x = user32.GetSystemMetrics(0) // 2
        y = user32.GetSystemMetrics(1) // 2
        user32.SetCursorPos(int(x), int(y))
    except Exception:
        pass


def ensure_fresh_notepad() -> dict:
    """Open a fresh, untitled Notepad (so Ctrl+S opens 'Save As')."""
    state = ensure_window(process="notepad.exe")
    if not state["found"] or "Sem título" not in (state["title"] or ""):
        subprocess.Popen(["notepad.exe"])  # noqa: S607 - demo launcher
        for _ in range(20):
            time.sleep(0.25)
            state = ensure_window(process="notepad.exe")
            if state["found"] and "Sem título" in (state["title"] or ""):
                break
    if not state["found"]:
        sys.exit("Could not find or open Notepad.")
    return state


def wait_for_dialog(timeout: float = 10.0) -> dict:
    """Wait for the 'Salvar como' window and return its rect (x, y, w, h)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        win = get_window("Salvar como")
        if win and win.get("width"):
            return win
        time.sleep(0.25)
    sys.exit("The 'Salvar como' dialog never appeared.")


def main(name: str = "Matheus") -> int:
    target = DOWNLOADS / f"{name}.txt"
    if target.exists():
        target.unlink()  # start clean -> no "replace?" prompt

    _park_cursor()  # keep the cursor off the fail-safe corners
    state = ensure_fresh_notepad()
    print(f"Notepad pid={state['pid']} foreground={state['foreground']}")

    # json = recordable events; screenshot_steps = capture a screenshot after
    # every successful step so the HTML report shows each one.
    bot = VisusBot(config={"log_format": "json", "screenshot_steps": True})
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    zip_path = ARTIFACTS / "notepad_save_by_image.zip"
    html_path = ARTIFACTS / "notepad_save_by_image.html"

    with Session.start_recording(zip_path):
        # Select-all first so we REPLACE any pre-existing content (a reused
        # untitled Notepad), then type the name and open the Save As dialog.
        bot.execute_tasks(
            [
                {"type": "keyboard_command", "command": "Ctrl+A"},
                {"type": "type_text", "text": name},
                {"type": "keyboard_command", "command": "Ctrl+S"},
            ]
        )
        dlg = wait_for_dialog()
        region = [dlg["x"], dlg["y"], dlg["width"], dlg["height"]]
        # Left sidebar only (skip the top toolbar/address bar) so the
        # "Downloads" template can't match the word in the address breadcrumb.
        sidebar = [dlg["x"], dlg["y"] + 90, 205, dlg["height"] - 140]
        print(f"Save As dialog at {region}; sidebar search region {sidebar}")

        # Set the filename in the focused 'Nome' field, then click BY IMAGE.
        # Uses backtrack (retry from the start on a miss), wait_until_found
        # (poll for the element before clicking), and wait_until_disappears
        # (confirm the dialog actually closed after saving).
        bot.execute_tasks(
            [
                {"type": "keyboard_command", "command": "Ctrl+A"},
                {"type": "type_text", "text": f"{name}.txt"},
                # Wait for the Downloads sidebar item to render, then click it
                # (scoped to the sidebar). Retry the flow if it never appears.
                {
                    "image": NAV_DOWNLOADS,
                    "region": sidebar,
                    "confidence": 0.8,
                    "wait_until_found": True,
                    "wait_timeout": 10,
                    "backtrack": True,
                },
                # Click "Salvar" located RELATIVE to the unique "Cancelar"
                # anchor (so the dialog TITLE 'Salvar como' can't be hit), then
                # wait until "Cancelar" DISAPPEARS = the dialog closed = saved.
                {
                    "type": "relative_image",
                    "anchor_image": BTN_CANCELAR,
                    "target_image": BTN_SALVAR,
                    "max_distance": 180,
                    "confidence": 0.8,
                    "specific": True,
                    "target_region": region,
                    "backtrack": True,
                    # Consumed by the post-click "wait to disappear" step:
                    "image": BTN_CANCELAR,
                    "region": region,
                    "wait_until_disappears": True,
                    "wait_timeout": 10,
                },
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

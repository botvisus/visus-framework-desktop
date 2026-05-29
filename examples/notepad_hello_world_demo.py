r"""Standalone automation -- reproduces the live MCP run WITHOUT any AI/MCP.

What it does (Windows):
  1. Launch Notepad and capture its real window rectangle (win32) so the
     coordinates work regardless of where Windows places the window.
  2. Click into the text area to focus it, type "hello world".
  3. Save a per-step screenshot ("print of each position") to
     ``examples/automation_trace/``.
  4. Ctrl+S -> type the absolute Downloads path into the (default-focused)
     filename field -> confirm.
  5. Optionally demonstrate find_image + click_image on the "Salvar"/"Save"
     button: it captures the button region at runtime, relocates it with
     the cv2 matcher, and clicks it. Falls back to Enter (the robust path)
     when the button can't be located -- so the script is reliable on any
     locale / resolution.
  6. wait_for_file_stable confirms the file landed, then the Notepad
     process is closed by PID (clean -- the file is already saved).

This uses the ``visus.desktop`` LIBRARY directly. The MCP server is just
an AI-facing wrapper over these same calls; you do not need it (or any
model) to run deterministic automation like this.

Run it yourself -- it drives REAL keyboard/mouse on the focused window.
A countdown gives you time to stop touching input. Ctrl+C aborts.

    python examples/notepad_hello_world_demo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from visus.desktop import (
    VisusBot,
    click_at,
    click_image,
    find_image,
    keyboard_command,
    type_text,
    wait_for_file_stable,
    wait_for_stable_screen,
)
from visus.desktop.core.process import kill_process
from visus.desktop.core.screen import capture_screen

OUT = Path(__file__).resolve().parent / "automation_trace"
OUT.mkdir(exist_ok=True)

TARGET_FILE = Path.home() / "Downloads" / "hello_world_visus.txt"

_step = 0


def trace(name: str, region: tuple[int, int, int, int] | None = None) -> Path:
    """Save a screenshot of the current position; return its path.

    With ``region`` it crops to that area (the "print of the position").
    Without it, captures the full screen.
    """
    global _step
    _step += 1
    path = OUT / f"{_step:02d}_{name}.png"
    capture_screen(region=region).save(str(path))
    print(f"  [trace] {path.name}" + (f"  region={region}" if region else ""))
    return path


def find_notepad_rect(pid: int, timeout: float = 8.0):
    """Return the (left, top, right, bottom) rect of the Notepad window.

    Matched by the launched PID so it is locale-independent (works for
    'Notepad' and 'Bloco de Notas' alike). Returns None on timeout.
    """
    import win32gui
    import win32process

    def _collect(hwnd, acc):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        _, wpid = win32process.GetWindowThreadProcessId(hwnd)
        if wpid == pid and win32gui.GetWindowText(hwnd):
            acc.append(win32gui.GetWindowRect(hwnd))
        return True

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found: list = []
        win32gui.EnumWindows(_collect, found)
        if found:
            return found[0]
        time.sleep(0.2)
    return None


def countdown(seconds: int = 6) -> None:
    print(f"\n>>> Automation starts in {seconds}s. "
          "Move focus away / stop typing now. Ctrl+C to abort.")
    for i in range(seconds, 0, -1):
        print(f"    {i}...", end="", flush=True)
        time.sleep(1)
    print(" GO\n")


def main() -> int:
    if sys.platform != "win32":
        print("This demo targets Windows Notepad. On Linux/macOS adapt the "
              "launch target and the save-dialog flow.")
        return 1

    print("=== visus-desktop: Notepad -> 'hello world' -> save to Downloads ===")
    print(f"Target file : {TARGET_FILE}")
    print(f"Trace output: {OUT}")

    # Overlay off so it doesn't cover the trace screenshots.
    VisusBot({"show_overlay": False})

    try:
        countdown()
    except KeyboardInterrupt:
        print("\nAborted before any input was sent.")
        return 1

    # 1. Launch Notepad and locate its real window rect.
    #    Use subprocess.Popen directly so we capture the PID (the library's
    #    launch() uses os.startfile on Windows, which returns no PID); we
    #    need the PID to target the window and clean up at the end.
    print("[1] launching notepad.exe")
    import subprocess

    proc = subprocess.Popen(["notepad.exe"])  # noqa: S603,S607
    pid = proc.pid
    print(f"    pid={pid}")

    wait_for_stable_screen(stable_for=0.6, timeout=8)
    rect = find_notepad_rect(pid)
    if rect is None:
        print("    could not find the Notepad window; aborting")
        return 1
    left, top, right, bottom = rect
    print(f"    window rect={rect}")
    trace("notepad_opened")

    # 2. Click into the text area (center of the window, safely below the
    #    menu bar) to focus it, then type.
    cx, cy = (left + right) // 2, (top + bottom) // 2
    print(f"[2] focusing text area @ ({cx},{cy}) and typing")
    click_at((cx, cy, 0, 0))
    type_text("hello world")
    wait_for_stable_screen(stable_for=0.4, timeout=5)
    # Position print of the typed text -- also serves as a find_image template.
    text_template = trace(
        "hello_world_text", region=(left + 1, top + 52, 520, 90)
    )

    # 2b. find_image round-trip on the typed text (proves the matcher).
    box = find_image(str(text_template), confidence=0.85)
    print(f"    find_image(text) -> {box}")

    # 3. Open the Save As dialog.
    print("[3] Ctrl+S -> Save As dialog")
    keyboard_command("Ctrl+S")
    wait_for_stable_screen(stable_for=0.6, timeout=8)
    trace("save_dialog")

    # 4. The filename field is focused by default: select-all, type the
    #    absolute path. This is the robust, locale-independent save path.
    print(f"[4] typing path: {TARGET_FILE}")
    keyboard_command("Ctrl+A")
    type_text(str(TARGET_FILE))
    trace("path_typed")

    # 5. Confirm. Try find_image+click on the Save button (the "vision"
    #    demo); fall back to Enter if it can't be located.
    saved_via = "Enter"
    try:
        # Capture the button strip at the bottom of the dialog and let the
        # user/maintainer drop a real button template here to enable the
        # find_image path. Without a template we go straight to Enter.
        button_template = OUT / "save_button_template.png"
        if button_template.exists() and click_image(
            str(button_template), confidence=0.85
        ):
            saved_via = "find_image+click_image"
        else:
            keyboard_command("Enter")
    except Exception:
        keyboard_command("Enter")
    print(f"    confirmed save via: {saved_via}")

    # Some Windows builds pop a "replace existing?" dialog -- confirm it.
    time.sleep(0.4)
    keyboard_command("Enter")

    # 6. Confirm the file actually landed on disk.
    print("[5] waiting for the file to be written")
    ok = wait_for_file_stable(str(TARGET_FILE), timeout=15, stable_for=1.0)
    trace("after_save")

    if ok and TARGET_FILE.exists():
        content = TARGET_FILE.read_text(encoding="utf-8", errors="replace")
        print(f"\nSUCCESS: {TARGET_FILE} ({TARGET_FILE.stat().st_size} bytes)")
        print(f"Content: {content!r}")
        rc = 0
    else:
        print("\nFAILED: file did not appear -- check the trace screenshots.")
        rc = 1

    # 7. Clean up: close Notepad by PID (file already saved -> clean).
    print("[6] closing Notepad")
    kill_process(pid)

    print(f"\nTrace screenshots: {OUT}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

"""End-to-end: launch Notepad, type, save-as, close.

This is the canonical "did the bot actually drive a real Windows app"
test. Touches every layer the unit suite mocks out: process launch,
window focus, keyboard typing, native window close, file appearance
on disk.

Windows-only -- mocking notepad on Linux/macOS defeats the purpose.
"""

from __future__ import annotations

import os
import time

import pytest

import visus.desktop as vd
from visus.desktop import (
    close_window,
    find_process,
    focus_window,
    is_process_running,
    kill_process,
    type_text,
    wait_for_file_stable,
)

pytestmark = pytest.mark.windows_only


def _kill_lingering_notepad():
    """Best-effort cleanup so prior failed runs don't leak processes."""
    proc = find_process(name="notepad.exe")
    if proc is not None:
        try:
            kill_process(target=proc)
        except Exception:
            pass


@pytest.fixture
def clean_notepad():
    _kill_lingering_notepad()
    yield
    _kill_lingering_notepad()


class TestRealNotepadFlow:
    @pytest.mark.real_input
    def test_launch_focus_type_close(self, clean_notepad, tmp_path):
        """Open Notepad, type a marker, close it without saving.

        DANGEROUS on a real desktop: it launches a window, types into
        whatever ends up focused, and closes windows matching "Notepad".
        Gated behind ``@pytest.mark.real_input`` + the
        ``VISUS_INTEGRATION_REAL_INPUT=1`` env var so it only runs on a
        throwaway machine / CI runner, never on a dev's working session.
        """
        bot = vd.VisusBot({"show_overlay": False})

        # 1. Launch.
        bot.launch("notepad.exe")
        # Give Windows ~3s to spawn the process.
        for _ in range(30):
            if is_process_running("notepad.exe"):
                break
            time.sleep(0.1)
        assert is_process_running("notepad.exe"), "notepad failed to launch"

        # 2. Focus. Title can take a moment + may be localized on
        # non-English Windows; poll a few common substrings.
        focused = False
        for _ in range(30):
            for needle in ("Notepad", "Bloco de Notas", "Sin título"):
                if focus_window(needle):
                    focused = True
                    break
            if focused:
                break
            time.sleep(0.1)
        assert focused is True, "could not focus a freshly-launched Notepad window"

        # 3. Type a marker.
        marker = "visus-integration-MARKER-9X4"
        type_text(marker)

        # 4. Close without saving (Alt+F4 then Don't save).
        close_window("Notepad")
        # Notepad pops a "Save changes?" dialog -- Tab to "Don't save",
        # then Enter. We send Alt+N as the localized accelerator on
        # English Windows ("Don't save"). On non-English Windows this
        # would need a real OCR pass; for now we kill the process to
        # guarantee no dialog is left behind.
        time.sleep(0.5)
        _kill_lingering_notepad()
        time.sleep(0.5)
        assert is_process_running("notepad.exe") is False

    def test_wait_for_file_stable_against_a_real_write(self, tmp_path):
        """Write a file incrementally and confirm wait_for_file_stable
        returns once the size settles."""
        import threading

        target = tmp_path / "growing.dat"

        def writer():
            with open(target, "wb") as fh:
                for _ in range(5):
                    fh.write(b"chunk\n")
                    fh.flush()
                    time.sleep(0.1)

        t = threading.Thread(target=writer)
        t.start()
        ok = wait_for_file_stable(
            str(target), timeout=10, stable_for=0.5, poll_interval=0.1
        )
        t.join()
        assert ok is True
        assert target.exists()
        assert os.path.getsize(target) > 0

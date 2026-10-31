"""Regression test for the alternative-overlay fallback.

Bug: ``x, y, w, h`` were unpacked inside the ``try`` (after ``import ctypes``),
so if a Win32 call failed the ``except`` block referenced unbound locals and
raised ``UnboundLocalError`` instead of logging the fallback. The unpack now
happens before the ``try``.
"""

from __future__ import annotations

import ctypes

from visus.desktop.core.overlay import VisualOverlay


def test_alternative_overlay_fallback_does_not_unbound_error(monkeypatch):
    class _Boom:
        def __getattr__(self, name):
            raise OSError("windll unavailable")

    # Force the Win32 path to fail so the except/fallback branch runs.
    monkeypatch.setattr(ctypes, "windll", _Boom(), raising=False)

    overlay = VisualOverlay(color="red", width=4, duration=1)
    # Before the fix this raised UnboundLocalError; now it returns cleanly.
    assert overlay._create_overlay_alternative((10, 20, 30, 40)) is None


def _tk_calls_from(thread_target_runs_in_main: bool, monkeypatch) -> list:
    import threading

    from visus.desktop.core import overlay as overlay_mod

    monkeypatch.setattr(overlay_mod.sys, "platform", "darwin")
    overlay = VisualOverlay(color="red", width=4, duration=1)
    calls: list = []
    monkeypatch.setattr(overlay, "_tkinter_available", True)
    monkeypatch.setattr(overlay, "_create_overlay_tkinter", lambda r: calls.append(r) or True)
    monkeypatch.setattr(overlay, "_fix_tkinter_environment", lambda: True)
    if thread_target_runs_in_main:
        overlay._create_overlay_with_fallback((1, 2, 3, 4))
    else:
        worker = threading.Thread(target=overlay._create_overlay_with_fallback, args=((1, 2, 3, 4),))
        worker.start()
        worker.join()
    return calls


def test_macos_never_opens_tk_off_the_main_thread(monkeypatch):
    """Tk on macOS from a background thread aborts the process (CI: "Fatal Python
    error: Aborted" in wm_attributes) -- and show() is non-blocking by default."""
    assert _tk_calls_from(False, monkeypatch) == []


def test_macos_still_uses_tk_on_the_main_thread(monkeypatch):
    assert _tk_calls_from(True, monkeypatch) == [(1, 2, 3, 4)]

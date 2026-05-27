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

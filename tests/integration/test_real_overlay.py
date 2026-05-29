"""Render a real overlay (no Tk mock) against the live display.

Exercises the actual Tk window creation chain that the unit suite
short-circuits behind ``patch("visus.desktop.core.overlay.tk.Tk")``.
On Linux this needs Xvfb; on Windows the native screen is used. The
overlay is shown non-blocking for a tiny duration so it never blocks
the test runner.
"""

from __future__ import annotations

import time

import pytest

from visus.desktop.core.overlay import VisualOverlay

# The overlay pops a borderless top-most Tk window that steals focus and
# covers the screen for its duration -- intrusive on a real desktop, so
# the whole module is gated behind the real-input env var.
pytestmark = pytest.mark.real_input


class TestRealOverlay:
    def test_non_blocking_show_returns_immediately(self):
        overlay = VisualOverlay(color="red", width=3, duration=50)
        start = time.monotonic()
        overlay.show((0, 0, 64, 32))
        elapsed = time.monotonic() - start
        # ``blocking=False`` (default) runs the Tk loop in a daemon
        # thread; the call must return before the duration elapses.
        assert elapsed < 1.0, (
            f"non-blocking overlay returned after {elapsed:.2f}s "
            "-- the daemon thread is supposed to absorb the wait"
        )

    def test_multiple_overlays_render_without_exception(self):
        overlay = VisualOverlay(color="blue", duration=50)
        # If any Tk code path raises here, the test fails -- this is the
        # only place in the suite where the real Tk binding executes.
        overlay.show_multiple([(0, 0, 32, 32), (50, 50, 32, 32)])

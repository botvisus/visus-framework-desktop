"""Regression tests for the virtual mouse coordinate math.

Bug: on scaled (high-DPI) displays the virtual click landed in the wrong place
because the screen->client conversion multiplied the client offset by the monitor
DPI factor. The conversion must use the raw ScreenToClient result, since the input
point and the Win32 API already share the same coordinate space.
"""

from __future__ import annotations

import sys

import pytest

from tests import tesseract_available

try:
    import win32gui  # noqa: F401  # availability probe

    _WIN32 = True
except Exception:
    _WIN32 = False

pytestmark = pytest.mark.skipif(
    not (sys.platform == "win32" and _WIN32 and tesseract_available()),
    reason="Requires Windows + pywin32 + Tesseract",
)


def test_resolve_client_coordinates_no_dpi_distortion(monkeypatch):
    import win32gui

    from visus.desktop.core.virtual_mouse import VirtualMouse
    from visus.desktop.utils.config import BotVisionConfig

    vm = VirtualMouse(BotVisionConfig())

    # Simulate a window whose client origin is at screen (100, 100):
    # the real ScreenToClient returns (screen.x - 100, screen.y - 100).
    monkeypatch.setattr(
        win32gui, "ScreenToClient", lambda hwnd, pt: (pt[0] - 100, pt[1] - 100)
    )

    client_x, client_y, screen_x, screen_y = vm._resolve_client_coordinates(
        123, (300, 200)
    )

    # The correct client point is (200, 100) regardless of any monitor DPI scaling.
    assert (client_x, client_y) == (200, 100)
    assert (screen_x, screen_y) == (300, 200)


def test_resolve_client_coordinates_falls_back_on_error(monkeypatch):
    import win32gui

    from visus.desktop.core.virtual_mouse import VirtualMouse
    from visus.desktop.utils.config import BotVisionConfig

    vm = VirtualMouse(BotVisionConfig())

    def boom(hwnd, pt):
        raise OSError("no such window")

    monkeypatch.setattr(win32gui, "ScreenToClient", boom)

    # On failure it returns the screen coordinates unchanged (best-effort fallback).
    result = vm._resolve_client_coordinates(123, (300, 200))
    assert result == (300, 200, 300, 200)

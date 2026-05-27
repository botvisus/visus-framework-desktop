"""Tests for ``visus.desktop.core.overlay``.

The overlay's ``__init__`` probes Tkinter by creating a hidden ``tk.Tk()``
window. To keep these tests headless and fast, ``tk.Tk`` is replaced with a
stub so no real window is ever opened. Logic that genuinely needs a live
display is guarded with skipif rather than faked.
"""

from __future__ import annotations

import os

import pytest

import visus.desktop.core.overlay as overlay_module
from visus.desktop.core.overlay import VisualOverlay, show_overlay


class FakeTk:
    """Minimal stand-in for ``tkinter.Tk`` used during availability probing."""

    def __init__(self, *args, **kwargs):
        pass

    def withdraw(self):
        pass

    def destroy(self):
        pass


@pytest.fixture
def fake_tk(monkeypatch):
    """Replace ``tk.Tk`` so construction never opens a window (probe succeeds)."""
    monkeypatch.setattr(overlay_module.tk, "Tk", FakeTk)
    return FakeTk


@pytest.fixture
def broken_tk(monkeypatch):
    """Replace ``tk.Tk`` with one that raises, so the probe reports unavailable."""

    def boom(*args, **kwargs):
        raise RuntimeError("no display")

    monkeypatch.setattr(overlay_module.tk, "Tk", boom)


# --------------------------------------------------------------------------- #
# Construction & parameter handling
# --------------------------------------------------------------------------- #
def test_default_construction(fake_tk):
    """Defaults: red, width 4, duration 1000ms."""
    overlay = VisualOverlay()
    assert overlay.color == "red"
    assert overlay.width == 4
    assert overlay.duration == 1000


def test_custom_construction(fake_tk):
    """Custom color/width/duration are stored verbatim."""
    overlay = VisualOverlay(color="blue", width=8, duration=2500)
    assert overlay.color == "blue"
    assert overlay.width == 8
    assert overlay.duration == 2500


def test_arbitrary_color_is_stored(fake_tk):
    """An unusual color string is stored without validation at construction."""
    overlay = VisualOverlay(color="chartreuse")
    assert overlay.color == "chartreuse"


def test_tkinter_available_true_when_probe_succeeds(fake_tk):
    """A successful ``tk.Tk()`` probe sets _tkinter_available True."""
    overlay = VisualOverlay()
    assert overlay._tkinter_available is True


def test_tkinter_available_false_when_probe_raises(broken_tk):
    """A failing ``tk.Tk()`` probe sets _tkinter_available False."""
    overlay = VisualOverlay()
    assert overlay._tkinter_available is False


def test_check_tkinter_availability_method(fake_tk):
    """The probe method returns True with a working (stubbed) Tk."""
    overlay = VisualOverlay()
    assert overlay._check_tkinter_availability() is True


# --------------------------------------------------------------------------- #
# Color tables used by the drawing backends
# --------------------------------------------------------------------------- #
class _FakeGdi:
    """Records the pen color requested via CreatePen; no-ops everything else."""

    def __init__(self, recorder):
        self._recorder = recorder

    def CreatePen(self, style, width, color):
        self._recorder["pen_color"] = color
        return 1  # truthy handle

    def SelectObject(self, dc, obj):
        return 99

    def MoveToEx(self, *a, **k):
        return None

    def LineTo(self, *a, **k):
        return None

    def GdiFlush(self):
        return None

    def DeleteObject(self, obj):
        return None


class _FakeUser32:
    def GetDC(self, hwnd):
        return 1234  # truthy DC handle

    def ReleaseDC(self, *a, **k):
        return None

    def InvalidateRect(self, *a, **k):
        return None

    def UpdateWindow(self, *a, **k):
        return None


class _FakeWindll:
    def __init__(self, recorder):
        self.user32 = _FakeUser32()
        self.gdi32 = _FakeGdi(recorder)


def _patch_alternative_backend(monkeypatch, recorder):
    """Patch ctypes.windll + time.sleep so the Windows-API backend runs headless."""
    import ctypes

    monkeypatch.setattr(ctypes, "windll", _FakeWindll(recorder), raising=False)
    # The backend imports ``time`` locally; patch the real module's sleep.
    import time as _time

    monkeypatch.setattr(_time, "sleep", lambda *a, **k: None)


def test_known_color_maps_to_expected_bgr(fake_tk, monkeypatch):
    """The Windows-API backend maps a known color name to its BGR int."""
    recorder = {}
    _patch_alternative_backend(monkeypatch, recorder)

    overlay = VisualOverlay(color="green")
    overlay._create_overlay_alternative((10, 10, 20, 20))

    # "green" -> BGR 0x00FF00 per the backend's color table.
    assert recorder["pen_color"] == 0x00FF00


def test_unknown_color_defaults_to_red_in_alternative(fake_tk, monkeypatch):
    """An unknown color defaults to the red BGR value (0x0000FF)."""
    recorder = {}
    _patch_alternative_backend(monkeypatch, recorder)

    overlay = VisualOverlay(color="not-a-color")
    overlay._create_overlay_alternative((0, 0, 5, 5))

    assert recorder["pen_color"] == 0x0000FF


# --------------------------------------------------------------------------- #
# show() wiring (non-blocking + blocking) without opening a window
# --------------------------------------------------------------------------- #
def test_show_nonblocking_spawns_thread(fake_tk, monkeypatch):
    """Non-blocking show() dispatches the work onto a daemon thread."""
    overlay = VisualOverlay()
    captured = {}

    def fake_fallback(region):
        captured["region"] = region

    monkeypatch.setattr(overlay, "_create_overlay_with_fallback", fake_fallback)

    overlay.show((1, 2, 3, 4), blocking=False)

    # Give the daemon thread a moment to run the (instant) fake.
    import time

    deadline = time.time() + 1.0
    while "region" not in captured and time.time() < deadline:
        time.sleep(0.01)

    assert captured["region"] == (1, 2, 3, 4)


def test_show_blocking_calls_fallback_directly(fake_tk, monkeypatch):
    """Blocking show() runs the fallback synchronously on the calling thread."""
    overlay = VisualOverlay()
    captured = {}

    monkeypatch.setattr(
        overlay,
        "_create_overlay_with_fallback",
        lambda region: captured.setdefault("region", region),
    )

    overlay.show((5, 6, 7, 8), blocking=True)

    assert captured["region"] == (5, 6, 7, 8)


def test_fallback_uses_tkinter_first_when_available(fake_tk, monkeypatch):
    """When Tkinter is available, the fallback tries the Tkinter backend first."""
    overlay = VisualOverlay()
    calls = []

    monkeypatch.setattr(
        overlay,
        "_create_overlay_tkinter",
        lambda region: calls.append(("tk", region)) or True,
    )

    overlay._create_overlay_with_fallback((9, 9, 9, 9))

    assert calls == [("tk", (9, 9, 9, 9))]


# --------------------------------------------------------------------------- #
# Convenience function wiring
# --------------------------------------------------------------------------- #
def test_show_overlay_constructs_and_shows(monkeypatch):
    """show_overlay builds a VisualOverlay with the given args and calls .show."""
    created = {}
    shown = {}

    class StubOverlay:
        def __init__(self, color="red", width=4, duration=1000):
            created["color"] = color
            created["width"] = width
            created["duration"] = duration

        def show(self, region, blocking=False):
            shown["region"] = region
            shown["blocking"] = blocking

    monkeypatch.setattr(overlay_module, "VisualOverlay", StubOverlay)

    show_overlay((100, 100, 200, 50), duration=2000, color="blue", width=6)

    assert created == {"color": "blue", "width": 6, "duration": 2000}
    assert shown == {"region": (100, 100, 200, 50), "blocking": False}


def test_show_overlay_defaults(monkeypatch):
    """show_overlay applies its documented defaults when only region is given."""
    created = {}

    class StubOverlay:
        def __init__(self, color="red", width=4, duration=1000):
            created.update(color=color, width=width, duration=duration)

        def show(self, region, blocking=False):
            pass

    monkeypatch.setattr(overlay_module, "VisualOverlay", StubOverlay)

    show_overlay((0, 0, 10, 10))

    assert created == {"color": "red", "width": 4, "duration": 1000}


# --------------------------------------------------------------------------- #
# Real-display smoke test (skipped on headless CI)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    os.environ.get("DISPLAY") is None and os.name != "nt",
    reason="Requires a real display (no DISPLAY set on a non-Windows host)",
)
def test_real_tkinter_probe_does_not_crash():
    """On a host with a display, constructing a VisualOverlay must not raise."""
    overlay = VisualOverlay()
    assert isinstance(overlay._tkinter_available, bool)

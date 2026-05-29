"""Tests for ``visus.desktop.core.screen``.

Capture is exercised without touching the real display: the mss-preferred path
and the pyautogui fallback are both driven via monkeypatching.
"""

from __future__ import annotations

import os

import pyautogui

from visus.desktop.core import screen


def test_get_display_size(monkeypatch):
    monkeypatch.setattr(pyautogui, "size", lambda: (1920, 1080))
    assert screen.get_display_size() == (1920, 1080)


def test_capture_prefers_mss(monkeypatch):
    """When mss works, capture_screen returns its result (no pyautogui call)."""
    sentinel = object()
    recorded = {}

    def fake_mss(region, monitor_index=None):
        recorded["region"] = region
        return sentinel

    monkeypatch.setattr(screen, "_capture_with_mss", fake_mss)
    # Guard: pyautogui must NOT be used when mss succeeds.
    monkeypatch.setattr(
        pyautogui,
        "screenshot",
        lambda **k: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    result = screen.capture_screen((1, 2, 3, 4))
    assert result is sentinel
    assert recorded["region"] == (1, 2, 3, 4)


def test_capture_falls_back_to_pyautogui(monkeypatch):
    """When mss fails, capture_screen falls back to pyautogui and forwards region."""
    recorded = {}

    def boom(region, monitor_index=None):
        raise RuntimeError("mss unavailable")

    def fake_screenshot(region=None):
        recorded["region"] = region
        return object()

    monkeypatch.setattr(screen, "_capture_with_mss", boom)
    monkeypatch.setattr(pyautogui, "screenshot", fake_screenshot)

    screen.capture_screen((5, 6, 7, 8))
    assert recorded["region"] == (5, 6, 7, 8)


def test_save_screenshot_writes_file_and_returns_path(monkeypatch, tmp_path):
    class FakeImage:
        def save(self, path):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("fake-image")

    monkeypatch.setattr(
        screen, "capture_screen", lambda region=None, monitor=None: FakeImage()
    )

    target = os.path.join(str(tmp_path), "shot.png")
    returned = screen.save_screenshot(target)
    assert returned == target
    assert os.path.exists(target)

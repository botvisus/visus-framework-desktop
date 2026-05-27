"""Tests for ``visus.desktop.core.screen``.

These tests monkeypatch ``pyautogui`` so they never query the real display
size nor take real screenshots.
"""

from __future__ import annotations

import os

import pyautogui

from visus.desktop.core import screen


def test_get_display_size(monkeypatch):
    """``get_display_size`` returns ``tuple(pyautogui.size())``."""
    monkeypatch.setattr(pyautogui, "size", lambda: (1920, 1080))

    assert screen.get_display_size() == (1920, 1080)


def test_capture_screen_passes_region(monkeypatch):
    """``capture_screen`` forwards the region argument to ``pyautogui``."""
    recorded = {}

    class FakeImage:
        pass

    def fake_screenshot(region=None):
        recorded["region"] = region
        return FakeImage()

    monkeypatch.setattr(pyautogui, "screenshot", fake_screenshot)

    result = screen.capture_screen((1, 2, 3, 4))

    assert isinstance(result, FakeImage)
    assert recorded["region"] == (1, 2, 3, 4)


def test_capture_screen_default_region_is_none(monkeypatch):
    """``capture_screen`` defaults the region to ``None`` (full screen)."""
    recorded = {}

    def fake_screenshot(region=None):
        recorded["region"] = region
        return object()

    monkeypatch.setattr(pyautogui, "screenshot", fake_screenshot)

    screen.capture_screen()

    assert recorded["region"] is None


def test_save_screenshot_writes_file_and_returns_path(monkeypatch, tmp_path):
    """``save_screenshot`` saves the image and returns the path."""

    class FakeImage:
        def save(self, path):
            # Write a tiny file so the test can assert it exists.
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("fake-image")

    monkeypatch.setattr(pyautogui, "screenshot", lambda region=None: FakeImage())

    target = os.path.join(str(tmp_path), "shot.png")
    returned = screen.save_screenshot(target)

    assert returned == target
    assert os.path.exists(target)

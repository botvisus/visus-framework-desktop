"""Real-display screen capture + monitor enumeration.

These tests hit the actual mss/pyautogui code path against a real
display (or an Xvfb virtual one on Linux CI). They exercise the
fallback branches that mocked unit tests cannot reach.
"""

from __future__ import annotations

import pytest
from PIL import Image

from visus.desktop import (
    capture_screen,
    get_display_size,
    get_monitors,
    take_screenshot,
)
from visus.desktop.core.screen import invalidate_screen_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    invalidate_screen_cache()
    yield
    invalidate_screen_cache()


class TestRealCapture:
    def test_full_screen_capture_is_a_pil_image(self):
        img = capture_screen()
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0

    def test_region_capture_matches_requested_size(self):
        img = capture_screen(region=(0, 0, 64, 32))
        assert img.size == (64, 32)

    def test_take_screenshot_returns_pil_image(self):
        img = take_screenshot(region=(0, 0, 32, 32))
        assert img.size == (32, 32)

    def test_get_display_size_returns_positive_pair(self):
        w, h = get_display_size()
        assert w > 0 and h > 0


class TestRealMonitors:
    def test_get_monitors_returns_at_least_one(self):
        mons = get_monitors()
        assert len(mons) >= 1
        primary = next((m for m in mons if m.is_primary), None)
        assert primary is not None
        assert primary.width > 0
        assert primary.height > 0

    def test_primary_monitor_capture_matches_size(self):
        primary = next(m for m in get_monitors() if m.is_primary)
        img = take_screenshot(monitor=primary.index)
        # mss reports raw pixel dimensions; allow a 4x tolerance for HiDPI.
        assert img.width >= primary.width // 4
        assert img.height >= primary.height // 4

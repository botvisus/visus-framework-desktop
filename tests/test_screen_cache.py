"""Tests for the per-region screenshot cache (Phase 3, E3).

Configure with ``config['screen_cache_ms']`` (or
``set_screen_cache_ms`` directly). Within the TTL, back-to-back
``capture_screen(region=...)`` calls on the same region return the
same cached PIL image, avoiding a redundant grab. The cache is
invalidated on click / type / explicit ``invalidate_screen_cache``.
"""

from __future__ import annotations

import time

import pytest
from PIL import Image

from visus.desktop.core.screen import (
    capture_screen,
    invalidate_screen_cache,
    set_screen_cache_ms,
)


@pytest.fixture(autouse=True)
def _reset_cache():
    set_screen_cache_ms(0)
    invalidate_screen_cache()
    yield
    set_screen_cache_ms(0)
    invalidate_screen_cache()


class TestScreenCache:
    def test_cache_disabled_by_default(self, monkeypatch):
        calls = {"n": 0}

        def fake(region=None, monitor_index=None):
            calls["n"] += 1
            return Image.new("RGB", (4, 4), color="white")

        monkeypatch.setattr(
            "visus.desktop.core.screen._capture_with_mss", fake
        )
        capture_screen(region=(0, 0, 10, 10))
        capture_screen(region=(0, 0, 10, 10))
        assert calls["n"] == 2  # default TTL=0: no caching

    def test_cache_returns_same_image_within_ttl(self, monkeypatch):
        set_screen_cache_ms(500)
        calls = {"n": 0}

        def fake(region=None, monitor_index=None):
            calls["n"] += 1
            return Image.new("RGB", (4, 4), color="red")

        monkeypatch.setattr(
            "visus.desktop.core.screen._capture_with_mss", fake
        )
        a = capture_screen(region=(0, 0, 10, 10))
        b = capture_screen(region=(0, 0, 10, 10))
        assert calls["n"] == 1
        assert a is b  # exact same object served from cache

    def test_different_regions_do_not_share_cache(self, monkeypatch):
        set_screen_cache_ms(500)
        calls = {"n": 0}

        def fake(region=None, monitor_index=None):
            calls["n"] += 1
            return Image.new("RGB", (4, 4), color="green")

        monkeypatch.setattr(
            "visus.desktop.core.screen._capture_with_mss", fake
        )
        capture_screen(region=(0, 0, 10, 10))
        capture_screen(region=(100, 100, 10, 10))
        assert calls["n"] == 2

    def test_cache_expires_after_ttl(self, monkeypatch):
        set_screen_cache_ms(10)  # 10 ms
        calls = {"n": 0}

        def fake(region=None, monitor_index=None):
            calls["n"] += 1
            return Image.new("RGB", (4, 4), color="blue")

        monkeypatch.setattr(
            "visus.desktop.core.screen._capture_with_mss", fake
        )
        capture_screen(region=(0, 0, 10, 10))
        time.sleep(0.05)
        capture_screen(region=(0, 0, 10, 10))
        assert calls["n"] == 2

    def test_invalidate_clears_cache(self, monkeypatch):
        set_screen_cache_ms(500)
        calls = {"n": 0}

        def fake(region=None, monitor_index=None):
            calls["n"] += 1
            return Image.new("RGB", (4, 4), color="purple")

        monkeypatch.setattr(
            "visus.desktop.core.screen._capture_with_mss", fake
        )
        capture_screen(region=(0, 0, 10, 10))
        invalidate_screen_cache()
        capture_screen(region=(0, 0, 10, 10))
        assert calls["n"] == 2

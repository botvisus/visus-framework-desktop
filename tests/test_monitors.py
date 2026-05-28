"""Tests for the explicit multi-monitor API (Phase 3, E4).

mss can already capture any monitor; this exposes that capability in a
typed way:

  * ``get_monitors()`` -> ``[Monitor(index, x, y, width, height,
    is_primary)]`` (the virtual screen sits at index 0; physical
    monitors start at 1).
  * ``take_screenshot(monitor=N)`` captures monitor N in its full
    extent.
  * ``capture_screen(monitor=N)`` accepts the same flag for the
    capabilities mixin.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import mss
import pytest

from visus.desktop import Monitor, capture_screen, get_monitors, take_screenshot


def _fake_mss(monitors):
    """Patch the mss class lookup to return a deterministic monitor list.

    The library prefers ``mss.MSS`` (the canonical class in mss>=10)
    and falls back to ``mss.mss`` (legacy alias). The helper patches
    whichever attribute exists so the test works on both versions.
    """

    class _Cm:
        def __init__(self):
            self.monitors = monitors

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def grab(self, monitor):
            from PIL import Image as _Image

            img = _Image.new(
                "RGB", (monitor["width"], monitor["height"]), color="white"
            )
            shot = MagicMock()
            shot.size = (monitor["width"], monitor["height"])
            shot.bgra = img.convert("RGBA").tobytes("raw", "BGRA")
            return shot

    return MagicMock(return_value=_Cm())


@contextmanager
def _patch_mss(monitors):
    """Apply the fake to whichever mss entry point the library uses."""
    fake = _fake_mss(monitors)
    target = "mss.MSS" if hasattr(mss, "MSS") else "mss.mss"
    with patch(target, fake):
        yield fake


class TestMonitorDataclass:
    def test_monitor_fields(self):
        m = Monitor(index=1, x=0, y=0, width=1920, height=1080, is_primary=True)
        assert m.index == 1
        assert m.is_primary is True
        assert m.width == 1920


class TestGetMonitors:
    def test_lists_all_physical_monitors(self):
        monitors = [
            {"left": 0, "top": 0, "width": 3840, "height": 1080},  # virtual screen
            {"left": 0, "top": 0, "width": 1920, "height": 1080},  # primary
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},  # secondary
        ]
        with _patch_mss(monitors):
            result = get_monitors()
        # Index 0 (the virtual screen) is dropped; physical monitors are 1, 2.
        assert len(result) == 2
        assert result[0].index == 1
        assert result[0].is_primary is True
        assert result[0].width == 1920
        assert result[1].index == 2
        assert result[1].x == 1920
        assert result[1].is_primary is False


class TestTakeScreenshotMonitor:
    def test_capture_with_explicit_monitor(self):
        monitors = [
            {"left": 0, "top": 0, "width": 3840, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 1920, "top": 0, "width": 1920, "height": 1080},
        ]
        with _patch_mss(monitors):
            img = take_screenshot(monitor=2)
        assert img.size == (1920, 1080)

    def test_capture_screen_accepts_monitor_flag(self):
        monitors = [
            {"left": 0, "top": 0, "width": 3840, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ]
        with _patch_mss(monitors):
            img = capture_screen(monitor=1)
        assert img.size == (1920, 1080)

    def test_invalid_monitor_index_raises(self):
        monitors = [
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
            {"left": 0, "top": 0, "width": 1920, "height": 1080},
        ]
        with _patch_mss(monitors):
            with pytest.raises(ValueError, match="monitor"):
                take_screenshot(monitor=99)

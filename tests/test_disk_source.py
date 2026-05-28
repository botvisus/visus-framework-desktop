"""Tests for the on-disk screen source (Phase 2, TS3).

``config['screen_source'] = 'disk:<path>'`` makes ``capture_screen``
return PNGs from a directory in alphabetical order, looping when
exhausted. Used by record/replay (O3) and by user tests that need a
deterministic screen without a display.
"""

from __future__ import annotations

import pytest
from PIL import Image

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.core.screen import capture_screen, set_screen_source

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


def _write_png(path, color):
    Image.new("RGB", (8, 8), color=color).save(path)


@pytest.fixture(autouse=True)
def _reset_screen_source():
    yield
    set_screen_source(None)


class TestDiskScreenSource:
    """``set_screen_source('disk:<path>')`` makes capture_screen read disk."""

    def test_capture_returns_frames_in_order(self, tmp_path):
        _write_png(tmp_path / "frame_001.png", "red")
        _write_png(tmp_path / "frame_002.png", "green")
        _write_png(tmp_path / "frame_003.png", "blue")
        set_screen_source(f"disk:{tmp_path}")

        first = capture_screen()
        second = capture_screen()
        third = capture_screen()
        assert first.getpixel((0, 0)) == (255, 0, 0)
        assert second.getpixel((0, 0)) == (0, 128, 0)
        assert third.getpixel((0, 0)) == (0, 0, 255)

    def test_capture_loops_when_exhausted(self, tmp_path):
        _write_png(tmp_path / "only.png", "red")
        set_screen_source(f"disk:{tmp_path}")
        a = capture_screen()
        b = capture_screen()
        assert a.getpixel((0, 0)) == (255, 0, 0)
        assert b.getpixel((0, 0)) == (255, 0, 0)

    def test_unset_source_returns_to_live_capture(self, tmp_path):
        """Clearing the source restores normal screen-capture behaviour."""
        _write_png(tmp_path / "x.png", "red")
        set_screen_source(f"disk:{tmp_path}")
        from_disk = capture_screen()
        assert from_disk.getpixel((0, 0)) == (255, 0, 0)

        set_screen_source(None)
        # After reset we no longer hit the disk source.
        from unittest.mock import patch

        with patch(
            "visus.desktop.core.screen._capture_with_mss",
            return_value=Image.new("RGB", (8, 8), color="white"),
        ):
            live = capture_screen()
        assert live.getpixel((0, 0)) == (255, 255, 255)

    def test_missing_directory_falls_back_to_live_capture(self, tmp_path):
        set_screen_source(f"disk:{tmp_path / 'does_not_exist'}")
        from unittest.mock import patch

        with patch(
            "visus.desktop.core.screen._capture_with_mss",
            return_value=Image.new("RGB", (8, 8), color="white"),
        ):
            img = capture_screen()
        assert img.getpixel((0, 0)) == (255, 255, 255)


@requires_tesseract
class TestConfigWiring:
    """``BotVisionConfig['screen_source']`` activates the disk source."""

    def test_config_screen_source_is_applied_at_executor_construction(
        self, tmp_path
    ):
        _write_png(tmp_path / "a.png", "red")
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "screen_source": f"disk:{tmp_path}",
            }
        )
        # Constructing the executor activated the source globally.
        img = capture_screen()
        assert img.getpixel((0, 0)) == (255, 0, 0)
        # The bot object exists; that's the only behaviour we care about.
        assert bot.executor is not None

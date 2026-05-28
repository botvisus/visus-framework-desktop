"""Tests for ``hybrid_find`` (Phase 3, T1).

``bot.hybrid_find(name)`` tries each targeting backend in order --
native (pywinauto) → OCR → image -- and returns the first hit. Every
layer is mockable so the test does not need a real display, OCR engine,
or app handle.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@requires_tesseract
class TestHybridFind:
    def _bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_native_hit_short_circuits(self):
        bot = self._bot()
        with patch.object(
            bot, "_hybrid_native_lookup", return_value=(10, 20, 100, 30)
        ) as native, patch.object(bot, "find_text") as ocr, patch.object(
            bot, "find_image"
        ) as image:
            box = bot.hybrid_find("Login")
        assert box == (10, 20, 100, 30)
        native.assert_called_once()
        ocr.assert_not_called()
        image.assert_not_called()

    def test_falls_back_to_ocr_when_native_misses(self):
        bot = self._bot()
        with patch.object(
            bot, "_hybrid_native_lookup", return_value=None
        ), patch.object(bot, "find_text", return_value=(1, 2, 3, 4)) as ocr, patch.object(
            bot, "find_image"
        ) as image:
            box = bot.hybrid_find("Login")
        assert box == (1, 2, 3, 4)
        ocr.assert_called_once()
        image.assert_not_called()

    def test_falls_back_to_image_when_native_and_ocr_miss(self):
        bot = self._bot()
        with patch.object(
            bot, "_hybrid_native_lookup", return_value=None
        ), patch.object(bot, "find_text", return_value=None), patch.object(
            bot, "find_image", return_value=(5, 6, 7, 8)
        ) as image:
            box = bot.hybrid_find("login_button.png")
        assert box == (5, 6, 7, 8)
        image.assert_called_once()

    def test_image_path_required_to_skip_to_image_layer(self):
        """A plain word is never passed to find_image (which would crash)."""
        bot = self._bot()
        with patch.object(
            bot, "_hybrid_native_lookup", return_value=None
        ), patch.object(bot, "find_text", return_value=None), patch.object(
            bot, "find_image"
        ) as image:
            box = bot.hybrid_find("Login")
        assert box is None
        image.assert_not_called()

    def test_all_layers_miss_returns_none(self):
        bot = self._bot()
        with patch.object(
            bot, "_hybrid_native_lookup", return_value=None
        ), patch.object(bot, "find_text", return_value=None), patch.object(
            bot, "find_image", return_value=None
        ):
            assert bot.hybrid_find("missing.png") is None

    def test_native_raises_is_treated_as_miss(self):
        """A platform-locked native layer does not crash hybrid_find."""
        from visus.desktop.exceptions import NotSupportedOnThisOS

        bot = self._bot()
        with patch.object(
            bot,
            "_hybrid_native_lookup",
            side_effect=NotSupportedOnThisOS("Linux"),
        ), patch.object(
            bot, "find_text", return_value=(11, 12, 13, 14)
        ):
            box = bot.hybrid_find("Login")
        assert box == (11, 12, 13, 14)

    def test_region_is_forwarded(self):
        bot = self._bot()
        with patch.object(
            bot, "_hybrid_native_lookup", return_value=None
        ), patch.object(bot, "find_text", return_value=(0, 0, 1, 1)) as ocr:
            bot.hybrid_find("Submit", region=(10, 20, 200, 40))
        _, kwargs = ocr.call_args
        assert kwargs.get("region") == (10, 20, 200, 40)

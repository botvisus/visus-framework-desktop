"""More coverage for VisusBot.extract_text_from_region and the relative
image / standalone helper paths.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.core.ocr_engine import OCRResult

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed",
)


@requires_tesseract
class TestExtractTextFromRegion:
    @pytest.fixture
    def bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_returns_list_of_strings_default(self, bot):
        sample = [
            OCRResult("hello", 90.0, (1, 2, 3, 4)),
            OCRResult("world", 85.0, (10, 20, 30, 40)),
        ]
        with patch.object(
            bot.executor, "_capture_region", return_value=MagicMock()
        ), patch.object(
            bot.ocr_engine, "extract_all_text", return_value=sample
        ):
            out = bot.extract_text_from_region(region=(0, 0, 100, 100))
        assert out == ["hello", "world"]

    def test_returns_full_data_with_absolute_box(self, bot):
        sample = [OCRResult("X", 95.0, (5, 6, 7, 8))]
        with patch.object(
            bot.executor, "_capture_region", return_value=MagicMock()
        ), patch.object(
            bot.ocr_engine, "extract_all_text", return_value=sample
        ):
            out = bot.extract_text_from_region(
                region=(100, 200, 300, 300),
                return_full_data=True,
            )
        assert isinstance(out, list)
        entry = out[0]
        assert entry["text"] == "X"
        assert entry["absolute_box"] == (105, 206, 7, 8)

    def test_confidence_threshold_filters_results(self, bot):
        sample = [
            OCRResult("low", 20.0, (0, 0, 1, 1)),
            OCRResult("high", 95.0, (0, 0, 1, 1)),
        ]
        with patch.object(
            bot.executor, "_capture_region", return_value=MagicMock()
        ), patch.object(
            bot.ocr_engine, "extract_all_text", return_value=sample
        ):
            out = bot.extract_text_from_region(
                region=(0, 0, 50, 50), confidence_threshold=80.0
            )
        assert out == ["high"]

    def test_whole_screen_fallback_when_no_region(self, bot):
        sample = [OCRResult("found", 90.0, (0, 0, 5, 5))]
        screen = MagicMock(width=1920, height=1080)
        with patch("pyautogui.screenshot", return_value=screen), patch.object(
            bot.ocr_engine, "extract_all_text", return_value=sample
        ):
            out = bot.extract_text_from_region()
        assert out == ["found"]

    def test_backtrack_retries_lower_threshold(self, bot):
        """When backtrack=True and the first pass returns no high-confidence
        match, the loop drops the threshold by 10 and retries -- so the
        second pass picks up a 50.0-confidence match that the first pass
        filtered out at 90.0."""
        sample = [OCRResult("X", 50.0, (0, 0, 1, 1))]

        with patch.object(
            bot.executor, "_capture_region", return_value=MagicMock()
        ), patch.object(
            bot.ocr_engine, "extract_all_text", return_value=sample
        ), patch("time.sleep"):
            out = bot.extract_text_from_region(
                region=(0, 0, 10, 10),
                confidence_threshold=90.0,
                backtrack=True,
                max_attempts=8,
            )
        # After threshold relaxes below 50.0 the loop returns the match.
        assert out == ["X"]

    def test_returns_empty_when_all_attempts_fail(self, bot):
        with patch.object(
            bot.executor, "_capture_region", return_value=MagicMock()
        ), patch.object(
            bot.ocr_engine, "extract_all_text", return_value=[]
        ), patch("time.sleep"):
            out = bot.extract_text_from_region(
                region=(0, 0, 10, 10),
                backtrack=True,
                max_attempts=2,
            )
        assert out == []

    def test_exception_with_backtrack_retries(self, bot):
        calls = {"n": 0}

        def explode_then_succeed(img, ft):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("io")
            return [OCRResult("ok", 90.0, (0, 0, 1, 1))]

        with patch.object(
            bot.executor, "_capture_region", return_value=MagicMock()
        ), patch.object(
            bot.ocr_engine,
            "extract_all_text",
            side_effect=explode_then_succeed,
        ), patch("time.sleep"):
            out = bot.extract_text_from_region(
                region=(0, 0, 10, 10),
                backtrack=True,
                max_attempts=2,
            )
        assert out == ["ok"]


@requires_tesseract
class TestFindRelativeImageWaitBranches:
    @pytest.fixture
    def bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_wait_until_found_path(self, bot):
        with patch.object(
            bot.executor.wait_manager,
            "wait_until_found",
            return_value=(1, 2, 3, 4),
        ):
            out = bot.find_relative_image(
                anchor_image="a.png",
                target_image="t.png",
                wait_until_found=True,
            )
        assert out == (1, 2, 3, 4)

    def test_wait_until_disappears_path_returns_result(self, bot):
        with patch.object(
            bot.executor.relative_detector,
            "locate_relative_image",
            return_value=(5, 6, 7, 8),
        ), patch.object(
            bot.executor.wait_manager,
            "wait_until_disappears",
            return_value=True,
        ):
            out = bot.find_relative_image(
                anchor_image="a.png",
                target_image="t.png",
                wait_until_disappears=True,
            )
        assert out == (5, 6, 7, 8)

    def test_wait_until_disappears_returns_none_if_first_miss(self, bot):
        with patch.object(
            bot.executor.relative_detector,
            "locate_relative_image",
            return_value=None,
        ):
            out = bot.find_relative_image(
                anchor_image="a.png",
                target_image="t.png",
                wait_until_disappears=True,
            )
        assert out is None

    def test_plain_path_exception_returns_none(self, bot):
        with patch.object(
            bot.executor.relative_detector,
            "locate_relative_image",
            side_effect=RuntimeError("io"),
        ):
            out = bot.find_relative_image(
                anchor_image="a.png", target_image="t.png"
            )
        assert out is None


@requires_tesseract
class TestStandaloneRunIndividualBacktrack:
    def test_start_individual_session_returns_bot(self):
        bot = vd.start_individual_session({"show_overlay": False})
        assert isinstance(bot, vd.VisusBot)

    def test_run_individual_tasks_with_backtrack_dispatches_callable(self):
        called = {"n": 0}

        def step(bot):
            called["n"] += 1
            return True

        # Returns (successful, total, bot).
        successful, total, bot = vd.run_individual_tasks_with_backtrack(
            [(step, (), {})],
            config={"show_overlay": False},
        )
        assert called["n"] == 1
        assert isinstance(bot, vd.VisusBot)

    def test_run_individual_tasks_swallows_callable_exceptions(self):
        def bad(bot):
            raise RuntimeError("io")

        successful, total, bot = vd.run_individual_tasks_with_backtrack(
            [(bad, (), {})],
            config={"show_overlay": False},
        )
        # The exception is swallowed and recorded as a failure.
        assert isinstance(bot, vd.VisusBot)

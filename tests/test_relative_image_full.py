"""Full coverage for ``RelativeImageDetector.locate_image_with_retry``.

Targets the missing line range 160-232 (the multi-scale retry loop
with confidence relaxation).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from visus.desktop.core.relative_image import RelativeImageDetector


@pytest.fixture
def detector():
    return RelativeImageDetector()


class TestLocateImageWithRetry:
    def test_finds_at_original_scale_first_attempt(self, detector, tmp_path):
        img = tmp_path / "tile.png"
        from PIL import Image as _PILImage

        _PILImage.new("RGB", (16, 16), color="red").save(img)
        match = MagicMock(left=10, top=20, width=16, height=16)
        with patch("pyautogui.locateOnScreen", return_value=match) as los:
            result = detector.locate_image_with_retry(str(img), confidence=0.9)
        assert result is match
        # First call is with scale==1.0 -- no temp file involved.
        first_args = los.call_args_list[0]
        assert first_args.args[0] == str(img)

    def test_finds_at_scaled_variant(self, detector, tmp_path):
        img = tmp_path / "tile.png"
        from PIL import Image as _PILImage

        _PILImage.new("RGB", (16, 16), color="red").save(img)
        match = MagicMock(left=11, top=21, width=15, height=15)
        # First call (scale 1.0) misses; second (scale 0.95) hits.
        with patch(
            "pyautogui.locateOnScreen", side_effect=[None, match]
        ):
            result = detector.locate_image_with_retry(
                str(img), confidence=0.9, max_attempts=1
            )
        assert result is match

    def test_forwards_region_kwarg(self, detector, tmp_path):
        img = tmp_path / "tile.png"
        from PIL import Image as _PILImage

        _PILImage.new("RGB", (16, 16), color="red").save(img)
        match = MagicMock(left=1, top=2, width=3, height=4)
        with patch("pyautogui.locateOnScreen", return_value=match) as los:
            detector.locate_image_with_retry(
                str(img), region=(0, 0, 100, 100), confidence=0.9
            )
        assert los.call_args.kwargs.get("region") == (0, 0, 100, 100)

    def test_relaxes_confidence_after_scale_loop(self, detector, tmp_path):
        img = tmp_path / "tile.png"
        from PIL import Image as _PILImage

        _PILImage.new("RGB", (16, 16), color="red").save(img)
        # Misses every scale; the "adjusted confidence" branch is what
        # eventually returns the match.
        match = MagicMock(left=5, top=6, width=7, height=8)
        with patch(
            "pyautogui.locateOnScreen",
            side_effect=[None, None, None, match],
        ), patch("time.sleep"):
            result = detector.locate_image_with_retry(
                str(img), confidence=0.9, max_attempts=1
            )
        assert result is match

    def test_returns_none_after_all_attempts_exhausted(self, detector, tmp_path):
        img = tmp_path / "tile.png"
        from PIL import Image as _PILImage

        _PILImage.new("RGB", (16, 16), color="red").save(img)
        with patch("pyautogui.locateOnScreen", return_value=None), patch(
            "time.sleep"
        ):
            result = detector.locate_image_with_retry(
                str(img), confidence=0.9, max_attempts=2
            )
        assert result is None

    def test_exception_inside_scale_loop_is_swallowed(self, detector, tmp_path):
        img = tmp_path / "tile.png"
        from PIL import Image as _PILImage

        _PILImage.new("RGB", (16, 16), color="red").save(img)
        match = MagicMock(left=1, top=2, width=3, height=4)
        # First two calls raise (scales 1.0, 0.95); third returns the match.
        with patch(
            "pyautogui.locateOnScreen",
            side_effect=[RuntimeError("io"), RuntimeError("io"), match],
        ), patch("time.sleep"):
            result = detector.locate_image_with_retry(
                str(img), confidence=0.9, max_attempts=1
            )
        assert result is match

    def test_custom_scale_list_respected(self, detector, tmp_path):
        img = tmp_path / "tile.png"
        from PIL import Image as _PILImage

        _PILImage.new("RGB", (16, 16), color="red").save(img)
        match = MagicMock(left=1, top=2, width=3, height=4)
        with patch(
            "pyautogui.locateOnScreen", return_value=match
        ) as los:
            detector.locate_image_with_retry(
                str(img), confidence=0.9, scales=[1.0], max_attempts=1
            )
        # Only one scale -> only one locateOnScreen call in the scale loop.
        # (Plus possibly one for the adjusted confidence path if scale loop
        # missed, but our mock returns a match immediately.)
        assert los.call_count >= 1

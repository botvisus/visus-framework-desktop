"""Tests for the cv2.matchTemplate-backed image matcher (Phase 3, E1).

mss handles screen capture; cv2.matchTemplate handles the actual
template-in-haystack search. The legacy ``pyautogui.locateOnScreen``
path stays as an opt-in fallback. ``config['matcher']`` chooses the
strategy: ``'cv2'`` (default) or ``'pyscreeze'``.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
from PIL import Image

from visus.desktop.core.locate import locate_template_cv2, safe_locate_on_screen


def _build_template(tile=(30, 30)):
    """Template carrying genuine variance so TM_CCOEFF_NORMED is well-defined."""
    arr = np.zeros((tile[1], tile[0], 3), dtype=np.uint8)
    # Diagonal red gradient -> non-zero variance per channel.
    for i in range(tile[1]):
        arr[i, :, 0] = (i * 200 // tile[1])  # red ramp top to bottom
        arr[i, :, 1] = 40
        arr[i, :, 2] = 80
    return Image.fromarray(arr, mode="RGB")


def _build_haystack(target_xy=(50, 60), size=(200, 200), tile=(30, 30)):
    """Synthesise a haystack with the templated tile placed at ``target_xy``."""
    arr = np.full((size[1], size[0], 3), 240, dtype=np.uint8)
    template = np.asarray(_build_template(tile))
    x, y = target_xy
    tw, th = tile
    arr[y:y + th, x:x + tw] = template
    return Image.fromarray(arr, mode="RGB")


class TestCv2MatcherDirect:
    def test_finds_template_at_known_position(self, tmp_path):
        haystack = _build_haystack(target_xy=(50, 60))
        template_path = tmp_path / "tile.png"
        _build_template().save(template_path)

        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=haystack
        ):
            box = locate_template_cv2(str(template_path), confidence=0.9)
        assert box is not None
        x, y, w, h = box
        assert (x, y) == (50, 60)
        assert (w, h) == (30, 30)

    def test_returns_none_when_template_absent(self, tmp_path):
        # Templated tile is the diagonal red gradient; haystack is a
        # high-frequency noise pattern with no copy of it.
        rng = np.random.default_rng(seed=42)
        noise = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
        haystack = Image.fromarray(noise, mode="RGB")
        template_path = tmp_path / "tile.png"
        _build_template().save(template_path)

        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=haystack
        ):
            box = locate_template_cv2(str(template_path), confidence=0.99)
        assert box is None

    def test_region_offsets_translate_to_absolute_coordinates(self, tmp_path):
        """When a region is passed the returned coords are screen-absolute."""
        haystack = _build_haystack(target_xy=(20, 30), size=(100, 100))
        template_path = tmp_path / "tile.png"
        _build_template().save(template_path)

        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=haystack
        ):
            box = locate_template_cv2(
                str(template_path),
                region=(500, 400, 100, 100),
                confidence=0.9,
            )
        assert box is not None
        # Local match at (20, 30) shifts to (520, 430) in screen coords.
        assert box[:2] == (520, 430)

    def test_template_not_on_disk_raises_matcher_error(self, tmp_path):
        """M2 regression -- missing template is an *error* (cannot attempt),
        not a "no match". Allows safe_locate_on_screen to fall back."""
        import pytest

        from visus.desktop.core.locate import _Cv2MatcherError

        with patch("visus.desktop.core.screen.capture_screen") as cap:
            with pytest.raises(_Cv2MatcherError):
                locate_template_cv2(
                    str(tmp_path / "nonexistent.png"), confidence=0.9
                )
        cap.assert_not_called()


class TestSafeLocateDispatch:
    def test_default_matcher_is_cv2(self):
        from visus.desktop.utils.config import BotVisionConfig

        defaults = BotVisionConfig._load_default_config(
            BotVisionConfig.__new__(BotVisionConfig)
        )
        assert defaults["matcher"] == "cv2"

    def test_safe_locate_uses_cv2_path(self, tmp_path):
        haystack = _build_haystack(target_xy=(10, 20))
        template_path = tmp_path / "tile.png"
        _build_template().save(template_path)

        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=haystack
        ):
            # Default config (matcher='cv2'); call goes through the cv2 path.
            box = safe_locate_on_screen(str(template_path), confidence=0.9)
        assert box is not None
        assert box[:2] == (10, 20)

    def test_safe_locate_falls_back_to_pyscreeze_on_cv2_error(self, tmp_path):
        """M2 regression -- an OpenCV-level error triggers the fallback."""
        bad_template = tmp_path / "bad.png"
        bad_template.write_bytes(b"not a png")

        called = {"pyscreeze": False}

        def fake_pyscreeze(path, **kwargs):
            called["pyscreeze"] = True
            return None

        with patch("pyautogui.locateOnScreen", side_effect=fake_pyscreeze):
            safe_locate_on_screen(str(bad_template), confidence=0.9)
        assert called["pyscreeze"] is True

    def test_safe_locate_does_not_fallback_on_legitimate_no_match(self, tmp_path):
        """M2 regression -- a clean "cv2 ran and missed" should NOT trigger
        a second pyscreeze scan (the original full-screen-scan wasted work)."""
        import numpy as np

        rng = np.random.default_rng(seed=7)
        noise = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
        from PIL import Image as _PILImage

        haystack = _PILImage.fromarray(noise, mode="RGB")
        template_path = tmp_path / "tile.png"
        _build_template().save(template_path)

        pyscreeze_calls = {"n": 0}

        def counting_pyscreeze(path, **kwargs):
            pyscreeze_calls["n"] += 1
            return None

        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=haystack
        ), patch("pyautogui.locateOnScreen", side_effect=counting_pyscreeze):
            box = safe_locate_on_screen(str(template_path), confidence=0.99)
        assert box is None
        assert pyscreeze_calls["n"] == 0, (
            "cv2 cleanly missed; pyscreeze must not be invoked"
        )

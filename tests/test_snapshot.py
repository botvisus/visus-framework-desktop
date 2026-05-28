"""Tests for screen snapshot regression (Phase 2, TS2).

``assert_screen_matches('path.png', region=...)`` compares the current
screen capture against a stored PNG. The first run (or when
``VISUS_UPDATE_SNAPSHOTS=1`` is set) writes the baseline; later runs
fail with a clear AssertionError when the pixels drift outside the
allowed tolerance.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PIL import Image

from visus_pytest import assert_screen_matches


def _img(color, size=(16, 16)):
    return Image.new("RGB", size, color=color)


class TestSnapshotRegression:
    def test_first_run_creates_baseline(self, tmp_path):
        snap = tmp_path / "login.png"
        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=_img("red")
        ):
            with pytest.raises(pytest.skip.Exception, match="snapshot created"):
                assert_screen_matches(snap)
        assert snap.exists()

    def test_matching_capture_passes(self, tmp_path):
        snap = tmp_path / "login.png"
        _img("red").save(snap)
        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=_img("red")
        ):
            assert_screen_matches(snap)

    def test_drift_above_tolerance_fails(self, tmp_path):
        snap = tmp_path / "login.png"
        _img("red").save(snap)
        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=_img("blue")
        ):
            with pytest.raises(AssertionError, match="differs"):
                assert_screen_matches(snap, tolerance=0.01)

    def test_tolerance_absorbs_minor_drift(self, tmp_path):
        """A small percentage of changed pixels passes when tolerance allows it."""
        snap = tmp_path / "login.png"
        _img("red").save(snap)
        # Swap a single pixel out of 256 -> 0.39% drift.
        actual = _img("red")
        actual.putpixel((0, 0), (0, 0, 255))
        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=actual
        ):
            assert_screen_matches(snap, tolerance=0.05)  # 5% allowed
            with pytest.raises(AssertionError):
                assert_screen_matches(snap, tolerance=0.0)  # strict

    def test_update_env_var_rewrites_baseline(self, tmp_path, monkeypatch):
        snap = tmp_path / "login.png"
        _img("red").save(snap)
        monkeypatch.setenv("VISUS_UPDATE_SNAPSHOTS", "1")
        with patch(
            "visus.desktop.core.screen.capture_screen", return_value=_img("blue")
        ):
            assert_screen_matches(snap)  # rewrites instead of failing
        rewritten = Image.open(snap).convert("RGB")
        assert rewritten.getpixel((0, 0)) == (0, 0, 255)

    def test_forwards_region_to_capture(self, tmp_path):
        snap = tmp_path / "x.png"
        captured = []

        def fake(region=None):
            captured.append({"region": region})
            return _img("red")

        with patch(
            "visus.desktop.core.screen.capture_screen", side_effect=fake
        ):
            with pytest.raises(pytest.skip.Exception):
                assert_screen_matches(snap, region=(10, 20, 100, 50))
        assert captured[0]["region"] == (10, 20, 100, 50)

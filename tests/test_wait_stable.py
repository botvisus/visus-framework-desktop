"""Tests for ``wait_for_stable_screen`` (Phase 2, S1).

The helper polls ``capture_screen`` and returns True once the captured
pixels have been unchanged for ``stable_for`` seconds, or False on
timeout. Classic SPA / Oracle Forms "wait until the redraw finishes"
primitive.
"""

from __future__ import annotations

from unittest.mock import patch

from PIL import Image

from visus.desktop import wait_for_stable_screen


def _img(color):
    return Image.new("RGB", (4, 4), color=color)


class TestWaitForStableScreen:
    def test_returns_true_when_screen_already_stable(self):
        # Capture always returns the same image; should resolve quickly.
        with patch(
            "visus.desktop.core.screen.capture_screen",
            return_value=_img("white"),
        ):
            ok = wait_for_stable_screen(
                stable_for=0.05, timeout=2.0, poll_interval=0.01
            )
        assert ok is True

    def test_returns_true_after_screen_stops_changing(self):
        """Screen flickers briefly, then stabilises -> stable detected."""
        sequence = [
            _img("white"),
            _img("black"),
            _img("red"),
            _img("blue"),
            _img("blue"),
            _img("blue"),
            _img("blue"),
            _img("blue"),
        ]
        idx = {"i": 0}

        def fake_capture(region=None):
            i = min(idx["i"], len(sequence) - 1)
            idx["i"] += 1
            return sequence[i]

        with patch(
            "visus.desktop.core.screen.capture_screen", side_effect=fake_capture
        ):
            ok = wait_for_stable_screen(
                stable_for=0.05, timeout=2.0, poll_interval=0.01
            )
        assert ok is True

    def test_returns_false_when_screen_never_settles(self):
        toggle = {"flip": False}

        def fake_capture(region=None):
            toggle["flip"] = not toggle["flip"]
            return _img("white" if toggle["flip"] else "black")

        with patch(
            "visus.desktop.core.screen.capture_screen", side_effect=fake_capture
        ):
            ok = wait_for_stable_screen(
                stable_for=0.2, timeout=0.4, poll_interval=0.01
            )
        assert ok is False

    def test_forwards_region_to_capture_screen(self):
        captured_kwargs = []

        def fake_capture(region=None):
            captured_kwargs.append({"region": region})
            return _img("white")

        with patch(
            "visus.desktop.core.screen.capture_screen", side_effect=fake_capture
        ):
            wait_for_stable_screen(
                region=(10, 20, 100, 50),
                stable_for=0.05,
                timeout=1.0,
                poll_interval=0.01,
            )
        assert captured_kwargs[0]["region"] == (10, 20, 100, 50)

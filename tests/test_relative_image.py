"""Tests for ``visus.desktop.core.relative_image.RelativeImageDetector``.

The image-search calls (``pyautogui.locateOnScreen`` / ``locateAllOnScreen`` /
``center``) are monkeypatched so synthetic boxes are fed in. No real screenshot
is ever taken. The tests focus on the nearest-target selection logic.
"""

from __future__ import annotations

import collections

import pyautogui
import pytest

from visus.desktop.core.relative_image import RelativeImageDetector
from visus.desktop.exceptions import ImageNotFoundError

# Box / Point shapes matching pyautogui's own namedtuples.
Box = collections.namedtuple("Box", "left top width height")
Point = collections.namedtuple("Point", "x y")


def _center(box):
    """Mimic pyautogui.center: centre point of a Box."""
    return Point(box.left + box.width // 2, box.top + box.height // 2)


@pytest.fixture
def detector():
    return RelativeImageDetector()


def test_construction(detector):
    """The detector constructs without arguments."""
    assert isinstance(detector, RelativeImageDetector)


def test_raises_when_anchor_not_found(monkeypatch, detector):
    """A missing anchor raises ImageNotFoundError (wrapped)."""
    monkeypatch.setattr(pyautogui, "locateOnScreen", lambda *a, **k: None)
    monkeypatch.setattr(pyautogui, "center", _center)

    with pytest.raises(ImageNotFoundError):
        detector.locate_relative_image("anchor.png", "target.png")


def test_returns_none_when_no_targets(monkeypatch, detector):
    """When no target occurrences exist, returns None."""
    anchor = Box(100, 100, 20, 20)
    monkeypatch.setattr(pyautogui, "locateOnScreen", lambda *a, **k: anchor)
    monkeypatch.setattr(pyautogui, "locateAllOnScreen", lambda *a, **k: iter([]))
    monkeypatch.setattr(pyautogui, "center", _center)

    assert detector.locate_relative_image("anchor.png", "target.png") is None


def test_picks_closest_target_to_anchor(monkeypatch, detector):
    """Among several targets, the one nearest the anchor centre is returned."""
    anchor = Box(100, 100, 10, 10)  # centre (105, 105)
    near = Box(110, 110, 10, 10)  # centre (115, 115) -> ~14px away
    far = Box(400, 400, 10, 10)  # centre (405, 405) -> ~424px away

    monkeypatch.setattr(pyautogui, "locateOnScreen", lambda *a, **k: anchor)
    monkeypatch.setattr(
        pyautogui, "locateAllOnScreen", lambda *a, **k: iter([far, near])
    )
    monkeypatch.setattr(pyautogui, "center", _center)

    result = detector.locate_relative_image(
        "anchor.png", "target.png", max_distance=1000
    )

    assert result == near


def test_returns_none_when_all_targets_beyond_max_distance(monkeypatch, detector):
    """If every target is farther than max_distance, returns None."""
    anchor = Box(0, 0, 10, 10)  # centre (5, 5)
    far1 = Box(500, 500, 10, 10)
    far2 = Box(800, 800, 10, 10)

    monkeypatch.setattr(pyautogui, "locateOnScreen", lambda *a, **k: anchor)
    monkeypatch.setattr(
        pyautogui, "locateAllOnScreen", lambda *a, **k: iter([far1, far2])
    )
    monkeypatch.setattr(pyautogui, "center", _center)

    result = detector.locate_relative_image(
        "anchor.png", "target.png", max_distance=50
    )

    assert result is None


def test_target_exactly_at_max_distance_is_included(monkeypatch, detector):
    """A target whose distance equals max_distance is accepted (<=)."""
    anchor = Box(0, 0, 0, 0)  # centre (0, 0)
    # centre (30, 40) -> distance exactly 50.
    target = Box(30, 40, 0, 0)

    monkeypatch.setattr(pyautogui, "locateOnScreen", lambda *a, **k: anchor)
    monkeypatch.setattr(pyautogui, "locateAllOnScreen", lambda *a, **k: iter([target]))
    monkeypatch.setattr(pyautogui, "center", _center)

    result = detector.locate_relative_image(
        "anchor.png", "target.png", max_distance=50
    )

    assert result == target


def test_single_target_within_range_returned(monkeypatch, detector):
    """A single in-range target is returned directly."""
    anchor = Box(50, 50, 10, 10)
    target = Box(60, 60, 10, 10)

    monkeypatch.setattr(pyautogui, "locateOnScreen", lambda *a, **k: anchor)
    monkeypatch.setattr(pyautogui, "locateAllOnScreen", lambda *a, **k: iter([target]))
    monkeypatch.setattr(pyautogui, "center", _center)

    result = detector.locate_relative_image("anchor.png", "target.png")

    assert result == target


def test_target_region_is_forwarded(monkeypatch, detector):
    """When target_region is given it is forwarded to locateAllOnScreen."""
    anchor = Box(0, 0, 10, 10)
    target = Box(5, 5, 10, 10)
    captured = {}

    monkeypatch.setattr(pyautogui, "locateOnScreen", lambda *a, **k: anchor)

    def fake_all(image_path, **kwargs):
        captured["image_path"] = image_path
        captured.update(kwargs)
        return iter([target])

    monkeypatch.setattr(pyautogui, "locateAllOnScreen", fake_all)
    monkeypatch.setattr(pyautogui, "center", _center)

    detector.locate_relative_image(
        "anchor.png",
        "target.png",
        target_region=(10, 20, 30, 40),
        confidence=0.8,
    )

    assert captured["image_path"] == "target.png"
    assert captured["region"] == (10, 20, 30, 40)
    assert captured["confidence"] == 0.8


def test_confidence_forwarded_to_anchor_search(monkeypatch, detector):
    """The confidence value is forwarded to the anchor locateOnScreen call."""
    anchor = Box(0, 0, 10, 10)
    captured = {}

    def fake_locate(image_path, **kwargs):
        captured["image_path"] = image_path
        captured.update(kwargs)
        return anchor

    monkeypatch.setattr(pyautogui, "locateOnScreen", fake_locate)
    monkeypatch.setattr(pyautogui, "locateAllOnScreen", lambda *a, **k: iter([]))
    monkeypatch.setattr(pyautogui, "center", _center)

    detector.locate_relative_image("anchor.png", "target.png", confidence=0.77)

    assert captured["image_path"] == "anchor.png"
    assert captured["confidence"] == 0.77


def test_unexpected_error_wrapped_as_image_not_found(monkeypatch, detector):
    """Any backend exception is wrapped in ImageNotFoundError."""

    def boom(*a, **k):
        raise RuntimeError("backend exploded")

    monkeypatch.setattr(pyautogui, "locateOnScreen", boom)
    monkeypatch.setattr(pyautogui, "center", _center)

    with pytest.raises(ImageNotFoundError):
        detector.locate_relative_image("anchor.png", "target.png")

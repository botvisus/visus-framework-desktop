"""Tests for ``visus.desktop.core.locate``.

These tests monkeypatch ``pyautogui.locateAllOnScreen`` /
``pyautogui.locateOnScreen`` so they never take a real screenshot or search the
real screen.
"""

from __future__ import annotations

import collections

import pyautogui

from visus.desktop.core import locate

# A Box-like namedtuple matching pyautogui's own ``Box`` shape.
Box = collections.namedtuple("Box", "left top width height")


# --------------------------------------------------------------------------- #
# find_all
# --------------------------------------------------------------------------- #
def test_find_all_returns_plain_tuples(monkeypatch):
    """Each Box-like match is converted to a plain ``(l, t, w, h)`` tuple."""
    boxes = [Box(10, 20, 30, 40), Box(50, 60, 70, 80)]
    monkeypatch.setattr(
        pyautogui, "locateAllOnScreen", lambda *a, **k: iter(boxes)
    )

    result = locate.find_all("image.png")

    assert result == [(10, 20, 30, 40), (50, 60, 70, 80)]
    assert all(isinstance(item, tuple) for item in result)


def test_find_all_empty_iterator(monkeypatch):
    """An empty iterator from pyautogui yields an empty list."""
    monkeypatch.setattr(pyautogui, "locateAllOnScreen", lambda *a, **k: iter([]))

    assert locate.find_all("image.png") == []


def test_find_all_returns_empty_when_none(monkeypatch):
    """``None`` (some pyautogui versions) is treated as no matches."""
    monkeypatch.setattr(pyautogui, "locateAllOnScreen", lambda *a, **k: None)

    assert locate.find_all("image.png") == []


def test_find_all_swallows_generic_exception(monkeypatch):
    """A generic raise from pyautogui results in an empty list."""

    def boom(*a, **k):
        raise RuntimeError("backend exploded")

    monkeypatch.setattr(pyautogui, "locateAllOnScreen", boom)

    assert locate.find_all("image.png") == []


def test_find_all_handles_image_not_found_exception(monkeypatch):
    """``ImageNotFoundException`` is treated as no matches."""
    not_found = getattr(pyautogui, "ImageNotFoundException", RuntimeError)

    def boom(*a, **k):
        raise not_found("not found")

    monkeypatch.setattr(pyautogui, "locateAllOnScreen", boom)

    assert locate.find_all("image.png") == []


def test_find_all_retries_without_confidence_on_opencv_error(monkeypatch):
    """When confidence raises (missing OpenCV) the call retries without it."""
    seen_kwargs = []
    boxes = [Box(1, 2, 3, 4)]

    def fake(image_path, **kwargs):
        seen_kwargs.append(kwargs)
        if "confidence" in kwargs:
            raise NotImplementedError("OpenCV is required for confidence")
        return iter(boxes)

    monkeypatch.setattr(pyautogui, "locateAllOnScreen", fake)

    result = locate.find_all("image.png", confidence=0.95)

    assert result == [(1, 2, 3, 4)]
    # First attempt with confidence, second without.
    assert "confidence" in seen_kwargs[0]
    assert "confidence" not in seen_kwargs[1]


def test_find_all_forwards_arguments(monkeypatch):
    """Region/confidence/grayscale are forwarded to pyautogui."""
    captured = {}

    def fake(image_path, **kwargs):
        captured["image_path"] = image_path
        captured.update(kwargs)
        return iter([Box(0, 0, 1, 1)])

    monkeypatch.setattr(pyautogui, "locateAllOnScreen", fake)

    locate.find_all(
        "tpl.png", region=(5, 6, 7, 8), confidence=0.8, grayscale=True
    )

    assert captured["image_path"] == "tpl.png"
    assert captured["region"] == (5, 6, 7, 8)
    assert captured["confidence"] == 0.8
    assert captured["grayscale"] is True


# --------------------------------------------------------------------------- #
# find_multiple
# --------------------------------------------------------------------------- #
def test_find_multiple_dict_input(monkeypatch):
    """Dict input maps labels to tuples or ``None`` per match."""

    def fake(image_path, **kwargs):
        if image_path == "ok.png":
            return Box(11, 22, 33, 44)
        return None

    monkeypatch.setattr(pyautogui, "locateOnScreen", fake)

    result = locate.find_multiple({"good": "ok.png", "bad": "missing.png"})

    assert result == {"good": (11, 22, 33, 44), "bad": None}


def test_find_multiple_handles_raise_as_none(monkeypatch):
    """A lookup that raises is stored as ``None``, others still resolve."""

    def fake(image_path, **kwargs):
        if image_path == "ok.png":
            return Box(1, 1, 2, 2)
        raise RuntimeError("lookup failed")

    monkeypatch.setattr(pyautogui, "locateOnScreen", fake)

    result = locate.find_multiple({"good": "ok.png", "boom": "err.png"})

    assert result == {"good": (1, 1, 2, 2), "boom": None}


def test_find_multiple_list_input_uses_paths_as_keys(monkeypatch):
    """List input keys the result dict by the image paths themselves."""

    def fake(image_path, **kwargs):
        if image_path == "a.png":
            return Box(5, 5, 5, 5)
        return None

    monkeypatch.setattr(pyautogui, "locateOnScreen", fake)

    result = locate.find_multiple(["a.png", "b.png"])

    assert result == {"a.png": (5, 5, 5, 5), "b.png": None}


def test_find_multiple_handles_image_not_found_exception(monkeypatch):
    """``ImageNotFoundException`` per image is stored as ``None``."""
    not_found = getattr(pyautogui, "ImageNotFoundException", RuntimeError)

    def fake(image_path, **kwargs):
        if image_path == "ok.png":
            return Box(9, 8, 7, 6)
        raise not_found("nope")

    monkeypatch.setattr(pyautogui, "locateOnScreen", fake)

    result = locate.find_multiple(["ok.png", "nope.png"])

    assert result == {"ok.png": (9, 8, 7, 6), "nope.png": None}


def test_find_multiple_retries_without_confidence_on_opencv_error(monkeypatch):
    """find_multiple retries a per-image lookup without confidence on OpenCV error."""
    seen_kwargs = []

    def fake(image_path, **kwargs):
        seen_kwargs.append(kwargs)
        if "confidence" in kwargs:
            raise NotImplementedError("OpenCV is required for confidence")
        return Box(2, 4, 6, 8)

    monkeypatch.setattr(pyautogui, "locateOnScreen", fake)

    result = locate.find_multiple({"x": "x.png"}, confidence=0.7)

    assert result == {"x": (2, 4, 6, 8)}
    assert "confidence" in seen_kwargs[0]
    assert "confidence" not in seen_kwargs[1]


def test_find_multiple_forwards_region_and_grayscale(monkeypatch):
    """Region and grayscale are forwarded to each per-image lookup."""
    captured = {}

    def fake(image_path, **kwargs):
        captured.update(kwargs)
        return Box(0, 0, 1, 1)

    monkeypatch.setattr(pyautogui, "locateOnScreen", fake)

    locate.find_multiple(
        {"a": "a.png"}, region=(1, 2, 3, 4), confidence=0.6, grayscale=True
    )

    assert captured["region"] == (1, 2, 3, 4)
    assert captured["confidence"] == 0.6
    assert captured["grayscale"] is True

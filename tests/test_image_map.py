"""
Tests for :mod:`visus.desktop.core.image_map`.

These tests use ``tmp_path`` to create dummy image files and exercise the full
public API of :class:`ImageMap` without requiring a real screen.
"""

from __future__ import annotations

import pytest

from visus.desktop.core.image_map import ImageMap


def _make_image(tmp_path, name: str) -> str:
    """Create a dummy image file and return its path as a string."""
    path = tmp_path / name
    path.write_bytes(b"fake-image-bytes")
    return str(path)


def test_register_and_get(tmp_path):
    """A registered label returns the exact path it was registered with."""
    img = _make_image(tmp_path, "button.png")
    image_map = ImageMap()
    image_map.register("button", img)
    assert image_map.get("button") == img


def test_register_nonexistent_path_raises(tmp_path):
    """Registering a path that does not exist raises FileNotFoundError."""
    image_map = ImageMap()
    missing = str(tmp_path / "missing.png")
    with pytest.raises(FileNotFoundError):
        image_map.register("missing", missing)


def test_register_empty_label_raises(tmp_path):
    """Registering an empty label raises ValueError."""
    img = _make_image(tmp_path, "logo.png")
    image_map = ImageMap()
    with pytest.raises(ValueError):
        image_map.register("", img)


def test_get_unknown_label_raises():
    """Looking up an unregistered label raises KeyError."""
    image_map = ImageMap()
    with pytest.raises(KeyError):
        image_map.get("nope")


def test_resolve_known_label_returns_path(tmp_path):
    """resolve() returns the registered path when given a known label."""
    img = _make_image(tmp_path, "icon.png")
    image_map = ImageMap()
    image_map.register("icon", img)
    assert image_map.resolve("icon") == img


def test_resolve_unknown_string_returned_unchanged():
    """resolve() returns an unknown string unchanged (treated as a path)."""
    image_map = ImageMap()
    raw_path = "C:/some/raw/path.png"
    assert image_map.resolve(raw_path) == raw_path


def test_contains(tmp_path):
    """__contains__ reflects whether a label is registered."""
    img = _make_image(tmp_path, "ok.png")
    image_map = ImageMap()
    image_map.register("ok", img)
    assert "ok" in image_map
    assert "absent" not in image_map


def test_labels_sorted(tmp_path):
    """labels() returns all registered labels in sorted order."""
    img_a = _make_image(tmp_path, "a.png")
    img_b = _make_image(tmp_path, "b.png")
    image_map = ImageMap()
    image_map.register("zebra", img_b)
    image_map.register("alpha", img_a)
    assert image_map.labels() == ["alpha", "zebra"]


def test_register_many(tmp_path):
    """register_many() registers every label/path pair in the mapping."""
    img_a = _make_image(tmp_path, "first.png")
    img_b = _make_image(tmp_path, "second.png")
    image_map = ImageMap()
    image_map.register_many({"first": img_a, "second": img_b})
    assert image_map.get("first") == img_a
    assert image_map.get("second") == img_b
    assert image_map.labels() == ["first", "second"]


def test_clear(tmp_path):
    """clear() removes all registered labels."""
    img = _make_image(tmp_path, "tmp.png")
    image_map = ImageMap()
    image_map.register("tmp", img)
    assert "tmp" in image_map
    image_map.clear()
    assert image_map.labels() == []
    assert "tmp" not in image_map

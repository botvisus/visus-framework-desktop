"""pytest-visus -- bundled pytest fixtures for testing Visus Desktop bots.

Auto-discovered via the ``[project.entry-points."pytest11"]`` table in
``pyproject.toml``. Users get the fixtures by installing the extra:

    pip install 'visus-desktop[test]'

and writing tests against the three fixtures exported below.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

__all__ = ["mock_screen", "fake_ocr", "record_clicks", "assert_screen_matches"]


def assert_screen_matches(
    snapshot_path: str | os.PathLike[str],
    region: tuple[int, int, int, int] | None = None,
    tolerance: float = 0.0,
) -> None:
    """Assert the current screen matches a stored baseline PNG (Phase 2 / TS2).

    Behaviour by state:
      * **Baseline missing** (or ``VISUS_UPDATE_SNAPSHOTS=1`` env var
        set): the current capture is saved to ``snapshot_path``. On the
        missing-baseline path the function raises ``pytest.skip`` so the
        test signals "first run, baseline created" without silently
        passing.
      * **Baseline present**: capture is compared pixel-by-pixel.
        ``tolerance`` is the maximum fraction of differing pixels (0.0
        = exact match, 0.05 = 5% allowed). When sizes differ the
        comparison fails outright -- callers should pin the ``region``.

    Args:
        snapshot_path: PNG path under ``tests/snapshots/`` (or wherever
            you choose). Parent directories are created if needed.
        region: ``(x, y, w, h)`` forwarded to ``capture_screen``.
        tolerance: ``[0.0, 1.0]`` -- fraction of pixels allowed to
            differ before the comparison fails.
    """
    from visus.desktop.core import screen as _screen

    path = Path(snapshot_path)
    actual = _screen.capture_screen(region=region).convert("RGB")

    update_requested = os.environ.get("VISUS_UPDATE_SNAPSHOTS") == "1"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        actual.save(path)
        pytest.skip(f"snapshot created at {path}")
    if update_requested:
        actual.save(path)
        return

    expected = Image.open(path).convert("RGB")
    if expected.size != actual.size:
        raise AssertionError(
            f"snapshot {path} differs in size: expected {expected.size}, "
            f"got {actual.size}"
        )
    diff_fraction = _pixel_diff_fraction(actual, expected)
    if diff_fraction > tolerance:
        raise AssertionError(
            f"screen differs from {path} by {diff_fraction:.2%} of pixels "
            f"(tolerance {tolerance:.2%})"
        )


def _pixel_diff_fraction(a: Image.Image, b: Image.Image) -> float:
    """Return the fraction of differing pixels between two equal-size images."""
    import numpy as np

    arr_a = np.asarray(a)
    arr_b = np.asarray(b)
    diff_mask = np.any(arr_a != arr_b, axis=-1)
    if diff_mask.size == 0:
        return 0.0
    return float(diff_mask.sum()) / float(diff_mask.size)


class _MockScreen:
    """Drop-in replacement for ``capture_screen`` used by ``mock_screen``."""

    def __init__(self):
        self.frames: list = []
        self.index = 0
        self.calls: list = []

    def push(self, image) -> None:
        """Queue a PIL ``Image`` to be returned by the next ``capture_screen``."""
        self.frames.append(image)

    def __call__(self, region=None):
        self.calls.append({"region": region})
        if not self.frames:
            return Image.new("RGB", (100, 100), color="white")
        image = self.frames[self.index % len(self.frames)]
        self.index += 1
        if region is not None:
            x, y, w, h = region
            image = image.crop((x, y, x + w, y + h))
        return image


@pytest.fixture
def mock_screen(monkeypatch):
    """Patch ``capture_screen`` everywhere it's imported.

    Returns a ``_MockScreen`` instance. Push PIL images with ``.push(img)``
    -- they're returned in sequence (looping when exhausted) by every
    in-library call to ``capture_screen``.
    """
    mock = _MockScreen()
    monkeypatch.setattr(
        "visus.desktop.core.screen.capture_screen", mock, raising=True
    )
    monkeypatch.setattr(
        "visus.desktop.core.task_executor.capture_screen", mock, raising=True
    )
    return mock


class _FakeOCR:
    """Queue ``(text, box, confidence)`` triples for ``OCREngine.find_text``."""

    def __init__(self):
        self.entries: list = []

    def returns(self, text: str, box=(0, 0, 100, 20), confidence: float = 95.0):
        self.entries.append((text, box, confidence))

    def find_text(
        self,
        region_img: Any,
        target_text: str,
        filter_type: str = "both",
        early_confidence_threshold: float = 75.0,
    ):
        boxes: list = []
        scores: list = []
        for text, box, conf in self.entries:
            if str(target_text).lower() in str(text).lower():
                boxes.append(box)
                scores.append(conf)
                if conf >= early_confidence_threshold:
                    return [box], [conf], True
        return boxes, scores, False


@pytest.fixture
def fake_ocr(monkeypatch):
    """Patch ``OCREngine.find_text`` with a queue-driven fake.

    Call ``fake_ocr.returns("Login")`` to make the engine "find" that
    word with a stub bounding box and a high confidence; matches are
    case-insensitive substring matches against ``target_text``.
    """
    fake = _FakeOCR()

    def proxy(self, region_img, target_text, filter_type="both",
              early_confidence_threshold=75.0):
        return fake.find_text(
            region_img, target_text, filter_type, early_confidence_threshold
        )

    monkeypatch.setattr(
        "visus.desktop.core.ocr_engine.OCREngine.find_text", proxy, raising=True
    )
    return fake


@pytest.fixture
def record_clicks(monkeypatch):
    """Capture every ``pyautogui`` mouse call so tests can assert intent.

    Returns a list. Each click adds ``{"args": (...), "kwargs": {...}}``;
    ``mouseDown`` / ``mouseUp`` add ``{"event": "down"|"up", ...}``.
    """
    import pyautogui

    events: list = []

    def click(*args, **kwargs):
        events.append({"args": args, "kwargs": kwargs})

    def mouse_down(*args, **kwargs):
        events.append({"event": "down", "args": args, "kwargs": kwargs})

    def mouse_up(*args, **kwargs):
        events.append({"event": "up", "args": args, "kwargs": kwargs})

    monkeypatch.setattr(pyautogui, "click", click)
    monkeypatch.setattr(pyautogui, "mouseDown", mouse_down)
    monkeypatch.setattr(pyautogui, "mouseUp", mouse_up)
    return events

"""Real (non-mocked) tests for ``occurrence`` in find_image / click_image.

Unlike ``test_finders.py`` -- which mocks ``core.locate.find_all`` -- these
tests exercise the **real** image-matching engine end to end:

* A real template PNG (the "needle") and a real 800x600 "screen" PNG (the
  "haystack") with three pixel-identical copies of the needle pasted at known
  positions are written to disk.
* The ONLY substitution is the screen *source*: ``pyscreeze.screenshot`` is
  pointed at the haystack so the search has a deterministic, headless-safe
  picture to scan. The matching itself (OpenCV ``matchTemplate`` via pyscreeze)
  runs for real -- no match coordinates are faked.
* The final OS-level mouse click is recorded (not performed), the same way the
  rest of the suite stubs ``VirtualMouse.click``.

So these assert the genuine behaviour: the engine finds all three copies, sorts
them top-to-bottom / left-to-right, and ``occurrence=N`` returns/clicks the Nth.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from tests import tesseract_available

pytestmark = pytest.mark.skipif(
    not tesseract_available(), reason="Tesseract not installed (VisusBot init)"
)

# Reading-order (top->bottom, left->right) positions of the three needle copies.
# Deliberately written out of reading order to prove the sort is real.
_PASTE_POSITIONS = [(500, 400), (100, 50), (300, 250)]
_NEEDLE_W, _NEEDLE_H = 30, 20
# What the engine should return, in reading order, as (x, y, w, h):
_EXPECTED_IN_READING_ORDER = [
    (100, 50, _NEEDLE_W, _NEEDLE_H),
    (300, 250, _NEEDLE_W, _NEEDLE_H),
    (500, 400, _NEEDLE_W, _NEEDLE_H),
]


def _make_needle(path: str) -> None:
    """A small, distinctive template: red border + blue diagonal on white."""
    img = Image.new("RGB", (_NEEDLE_W, _NEEDLE_H), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([2, 2, _NEEDLE_W - 3, _NEEDLE_H - 3], outline="red", width=2)
    draw.line([2, 2, _NEEDLE_W - 3, _NEEDLE_H - 3], fill="blue", width=2)
    img.save(path)


def _make_haystack(needle_path: str) -> Image.Image:
    """An 800x600 white 'screen' with three identical needle copies pasted in."""
    needle = Image.open(needle_path).convert("RGB")
    hay = Image.new("RGB", (800, 600), "white")
    for pos in _PASTE_POSITIONS:
        hay.paste(needle, pos)
    return hay


@pytest.fixture()
def scene(tmp_path, monkeypatch):
    """Write real needle/haystack PNGs and point the screen source at them.

    Yields the on-disk needle path. The real OpenCV matcher runs against the
    in-memory haystack returned by the patched ``pyscreeze.screenshot``.
    """
    import pyscreeze

    needle_path = str(tmp_path / "needle.png")
    _make_needle(needle_path)
    hay = _make_haystack(needle_path)

    # Only the screen *capture* is redirected; matching stays real. Hand out a
    # fresh copy each call -- pyscreeze may close the returned image's fp.
    monkeypatch.setattr(pyscreeze, "screenshot", lambda *a, **k: hay.copy())
    return needle_path


def _make_bot():
    from visus.desktop import VisusBot

    return VisusBot(config={"show_overlay": False})


class _ClickRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return True

    @property
    def last(self):
        return self.calls[-1]


# --------------------------------------------------------------------------- #
# find_image -- real engine
# --------------------------------------------------------------------------- #
class TestFindImageOccurrenceReal:
    def test_engine_really_finds_all_three_copies(self, scene):
        from visus.desktop.core import locate

        boxes = sorted(locate.find_all(scene, confidence=0.9), key=lambda b: (b[1], b[0]))
        assert boxes == _EXPECTED_IN_READING_ORDER

    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_occurrence_returns_nth_in_reading_order(self, scene, n):
        bot = _make_bot()
        box = bot.find_image(scene, occurrence=n)
        assert box == _EXPECTED_IN_READING_ORDER[n - 1]

    def test_occurrence_beyond_available_returns_none(self, scene):
        bot = _make_bot()
        assert bot.find_image(scene, occurrence=4) is None

    def test_default_returns_a_real_match(self, scene):
        bot = _make_bot()
        # occurrence defaults to 1; must be one of the three real copies.
        assert bot.find_image(scene) in _EXPECTED_IN_READING_ORDER


# --------------------------------------------------------------------------- #
# click_image -- real engine, recorded click
# --------------------------------------------------------------------------- #
class TestClickImageOccurrenceReal:
    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_clicks_center_of_nth_match(self, scene, n):
        bot = _make_bot()
        rec = _ClickRecorder()
        bot.executor.virtual_mouse.click = rec

        assert bot.click_image(scene, occurrence=n) is True
        x, y, w, h = _EXPECTED_IN_READING_ORDER[n - 1]
        _, kwargs = rec.last
        assert (kwargs["x"], kwargs["y"]) == (x + w // 2, y + h // 2)

    def test_occurrence_beyond_available_does_not_click(self, scene):
        bot = _make_bot()
        rec = _ClickRecorder()
        bot.executor.virtual_mouse.click = rec

        assert bot.click_image(scene, occurrence=4) is False
        assert rec.calls == []


# --------------------------------------------------------------------------- #
# occurrence + region/specific -- the Visus Studio scenario
# --------------------------------------------------------------------------- #
class TestOccurrenceWithCapturedRegionReal:
    """Regression: a captured template carries the *first* copy's box as ``region``.

    Studio captures a screen area to build the template, so the saved step's
    ``region`` is the bounding box of the FIRST occurrence. With ``specific=False``
    (the Studio default = "search the whole screen") ``occurrence=2`` must still
    reach the 2nd/3rd copies, which live OUTSIDE that captured box.
    """

    # region = bounding box of the first copy in reading order (100, 50, 30, 20)
    _FIRST_BOX_REGION = (100, 50, _NEEDLE_W, _NEEDLE_H)

    @pytest.mark.parametrize("n", [1, 2, 3])
    def test_nonspecific_occurrence_ignores_captured_region(self, scene, n):
        bot = _make_bot()
        box = bot.find_image(
            scene, region=self._FIRST_BOX_REGION, specific=False, occurrence=n
        )
        assert box == _EXPECTED_IN_READING_ORDER[n - 1]

    def test_nonspecific_click_second_copy_with_captured_region(self, scene):
        bot = _make_bot()
        rec = _ClickRecorder()
        bot.executor.virtual_mouse.click = rec

        ok = bot.click_image(
            scene, region=self._FIRST_BOX_REGION, specific=False, occurrence=2
        )
        assert ok is True
        x, y, w, h = _EXPECTED_IN_READING_ORDER[1]
        _, kwargs = rec.last
        assert (kwargs["x"], kwargs["y"]) == (x + w // 2, y + h // 2)

    def test_specific_true_still_restricts_to_region(self, scene):
        # specific=True means "only look inside this region" -- so a region that
        # only contains the first copy legitimately has no 2nd occurrence.
        bot = _make_bot()
        assert (
            bot.find_image(
                scene, region=self._FIRST_BOX_REGION, specific=True, occurrence=2
            )
            is None
        )


# --------------------------------------------------------------------------- #
# standalone module-level wrappers -- real engine
# --------------------------------------------------------------------------- #
class TestStandaloneWrappersReal:
    def test_standalone_find_image_occurrence(self, scene):
        import visus.desktop as vd

        assert vd.find_image(scene, occurrence=2) == _EXPECTED_IN_READING_ORDER[1]
        assert vd.find_image(scene, occurrence=3) == _EXPECTED_IN_READING_ORDER[2]

    def test_standalone_click_image_occurrence(self, scene, monkeypatch):
        import visus.desktop as vd
        from visus.desktop.core.virtual_mouse import VirtualMouse

        rec = _ClickRecorder()
        # The standalone wrapper builds its own VisusBot, so stub the OS click
        # at the class level. Matching still runs for real against the haystack.
        monkeypatch.setattr(VirtualMouse, "click", lambda self, *a, **k: rec(*a, **k))

        assert vd.click_image(scene, occurrence=2) is True
        x, y, w, h = _EXPECTED_IN_READING_ORDER[1]
        _, kwargs = rec.last
        assert (kwargs["x"], kwargs["y"]) == (x + w // 2, y + h // 2)

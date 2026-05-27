"""Focused, fully-mocked tests for the VisusBot finder/click methods.

No real screen, mouse, keyboard, or OCR is touched. Everything is mocked at
the lowest reasonable boundary:

* Image search ultimately calls ``pyautogui.locateOnScreen`` inside the
  executor's ``_parallel_scale_search``. Tests either monkeypatch that, or the
  executor's ``_locate_image_with_retry`` (the call boundary ``find_image``
  uses).
* Text/OCR goes through ``pyautogui.screenshot`` and
  ``OCREngine.find_text``; both are monkeypatched.
* Every click goes through ``TaskExecutor._perform_action`` ->
  ``_perform_click`` -> ``VirtualMouse.click``. Tests record the click via the
  instance's ``virtual_mouse.click`` and disable the overlay so no GUI thread
  starts.
* ``sendtext`` typing is mocked at ``TaskExecutor._process_sendtext``.

``VisusBot()`` requires Tesseract, so every test that builds a bot is guarded
with ``@pytest.mark.skipif(not tesseract_available())`` (Tesseract IS installed
on this machine, so they run here).
"""

from __future__ import annotations

import pytest
from PIL import Image

from tests import tesseract_available

pytestmark = pytest.mark.skipif(
    not tesseract_available(), reason="Tesseract not installed"
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _make_bot():
    """Build a VisusBot with overlays disabled (no GUI thread on clicks)."""
    from visus.desktop import VisusBot

    return VisusBot(config={"show_overlay": False, "overlay_enabled": False})


class _ClickRecorder:
    """Stand-in for ``VirtualMouse.click`` that records every call."""

    def __init__(self, return_value=True):
        self.calls = []
        self.return_value = return_value

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.return_value

    @property
    def last(self):
        return self.calls[-1]


def _install_click_recorder(bot, return_value=True):
    """Replace the bot's virtual_mouse.click with a recorder; return it."""
    rec = _ClickRecorder(return_value=return_value)
    bot.executor.virtual_mouse.click = rec
    return rec


def _fake_screen(width=1920, height=1080):
    return Image.new("RGB", (width, height), color="white")


def _make_png(tmp_path, name="img.png", size=(20, 10)):
    p = tmp_path / name
    Image.new("RGB", size, color="black").save(p)
    return str(p)


# --------------------------------------------------------------------------- #
# find_image (~10 tests)
# --------------------------------------------------------------------------- #
class TestFindImage:
    def test_returns_location_when_locate_succeeds(self, monkeypatch):
        bot = _make_bot()
        monkeypatch.setattr(
            bot.executor, "_locate_image_with_retry", lambda *a, **k: (10, 20, 30, 40)
        )
        assert bot.find_image("button.png") == (10, 20, 30, 40)

    def test_returns_none_when_not_found(self, monkeypatch):
        bot = _make_bot()
        monkeypatch.setattr(
            bot.executor, "_locate_image_with_retry", lambda *a, **k: None
        )
        assert bot.find_image("button.png") is None

    def test_resolves_registered_label_to_path(self, monkeypatch, tmp_path):
        bot = _make_bot()
        real = _make_png(tmp_path, "save.png")
        bot.register_image("save", real)

        seen = {}

        def fake_locate(path, region=None, confidence=0.9):
            seen["path"] = path
            return (1, 2, 3, 4)

        monkeypatch.setattr(bot.executor, "_locate_image_with_retry", fake_locate)
        assert bot.find_image("save") == (1, 2, 3, 4)
        assert seen["path"] == real  # the label was resolved to its real path

    def test_specific_true_with_region_searches_in_region(self, monkeypatch):
        bot = _make_bot()
        seen = {}

        def fake_locate(path, region=None, confidence=0.9):
            seen["region"] = region
            return (5, 5, 5, 5)

        monkeypatch.setattr(bot.executor, "_locate_image_with_retry", fake_locate)
        bot.find_image("b.png", region=(100, 100, 50, 50), specific=True)
        assert seen["region"] == (100, 100, 50, 50)

    def test_specific_true_without_region_searches_whole_screen(self, monkeypatch):
        bot = _make_bot()
        seen = {}

        def fake_locate(path, region=None, confidence=0.9):
            seen["region"] = region
            return (5, 5, 5, 5)

        monkeypatch.setattr(bot.executor, "_locate_image_with_retry", fake_locate)
        bot.find_image("b.png", region=None, specific=True)
        assert seen["region"] is None  # no region -> whole screen

    def test_confidence_passed_through(self, monkeypatch):
        bot = _make_bot()
        seen = {}

        def fake_locate(path, region=None, confidence=0.9):
            seen["confidence"] = confidence
            return (0, 0, 1, 1)

        monkeypatch.setattr(bot.executor, "_locate_image_with_retry", fake_locate)
        bot.find_image("b.png", confidence=0.55, specific=True)
        assert seen["confidence"] == 0.55

    def test_specific_false_tries_scales(self, monkeypatch, tmp_path):
        # specific=False with a real png exercises the resize/scale loop in
        # find_image; locateOnScreen is the lowest boundary here.
        bot = _make_bot()
        png = _make_png(tmp_path)
        calls = []

        def fake_locate(path, region=None, confidence=0.9):
            calls.append(path)
            return None  # never find -> all scales attempted

        monkeypatch.setattr(bot.executor, "_locate_image_with_retry", fake_locate)
        result = bot.find_image(png, specific=False)
        assert result is None
        # default scales when not specific: [1.0, 0.95, 1.05] -> 3 attempts
        assert len(calls) == 3

    def test_specific_false_returns_first_scale_hit(self, monkeypatch, tmp_path):
        bot = _make_bot()
        png = _make_png(tmp_path)
        monkeypatch.setattr(
            bot.executor, "_locate_image_with_retry", lambda *a, **k: (7, 8, 9, 10)
        )
        assert bot.find_image(png, specific=False) == (7, 8, 9, 10)

    def test_max_attempts_retries_with_backtrack(self, monkeypatch):
        bot = _make_bot()
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)
        attempts = {"n": 0}

        def fake_locate(*a, **k):
            attempts["n"] += 1
            return None

        monkeypatch.setattr(bot.executor, "_locate_image_with_retry", fake_locate)
        result = bot.find_image("b.png", specific=True, backtrack=True, max_attempts=3)
        assert result is None
        # one locate call per attempt (specific -> single scale)
        assert attempts["n"] == 3

    def test_wait_until_found_routes_to_executor(self, monkeypatch):
        bot = _make_bot()
        seen = {}

        def fake_wait(task, attempt):
            seen["task"] = task
            return (11, 22, 33, 44)

        monkeypatch.setattr(bot.executor, "_find_image_with_wait", fake_wait)
        result = bot.find_image("b.png", wait_until_found=True, wait_timeout=5)
        assert result == (11, 22, 33, 44)
        assert seen["task"]["wait_until_found"] is True
        assert seen["task"]["wait_timeout"] == 5

    def test_returns_none_gracefully_on_locate_exception(self, monkeypatch):
        bot = _make_bot()

        def boom(*a, **k):
            raise RuntimeError("locate exploded")

        monkeypatch.setattr(bot.executor, "_locate_image_with_retry", boom)
        # specific=True, no backtrack -> exception is swallowed and None returned
        assert bot.find_image("b.png", specific=True) is None


# --------------------------------------------------------------------------- #
# click_image (~10 tests)
# --------------------------------------------------------------------------- #
class TestClickImage:
    def test_found_clicks_and_returns_true(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: (100, 200, 40, 20))

        assert bot.click_image("b.png") is True
        assert len(rec.calls) == 1
        # center of (100,200,40,20) -> (100+20, 200+10) == (120, 210)
        _, kwargs = rec.last
        assert kwargs["x"] == 120
        assert kwargs["y"] == 210

    def test_not_found_returns_false_and_no_click(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: None)

        assert bot.click_image("b.png") is False
        assert rec.calls == []

    def test_label_resolution(self, monkeypatch, tmp_path):
        bot = _make_bot()
        _install_click_recorder(bot)
        real = _make_png(tmp_path, "ok.png")
        bot.register_image("ok", real)

        seen = {}

        def fake_find(image_path, *a, **k):
            seen["path"] = image_path
            return (0, 0, 2, 2)

        monkeypatch.setattr(bot, "find_image", fake_find)
        assert bot.click_image("ok") is True
        # click_image resolves the label before delegating to find_image
        assert seen["path"] == real

    def test_mouse_button_passthrough_right(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: (0, 0, 10, 10))

        bot.click_image("b.png", mouse_button="right")
        _, kwargs = rec.last
        assert kwargs["button"] == "right"

    def test_mouse_button_double_left_normalized(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: (0, 0, 10, 10))

        bot.click_image("b.png", mouse_button="double left")
        _, kwargs = rec.last
        assert kwargs["button"] == "double"  # normalized by _perform_click

    def test_delay_sleeps_after_click(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: (0, 0, 10, 10))
        slept = []
        monkeypatch.setattr("time.sleep", lambda s: slept.append(s))

        bot.click_image("b.png", delay=2.5)
        assert 2.5 in slept

    def test_sendtext_typed_after_click(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: (0, 0, 10, 10))
        sent = {}
        monkeypatch.setattr(
            bot.executor, "_process_sendtext", lambda text: sent.setdefault("t", text)
        )

        bot.click_image("b.png", sendtext="hello{enter}")
        assert sent["t"] == "hello{enter}"

    def test_no_sendtext_means_no_typing(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: (0, 0, 10, 10))
        calls = []
        monkeypatch.setattr(
            bot.executor, "_process_sendtext", lambda text: calls.append(text)
        )

        bot.click_image("b.png")
        assert calls == []

    def test_returns_false_when_click_backend_fails(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot, return_value=False)  # virtual click "fails"
        monkeypatch.setattr(bot, "find_image", lambda *a, **k: (0, 0, 10, 10))
        # _perform_click raises TaskExecutionError on a falsey backend result;
        # _click_image_internal catches it and returns False.
        assert bot.click_image("b.png") is False

    def test_backtrack_true_routes_through_backtrack_path(self, monkeypatch):
        bot = _make_bot()
        routed = {}

        def fake_backtrack(method_name, method_func, *args, **kwargs):
            routed["method"] = method_name
            routed["backtrack"] = kwargs.get("backtrack")
            return True

        monkeypatch.setattr(
            bot, "_execute_with_individual_backtrack", fake_backtrack
        )
        assert bot.click_image("b.png", backtrack=True) is True
        assert routed["method"] == "click_image"
        assert routed["backtrack"] is True

    def test_confidence_and_region_forwarded_to_find_image(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        seen = {}

        def fake_find(image_path, region=None, confidence=0.9, *a, **k):
            seen["region"] = region
            seen["confidence"] = confidence
            return (0, 0, 4, 4)

        monkeypatch.setattr(bot, "find_image", fake_find)
        bot.click_image("b.png", region=(1, 2, 3, 4), confidence=0.8)
        assert seen["region"] == (1, 2, 3, 4)
        assert seen["confidence"] == 0.8


# --------------------------------------------------------------------------- #
# find_text (~10 tests)
# --------------------------------------------------------------------------- #
class TestFindText:
    def _patch_screen(self, bot, monkeypatch, width=1920, height=1080):
        import pyautogui

        monkeypatch.setattr(
            pyautogui, "screenshot", lambda *a, **k: _fake_screen(width, height)
        )

    def test_found_returns_box_full_screen(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        monkeypatch.setattr(
            bot.ocr_engine,
            "find_text",
            lambda *a, **k: ([(10, 20, 30, 40)], [90.0], True),
        )
        # full screen -> region equals image size, so the box is returned as-is
        assert bot.find_text("Login") == (10, 20, 30, 40)

    def test_not_found_returns_none(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        monkeypatch.setattr(bot.ocr_engine, "find_text", lambda *a, **k: ([], [], False))
        assert bot.find_text("Nope") is None

    def test_region_converts_to_absolute_coordinates(self, monkeypatch):
        bot = _make_bot()
        # capture_region returns a small image; box is relative to the region.
        monkeypatch.setattr(
            bot.executor, "_capture_region", lambda region: _fake_screen(50, 50)
        )
        monkeypatch.setattr(
            bot.ocr_engine,
            "find_text",
            lambda *a, **k: ([(5, 6, 7, 8)], [90.0], True),
        )
        result = bot.find_text("Hi", region=(100, 200, 50, 50))
        # absolute x,y = region offset + relative box; w,h unchanged
        assert result == (105, 206, 7, 8)

    def test_occurrence_selects_correct_box(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        boxes = [(1, 1, 1, 1), (2, 2, 2, 2), (3, 3, 3, 3)]
        monkeypatch.setattr(
            bot.ocr_engine, "find_text", lambda *a, **k: (boxes, [90, 90, 90], True)
        )
        assert bot.find_text("x", occurrence=2) == (2, 2, 2, 2)

    def test_occurrence_beyond_available_returns_none(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        monkeypatch.setattr(
            bot.ocr_engine,
            "find_text",
            lambda *a, **k: ([(1, 1, 1, 1)], [90.0], True),
        )
        assert bot.find_text("x", occurrence=5) is None

    def test_filter_type_forwarded_to_ocr(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        seen = {}

        def fake_ocr(region_img, text, filter_type, threshold):
            seen["filter_type"] = filter_type
            return ([(0, 0, 1, 1)], [90.0], True)

        monkeypatch.setattr(bot.ocr_engine, "find_text", fake_ocr)
        bot.find_text("x", filter_type="numbers")
        assert seen["filter_type"] == "numbers"

    def test_confidence_threshold_forwarded_to_ocr(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        seen = {}

        def fake_ocr(region_img, text, filter_type, threshold):
            seen["threshold"] = threshold
            return ([(0, 0, 1, 1)], [90.0], True)

        monkeypatch.setattr(bot.ocr_engine, "find_text", fake_ocr)
        bot.find_text("x", confidence_threshold=88.0)
        assert seen["threshold"] == 88.0

    def test_target_text_forwarded_to_ocr(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        seen = {}

        def fake_ocr(region_img, text, filter_type, threshold):
            seen["text"] = text
            return ([(0, 0, 1, 1)], [90.0], True)

        monkeypatch.setattr(bot.ocr_engine, "find_text", fake_ocr)
        bot.find_text("Confirmar")
        assert seen["text"] == "Confirmar"

    def test_backtrack_retries_and_lowers_threshold(self, monkeypatch):
        bot = _make_bot()
        self._patch_screen(bot, monkeypatch)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)
        thresholds = []

        def fake_ocr(region_img, text, filter_type, threshold):
            thresholds.append(threshold)
            return ([], [], False)  # never found

        monkeypatch.setattr(bot.ocr_engine, "find_text", fake_ocr)
        result = bot.find_text("x", confidence_threshold=75.0, backtrack=True, max_attempts=3)
        assert result is None
        # threshold is reduced by 5 each retry: 75 -> 70 -> 65
        assert thresholds == [75.0, 70.0, 65.0]

    def test_wait_until_found_routes_to_executor(self, monkeypatch):
        bot = _make_bot()
        seen = {}

        def fake_wait(task, attempt):
            seen["task"] = task
            return (9, 9, 9, 9)

        monkeypatch.setattr(bot.executor, "_find_text_with_wait", fake_wait)
        result = bot.find_text("x", wait_until_found=True, wait_timeout=7)
        assert result == (9, 9, 9, 9)
        assert seen["task"]["wait_until_found"] is True
        assert seen["task"]["wait_timeout"] == 7


# --------------------------------------------------------------------------- #
# click_text (~10 tests)
# --------------------------------------------------------------------------- #
class TestClickText:
    def test_found_clicks_and_returns_true(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_text", lambda *a, **k: (100, 100, 20, 20))

        assert bot.click_text("Save") is True
        # center of (100,100,20,20) -> (110, 110)
        _, kwargs = rec.last
        assert (kwargs["x"], kwargs["y"]) == (110, 110)

    def test_not_found_returns_false(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_text", lambda *a, **k: None)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)

        assert bot.click_text("Save", max_attempts=1) is False
        assert rec.calls == []

    def test_click_passes_correct_coords(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_text", lambda *a, **k: (200, 300, 40, 60))

        bot.click_text("X")
        _, kwargs = rec.last
        assert (kwargs["x"], kwargs["y"]) == (220, 330)

    def test_occurrence_forwarded_to_find_text(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        seen = {}

        def fake_find(text, region=None, filter_type="both", threshold=None,
                      occurrence=1, *a, **k):
            seen["occurrence"] = occurrence
            return (0, 0, 2, 2)

        monkeypatch.setattr(bot, "find_text", fake_find)
        bot.click_text("X", occurrence=3)
        assert seen["occurrence"] == 3

    def test_filter_type_forwarded_to_find_text(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        seen = {}

        def fake_find(text, region=None, filter_type="both", *a, **k):
            seen["filter_type"] = filter_type
            return (0, 0, 2, 2)

        monkeypatch.setattr(bot, "find_text", fake_find)
        bot.click_text("X", filter_type="letters")
        assert seen["filter_type"] == "letters"

    def test_confidence_threshold_forwarded(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        seen = {}

        def fake_find(text, region=None, filter_type="both", threshold=None, *a, **k):
            seen["threshold"] = threshold
            return (0, 0, 2, 2)

        monkeypatch.setattr(bot, "find_text", fake_find)
        bot.click_text("X", confidence_threshold=91.0)
        assert seen["threshold"] == 91.0

    def test_default_confidence_threshold_from_config(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        seen = {}

        def fake_find(text, region=None, filter_type="both", threshold=None, *a, **k):
            seen["threshold"] = threshold
            return (0, 0, 2, 2)

        monkeypatch.setattr(bot, "find_text", fake_find)
        bot.click_text("X")  # no explicit threshold -> uses config value (75.0)
        assert seen["threshold"] == bot.config.confidence_threshold

    def test_mouse_button_passthrough(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_text", lambda *a, **k: (0, 0, 10, 10))

        bot.click_text("X", mouse_button="right")
        _, kwargs = rec.last
        assert kwargs["button"] == "right"

    def test_sendtext_typed_after_click(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        monkeypatch.setattr(bot, "find_text", lambda *a, **k: (0, 0, 10, 10))
        sent = {}
        monkeypatch.setattr(
            bot.executor, "_process_sendtext", lambda text: sent.setdefault("t", text)
        )

        bot.click_text("X", sendtext="usuario123")
        assert sent["t"] == "usuario123"

    def test_backtrack_true_routes_through_backtrack_path(self, monkeypatch):
        bot = _make_bot()
        routed = {}

        def fake_backtrack(method_name, method_func, *args, **kwargs):
            routed["method"] = method_name
            return True

        monkeypatch.setattr(bot, "_execute_with_individual_backtrack", fake_backtrack)
        assert bot.click_text("X", backtrack=True) is True
        assert routed["method"] == "click_text"

    def test_retries_until_found(self, monkeypatch):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        monkeypatch.setattr("time.sleep", lambda *a, **k: None)
        seq = [None, None, (0, 0, 5, 5)]

        def fake_find(*a, **k):
            return seq.pop(0)

        monkeypatch.setattr(bot, "find_text", fake_find)
        assert bot.click_text("X", max_attempts=3) is True
        assert len(rec.calls) == 1  # clicked once, on the third find

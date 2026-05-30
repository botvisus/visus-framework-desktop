"""Focused, fully-mocked tests for the VisusBot direct input methods:
``click_at``, ``click_coordinates`` and ``type_text``.

No real mouse or keyboard I/O happens:

* Coordinate clicks go through ``TaskExecutor._perform_action`` ->
  ``_perform_click`` -> ``VirtualMouse.click``; the bot's ``virtual_mouse.click``
  is replaced with a recorder and the overlay is disabled.
* ``type_text`` delegates to ``KeyboardCommander.type_text`` (plain text) or
  ``process_sendtext_command`` (special sequences); both are mocked.

``VisusBot()`` requires Tesseract, so each test is guarded with
``@pytest.mark.skipif(not tesseract_available())``.
"""

from __future__ import annotations

import pytest

from tests import tesseract_available

pytestmark = pytest.mark.skipif(
    not tesseract_available(), reason="Tesseract not installed"
)


def _make_bot():
    from visus.desktop import VisusBot

    return VisusBot(config={"show_overlay": False})


class _ClickRecorder:
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
    rec = _ClickRecorder(return_value=return_value)
    bot.executor.virtual_mouse.click = rec
    return rec


# --------------------------------------------------------------------------- #
# click_at (~10 tests)
# --------------------------------------------------------------------------- #
class TestClickAt:
    def test_returns_true_on_success(self):
        bot = _make_bot()
        _install_click_recorder(bot)
        assert bot.click_at((10, 20, 30, 40)) is True

    def test_forwards_center_coords_to_backend(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_at((10, 20, 30, 40))
        _, kwargs = rec.last
        # center of (10,20,30,40) -> (10+15, 20+20) == (25, 40)
        assert (kwargs["x"], kwargs["y"]) == (25, 40)

    def test_default_button_is_left(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_at((0, 0, 10, 10))
        _, kwargs = rec.last
        assert kwargs["button"] == "left"

    def test_button_right_forwarded(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_at((0, 0, 10, 10), mouse_button="right")
        _, kwargs = rec.last
        assert kwargs["button"] == "right"

    def test_button_double_forwarded(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_at((0, 0, 10, 10), mouse_button="double")
        _, kwargs = rec.last
        assert kwargs["button"] == "double"

    def test_button_move_to_forwarded(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_at((0, 0, 10, 10), mouse_button="move_to")
        _, kwargs = rec.last
        assert kwargs["button"] == "move_to"

    def test_location_info_passed_to_backend(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_at((10, 20, 30, 40))
        _, kwargs = rec.last
        # _perform_click forwards the full region so the virtual mouse can
        # recompute the exact center.
        assert kwargs["location_info"] == (10, 20, 30, 40)

    def test_delay_sleeps_after_click(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        slept = []
        monkeypatch.setattr("time.sleep", lambda s: slept.append(s))
        bot.click_at((0, 0, 10, 10), delay=1.5)
        assert 1.5 in slept

    def test_returns_false_when_backend_fails(self):
        bot = _make_bot()
        _install_click_recorder(bot, return_value=False)
        # falsey backend -> _perform_click raises -> click_at catches -> False
        assert bot.click_at((0, 0, 10, 10)) is False

    def test_returns_false_on_backend_exception(self, monkeypatch):
        bot = _make_bot()

        def boom(*a, **k):
            raise RuntimeError("backend exploded")

        bot.executor.virtual_mouse.click = boom
        assert bot.click_at((0, 0, 10, 10)) is False

    def test_single_click_per_call(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_at((0, 0, 10, 10))
        assert len(rec.calls) == 1


# --------------------------------------------------------------------------- #
# click_coordinates (~10 tests)
# --------------------------------------------------------------------------- #
class TestClickCoordinates:
    def test_returns_true_on_success(self):
        bot = _make_bot()
        _install_click_recorder(bot)
        assert bot.click_coordinates(100, 200) is True

    def test_forwards_exact_coords(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_coordinates(100, 200)
        _, kwargs = rec.last
        # internal location is (x, y, 1, 1) -> center == (x, y) since w//2 == 0
        assert (kwargs["x"], kwargs["y"]) == (100, 200)

    def test_default_button_is_left(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_coordinates(5, 5)
        _, kwargs = rec.last
        assert kwargs["button"] == "left"

    def test_button_right_forwarded(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_coordinates(5, 5, mouse_button="right")
        _, kwargs = rec.last
        assert kwargs["button"] == "right"

    def test_button_double_forwarded(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_coordinates(5, 5, mouse_button="double")
        _, kwargs = rec.last
        assert kwargs["button"] == "double"

    def test_button_move_to_forwarded(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_coordinates(5, 5, mouse_button="move_to")
        _, kwargs = rec.last
        assert kwargs["button"] == "move_to"

    def test_delay_sleeps_after_click(self, monkeypatch):
        bot = _make_bot()
        _install_click_recorder(bot)
        slept = []
        monkeypatch.setattr("time.sleep", lambda s: slept.append(s))
        bot.click_coordinates(5, 5, delay=0.75)
        assert 0.75 in slept

    def test_returns_false_when_backend_fails(self):
        bot = _make_bot()
        _install_click_recorder(bot, return_value=False)
        assert bot.click_coordinates(5, 5) is False

    def test_returns_false_on_backend_exception(self):
        bot = _make_bot()

        def boom(*a, **k):
            raise RuntimeError("backend exploded")

        bot.executor.virtual_mouse.click = boom
        assert bot.click_coordinates(5, 5) is False

    def test_backtrack_true_routes_through_backtrack_path(self, monkeypatch):
        bot = _make_bot()
        routed = {}

        def fake_backtrack(method_name, method_func, *args, **kwargs):
            routed["method"] = method_name
            return True

        monkeypatch.setattr(bot, "_execute_with_individual_backtrack", fake_backtrack)
        assert bot.click_coordinates(5, 5, backtrack=True) is True
        assert routed["method"] == "click_coordinates"

    def test_single_click_per_call(self):
        bot = _make_bot()
        rec = _install_click_recorder(bot)
        bot.click_coordinates(5, 5)
        assert len(rec.calls) == 1


# --------------------------------------------------------------------------- #
# type_text (~10 tests)
# --------------------------------------------------------------------------- #
class TestTypeText:
    def test_plain_text_routes_to_type_text_backend(self, monkeypatch):
        bot = _make_bot()
        seen = {}
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "type_text",
            lambda text, interval: seen.update(text=text, interval=interval),
        )
        assert bot.type_text("hello world") is True
        assert seen["text"] == "hello world"

    def test_interval_forwarded_to_backend(self, monkeypatch):
        bot = _make_bot()
        seen = {}
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "type_text",
            lambda text, interval: seen.update(interval=interval),
        )
        bot.type_text("abc", interval=0.2)
        assert seen["interval"] == 0.2

    def test_plain_text_does_not_call_special_handler(self, monkeypatch):
        bot = _make_bot()
        special_calls = []
        monkeypatch.setattr(
            bot.executor.keyboard_commander, "type_text", lambda *a, **k: None
        )
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "process_sendtext_command",
            lambda *a, **k: special_calls.append(a),
        )
        bot.type_text("just text")
        assert special_calls == []

    def test_special_sequence_ctrl_routes_to_special_handler(self, monkeypatch):
        bot = _make_bot()
        seen = {}
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "process_sendtext_command",
            lambda text: seen.setdefault("text", text),
        )
        assert bot.type_text("{ctrl}a") is True
        assert seen["text"] == "{ctrl}a"

    def test_special_sequence_enter_routes_to_special_handler(self, monkeypatch):
        bot = _make_bot()
        seen = {}
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "process_sendtext_command",
            lambda text: seen.setdefault("text", text),
        )
        bot.type_text("New Text{enter}")
        assert seen["text"] == "New Text{enter}"

    def test_special_sequence_tab_routes_to_special_handler(self, monkeypatch):
        bot = _make_bot()
        seen = {}
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "process_sendtext_command",
            lambda text: seen.setdefault("text", text),
        )
        bot.type_text("a{tab}b")
        assert seen["text"] == "a{tab}b"

    def test_special_sequence_del_routes_to_special_handler(self, monkeypatch):
        bot = _make_bot()
        seen = {}
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "process_sendtext_command",
            lambda text: seen.setdefault("text", text),
        )
        bot.type_text("{del}gone")
        assert seen["text"] == "{del}gone"

    def test_special_sequence_does_not_call_plain_handler(self, monkeypatch):
        bot = _make_bot()
        plain_calls = []
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "type_text",
            lambda *a, **k: plain_calls.append(a),
        )
        monkeypatch.setattr(
            bot.executor.keyboard_commander,
            "process_sendtext_command",
            lambda *a, **k: None,
        )
        bot.type_text("{ctrl}a")
        assert plain_calls == []

    def test_delay_sleeps_after_typing(self, monkeypatch):
        bot = _make_bot()
        monkeypatch.setattr(
            bot.executor.keyboard_commander, "type_text", lambda *a, **k: None
        )
        slept = []
        monkeypatch.setattr("time.sleep", lambda s: slept.append(s))
        bot.type_text("hi", delay=1.0)
        assert 1.0 in slept

    def test_returns_false_on_backend_exception(self, monkeypatch):
        bot = _make_bot()

        def boom(*a, **k):
            raise RuntimeError("typing exploded")

        monkeypatch.setattr(bot.executor.keyboard_commander, "type_text", boom)
        assert bot.type_text("oops") is False

    def test_backtrack_true_routes_through_backtrack_path(self, monkeypatch):
        bot = _make_bot()
        routed = {}

        def fake_backtrack(method_name, method_func, *args, **kwargs):
            routed["method"] = method_name
            return True

        monkeypatch.setattr(bot, "_execute_with_individual_backtrack", fake_backtrack)
        assert bot.type_text("hi", backtrack=True) is True
        assert routed["method"] == "type_text"

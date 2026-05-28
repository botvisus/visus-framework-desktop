"""Delegation tests for ``visus.desktop.core.capabilities``.

Each :class:`CapabilitiesMixin` method is a thin wrapper around a focused
capability module. These tests monkeypatch the underlying module functions and
assert that every mixin method forwards the right arguments and propagates the
underlying return value -- without touching the real screen, mouse, processes,
windows, clipboard, filesystem watchers, web browser or accessibility layer.

``capabilities`` imports its dependencies as module aliases
(``from . import screen as _screen`` and friends). Because those imports bind
the same module objects, patching an attribute on, for example,
``visus.desktop.core.screen`` is observed through ``_screen`` inside the mixin.
"""

from __future__ import annotations

import webbrowser

import pytest

import visus.desktop.core.locate as locate_mod
import visus.desktop.core.mouse_extra as mouse_mod
import visus.desktop.core.native as native_mod
import visus.desktop.core.process as process_mod
import visus.desktop.core.screen as screen_mod
import visus.desktop.core.window as window_mod
import visus.desktop.utils.clipboard as clipboard_mod
import visus.desktop.utils.files as files_mod
from visus.desktop.core.capabilities import CapabilitiesMixin
from visus.desktop.core.image_map import ImageMap
from visus.desktop.core.keyboard_extra import KeyboardMixin
from visus.desktop.core.native import Backend, NativeError


class _Bot(CapabilitiesMixin, KeyboardMixin):
    """Minimal host combining both mixins (no Tesseract/VisusBot needed)."""


def _make_recorder(monkeypatch, module, attr, return_value=None):
    """Patch ``module.attr`` with a call recorder and return the recorder.

    The recorder is a callable that stores ``(args, kwargs)`` of each call on
    its ``.calls`` list and returns ``return_value``.
    """

    class _Recorder:
        def __init__(self):
            self.calls = []

        def __call__(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return return_value

    rec = _Recorder()
    monkeypatch.setattr(module, attr, rec)
    return rec


# ---------------------------------------------------------------------------
# image_map property
# ---------------------------------------------------------------------------
def test_image_map_lazy_creation_and_caching():
    bot = _Bot()
    # Not created until first access.
    assert "_image_map" not in bot.__dict__
    first = bot.image_map
    assert isinstance(first, ImageMap)
    assert bot.__dict__["_image_map"] is first
    # Subsequent accesses return the very same instance (no re-creation).
    assert bot.image_map is first


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
def test_wait_for_file(monkeypatch):
    rec = _make_recorder(monkeypatch, files_mod, "wait_for_file", return_value=True)
    bot = _Bot()
    result = bot.wait_for_file("report.pdf", timeout=30, poll_interval=0.25)
    assert result is True
    assert rec.calls == [(("report.pdf", 30, 0.25), {})]


def test_wait_for_file_stable(monkeypatch):
    rec = _make_recorder(
        monkeypatch, files_mod, "wait_for_file_stable", return_value=False
    )
    bot = _Bot()
    result = bot.wait_for_file_stable(
        "dl.zip", timeout=12, stable_for=2.0, poll_interval=0.3
    )
    assert result is False
    assert rec.calls == [(("dl.zip", 12, 2.0, 0.3), {})]


# ---------------------------------------------------------------------------
# Clipboard
# ---------------------------------------------------------------------------
def test_copy(monkeypatch):
    rec = _make_recorder(monkeypatch, clipboard_mod, "copy")
    bot = _Bot()
    assert bot.copy("hello") is None
    assert rec.calls == [(("hello",), {})]


def test_paste(monkeypatch):
    rec = _make_recorder(monkeypatch, clipboard_mod, "paste", return_value="clip")
    bot = _Bot()
    assert bot.paste() == "clip"
    assert rec.calls == [((), {})]


def test_get_clipboard(monkeypatch):
    rec = _make_recorder(
        monkeypatch, clipboard_mod, "get_clipboard", return_value="clip2"
    )
    bot = _Bot()
    assert bot.get_clipboard() == "clip2"
    assert rec.calls == [((), {})]


# ---------------------------------------------------------------------------
# Screen
# ---------------------------------------------------------------------------
def test_take_screenshot(monkeypatch):
    sentinel = object()
    rec = _make_recorder(
        monkeypatch, screen_mod, "capture_screen", return_value=sentinel
    )
    bot = _Bot()
    region = (1, 2, 3, 4)
    assert bot.take_screenshot(region) is sentinel
    assert rec.calls == [((region,), {})]


def test_take_screenshot_default_region(monkeypatch):
    rec = _make_recorder(monkeypatch, screen_mod, "capture_screen", return_value=None)
    bot = _Bot()
    bot.take_screenshot()
    assert rec.calls == [((None,), {})]


def test_save_screenshot(monkeypatch):
    rec = _make_recorder(
        monkeypatch, screen_mod, "save_screenshot", return_value="out.png"
    )
    bot = _Bot()
    region = (0, 0, 10, 10)
    assert bot.save_screenshot("out.png", region) == "out.png"
    assert rec.calls == [(("out.png", region), {})]


def test_get_display_size(monkeypatch):
    rec = _make_recorder(
        monkeypatch, screen_mod, "get_display_size", return_value=(1920, 1080)
    )
    bot = _Bot()
    assert bot.get_display_size() == (1920, 1080)
    assert rec.calls == [((), {})]


# ---------------------------------------------------------------------------
# Process / application
# ---------------------------------------------------------------------------
def test_launch(monkeypatch):
    rec = _make_recorder(monkeypatch, process_mod, "launch")
    bot = _Bot()
    assert bot.launch("notepad.exe") is None
    assert rec.calls == [(("notepad.exe",), {})]


def test_find_process(monkeypatch):
    sentinel = object()
    rec = _make_recorder(
        monkeypatch, process_mod, "find_process", return_value=sentinel
    )
    bot = _Bot()
    assert bot.find_process(name="notepad", pid=42) is sentinel
    # Mixin forwards name/pid as keyword arguments.
    assert rec.calls == [((), {"name": "notepad", "pid": 42})]


def test_is_process_running(monkeypatch):
    rec = _make_recorder(
        monkeypatch, process_mod, "is_process_running", return_value=True
    )
    bot = _Bot()
    assert bot.is_process_running("chrome") is True
    assert rec.calls == [(("chrome",), {})]


def test_kill_process(monkeypatch):
    rec = _make_recorder(
        monkeypatch, process_mod, "kill_process", return_value=False
    )
    bot = _Bot()
    assert bot.kill_process(1234) is False
    assert rec.calls == [((1234,), {})]


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "method, func",
    [
        ("focus_window", "focus_window"),
        ("maximize_window", "maximize_window"),
        ("minimize_window", "minimize_window"),
        ("close_window", "close_window"),
    ],
)
def test_window_methods(monkeypatch, method, func):
    rec = _make_recorder(monkeypatch, window_mod, func, return_value=True)
    bot = _Bot()
    assert getattr(bot, method)("Untitled - Notepad") is True
    assert rec.calls == [(("Untitled - Notepad",), {})]


# ---------------------------------------------------------------------------
# Image map registration helpers
# ---------------------------------------------------------------------------
def test_register_image_and_get_image(tmp_path):
    img = tmp_path / "save.png"
    img.write_bytes(b"\x89PNG\r\n")
    bot = _Bot()
    bot.register_image("save", str(img))
    assert bot.get_image("save") == str(img)
    assert "save" in bot.image_map


def test_register_images_bulk(tmp_path):
    a = tmp_path / "a.png"
    a.write_bytes(b"a")
    b = tmp_path / "b.png"
    b.write_bytes(b"b")
    bot = _Bot()
    bot.register_images({"a": str(a), "b": str(b)})
    assert bot.get_image("a") == str(a)
    assert bot.get_image("b") == str(b)


# ---------------------------------------------------------------------------
# Mouse extras
# ---------------------------------------------------------------------------
def test_scroll(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "scroll")
    bot = _Bot()
    assert bot.scroll(5, 100, 200) is None
    assert rec.calls == [((5, 100, 200), {})]


def test_scroll_default_coords(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "scroll")
    bot = _Bot()
    bot.scroll(-3)
    assert rec.calls == [((-3, None, None), {})]


def test_drag(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "drag")
    bot = _Bot()
    assert bot.drag(1, 2, 3, 4, duration=1.5, button="right") is None
    assert rec.calls == [((1, 2, 3, 4, 1.5, "right"), {})]


def test_drag_defaults(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "drag")
    bot = _Bot()
    bot.drag(10, 20, 30, 40)
    assert rec.calls == [((10, 20, 30, 40, 0.5, "left"), {})]


def test_triple_click(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "triple_click")
    bot = _Bot()
    assert bot.triple_click(50, 60, interval=0.1) is None
    assert rec.calls == [((50, 60, 0.1), {})]


def test_triple_click_defaults(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "triple_click")
    bot = _Bot()
    bot.triple_click()
    assert rec.calls == [((None, None, 0.05), {})]


def test_move_random(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "move_random")
    bot = _Bot()
    assert bot.move_random(7, 8, max_offset=5, duration=0.4) is None
    assert rec.calls == [((7, 8, 5, 0.4), {})]


def test_move_random_defaults(monkeypatch):
    rec = _make_recorder(monkeypatch, mouse_mod, "move_random")
    bot = _Bot()
    bot.move_random(11, 12)
    assert rec.calls == [((11, 12, 3, 0.2), {})]


# ---------------------------------------------------------------------------
# Web
# ---------------------------------------------------------------------------
def test_browse(monkeypatch):
    rec = _make_recorder(monkeypatch, webbrowser, "open")
    bot = _Bot()
    assert bot.browse("https://example.com") is None
    assert rec.calls == [(("https://example.com",), {})]


# ---------------------------------------------------------------------------
# find_all / find_multiple (image label resolution)
# ---------------------------------------------------------------------------
def test_find_all_resolves_label(monkeypatch, tmp_path):
    img = tmp_path / "btn.png"
    img.write_bytes(b"x")
    boxes = [(1, 2, 3, 4)]
    rec = _make_recorder(monkeypatch, locate_mod, "find_all", return_value=boxes)
    bot = _Bot()
    bot.register_image("btn", str(img))
    region = (0, 0, 100, 100)

    result = bot.find_all("btn", region=region, confidence=0.8, grayscale=True)

    assert result is boxes
    # The registered label was resolved to its real path before delegation.
    assert rec.calls == [((str(img), region, 0.8, True), {})]


def test_find_all_passes_path_through_unchanged(monkeypatch):
    rec = _make_recorder(monkeypatch, locate_mod, "find_all", return_value=[])
    bot = _Bot()
    bot.find_all("c:/raw/path.png")
    # Unknown labels are passed through unchanged with default args.
    assert rec.calls == [(("c:/raw/path.png", None, 0.9, False), {})]


def test_find_multiple_dict_form(monkeypatch, tmp_path):
    ok = tmp_path / "ok.png"
    ok.write_bytes(b"o")
    cancel = tmp_path / "cancel.png"
    cancel.write_bytes(b"c")
    expected = {"ok": (1, 1, 1, 1), "cancel": None}
    rec = _make_recorder(
        monkeypatch, locate_mod, "find_multiple", return_value=expected
    )
    bot = _Bot()
    bot.register_image("ok", str(ok))
    region = (5, 5, 50, 50)

    result = bot.find_multiple(
        {"ok": "ok", "cancel": str(cancel)},
        region=region,
        confidence=0.7,
        grayscale=True,
    )

    assert result is expected
    # Values are resolved (label -> path); raw path passes through; keys kept.
    (args, kwargs) = rec.calls[0]
    assert args == ({"ok": str(ok), "cancel": str(cancel)}, region, 0.7, True)
    assert kwargs == {}


def test_find_multiple_list_form(monkeypatch, tmp_path):
    save = tmp_path / "save.png"
    save.write_bytes(b"s")
    rec = _make_recorder(monkeypatch, locate_mod, "find_multiple", return_value={})
    bot = _Bot()
    bot.register_image("save", str(save))

    bot.find_multiple(["save", "other.png"])

    # In list form each item becomes both the key and the resolved value.
    (args, kwargs) = rec.calls[0]
    assert args == (
        {"save": str(save), "other.png": "other.png"},
        None,
        0.9,
        False,
    )
    assert kwargs == {}


# ---------------------------------------------------------------------------
# Coordinate helpers (pure functions)
# ---------------------------------------------------------------------------
def test_get_element_coords():
    assert _Bot.get_element_coords((10, 20, 30, 40)) == (10, 20)
    assert _Bot().get_element_coords((1, 2, 3, 4)) == (1, 2)


def test_get_element_coords_centered():
    # center = (x + w//2, y + h//2)
    assert _Bot.get_element_coords_centered((10, 20, 30, 40)) == (25, 40)
    assert _Bot().get_element_coords_centered((0, 0, 100, 50)) == (50, 25)


# ---------------------------------------------------------------------------
# Native (accessibility) automation
# ---------------------------------------------------------------------------
def test_connect_to_app_stores_and_returns(monkeypatch):
    sentinel_app = object()
    rec = _make_recorder(
        monkeypatch, native_mod, "connect_to_app", return_value=sentinel_app
    )
    bot = _Bot()

    returned = bot.connect_to_app(
        Backend.WIN32, timeout=5.0, poll_interval=0.1, title="Calc"
    )

    assert returned is sentinel_app
    assert bot.app is sentinel_app
    assert rec.calls == [((Backend.WIN32, 5.0, 0.1), {"title": "Calc"})]


def test_connect_to_app_defaults(monkeypatch):
    sentinel_app = object()
    rec = _make_recorder(
        monkeypatch, native_mod, "connect_to_app", return_value=sentinel_app
    )
    bot = _Bot()

    bot.connect_to_app(title_re=".*Editor")

    assert rec.calls == [((Backend.UIA, 60.0, 0.5), {"title_re": ".*Editor"})]


def test_find_app_window_raises_when_not_connected():
    bot = _Bot()
    with pytest.raises(NativeError, match="Not connected"):
        bot.find_app_window(title="x")


def test_find_app_window_delegates_when_connected(monkeypatch):
    sentinel_window = object()
    rec = _make_recorder(
        monkeypatch, native_mod, "find_window", return_value=sentinel_window
    )
    bot = _Bot()
    fake_app = object()
    bot.app = fake_app

    result = bot.find_app_window(timeout=3.0, title="Main")

    assert result is sentinel_window
    assert rec.calls == [((fake_app, 3.0), {"title": "Main"})]


def test_find_app_element_raises_when_not_connected():
    bot = _Bot()
    with pytest.raises(NativeError, match="Not connected"):
        bot.find_app_element(title="x")


def test_find_app_element_delegates_when_connected(monkeypatch):
    sentinel_element = object()
    rec = _make_recorder(
        monkeypatch, native_mod, "find_element", return_value=sentinel_element
    )
    bot = _Bot()
    fake_app = object()
    fake_parent = object()
    bot.app = fake_app

    result = bot.find_app_element(
        from_parent_window=fake_parent, timeout=2.0, auto_id="okBtn"
    )

    assert result is sentinel_element
    assert rec.calls == [((fake_app, fake_parent, 2.0), {"auto_id": "okBtn"})]


def test_find_app_element_default_parent_when_connected(monkeypatch):
    rec = _make_recorder(monkeypatch, native_mod, "find_element", return_value=None)
    bot = _Bot()
    fake_app = object()
    bot.app = fake_app

    bot.find_app_element(control_type="Button")

    # from_parent_window defaults to None and timeout to 10.0.
    assert rec.calls == [((fake_app, None, 10.0), {"control_type": "Button"})]

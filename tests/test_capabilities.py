"""Tests for the CapabilitiesMixin wiring (BotCity-parity helpers on the bot).

The mixin is exercised on a tiny standalone subclass so these tests do not need
Tesseract (which ``VisusBot()`` would require). ``VisusBot`` inherits this mixin,
so the same methods are available on a real bot.
"""

from __future__ import annotations

import pytest

from visus.desktop.core.capabilities import CapabilitiesMixin


class _Bot(CapabilitiesMixin):
    """Minimal host for the mixin (no Tesseract/config needed)."""


def test_visusbot_inherits_mixin():
    from visus.desktop import VisusBot

    assert issubclass(VisusBot, CapabilitiesMixin)


def test_image_map_register_get_resolve(tmp_path):
    img = tmp_path / "save.png"
    img.write_bytes(b"\x89PNG\r\n")
    bot = _Bot()

    bot.register_image("save", str(img))
    assert bot.get_image("save") == str(img)
    # A registered label resolves to its path; an unknown string is returned as-is.
    assert bot.image_map.resolve("save") == str(img)
    assert bot.image_map.resolve("not_a_label.png") == "not_a_label.png"


def test_register_images_bulk(tmp_path):
    a = tmp_path / "a.png"
    a.write_bytes(b"x")
    b = tmp_path / "b.png"
    b.write_bytes(b"y")
    bot = _Bot()

    bot.register_images({"a": str(a), "b": str(b)})
    assert bot.get_image("a") == str(a)
    assert bot.get_image("b") == str(b)


def test_clipboard_delegation(monkeypatch):
    store = {"v": ""}
    import pyperclip

    monkeypatch.setattr(pyperclip, "copy", lambda t: store.__setitem__("v", t))
    monkeypatch.setattr(pyperclip, "paste", lambda: store["v"])

    bot = _Bot()
    bot.copy("hello")
    assert bot.paste() == "hello"
    assert bot.get_clipboard() == "hello"


def test_browse_delegation(monkeypatch):
    opened = []
    import webbrowser

    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url))
    _Bot().browse("https://example.com")
    assert opened == ["https://example.com"]


def test_wait_for_file_delegation(tmp_path):
    bot = _Bot()
    existing = tmp_path / "f.txt"
    existing.write_text("ok")
    assert bot.wait_for_file(str(existing), timeout=0.5, poll_interval=0.1) is True
    missing = tmp_path / "nope.txt"
    assert bot.wait_for_file(str(missing), timeout=0.3, poll_interval=0.1) is False


def test_get_image_unknown_label_raises():
    bot = _Bot()
    with pytest.raises(KeyError):
        bot.get_image("never_registered")


def test_visusbot_inherits_keyboard_mixin():
    from visus.desktop import VisusBot
    from visus.desktop.core.keyboard_extra import KeyboardMixin

    assert issubclass(VisusBot, KeyboardMixin)


def test_find_all_resolves_label(monkeypatch, tmp_path):
    from visus.desktop.core import locate

    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    recorded = {}

    def fake_find_all(path, region=None, confidence=0.9, grayscale=False):
        recorded["path"] = path
        return [(1, 2, 3, 4)]

    monkeypatch.setattr(locate, "find_all", fake_find_all)

    bot = _Bot()
    bot.register_image("a", str(img))
    result = bot.find_all("a")  # passes a label; must resolve to the path

    assert recorded["path"] == str(img)
    assert result == [(1, 2, 3, 4)]


def test_find_multiple_resolves_labels(monkeypatch, tmp_path):
    from visus.desktop.core import locate

    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    recorded = {}

    def fake_find_multiple(images, region=None, confidence=0.9, grayscale=False):
        recorded["images"] = images
        return {k: None for k in images}

    monkeypatch.setattr(locate, "find_multiple", fake_find_multiple)

    bot = _Bot()
    bot.register_image("a", str(img))
    bot.find_multiple(["a", "literal.png"])

    # Keys stay as given; the "a" label resolves to its path, unknown stays as-is.
    assert recorded["images"]["a"] == str(img)
    assert recorded["images"]["literal.png"] == "literal.png"


def test_find_app_window_requires_connect():
    from visus.desktop.core.native import NativeError

    bot = _Bot()
    with pytest.raises(NativeError):
        bot.find_app_window(title="x")


def test_element_coord_helpers():
    bot = _Bot()
    assert bot.get_element_coords((10, 20, 30, 40)) == (10, 20)
    assert bot.get_element_coords_centered((10, 20, 30, 40)) == (25, 40)

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

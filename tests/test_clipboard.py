"""
Tests for ``visus.desktop.utils.clipboard``.

The real OS clipboard is never touched: ``pyperclip.copy`` and
``pyperclip.paste`` are monkeypatched to a simple in-memory store.
"""

from __future__ import annotations

import pyperclip

from visus.desktop.utils.clipboard import copy, get_clipboard, paste


def _install_fake_clipboard(monkeypatch):
    """Patch pyperclip with an in-memory clipboard and return its store."""
    store = {"value": ""}

    def fake_copy(text):
        store["value"] = text

    def fake_paste():
        return store["value"]

    monkeypatch.setattr(pyperclip, "copy", fake_copy)
    monkeypatch.setattr(pyperclip, "paste", fake_paste)
    return store


class TestClipboardRoundTrip:
    """copy/paste/get_clipboard wrap pyperclip without hitting the OS."""

    def test_copy_then_paste_round_trips(self, monkeypatch):
        _install_fake_clipboard(monkeypatch)
        copy("round trip text")
        assert paste() == "round trip text"

    def test_get_clipboard_is_alias_of_paste(self, monkeypatch):
        _install_fake_clipboard(monkeypatch)
        copy("aliased value")
        assert get_clipboard() == "aliased value"

    def test_copy_returns_none(self, monkeypatch):
        _install_fake_clipboard(monkeypatch)
        assert copy("anything") is None

    def test_copy_overwrites_previous_value(self, monkeypatch):
        _install_fake_clipboard(monkeypatch)
        copy("first")
        copy("second")
        assert get_clipboard() == "second"

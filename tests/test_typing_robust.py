"""Robustness fixes for typing + clipboard.

* ``KeyboardCommander.type_with_tokens`` expands {enter}/{tab}/{esc}/
  {backspace}/{del}/{ctrl}a ANYWHERE in the string and enters literal text via
  the clipboard (no dropped characters), falling back to ``typewrite``.
* ``utils.clipboard.copy`` retries transient Windows clipboard locks.
"""

from __future__ import annotations

from unittest.mock import call, patch

import pyperclip

import visus.desktop.utils.clipboard as clip
from visus.desktop.core.keyboard_commands import KeyboardCommander


class TestTypeWithTokens:
    def test_expands_tokens_anywhere_and_pastes_literals(self):
        kc = KeyboardCommander()
        pasted: list[str] = []
        with patch(
            "visus.desktop.utils.clipboard.copy",
            side_effect=lambda t, *a, **k: pasted.append(t),
        ), patch("visus.desktop.core.keyboard_commands.pyautogui") as pg:
            kc.type_with_tokens("a{enter}{enter}b{ctrl}a")

        # Literal segments go through the clipboard (robust, no dropped chars).
        assert pasted == ["a", "b"]
        # {enter} pressed twice (mid-string), {ctrl}a expanded as a hotkey.
        assert pg.press.call_args_list.count(call("enter")) == 2
        pg.hotkey.assert_any_call("ctrl", "a")
        # Each literal paste is a Ctrl+V.
        assert pg.hotkey.call_args_list.count(call("ctrl", "v")) == 2

    def test_falls_back_to_typewrite_when_clipboard_unavailable(self):
        kc = KeyboardCommander()
        with patch(
            "visus.desktop.utils.clipboard.copy",
            side_effect=RuntimeError("clipboard locked"),
        ), patch("visus.desktop.core.keyboard_commands.pyautogui") as pg:
            kc.type_with_tokens("hello")
        pg.typewrite.assert_called_once()
        assert pg.typewrite.call_args[0][0] == "hello"

    def test_trailing_and_tab_tokens(self):
        kc = KeyboardCommander()
        with patch(
            "visus.desktop.utils.clipboard.copy", side_effect=lambda t, *a, **k: None
        ), patch("visus.desktop.core.keyboard_commands.pyautogui") as pg:
            kc.type_with_tokens("name{tab}value{enter}")
        pg.press.assert_any_call("tab")
        pg.press.assert_any_call("enter")


class TestClipboardRetry:
    def test_copy_retries_then_succeeds(self, monkeypatch):
        calls = {"n": 0}

        def flaky(_text):
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("OpenClipboard failed")

        monkeypatch.setattr(pyperclip, "copy", flaky)
        clip.copy("hi", retries=5, delay=0)
        assert calls["n"] == 3

    def test_copy_reraises_after_exhausting_retries(self, monkeypatch):
        def always_fail(_text):
            raise RuntimeError("OpenClipboard failed")

        monkeypatch.setattr(pyperclip, "copy", always_fail)
        try:
            clip.copy("hi", retries=2, delay=0)
        except RuntimeError as exc:
            assert "OpenClipboard" in str(exc)
        else:
            raise AssertionError("expected the clipboard error to propagate")

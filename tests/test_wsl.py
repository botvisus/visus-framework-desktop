"""Tests for WSL detection + guidance (Phase 4, X4).

``visus.desktop.platform.is_wsl()`` returns True when the current
process runs inside the Windows Subsystem for Linux. The doctor uses
it to emit a friendly hint about ``DISPLAY`` when Tk/X isn't reachable.
"""

from __future__ import annotations

from unittest.mock import patch

from visus.desktop.platform import is_wsl, wsl_display_hint


class TestIsWSL:
    def test_native_linux_returns_false(self):
        with patch(
            "visus.desktop.platform._read_proc_version",
            return_value="Linux version 6.8.0-generic (build@host)\n",
        ):
            assert is_wsl() is False

    def test_wsl1_returns_true(self):
        with patch(
            "visus.desktop.platform._read_proc_version",
            return_value="Linux version 4.4.0-Microsoft-Standard #1\n",
        ):
            assert is_wsl() is True

    def test_wsl2_returns_true(self):
        with patch(
            "visus.desktop.platform._read_proc_version",
            return_value="Linux version 5.15.146.1-microsoft-standard-WSL2\n",
        ):
            assert is_wsl() is True

    def test_windows_returns_false(self):
        with patch(
            "visus.desktop.platform._read_proc_version", return_value=None
        ):
            assert is_wsl() is False


class TestWSLDisplayHint:
    def test_hint_mentions_display_when_no_x_server(self, monkeypatch):
        monkeypatch.delenv("DISPLAY", raising=False)
        with patch("visus.desktop.platform.is_wsl", return_value=True):
            hint = wsl_display_hint()
        assert hint is not None
        assert "DISPLAY" in hint
        assert "WSL" in hint or "wsl" in hint.lower()

    def test_no_hint_when_display_set(self, monkeypatch):
        monkeypatch.setenv("DISPLAY", ":0")
        with patch("visus.desktop.platform.is_wsl", return_value=True):
            assert wsl_display_hint() is None

    def test_no_hint_outside_wsl(self, monkeypatch):
        monkeypatch.delenv("DISPLAY", raising=False)
        with patch("visus.desktop.platform.is_wsl", return_value=False):
            assert wsl_display_hint() is None

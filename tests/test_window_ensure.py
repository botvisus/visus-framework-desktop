"""Tests for the fast window-state primitive ``ensure_window`` / ``list_windows``.

The win32-touching helpers (`_enum_visible_windows`, `_window_flags`,
`_restore`, `_bring_to_front`, `_pids_for_process`) are patched so the
orchestration logic is testable on any OS. A single ``windows_only`` smoke
exercises the real enumeration.
"""

from __future__ import annotations

import sys

import pytest

from visus.desktop.core import window as w

_NORMAL = {
    "minimized": False,
    "maximized": False,
    "foreground": True,
    "rect": (427, 0, 1855, 735),
}
_MINIMIZED = {
    "minimized": True,
    "maximized": False,
    "foreground": False,
    "rect": (-32000, -32000, -31840, -31972),
}


class TestEnsureWindow:
    def test_requires_a_target(self):
        with pytest.raises(ValueError):
            w.ensure_window()

    def test_not_found_by_title(self, monkeypatch):
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: [])
        result = w.ensure_window(title="Ghost")
        assert result["found"] is False
        assert result["shown"] is False
        assert result["rect"] is None
        assert result["matches"] == 0

    def test_process_not_running(self, monkeypatch):
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: [])
        monkeypatch.setattr(w, "_process_running", lambda name: False)
        result = w.ensure_window(process="ghost.exe")
        assert result["found"] is False
        assert result["running"] is False

    def test_process_running_without_window(self, monkeypatch):
        # Process exists but has no top-level window (e.g. tray app).
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: [])
        monkeypatch.setattr(w, "_process_running", lambda name: True)
        result = w.ensure_window(process="trayapp.exe")
        assert result["found"] is False
        assert result["running"] is True

    def test_found_minimized_restores_and_foregrounds(self, monkeypatch):
        cands = [(657526, "Sem título - Bloco de Notas", 18756)]
        flags = iter([_MINIMIZED, _NORMAL])
        calls = {"restore": [], "front": []}
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: cands)
        monkeypatch.setattr(w, "_window_flags", lambda h: next(flags))
        monkeypatch.setattr(w, "_restore", lambda h: calls["restore"].append(h))
        monkeypatch.setattr(
            w, "_bring_to_front", lambda h: calls["front"].append(h) or True
        )
        result = w.ensure_window(title="Bloco de Notas", show=True)
        assert calls["restore"] == [657526]
        assert calls["front"] == [657526]
        assert result["found"] is True
        assert result["minimized"] is False
        assert result["foreground"] is True
        assert result["shown"] is True
        assert result["hwnd"] == 657526
        assert result["pid"] == 18756
        assert result["rect"] == {"x": 427, "y": 0, "width": 1428, "height": 735}

    def test_found_not_minimized_does_not_restore(self, monkeypatch):
        cands = [(1, "My App", 10)]
        flags = iter([_NORMAL, _NORMAL])
        restored = []
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: cands)
        monkeypatch.setattr(w, "_window_flags", lambda h: next(flags))
        monkeypatch.setattr(w, "_restore", lambda h: restored.append(h))
        monkeypatch.setattr(w, "_bring_to_front", lambda h: True)
        result = w.ensure_window(title="My App", show=True)
        assert restored == []
        assert result["found"] is True

    def test_show_false_skips_actions(self, monkeypatch):
        cands = [(1, "My App", 10)]
        flags = iter([_MINIMIZED, _MINIMIZED])
        restored = []
        fronted = []
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: cands)
        monkeypatch.setattr(w, "_window_flags", lambda h: next(flags))
        monkeypatch.setattr(w, "_restore", lambda h: restored.append(h))
        monkeypatch.setattr(w, "_bring_to_front", lambda h: fronted.append(h) or True)
        result = w.ensure_window(title="My App", show=False)
        assert restored == []
        assert fronted == []
        assert result["minimized"] is True
        # minimized + not shown => no usable rect
        assert result["rect"] is None

    def test_process_filter_matches_by_name(self, monkeypatch):
        cands = [
            (1, "notepad_demo.py - Visual Studio Code", 4616),
            (2, "Sem título - Bloco de Notas", 18756),
        ]
        names = {4616: "Code.exe", 18756: "notepad.exe"}
        flags = iter([_NORMAL, _NORMAL])
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: cands)
        monkeypatch.setattr(w, "_process_name", lambda pid: names[pid])
        monkeypatch.setattr(w, "_window_flags", lambda h: next(flags))
        monkeypatch.setattr(w, "_restore", lambda h: None)
        monkeypatch.setattr(w, "_bring_to_front", lambda h: True)
        result = w.ensure_window(process="notepad.exe")
        # VSCode (Code.exe) excluded by process name; only real notepad matches.
        assert result["found"] is True
        assert result["pid"] == 18756
        assert result["matches"] == 1

    def test_title_and_process_combine(self, monkeypatch):
        cands = [
            (2, "Sem título - Bloco de Notas", 18756),
            (3, "Outro - Bloco de Notas", 18756),
        ]
        flags = iter([_NORMAL, _NORMAL])
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: cands)
        monkeypatch.setattr(w, "_process_name", lambda pid: "notepad.exe")
        monkeypatch.setattr(w, "_window_flags", lambda h: next(flags))
        monkeypatch.setattr(w, "_restore", lambda h: None)
        monkeypatch.setattr(w, "_bring_to_front", lambda h: True)
        result = w.ensure_window(title="Sem título", process="notepad.exe")
        assert result["found"] is True
        assert result["hwnd"] == 2
        assert result["matches"] == 1


class TestListWindows:
    def test_list_windows_by_title(self, monkeypatch):
        cands = [
            (1, "Sem título - Bloco de Notas", 18756),
            (2, "Visual Studio Code", 4616),
        ]
        monkeypatch.setattr(w, "_enum_visible_windows", lambda: cands)
        monkeypatch.setattr(w, "_window_flags", lambda h: _NORMAL)
        rows = w.list_windows(title="Bloco de Notas")
        assert len(rows) == 1
        assert rows[0]["pid"] == 18756
        assert rows[0]["minimized"] is False


@pytest.mark.windows_only
@pytest.mark.skipif(sys.platform != "win32", reason="win32 enumeration")
class TestRealEnumeration:
    def test_enum_returns_list(self):
        wins = w._enum_visible_windows()
        assert isinstance(wins, list)
        # Every entry is (hwnd, title, pid).
        for entry in wins:
            assert len(entry) == 3

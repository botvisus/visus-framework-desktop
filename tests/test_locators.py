"""Tests for the precise locators (get_window, win32 menu, UIA, layered)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from visus.desktop.core import locators as _loc

# ---------------------------------------------------------------------------
# get_window / find_window_handle
# ---------------------------------------------------------------------------


class TestGetWindow:
    """``get_window`` / ``find_window_handle`` share the single enumeration in
    ``core.window``, so the tests patch that one source of truth."""

    def _patch_windows(self, monkeypatch, windows, flags=None):
        from visus.desktop.core import window as w

        monkeypatch.setattr(w, "_enum_visible_windows", lambda: windows)
        monkeypatch.setattr(
            w,
            "_window_flags",
            lambda h: flags
            or {
                "minimized": False,
                "maximized": False,
                "foreground": True,
                "rect": (297, 112, 1725, 847),
            },
        )

    def test_resolves_window_rect_and_pid(self, monkeypatch):
        self._patch_windows(
            monkeypatch, [(42, "Sem título - Bloco de Notas", 18756)]
        )
        out = _loc.get_window("Bloco de Notas")
        assert out["pid"] == 18756
        assert out["hwnd"] == 42
        assert out["x"] == 297 and out["y"] == 112
        assert out["width"] == 1725 - 297
        assert out["height"] == 847 - 112

    def test_returns_none_when_no_match(self, monkeypatch):
        self._patch_windows(monkeypatch, [(42, "Some Other App", 18756)])
        assert _loc.get_window("Bloco de Notas") is None

    def test_find_window_handle_returns_hwnd(self, monkeypatch):
        self._patch_windows(monkeypatch, [(99, "Bloco de Notas", 1)])
        assert _loc.find_window_handle("Bloco") == 99

    def test_minimized_window_has_null_rect(self, monkeypatch):
        self._patch_windows(
            monkeypatch,
            [(42, "Sem título - Bloco de Notas", 18756)],
            flags={
                "minimized": True,
                "maximized": False,
                "foreground": False,
                "rect": (-32000, -32000, -31840, -31972),
            },
        )
        out = _loc.get_window("Bloco de Notas")
        assert out["hwnd"] == 42 and out["x"] is None


# ---------------------------------------------------------------------------
# Win32 menu
# ---------------------------------------------------------------------------


class TestLocateWin32Menu:
    def _fake(self, labels, rects, has_menu=True):
        """Build a fake win32gui + ctypes for a menu with given labels/rects."""
        win32gui = MagicMock()
        win32gui.GetMenu = MagicMock(return_value=(123 if has_menu else 0))
        win32gui.GetMenuItemCount = MagicMock(return_value=len(labels))
        win32gui.GetMenuItemRect = MagicMock(
            side_effect=lambda hwnd, hmenu, i: (1, rects[i])
        )
        return win32gui

    def test_no_classic_menu_returns_none(self):
        win32gui = self._fake([], [], has_menu=False)
        with patch.dict(sys.modules, {"win32gui": win32gui}):
            assert _loc.locate_win32_menu(555, "Arquivo") is None

    def test_locates_menu_item_by_label(self):
        labels = ["&Arquivo", "&Editar", "&Formatar", "E&xibir", "&Ajuda"]
        rects = [
            (435, 31, 491, 50),
            (491, 31, 535, 50),
            (535, 31, 597, 50),
            (597, 31, 640, 50),
            (640, 31, 685, 50),
        ]
        win32gui = self._fake(labels, rects)
        with patch.dict(sys.modules, {"win32gui": win32gui}), patch.object(
            _loc, "_menu_label", side_effect=lambda hm, i: labels[i].replace("&", "")
        ):
            box = _loc.locate_win32_menu(555, "Formatar")
        # rect[2] = (535,31,597,50) -> (535,31, 62, 19)
        assert box == (535, 31, 62, 19)

    def test_label_match_is_case_insensitive(self):
        labels = ["&Arquivo"]
        rects = [(435, 31, 491, 50)]
        win32gui = self._fake(labels, rects)
        with patch.dict(sys.modules, {"win32gui": win32gui}), patch.object(
            _loc, "_menu_label", side_effect=lambda hm, i: "Arquivo"
        ):
            box = _loc.locate_win32_menu(555, "arquivo")
        assert box == (435, 31, 56, 19)

    def test_no_label_match_returns_none(self):
        labels = ["&Arquivo"]
        rects = [(435, 31, 491, 50)]
        win32gui = self._fake(labels, rects)
        with patch.dict(sys.modules, {"win32gui": win32gui}), patch.object(
            _loc, "_menu_label", side_effect=lambda hm, i: "Arquivo"
        ):
            assert _loc.locate_win32_menu(555, "Nonexistent") is None

    def test_none_hwnd_returns_none(self):
        assert _loc.locate_win32_menu(None, "Arquivo") is None


class TestNormalizeRect:
    def test_flag_rect_tuple(self):
        assert _loc._normalize_rect((1, (10, 20, 30, 40))) == (10, 20, 30, 40)

    def test_plain_rect_tuple(self):
        assert _loc._normalize_rect((10, 20, 30, 40)) == (10, 20, 30, 40)

    def test_garbage_returns_none(self):
        assert _loc._normalize_rect(("x",)) is None


# ---------------------------------------------------------------------------
# UIA directed
# ---------------------------------------------------------------------------


class TestLocateUiaDirected:
    def test_returns_box_from_child_window(self):
        rect = MagicMock(left=435, top=31, right=491, bottom=50)
        ctrl = MagicMock()
        ctrl.exists = MagicMock(return_value=True)
        ctrl.rectangle = MagicMock(return_value=rect)
        top = MagicMock()
        top.child_window = MagicMock(return_value=ctrl)
        app = MagicMock()
        app.connect = MagicMock()
        app.top_window = MagicMock(return_value=top)
        fake_pwa = MagicMock(Application=MagicMock(return_value=app))
        with patch.dict(sys.modules, {"pywinauto": fake_pwa}):
            box = _loc.locate_uia_directed("Arquivo", pid=18756, timeout=2.0)
        assert box == (435, 31, 56, 19)

    def test_returns_none_when_not_found(self):
        ctrl = MagicMock()
        ctrl.exists = MagicMock(return_value=False)
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        app = MagicMock(top_window=MagicMock(return_value=top))
        fake_pwa = MagicMock(Application=MagicMock(return_value=app))
        with patch.dict(sys.modules, {"pywinauto": fake_pwa}):
            box = _loc.locate_uia_directed("Ghost", pid=1, timeout=0.5)
        assert box is None

    def test_missing_pywinauto_returns_none(self):
        real_import = __import__

        def fake_import(name, *a, **k):
            if name == "pywinauto":
                raise ImportError(name)
            return real_import(name, *a, **k)

        with patch("builtins.__import__", side_effect=fake_import):
            assert _loc.locate_uia_directed("Arquivo", pid=1) is None


# ---------------------------------------------------------------------------
# Layered precedence: win32 -> ocr -> uia
# ---------------------------------------------------------------------------


class TestLocateLayered:
    def test_win32_wins_first(self):
        bot = MagicMock()
        bot.find_text = MagicMock(return_value=(9, 9, 9, 9))
        with patch.object(_loc, "locate_win32_menu", return_value=(1, 2, 3, 4)):
            box, method = _loc.locate_layered("Arquivo", bot=bot, hwnd=555, pid=1)
        assert box == (1, 2, 3, 4)
        assert method == "win32"
        bot.find_text.assert_not_called()

    def test_falls_back_to_ocr_when_no_win32(self):
        bot = MagicMock()
        bot.find_text = MagicMock(return_value=(5, 6, 7, 8))
        with patch.object(_loc, "locate_win32_menu", return_value=None), patch.object(
            _loc, "locate_uia_directed", return_value=(1, 1, 1, 1)
        ):
            box, method = _loc.locate_layered("Login", bot=bot, hwnd=555, pid=1)
        assert box == (5, 6, 7, 8)
        assert method == "text"

    def test_falls_back_to_uia_when_win32_and_ocr_miss(self):
        bot = MagicMock()
        bot.find_text = MagicMock(return_value=None)
        with patch.object(_loc, "locate_win32_menu", return_value=None), patch.object(
            _loc, "locate_uia_directed", return_value=(2, 2, 2, 2)
        ):
            box, method = _loc.locate_layered("Btn", bot=bot, hwnd=555, pid=42)
        assert box == (2, 2, 2, 2)
        assert method == "native"

    def test_all_miss_returns_none(self):
        bot = MagicMock()
        bot.find_text = MagicMock(return_value=None)
        with patch.object(_loc, "locate_win32_menu", return_value=None), patch.object(
            _loc, "locate_uia_directed", return_value=None
        ):
            box, method = _loc.locate_layered("X", bot=bot, hwnd=1, pid=1)
        assert box is None
        assert method is None

    def test_no_hwnd_skips_win32(self):
        bot = MagicMock()
        bot.find_text = MagicMock(return_value=(3, 3, 3, 3))
        with patch.object(_loc, "locate_win32_menu") as w32:
            box, method = _loc.locate_layered("Login", bot=bot, hwnd=None, pid=1)
        w32.assert_not_called()
        assert method == "text"

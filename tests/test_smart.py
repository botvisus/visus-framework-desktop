"""Tests for the unified cascading locate/click (smart_find / smart_click).

Default precedence: native -> image -> ocr -> coordinates. The ``order``
parameter lets the caller force a specific method or reorder the cascade.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from visus.desktop.core import smart as _smart


def _bot():
    bot = MagicMock()
    bot.find_text = MagicMock(return_value=None)
    bot.find_image = MagicMock(return_value=None)
    bot.click_text = MagicMock(return_value=False)
    bot.click_image = MagicMock(return_value=False)
    bot.click_at = MagicMock(return_value=True)
    return bot


# ---------------------------------------------------------------------------
# smart_find -- cascade precedence
# ---------------------------------------------------------------------------


class TestSmartFindPrecedence:
    def test_native_wins_first(self):
        bot = _bot()
        bot.find_image.return_value = (9, 9, 9, 9)
        with patch.object(
            _smart, "native_get_state",
            return_value={"exists": True, "rect": {"x": 1, "y": 2, "width": 3, "height": 4}},
        ):
            out = _smart.smart_find("Salvar", image="s.png", bot=bot)
        assert out["found"] is True
        assert out["method"] == "native"
        assert out["box"] == {"x": 1, "y": 2, "width": 3, "height": 4}
        bot.find_image.assert_not_called()

    def test_falls_to_image_when_native_misses(self):
        bot = _bot()
        bot.find_image.return_value = (10, 20, 30, 40)
        with patch.object(_smart, "native_get_state", return_value={"exists": False}):
            out = _smart.smart_find("Salvar", image="s.png", bot=bot)
        assert out["method"] == "image"
        assert out["box"] == {"x": 10, "y": 20, "width": 30, "height": 40}

    def test_falls_to_ocr_when_native_and_image_miss(self):
        bot = _bot()
        bot.find_text.return_value = (5, 6, 7, 8)
        with patch.object(_smart, "native_get_state", return_value=None):
            out = _smart.smart_find("Salvar", image="s.png", bot=bot)
        assert out["method"] == "ocr"
        assert out["box"] == {"x": 5, "y": 6, "width": 7, "height": 8}

    def test_falls_to_coordinates_last(self):
        bot = _bot()
        with patch.object(_smart, "native_get_state", return_value=None):
            out = _smart.smart_find(
                "Salvar", image="s.png", coordinates=[100, 200], bot=bot
            )
        assert out["method"] == "coordinates"
        assert out["box"] == {"x": 100, "y": 200, "width": 0, "height": 0}

    def test_all_miss_returns_not_found(self):
        bot = _bot()
        with patch.object(_smart, "native_get_state", return_value=None):
            out = _smart.smart_find("Ghost", bot=bot)
        assert out["found"] is False
        assert out["method"] is None


# ---------------------------------------------------------------------------
# smart_find -- explicit method choice via order=
# ---------------------------------------------------------------------------


class TestSmartFindOrder:
    def test_force_ocr_only(self):
        bot = _bot()
        bot.find_text.return_value = (1, 1, 1, 1)
        # native would match, but order forces ocr only -> native never tried.
        with patch.object(
            _smart, "native_get_state",
            return_value={"exists": True, "rect": {"x": 0, "y": 0, "width": 1, "height": 1}},
        ) as ns:
            out = _smart.smart_find("X", order=["ocr"], bot=bot)
        assert out["method"] == "ocr"
        ns.assert_not_called()

    def test_force_image_only_skips_others(self):
        bot = _bot()
        bot.find_image.return_value = (2, 2, 2, 2)
        out = _smart.smart_find("X", image="x.png", order=["image"], bot=bot)
        assert out["method"] == "image"
        bot.find_text.assert_not_called()

    def test_reordered_cascade(self):
        bot = _bot()
        bot.find_text.return_value = (3, 3, 3, 3)
        # order puts ocr before native; ocr matches first.
        with patch.object(_smart, "native_get_state") as ns:
            out = _smart.smart_find("X", order=["ocr", "native"], bot=bot)
        assert out["method"] == "ocr"
        ns.assert_not_called()

    def test_tried_list_records_attempts(self):
        bot = _bot()
        with patch.object(_smart, "native_get_state", return_value=None):
            out = _smart.smart_find("X", bot=bot)
        # No image/coordinates provided, so only native + ocr are attempted.
        assert out["tried"] == ["native", "ocr"]

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            _smart.smart_find("X", order=["telepathy"], bot=_bot())


# ---------------------------------------------------------------------------
# smart_click -- cascade
# ---------------------------------------------------------------------------


class TestSmartClick:
    def test_native_click_first(self):
        bot = _bot()
        with patch.object(_smart, "native_click", return_value=True) as nc:
            out = _smart.smart_click("Salvar", image="s.png", bot=bot)
        assert out["clicked"] is True
        assert out["method"] == "native"
        nc.assert_called_once()
        bot.click_image.assert_not_called()

    def test_falls_to_image_click(self):
        bot = _bot()
        bot.click_image.return_value = True
        with patch.object(_smart, "native_click", return_value=False):
            out = _smart.smart_click("Salvar", image="s.png", bot=bot)
        assert out["method"] == "image"

    def test_falls_to_ocr_click(self):
        bot = _bot()
        bot.click_text.return_value = True
        with patch.object(_smart, "native_click", return_value=False):
            out = _smart.smart_click("Salvar", image="s.png", bot=bot)
        assert out["method"] == "ocr"

    def test_falls_to_coordinates_click(self):
        bot = _bot()
        with patch.object(_smart, "native_click", return_value=False):
            out = _smart.smart_click(
                "Salvar", coordinates=[300, 400], bot=bot
            )
        assert out["method"] == "coordinates"
        bot.click_at.assert_called_once()

    def test_force_native_only(self):
        bot = _bot()
        with patch.object(_smart, "native_click", return_value=False) as nc:
            out = _smart.smart_click("X", order=["native"], window="App", bot=bot)
        assert out["clicked"] is False
        nc.assert_called_once()
        bot.click_text.assert_not_called()

    def test_native_selector_forwarded(self):
        bot = _bot()
        with patch.object(_smart, "native_click", return_value=True) as nc:
            _smart.smart_click(
                "Salvar", window="App", control_type="Button",
                auto_id="btnSave", bot=bot,
            )
        kwargs = nc.call_args.kwargs
        assert kwargs["title"] == "Salvar"
        assert kwargs["control_type"] == "Button"
        assert kwargs["auto_id"] == "btnSave"
        assert kwargs["window"] == "App"


# ---------------------------------------------------------------------------
# MCP wrappers
# ---------------------------------------------------------------------------


class TestMcpSmartTools:
    def test_tools_registered(self):
        from visus.desktop import mcp_server as ms

        tools = ms._tools_for_tests()
        assert "smart_find" in tools
        assert "smart_click" in tools

    def test_smart_click_tool_forwards(self):
        from visus.desktop import mcp_server as ms

        ms.reset_bot_for_tests()
        with patch(
            "visus.desktop.core.smart.smart_click",
            return_value={"clicked": True, "method": "native", "tried": ["native"]},
        ) as sc:
            out = ms._tools_for_tests()["smart_click"](
                query="Salvar", image="s.png", order=["native", "ocr"]
            )
        assert out["method"] == "native"
        assert sc.call_args.kwargs["order"] == ["native", "ocr"]

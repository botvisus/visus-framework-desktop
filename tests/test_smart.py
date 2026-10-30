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


_FOUND = {"exists": True, "rect": {"x": 1, "y": 2, "width": 3, "height": 4}}
_MISSING = {"exists": False}


def _native(found=_FOUND, clicked=True):
    """Simula o nativo: a consulta (qual nome acha o controle) e o clique."""
    state = patch.object(
        _smart, "native_get_state",
        side_effect=found if isinstance(found, list) else None,
        return_value=None if isinstance(found, list) else found,
    )
    click = patch.object(_smart, "native_click", return_value=clicked)
    return state, click


class TestSmartClick:
    def test_native_click_first(self):
        bot = _bot()
        state, click = _native()
        with state, click as nc:
            out = _smart.smart_click("Salvar", image="s.png", bot=bot)
        assert out["clicked"] is True
        assert out["method"] == "native"
        nc.assert_called_once()
        bot.click_image.assert_not_called()

    def test_falls_to_image_click(self):
        bot = _bot()
        bot.click_image.return_value = True
        state, click = _native(found=_MISSING)
        with state, click:
            out = _smart.smart_click("Salvar", image="s.png", bot=bot)
        assert out["method"] == "image"

    def test_falls_to_ocr_click(self):
        bot = _bot()
        bot.click_text.return_value = True
        state, click = _native(found=_MISSING)
        with state, click:
            out = _smart.smart_click("Salvar", image="s.png", bot=bot)
        assert out["method"] == "ocr"

    def test_falls_to_coordinates_click(self):
        bot = _bot()
        state, click = _native(found=_MISSING)
        with state, click:
            out = _smart.smart_click("Salvar", coordinates=[300, 400], bot=bot)
        assert out["method"] == "coordinates"
        bot.click_at.assert_called_once()

    def test_force_native_only(self):
        """Sem o controle, o nativo não clica (nem pelo OCR, fora da ordem pedida) e
        desiste rápido: só a consulta, ~1,5 s por nome, em vez de esperar o prazo."""
        bot = _bot()
        state, click = _native(found=_MISSING)
        with state as ns, click as nc:
            out = _smart.smart_click("X", order=["native"], window="App", bot=bot)
        assert out["clicked"] is False
        nc.assert_not_called()
        names = [{k: v for k, v in c.kwargs.items() if k.startswith("title")} for c in ns.call_args_list]
        assert names == [{"title": "X"}, {"title_re": "(?i)^X$"}]
        assert all(c.kwargs["timeout"] <= 1.5 for c in ns.call_args_list)
        bot.click_text.assert_not_called()

    def test_texto_da_tela_com_outra_caixa_acha_pelo_nativo(self):
        """O Office mostra "INSERT" e o nome UIA é "Insert": ainda o nativo (~1 s), não o
        OCR (~7 s) -- e o clique sai UMA vez, com o prazo inteiro (o invoke de um link
        segura até o app reagir; com 1 s o smart clicava de novo pelo OCR)."""
        bot = _bot()
        state, click = _native(found=[_MISSING, _FOUND])
        with state, click as nc:
            out = _smart.smart_click("INSERT", window="Excel", bot=bot, timeout=5.0)
        assert out == {"clicked": True, "method": "native", "tried": ["native"]}
        nc.assert_called_once()
        assert nc.call_args.kwargs["title_re"] == "(?i)^INSERT$"
        assert nc.call_args.kwargs["timeout"] == 5.0
        bot.click_text.assert_not_called()

    def test_native_selector_forwarded(self):
        bot = _bot()
        state, click = _native()
        with state, click as nc:
            _smart.smart_click(
                "Salvar", window="App", control_type="Button",
                auto_id="btnSave", bot=bot,
            )
        kwargs = nc.call_args.kwargs
        assert kwargs["title"] == "Salvar"
        assert kwargs["control_type"] == "Button"
        assert kwargs["auto_id"] == "btnSave"
        assert kwargs["window"] == "App"


class TestSmartWindowArea:
    """Com --window, a imagem e o OCR leem só a moldura da janela -- várias vezes mais
    rápido que a tela inteira -- e, para clicar, a janela vem para a frente antes."""

    def test_ocr_le_so_a_janela_que_veio_para_a_frente(self):
        bot = _bot()
        bot.click_text.return_value = True
        state, click = _native(found=_MISSING)
        with state, click, \
                patch.object(_smart.sys, "platform", "win32"), \
                patch.object(_smart, "front_window", return_value="Book1 - Excel") as fw, \
                patch.object(_smart, "window_region", return_value=(10, 20, 300, 400)):
            out = _smart.smart_click("Salvar", window="Excel", bot=bot)
        assert out["method"] == "ocr"
        fw.assert_called_once_with("Excel")
        assert bot.click_text.call_args.kwargs["region"] == (10, 20, 300, 400)

    def test_janela_que_nao_vem_para_a_frente_nao_recebe_clique(self):
        """Outra janela por cima: clicar pelo pixel acertaria ELA -- os métodos por
        pixel são pulados e o resultado diz que não clicou."""
        bot = _bot()
        bot.click_text.return_value = True
        state, click = _native(found=_MISSING)
        with state, click, \
                patch.object(_smart, "front_window", return_value=None):
            out = _smart.smart_click("Salvar", image="s.png", window="Excel", bot=bot)
        assert out["clicked"] is False
        bot.click_image.assert_not_called()
        bot.click_text.assert_not_called()

    def test_regiao_dada_vence_a_janela(self):
        bot = _bot()
        bot.click_text.return_value = True
        state, click = _native(found=_MISSING)
        with state, click, \
                patch.object(_smart, "front_window", return_value="Excel"), \
                patch.object(_smart, "window_region") as wr:
            _smart.smart_click("Salvar", window="Excel", search_region=[1, 2, 3, 4], bot=bot)
        wr.assert_not_called()
        assert bot.click_text.call_args.kwargs["region"] == (1, 2, 3, 4)

    def test_find_le_a_janela_sem_trazer_para_a_frente(self):
        bot = _bot()
        bot.find_text.return_value = (11, 22, 33, 44)
        with patch.object(_smart, "native_get_state", return_value=_MISSING), \
                patch.object(_smart.sys, "platform", "win32"), \
                patch.object(_smart, "front_window") as fw, \
                patch.object(_smart, "window_region", return_value=(10, 20, 300, 400)):
            out = _smart.smart_find("Salvar", window="Excel", bot=bot)
        assert out["method"] == "ocr"
        fw.assert_not_called()
        assert bot.find_text.call_args.kwargs["region"] == (10, 20, 300, 400)


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

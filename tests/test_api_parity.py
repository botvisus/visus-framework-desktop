"""A API (VisusBot) e o MCP fazem o mesmo que a CLI: abrir e esperar a janela, a trava
de janela do teclado e o snapshot numerado moram no núcleo."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop
from visus.desktop import AppWindow, UseAppError, VisusBot, open_app, use_app
from visus.desktop import mcp_server as server


@pytest.fixture
def bot() -> VisusBot:
    b = VisusBot.__new__(VisusBot)  # sem tela: só os métodos de teclado
    b.executor = MagicMock()
    return b


def test_api_com_outra_janela_na_frente_nao_digita(bot: VisusBot) -> None:
    with patch("visus.desktop.core.window.front_window", return_value=None), patch(
        "visus.desktop.core.window.foreground_title", return_value="Terminal"
    ), patch("visus.desktop.core.human_typing.type_like_a_person") as typed:
        assert bot.type_text("segredo", window="Excel") is False
        assert bot.keyboard_command("Ctrl+B", window="Excel") is False
    typed.assert_not_called()
    bot.executor.keyboard_commander.execute_command.assert_not_called()


def test_api_com_a_janela_na_frente_digita(bot: VisusBot) -> None:
    with patch(
        "visus.desktop.core.window.front_window", return_value="Book1 - Excel"
    ), patch("visus.desktop.core.human_typing.type_like_a_person") as typed:
        assert bot.type_text("ID\tProduto", window="Excel") is True
    typed.assert_called_once_with("ID\tProduto", 0.02)


def test_api_open_app_espera_a_janela() -> None:
    with patch("visus.desktop.core.process.launch") as launch, patch(
        "visus.desktop.core.window.wait_front_window", return_value="Book1 - Excel"
    ) as wait:
        assert open_app("excel", wait_window="Excel", timeout=9) == {
            "target": "excel",
            "window": "Book1 - Excel",
        }
    launch.assert_called_once_with("excel")
    wait.assert_called_once_with("Excel", timeout=9)


def test_mcp_open_app_que_nao_abre_explica() -> None:
    with patch("visus.desktop.core.process.launch", side_effect=OSError("no such app")):
        out = server.open_app("nada-disso")
    assert out["opened"] is False
    assert "no such app" in out["error"]


def test_mcp_native_snapshot_numera_e_corta() -> None:
    nodes = [
        {"control_type": "Button", "title": "Bold", "auto_id": ""},
        {"control_type": "Pane", "title": "Ribbon", "auto_id": ""},
        {"control_type": "ListItem", "title": "Blue, Accent 1", "auto_id": ""},
    ]
    with patch(
        "visus.desktop.core.native_rpa.native_snapshot_nodes",
        return_value=("Book1 - Excel", nodes),
    ):
        out = server.native_snapshot(window="Excel", max_items=1)
    assert out["window"] == "Book1 - Excel"
    assert [i["title"] for i in out["items"]] == ["Bold"]
    assert out["more"] == 1


def test_mcp_teclado_repassa_a_janela() -> None:
    fake = MagicMock()
    fake.type_text.return_value = True
    fake.keyboard_command.return_value = True
    with patch.object(server, "get_bot", return_value=fake):
        assert server.type_text("oi", window="Excel") is True
        assert server.keyboard_command("Alt, H, O, I", window="Excel") is True
    assert fake.type_text.call_args.kwargs["window"] == "Excel"
    assert fake.keyboard_command.call_args.kwargs["window"] == "Excel"


def test_use_app_exportado_e_versao_0_4_4() -> None:
    from visus.desktop.core import app

    assert use_app is app.use_app
    assert visus.desktop.__version__ == "0.4.4"


def test_mcp_use_app_devolve_a_janela() -> None:
    win = AppWindow("Pasta1 - Excel", hwnd=5, pid=50, opened=True)
    with patch("visus.desktop.core.app.use_app", return_value=win) as use:
        out = server.use_app("EXCEL.EXE", window="Excel")
    assert out == {"title": "Pasta1 - Excel", "hwnd": 5, "pid": 50, "opened": True}
    use.assert_called_once_with("EXCEL.EXE", window="Excel", file=None, timeout=30.0)


def test_mcp_use_app_que_falha_explica() -> None:
    reason = "'Calculadora' is not open - open it before running"
    with patch("visus.desktop.core.app.use_app", side_effect=UseAppError(reason)):
        out = server.use_app(window="Calculadora")
    assert out == {"error": reason}

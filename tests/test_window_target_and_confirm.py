"""O que os agentes do Visus Studio erraram no Excel, medido:

- ``--window Excel`` com a "Ajuda do Excel" aberta digitou a tabela inteira na ajuda;
- ``window close Calculadora`` sem ``--yes`` só dizia "Aborted." (o agente tentou
  ``--window``, ``--force``…);
- o Alt+F4 recusado mandava usar ``window close`` sem dizer o ``--yes``."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core import window as win

runner = CliRunner()

EXCEL = ["Pasta1 - Excel", "Ajuda do Excel"]


@pytest.mark.parametrize(
    ("wanted", "titles", "ambiguous"),
    [
        ("Excel", EXCEL, True),  # a ajuda também tem "Excel"
        ("Pasta1 - Excel", EXCEL, False),  # o título exato
        ("pasta1 - excel", EXCEL, False),  # sem diferenciar caixa
        ("Excel", ["Pasta1 - Excel"], False),  # uma janela só
        ("Excel", [], False),  # nenhuma: quem decide é o "não está na frente"
    ],
)
def test_janela_ambigua(wanted: str, titles: list[str], ambiguous: bool) -> None:
    assert bool(win.ambiguous_window(wanted, titles)) is ambiguous


def test_mensagem_lista_as_janelas_e_diz_que_nada_saiu() -> None:
    text = win.ambiguous_message("Excel", EXCEL)
    assert "'Pasta1 - Excel'" in text and "'Ajuda do Excel'" in text
    assert "exact title" in text and "safe to retry" in text


def test_type_com_janela_ambigua_nao_digita() -> None:
    with patch("sys.platform", "win32"), patch.object(
        win, "matching_titles", return_value=EXCEL
    ), patch.object(win, "front_window") as front, patch(
        "visus.desktop.cli._common.build_bot"
    ) as bot:
        result = runner.invoke(cli, ["type", "--window", "Excel", "--", "oi"])
    assert result.exit_code == 1
    assert "matches 2 windows" in result.output
    front.assert_not_called()
    bot.assert_not_called()


def test_key_com_janela_ambigua_nao_aperta() -> None:
    with patch("sys.platform", "win32"), patch.object(
        win, "matching_titles", return_value=EXCEL
    ), patch("visus.desktop.cli._common.build_bot") as bot:
        result = runner.invoke(cli, ["key", "Ctrl+N", "--window", "Excel"])
    assert result.exit_code == 1 and "matches 2 windows" in result.output
    bot.assert_not_called()


def test_alt_f4_recusado_mostra_o_close_com_yes() -> None:
    result = runner.invoke(cli, ["key", "Alt+F4"])
    assert result.exit_code == 1
    assert 'window close "<its title>" --yes' in result.output


@pytest.mark.parametrize(
    ("args", "target"),
    [
        (["window", "close", "Calculadora"], "visus.desktop.core.window.close_window"),
        (["process", "kill", "123"], "visus.desktop.core.process.kill_process"),
    ],
)
def test_sem_terminal_pede_o_yes(args: list[str], target: str) -> None:
    """Sem ninguém no terminal (o agente), a resposta diz o que fazer, e nada acontece."""
    with patch(target) as action:
        result = runner.invoke(cli, args)
    assert result.exit_code == 1
    assert "pass --yes" in result.output and "Aborted" not in result.output
    action.assert_not_called()


def test_mcp_recusa_janela_ambigua() -> None:
    from visus.desktop import mcp_server

    with patch("sys.platform", "win32"), patch.object(
        win, "matching_titles", return_value=EXCEL
    ), patch.object(mcp_server, "get_bot") as bot:
        with pytest.raises(ValueError, match="matches 2 windows"):
            mcp_server.keyboard_command("Ctrl+N", window="Excel")
        with pytest.raises(ValueError, match="exact title"):
            mcp_server.type_text("oi", window="Excel")
    bot.assert_not_called()

"""Números negativos são valores, não opções: rolar para baixo é `mouse scroll -3`, e
um monitor à esquerda do principal tem X negativo."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from visus.desktop.cli import cli

runner = CliRunner()


def test_scroll_para_baixo_com_numero_negativo() -> None:
    with patch("visus.desktop.scroll") as scroll:
        r = runner.invoke(cli, ["mouse", "scroll", "-3", "--x", "10", "--y", "20"])
    assert r.exit_code == 0, r.output
    scroll.assert_called_once_with(-3, x=10, y=20)


def test_click_em_x_negativo() -> None:
    bot = MagicMock()
    bot.click_at.return_value = True
    bot.executor.virtual_mouse.last_click = None
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["mouse", "click", "-1500", "300"])
    assert r.exit_code == 0, r.output
    assert bot.click_at.call_args.args[0][:2] == (-1500, 300)


def test_opcao_errada_ainda_e_erro() -> None:
    r = runner.invoke(cli, ["mouse", "click", "10", "20", "--botao", "left"])
    assert r.exit_code != 0

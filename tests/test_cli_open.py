"""``visus open``: um app ou um arquivo como o "Executar" do Windows (``excel``,
``report.xlsx``) e, com ``--wait-window``, a janela dele na frente quando aparecer."""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from visus.desktop.cli import cli

runner = CliRunner()


def test_abre_pelo_sistema_e_nao_pelo_popen() -> None:
    with patch("visus.desktop.core.process.launch") as launch, patch(
        "subprocess.Popen"
    ) as popen:
        result = runner.invoke(cli, ["open", "excel", "--json"])
    assert result.exit_code == 0, result.output
    launch.assert_called_once_with("excel")
    popen.assert_not_called()
    assert json.loads(result.output) == {"target": "excel", "window": None}


def test_espera_a_janela_pronta_e_na_frente() -> None:
    """A tela de carregamento ("Opening - Excel") não conta: a janela tem de estar em
    foco e com o título parado por um instante."""
    import itertools

    ensure = itertools.chain([{"found": False}], itertools.repeat({"found": True}))
    fronts = itertools.chain(
        ["Opening - Excel", "Opening - Excel"], itertools.repeat("Pasta1 - Excel")
    )
    with patch("visus.desktop.core.process.launch"), patch("time.sleep"):
        with patch(
            "visus.desktop.core.window.ensure_window",
            side_effect=lambda **kw: next(ensure),
        ):
            with patch(
                "visus.desktop.core.window.foreground_title",
                side_effect=lambda: next(fronts),
            ):
                result = runner.invoke(
                    cli, ["open", "excel", "--wait-window", "Excel", "--json"]
                )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["window"] == "Pasta1 - Excel"


def test_janela_que_nao_aparece_e_erro_claro() -> None:
    ensure_path = "visus.desktop.core.window.ensure_window"
    with patch("visus.desktop.core.process.launch"), patch("time.sleep"):
        with patch(ensure_path, return_value={"found": False}), patch(
            "visus.desktop.core.window.foreground_title", return_value="Terminal"
        ):
            result = runner.invoke(
                cli, ["open", "excel", "--wait-window", "Excel", "--timeout", "0"]
            )
    assert result.exit_code != 0
    assert "no window titled 'Excel'" in result.output


def test_alvo_que_nao_existe_e_erro_claro() -> None:
    with patch(
        "visus.desktop.core.process.launch", side_effect=FileNotFoundError("not found")
    ):
        result = runner.invoke(cli, ["open", "naoexiste.xyz"])
    assert result.exit_code != 0
    assert "could not open 'naoexiste.xyz'" in result.output


def test_no_linux_arquivo_abre_no_programa_padrao(tmp_path) -> None:
    from visus.desktop.core import process

    doc = tmp_path / "relatorio.xlsx"
    doc.write_bytes(b"x")
    with patch("platform.system", return_value="Linux"), patch(
        "subprocess.Popen"
    ) as popen:
        process.launch(str(doc))
        process.launch("https://exemplo.com")
        process.launch("libreoffice --calc")
    assert popen.call_args_list[0].args[0] == ["xdg-open", str(doc)]
    assert popen.call_args_list[1].args[0] == ["xdg-open", "https://exemplo.com"]
    assert popen.call_args_list[2].args[0] == ["libreoffice", "--calc"], (
        "um comando continua comando"
    )


def test_type_com_janela_errada_na_frente_nao_digita_nada() -> None:
    """Como uma pessoa: olhar antes de digitar. Sem a janela pedida em foco, nenhuma
    tecla sai (antes, o texto caía em qualquer janela que estivesse na frente)."""
    with patch("visus.desktop.core.window.front_window", return_value=None), patch(
        "visus.desktop.core.window.foreground_title", return_value="Terminal"
    ), patch("visus.desktop.core.human_typing.type_like_a_person") as typed:
        result = runner.invoke(cli, ["type", "--window", "Excel", "--", "oi"])
        pressed = runner.invoke(cli, ["key", "Enter", "--window", "Excel"])
    assert result.exit_code != 0 and "nothing was typed" in result.output
    assert "now: 'Terminal'" in result.output
    assert pressed.exit_code != 0
    typed.assert_not_called()


def test_type_com_a_janela_certa_na_frente_digita() -> None:
    with patch(
        "visus.desktop.core.window.front_window", return_value="Pasta1 - Excel"
    ), patch("visus.desktop.core.human_typing.type_like_a_person") as typed:
        result = runner.invoke(cli, ["type", "--window", "Excel", "--", "Informática"])
    assert result.exit_code == 0, result.output
    assert typed.call_args.args[0] == "Informática"

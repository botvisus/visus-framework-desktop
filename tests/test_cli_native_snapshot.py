"""`native snapshot`: a janela como um agente de IA a lê — só o que dá para acionar,
numerado, uma linha por controle — e agir pelo NÚMERO (`native click 3`), como no
visus-web. Ler a árvore UIA em texto custa uma fração de um print e é exato.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core.native_rpa import select_actionable

runner = CliRunner()

NODES = [
    {"depth": 1, "control_type": "Window", "title": "Calculadora", "auto_id": "", "rect": [0, 0, 400, 600]},
    {"depth": 2, "control_type": "Text", "title": "Exibição é 0", "auto_id": "CalculatorResults", "rect": [10, 80, 380, 60]},
    {"depth": 3, "control_type": "Button", "title": "Sete", "auto_id": "num7Button", "rect": [10, 300, 90, 60]},
    {"depth": 3, "control_type": "Button", "title": "Mais", "auto_id": "plusButton", "rect": [300, 400, 90, 60]},
    {"depth": 3, "control_type": "Button", "title": "Fechar", "auto_id": "", "rect": [350, 0, 40, 30]},
    {"depth": 3, "control_type": "Button", "title": "Fechar", "auto_id": "", "rect": [350, 500, 40, 30]},
    {"depth": 2, "control_type": "Edit", "title": "Nome", "auto_id": "nome", "rect": [10, 10, 200, 30]},
]


def test_select_actionable_numera_so_o_que_da_para_acionar() -> None:
    items = select_actionable(NODES)
    assert [(i["index"], i["control_type"], i["title"]) for i in items] == [
        (0, "Button", "Sete"),
        (1, "Button", "Mais"),
        (2, "Button", "Fechar"),
        (3, "Button", "Fechar"),
        (4, "Edit", "Nome"),
    ]


def test_select_actionable_desambigua_repetidos_pelo_found_index() -> None:
    items = select_actionable(NODES)
    assert [i["found_index"] for i in items if i["title"] == "Fechar"] == [0, 1]
    assert items[0]["found_index"] == 0


def _snapshot(*extra: str):
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("Calculadora", NODES)):
        return runner.invoke(cli, ["native", "snapshot", "--window", "Calculadora", *extra])


def test_snapshot_imprime_compacto() -> None:
    r = _snapshot()
    assert r.exit_code == 0, r.output
    lines = r.output.splitlines()
    assert lines[0] == "Window: Calculadora"
    assert lines[1] == "  0  Button       Sete #num7Button"
    assert lines[3] == "  2  Button       Fechar"
    assert lines[5] == "  4  Edit         Nome #nome"


def test_snapshot_json_e_cache() -> None:
    r = _snapshot("--json")
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["window"] == "Calculadora"
    assert data["items"][1]["auto_id"] == "plusButton"


def test_click_pelo_numero_usa_o_seletor_guardado() -> None:
    _snapshot()
    with patch("visus.desktop.core.native_rpa.native_click", return_value=True) as m:
        r = runner.invoke(cli, ["native", "click", "3"])
    assert r.exit_code == 0, r.output
    kw = m.call_args.kwargs
    assert (kw["window"], kw["title"], kw["control_type"], kw["found_index"]) == ("Calculadora", "Fechar", "Button", 1)


def test_set_text_e_get_text_pelo_numero() -> None:
    _snapshot()
    with patch("visus.desktop.core.native_rpa.native_set_text", return_value=True) as m:
        r = runner.invoke(cli, ["native", "set-text", "4", "Ada Lovelace"])
    assert r.exit_code == 0, r.output
    assert m.call_args.kwargs["auto_id"] == "nome"
    assert m.call_args.kwargs["text"] == "Ada Lovelace"

    with patch("visus.desktop.core.native_rpa.native_get_text", return_value="Ada Lovelace") as g:
        r = runner.invoke(cli, ["native", "get-text", "4"])
    assert r.exit_code == 0, r.output
    assert "Ada Lovelace" in r.output
    assert g.call_args.kwargs["auto_id"] == "nome"


def test_set_text_sem_numero_continua_como_antes() -> None:
    with patch("visus.desktop.core.native_rpa.native_set_text", return_value=True) as m:
        r = runner.invoke(cli, ["native", "set-text", "olá", "--title", "Nome"])
    assert r.exit_code == 0, r.output
    assert m.call_args.kwargs["title"] == "Nome"


def test_numero_desconhecido_mensagem_clara() -> None:
    _snapshot()
    r = runner.invoke(cli, ["native", "click", "99"])
    assert r.exit_code == 1
    assert "snapshot" in r.output.lower()


def test_numero_sem_snapshot_mensagem_clara() -> None:
    r = runner.invoke(cli, ["native", "click", "0"])
    assert r.exit_code == 1
    assert "native snapshot" in r.output

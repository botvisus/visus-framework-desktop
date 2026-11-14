"""`native snapshot`: a janela como um agente de IA a lê — só o que dá para acionar,
numerado, uma linha por controle — e agir pelo NÚMERO (`native click 3`), como no
visus-web. Ler a árvore UIA em texto custa uma fração de um print e é exato.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core.native_rpa import select_actionable
from visus.desktop.core.outcome import ActionOutcome

runner = CliRunner()


@pytest.fixture(autouse=True)
def _snapshots_in_tmp(tmp_path, monkeypatch):
    """Os snapshots ficam numa pasta temporária, nunca no ~/.visus de verdade."""
    monkeypatch.setenv("VISUS_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.delenv("VISUS_DESKTOP_SESSION", raising=False)

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
    assert lines[0].startswith("Window: Calculadora  (snapshot s")
    assert lines[1] == "  0  Button       Sete #num7Button"
    assert lines[3] == "  2  Button       Fechar"
    assert lines[5] == "  4  Edit         Nome #nome"


def test_snapshot_json_e_cache() -> None:
    r = _snapshot("--json")
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["window"] == "Calculadora"
    assert data["items"][1]["auto_id"] == "plusButton"


def _live(nodes=NODES):
    """A janela relida na hora de agir (a conferência do controle)."""
    return patch(
        "visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("Calculadora", nodes)
    )


def test_click_pelo_numero_usa_o_seletor_guardado() -> None:
    _snapshot()
    with _live(), patch(
        "visus.desktop.core.native_rpa.native_click_ex", return_value=ActionOutcome.sent("Invoke")
    ) as m:
        r = runner.invoke(cli, ["native", "click", "3"])
    assert r.exit_code == 0, r.output
    kw = m.call_args.kwargs
    assert (kw["window"], kw["title"], kw["control_type"], kw["found_index"]) == ("Calculadora", "Fechar", "Button", 1)


def test_set_text_e_get_text_pelo_numero() -> None:
    _snapshot()
    with _live(), patch(
        "visus.desktop.core.native_rpa.native_set_text_ex",
        return_value=ActionOutcome.sent("keyboard", verified=True),
    ) as m:
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
    with patch(
        "visus.desktop.core.native_rpa.native_set_text_ex", return_value=ActionOutcome.sent("keyboard")
    ) as m:
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


# --- o número aponta sempre para o controle que o snapshot viu ------------------------


def test_janela_mudou_recusa_sem_enviar() -> None:
    """Apareceu mais um "Fechar": o found_index 1 agora pode ser outro controle."""
    _snapshot()
    extra = NODES + [
        {"depth": 3, "control_type": "Button", "title": "Fechar", "auto_id": "", "rect": [1, 1, 2, 2]}
    ]
    with _live(extra), patch("visus.desktop.core.native_rpa.native_click_ex") as m:
        r = runner.invoke(cli, ["native", "click", "3"])
    assert r.exit_code == 1
    assert "window changed" in r.output
    assert "safe to retry" in r.output
    m.assert_not_called()


def test_controle_sumiu_recusa_sem_enviar() -> None:
    _snapshot()
    sem_mais = [n for n in NODES if n["title"] != "Mais"]
    with _live(sem_mais), patch("visus.desktop.core.native_rpa.native_click_ex") as m:
        r = runner.invoke(cli, ["native", "click", "1"])
    assert r.exit_code == 1
    assert "gone" in r.output
    m.assert_not_called()


def test_sessoes_nao_misturam_snapshots(monkeypatch) -> None:
    monkeypatch.setenv("VISUS_DESKTOP_SESSION", "aba-1")
    _snapshot()
    monkeypatch.setenv("VISUS_DESKTOP_SESSION", "aba-2")
    r = runner.invoke(cli, ["native", "click", "0"])
    assert r.exit_code == 1
    assert "native snapshot" in r.output


def test_numero_fixado_vale_o_snapshot_dele() -> None:
    first = json.loads(_snapshot("--json").output)["snapshot_id"]
    with patch(
        "visus.desktop.core.native_rpa.native_snapshot_nodes",
        return_value=("Calculadora", NODES[:3]),
    ):
        runner.invoke(cli, ["native", "snapshot", "--window", "Calculadora"])
    with _live(), patch(
        "visus.desktop.core.native_rpa.native_click_ex", return_value=ActionOutcome.sent("Invoke")
    ) as m:
        r = runner.invoke(cli, ["native", "click", f"{first}:4"])
    assert r.exit_code == 0, r.output
    assert m.call_args.kwargs["auto_id"] == "nome"


def test_estados_aparecem_na_linha() -> None:
    nodes = [
        {"depth": 1, "control_type": "CheckBox", "title": "Lembrar", "auto_id": "", "rect": None,
         "actions": ["toggle"], "enabled": True, "toggle": 1},
        {"depth": 1, "control_type": "Button", "title": "Entrar", "auto_id": "ok", "rect": None,
         "actions": ["invoke"], "enabled": False},
        {"depth": 1, "control_type": "Edit", "title": "Senha", "auto_id": "pwd", "rect": None,
         "actions": ["value"], "enabled": True, "password": True},
    ]
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("Login", nodes)):
        r = runner.invoke(cli, ["native", "snapshot", "--window", "Login"])
    lines = r.output.splitlines()
    assert lines[1] == "  0  CheckBox     Lembrar [checked]"
    assert lines[2] == "  1  Button       Entrar #ok [disabled]"
    assert lines[3] == "  2  Edit         Senha #pwd [password]"


def test_get_text_de_senha_nao_revela() -> None:
    nodes = [{"depth": 1, "control_type": "Edit", "title": "Senha", "auto_id": "pwd",
              "rect": None, "password": True}]
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("Login", nodes)):
        runner.invoke(cli, ["native", "snapshot", "--window", "Login"])
    with patch("visus.desktop.core.native_rpa.native_get_text", return_value="s3gr3d0") as g:
        r = runner.invoke(cli, ["native", "get-text", "0"])
    assert "s3gr3d0" not in r.output
    assert "hidden" in r.output
    g.assert_not_called()


def test_custom_que_anuncia_acao_ganha_numero() -> None:
    """Um Custom/Group clicável (WPF, Chromium) entra; um sem ação, não."""
    nodes = [
        {"depth": 1, "control_type": "Custom", "title": "Card", "auto_id": "", "actions": ["invoke"]},
        {"depth": 1, "control_type": "Group", "title": "", "auto_id": "", "actions": ["scroll"]},
        {"depth": 1, "control_type": "Pane", "title": "Painel", "auto_id": "", "actions": []},
    ]
    assert [i["title"] for i in select_actionable(nodes)] == ["Card"]


@pytest.mark.parametrize(
    ("command", "function", "kwargs"),
    [
        (["check", "0"], "native_toggle", {"checked": True}),
        (["uncheck", "0"], "native_toggle", {"checked": False}),
        (["toggle", "0"], "native_toggle", {"checked": None}),
        (["expand", "0"], "native_expand", {"expand": True}),
        (["collapse", "0"], "native_expand", {"expand": False}),
        (["select", "0", "Azul"], "native_select", {"value": "Azul"}),
        (["scroll-into-view", "0"], "native_scroll_into_view", {}),
    ],
)
def test_acoes_semanticas_pelo_numero(command, function, kwargs) -> None:
    nodes = [{"depth": 1, "control_type": "ComboBox", "title": "Cor", "auto_id": "cor", "rect": None}]
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("Form", nodes)):
        runner.invoke(cli, ["native", "snapshot", "--window", "Form"])
        with patch(
            f"visus.desktop.core.native_rpa.{function}",
            return_value=ActionOutcome.sent("UIA", verified=True),
        ) as m:
            r = runner.invoke(cli, ["native", *command])
    assert r.exit_code == 0, r.output
    for key, value in kwargs.items():
        assert m.call_args.kwargs[key] == value
    assert m.call_args.kwargs["auto_id"] == "cor"
    assert m.call_args.kwargs["window"] == "Form"


def test_acao_que_pode_ter_chegado_avisa_para_conferir() -> None:
    nodes = [{"depth": 1, "control_type": "CheckBox", "title": "A", "auto_id": "a", "rect": None}]
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("F", nodes)):
        runner.invoke(cli, ["native", "snapshot", "--window", "F"])
        with patch(
            "visus.desktop.core.native_rpa.native_toggle",
            return_value=ActionOutcome.maybe_sent("timed out after the action was sent"),
        ):
            r = runner.invoke(cli, ["native", "check", "0", "--json"])
    assert r.exit_code == 1
    data = json.loads(r.output)
    assert data["delivery"] == "uncertain"
    assert data["retry_safe"] is False

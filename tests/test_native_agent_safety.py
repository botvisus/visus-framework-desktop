"""O que torna o agente seguro no desktop: o número do snapshot aponta sempre para o
controle certo, toda ação diz se chegou ao app, app travado responde na hora, a lista
de janelas só tem janelas reais, e as ações semânticas (toggle/select/expand) agem
sem mouse e conferem o resultado.

Ideias trazidas do agent-desktop (Vercel Labs, Apache-2.0) -- ver os módulos.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from visus.desktop.core import native_patterns as np_
from visus.desktop.core import native_rpa as nr
from visus.desktop.core import native_session as ns
from visus.desktop.core.outcome import ActionOutcome
from visus.desktop.core.win_health import passes_window_filter

# --- ActionOutcome -----------------------------------------------------------------------


def test_so_o_que_nao_chegou_e_seguro_repetir() -> None:
    assert ActionOutcome.not_sent("x").retry_safe is True
    assert ActionOutcome.sent("Invoke").retry_safe is False
    assert ActionOutcome.maybe_sent("x").retry_safe is False
    assert ActionOutcome.sent("Toggle", verified=False).ok is False
    assert ActionOutcome.sent("Toggle", verified=True).delivery == "verified"


def test_outcome_e_verdadeiro_quando_deu_certo() -> None:
    assert ActionOutcome.sent("Invoke")
    assert not ActionOutcome.not_sent("x")


def test_texto_diz_se_pode_repetir() -> None:
    assert "safe to retry" in ActionOutcome.not_sent("gone").human("clicked")
    assert "MAY have reached" in ActionOutcome.maybe_sent("timeout").human("clicked")
    assert ActionOutcome.sent("Invoke").human("clicked") == "clicked (Invoke)"


# --- filtro de janelas -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        (dict(visible=True, width=800, height=600, cloaked=False, tool=False), True),
        (dict(visible=False, width=800, height=600, cloaked=False, tool=False), False),
        (dict(visible=True, width=0, height=600, cloaked=False, tool=False), False),
        (dict(visible=True, width=800, height=600, cloaked=True, tool=False), False),
        (dict(visible=True, width=800, height=600, cloaked=False, tool=True), False),
    ],
)
def test_filtro_de_janela_real(kwargs, expected) -> None:
    assert passes_window_filter(**kwargs) is expected


@pytest.mark.skipif(sys.platform != "win32", reason="lista de janelas do Windows")
def test_lista_de_janelas_tira_as_fantasmas() -> None:
    from visus.desktop.core import window

    gui = MagicMock()
    gui.IsWindowVisible.return_value = True
    rects = {1: (0, 0, 800, 600), 2: (0, 0, 0, 0), 3: (0, 0, 800, 600), 4: (0, 0, 800, 600)}
    gui.GetWindowRect.side_effect = lambda h: rects[h]
    gui.GetWindowText.side_effect = lambda h: f"janela {h}"
    gui.EnumWindows.side_effect = lambda cb, extra: [cb(h, extra) for h in rects]
    proc = MagicMock()
    proc.GetWindowThreadProcessId.side_effect = lambda h: (0, 100 + h)
    with patch.dict(sys.modules, {"win32gui": gui, "win32process": proc}), patch(
        "visus.desktop.core.win_health.is_cloaked", side_effect=lambda h: h == 3
    ), patch("visus.desktop.core.win_health.is_tool_window", side_effect=lambda h: h == 4):
        assert [hwnd for hwnd, _, _ in window._enum_visible_windows()] == [1]


# --- app travado -------------------------------------------------------------------------


def test_app_travado_vira_motivo_claro_sem_enviar() -> None:
    with patch.object(nr, "_ensure_pywinauto", return_value=True), patch.object(
        nr, "_connect_top", side_effect=nr.NativeAppUnresponsive("the program is not responding")
    ):
        out = nr.native_click_ex(window="Excel", title="OK")
    assert out.ok is False
    assert out.retry_safe is True
    assert out.details["kind"] == "app_unresponsive"


# --- clique em degraus e repetição -------------------------------------------------------


def _top_with(ctrl):
    top = MagicMock()
    top.child_window.return_value = ctrl
    return top


def _ctrl():
    ctrl = MagicMock()
    ctrl.exists.return_value = True
    ctrl.rectangle.return_value = MagicMock(left=0, top=0, right=10, bottom=10)
    return ctrl


def test_sem_invoke_usa_a_acao_padrao_antes_do_mouse() -> None:
    ctrl = _ctrl()
    ctrl.invoke.side_effect = RuntimeError("no Invoke")
    with patch.object(nr, "_ensure_pywinauto", return_value=True), patch.object(
        nr, "_connect_top", return_value=_top_with(ctrl)
    ), patch.object(np_, "legacy_default_action", return_value=True):
        out = nr.native_click_ex(window="App", title="OK")
    assert out.ok and out.method == "DoDefaultAction"
    ctrl.click_input.assert_not_called()


def test_method_invoke_nunca_usa_o_mouse() -> None:
    ctrl = _ctrl()
    ctrl.invoke.side_effect = RuntimeError("no Invoke")
    with patch.object(nr, "_ensure_pywinauto", return_value=True), patch.object(
        nr, "_connect_top", return_value=_top_with(ctrl)
    ), patch.object(np_, "legacy_default_action", return_value=False):
        out = nr.native_click_ex(window="App", title="OK", method="invoke")
    assert out.ok is False and out.retry_safe is True
    ctrl.click_input.assert_not_called()


def test_clique_que_pode_ter_chegado_nao_e_repetido() -> None:
    ctrl = _ctrl()
    ctrl.click_input.side_effect = RuntimeError("COM error mid-click")
    with patch.object(nr, "_ensure_pywinauto", return_value=True), patch.object(
        nr, "_connect_top", return_value=_top_with(ctrl)
    ):
        out = nr.native_click_ex(window="App", title="OK", method="click", retries=3, delay=0)
    assert out.delivery == "uncertain"
    assert ctrl.click_input.call_count == 1


def test_o_que_nao_chegou_e_repetido() -> None:
    ctrl = _ctrl()
    ctrl.exists.side_effect = [False, False, True]
    with patch.object(nr, "_ensure_pywinauto", return_value=True), patch.object(
        nr, "_connect_top", return_value=_top_with(ctrl)
    ):
        out = nr.native_click_ex(window="App", title="OK", retries=3, delay=0)
    assert out.ok and out.method == "Invoke"
    assert ctrl.exists.call_count == 3


def test_native_click_continua_devolvendo_bool() -> None:
    with patch.object(nr, "native_click_ex", return_value=ActionOutcome.sent("Invoke")):
        assert nr.native_click(window="App", title="OK") is True


# --- conferência do número do snapshot ---------------------------------------------------

NODES = [
    {"control_type": "Button", "title": "Excluir", "auto_id": ""},
    {"control_type": "Button", "title": "Excluir", "auto_id": ""},
    {"control_type": "Edit", "title": "Nome", "auto_id": "nome"},
]


def test_snapshot_guarda_quantos_iguais_havia() -> None:
    items = nr.select_actionable(NODES)
    assert [(i["found_index"], i["match_count"]) for i in items] == [(0, 2), (1, 2), (0, 1)]


@pytest.mark.parametrize(
    ("live", "expected"),
    [
        (NODES, None),
        (NODES + [{"control_type": "Button", "title": "Excluir", "auto_id": ""}], "window changed"),
        ([NODES[2]], "gone"),
    ],
)
def test_conferencia_antes_de_agir(live, expected) -> None:
    item = nr.select_actionable(NODES)[1]
    with patch.object(nr, "native_snapshot_nodes", return_value=("App", live)):
        reason = nr.verify_snapshot_item({"window": "App"}, item)
    assert reason is None if expected is None else expected in reason


def test_janela_que_nao_responde_na_conferencia() -> None:
    item = nr.select_actionable(NODES)[2]
    with patch.object(nr, "native_snapshot_nodes", return_value=(None, [])):
        assert "not responding" in nr.verify_snapshot_item({"window": "App"}, item)


def test_snapshot_antigo_sem_contagem_passa() -> None:
    assert nr.verify_snapshot_item({"window": "App"}, {"title": "OK"}) is None


# --- snapshots por sessão ----------------------------------------------------------------


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUS_CONFIG", str(tmp_path / "config.json"))
    monkeypatch.delenv("VISUS_DESKTOP_SESSION", raising=False)
    return tmp_path


def test_ultimo_e_fixado(store) -> None:
    first = ns.save_snapshot({"items": [{"title": "A"}]})
    ns.save_snapshot({"items": [{"title": "B"}]})
    assert ns.load_ref("0")[1]["title"] == "B"
    assert ns.load_ref(f"{first}:0")[1]["title"] == "A"


def test_sessao_invalida_cai_no_default(store, monkeypatch) -> None:
    monkeypatch.setenv("VISUS_DESKTOP_SESSION", "../../etc")
    assert ns.session_name() == "default"


def test_guarda_no_maximo_32(store) -> None:
    ids = [ns.save_snapshot({"items": [{"n": i}]}) for i in range(ns.MAX_SNAPSHOTS + 5)]
    assert len(list(ns.snapshot_dir().glob("s*.json"))) <= ns.MAX_SNAPSHOTS
    assert ns.load_ref(f"{ids[-1]}:0")[1] == {"n": ns.MAX_SNAPSHOTS + 4}


@pytest.mark.parametrize("ref", ["abc", "s123:1", "-1", "3.5"])
def test_numero_invalido_explica(store, ref) -> None:
    ns.save_snapshot({"items": [{"title": "A"}]})
    with pytest.raises(ns.SnapshotError):
        ns.load_ref(ref)


# --- ações semânticas --------------------------------------------------------------------


class _Toggle:
    def __init__(self, states):
        self.states = list(states)
        self.calls = 0

    @property
    def CurrentToggleState(self):  # noqa: N802 - nome do COM
        return self.states[min(self.calls, len(self.states) - 1)]

    def Toggle(self):  # noqa: N802
        self.calls += 1


def _with_patterns(**patterns):
    return patch.object(np_, "_iface", side_effect=lambda w, name: patterns.get(name))


def test_check_ja_marcado_nao_envia() -> None:
    toggle = _Toggle([1])
    with _with_patterns(Toggle=toggle):
        out = np_.set_checked(MagicMock(), True)
    assert out.ok and out.method == "already"
    assert toggle.calls == 0


def test_check_de_tres_estados_leva_dois_toques() -> None:
    toggle = _Toggle([2, 0, 1])  # indeterminado -> desmarcado -> marcado
    with _with_patterns(Toggle=toggle), patch.object(np_, "VERIFY_TIMEOUT", 0):
        out = np_.set_checked(MagicMock(), True)
    assert out.ok and out.delivery == "verified"
    assert toggle.calls == 2


def test_toque_que_nao_muda_nada_nao_e_repetido() -> None:
    toggle = _Toggle([0])  # o app ignora o toque
    with _with_patterns(Toggle=toggle), patch.object(np_, "VERIFY_TIMEOUT", 0):
        out = np_.set_checked(MagicMock(), True)
    assert out.ok is False and out.delivery == "uncertain"
    assert toggle.calls == 1


def test_sem_toggle_nem_invoke_nao_envia() -> None:
    with _with_patterns():
        out = np_.set_checked(MagicMock(), True)
    assert out.retry_safe


def test_expand_folha_nao_envia() -> None:
    pattern = MagicMock(CurrentExpandCollapseState=np_.LEAF)
    with _with_patterns(ExpandCollapse=pattern):
        out = np_.set_expanded(MagicMock(), True)
    assert out.retry_safe
    pattern.Expand.assert_not_called()


def _option(name, rid):
    item = MagicMock()
    item.element_info.name = name
    item.element_info.runtime_id = rid
    return item


def test_select_com_nome_repetido_e_ambiguo() -> None:
    container = MagicMock()
    container.descendants.return_value = [_option("Azul", (1,)), _option("azul", (2,))]
    with _with_patterns(SelectionItem=MagicMock()):
        out = np_.select_option(container, "Azul")
    assert out.retry_safe and out.details["kind"] == "ambiguous"


def test_select_acha_e_confere() -> None:
    container = MagicMock()
    container.descendants.return_value = [_option("Verde", (1,)), _option("Azul", (2,))]
    pattern = MagicMock(CurrentIsSelected=True)
    with _with_patterns(SelectionItem=pattern), patch.object(np_, "expand_state", return_value=None):
        out = np_.select_option(container, "azul")
    assert out.ok and out.delivery == "verified"
    pattern.Select.assert_called_once()


def test_select_sem_a_opcao_nao_envia() -> None:
    container = MagicMock()
    container.descendants.return_value = [_option("Verde", (1,))]
    with _with_patterns(SelectionItem=MagicMock()), patch.object(
        np_, "expand_state", return_value=None
    ), patch.object(np_, "_scroll_once", return_value=False):
        out = np_.select_option(container, "Roxo")
    assert out.retry_safe and out.details["kind"] == "not_found"


class _Value:
    def __init__(self, current, accepts):
        self.CurrentValue = current
        self.CurrentIsReadOnly = False
        self.accepts = accepts

    def SetValue(self, value):  # noqa: N802 - nome do COM
        if value in self.accepts:
            self.CurrentValue = value


def test_combo_win32_escolhe_pelo_valor_e_confere() -> None:
    """O Mapa de Caracteres: a lista só existe aberta e o Expand não a abre sem foco."""
    container = MagicMock()
    container.descendants.return_value = []
    value = _Value("Arial", accepts={"Consolas"})
    with _with_patterns(Value=value), patch.object(np_, "expand_state", return_value=None), patch.object(
        np_, "VERIFY_TIMEOUT", 0
    ):
        out = np_.select_option(container, "Consolas")
        assert out.ok and out.method == "ValuePattern" and out.delivery == "verified"
        out = np_.select_option(container, "Nao existe")
    assert out.retry_safe and out.details["kind"] == "not_found"
    assert value.CurrentValue == "Consolas"


def test_acao_padrao_so_com_texto() -> None:
    legacy = MagicMock(CurrentDefaultAction="")
    with _with_patterns(LegacyIAccessible=legacy):
        assert np_.legacy_default_action(MagicMock()) is False
    legacy.DoDefaultAction.assert_not_called()
    legacy = MagicMock(CurrentDefaultAction="Press")
    with _with_patterns(LegacyIAccessible=legacy):
        assert np_.legacy_default_action(MagicMock()) is True
    legacy.DoDefaultAction.assert_called_once()


def test_estados_do_snapshot() -> None:
    assert np_.states_of({"enabled": False, "toggle": 2, "expand": 0, "password": True}) == [
        "disabled", "password", "mixed", "collapsed",
    ]
    assert np_.states_of({"expand": np_.LEAF}) == []


# --- Chromium: grupos anônimos não contam profundidade -----------------------------------


def _el(ctype, name="", children=(), auto_id=""):
    el = MagicMock()
    el.element_info.control_type = ctype
    el.element_info.name = name
    el.element_info.automation_id = auto_id
    el.element_info.class_name = ""
    el.children.return_value = list(children)
    el.rectangle.side_effect = RuntimeError("no rect")
    return el


def test_chromium_alcanca_botao_atras_de_grupos_anonimos() -> None:
    button = _el("Button", "Salvar")
    chain = button
    for _ in range(6):
        chain = _el("Group", children=[chain])
    top = _el("Window", children=[chain])
    top.element_info.class_name = "Chrome_WidgetWin_1"
    with patch.object(np_, "read_node_extras", return_value={}):
        titles = [n["title"] for n in nr._walk_tree(top, max_depth=3)]
    assert "Salvar" in titles


def test_fora_do_chromium_os_grupos_contam() -> None:
    button = _el("Button", "Salvar")
    chain = button
    for _ in range(6):
        chain = _el("Group", children=[chain])
    top = _el("Window", children=[chain])
    with patch.object(np_, "read_node_extras", return_value={}):
        titles = [n["title"] for n in nr._walk_tree(top, max_depth=3)]
    assert "Salvar" not in titles

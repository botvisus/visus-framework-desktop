"""A segunda leva do agent-desktop: leitura em lote, leitura incompleta dita, identidade
mais rígida, checagens antes da entrada física (UIPI, janela por cima, atalhos
perigosos, uma entrada por vez) e as esperas por janela e menu."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core import input_guard, native_rpa, uia_batch, waits

runner = CliRunner()


# --- atalhos perigosos ---------------------------------------------------------------

@pytest.mark.parametrize(
    "keys, blocked",
    [
        ("Alt+F4", "alt+f4"),
        ("alt+shift+tab", "alt+tab"),  # superconjunto: troca de janela igual
        ("Ctrl+Alt+F4", "alt+f4"),
        ("Windows+L", "win+l"),
        ("Super+d", "win+d"),
        ("Ctrl+Shift+Escape", "ctrl+shift+esc"),
        ("Ctrl, Alt+Tab", "alt+tab"),  # num passo de uma sequência
        ("Win + R", "win+r"),
    ],
)
def test_atalho_perigoso_e_reconhecido(keys, blocked):
    assert input_guard.blocked_combo(keys) == blocked


@pytest.mark.parametrize("keys", ["Ctrl+S", "Alt", "Alt, H, O, I", "Escape", "F4", "Tab", "Shift+Tab", ""])
def test_atalho_comum_passa(keys):
    assert input_guard.blocked_combo(keys) is None


def test_cli_key_recusa_atalho_perigoso_sem_enviar():
    bot = MagicMock()
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["key", "Alt+F4"])
    assert r.exit_code != 0
    assert "blocked" in r.output and "window close" in r.output
    bot.keyboard_command.assert_not_called()


def test_cli_key_force_envia(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUS_CONFIG", str(tmp_path / "config.json"))
    bot = MagicMock()
    bot.keyboard_command.return_value = True
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["key", "Alt+F4", "--force"])
    assert r.exit_code == 0, r.output
    bot.keyboard_command.assert_called_once()


def test_mcp_keyboard_command_recusa_atalho_perigoso():
    from visus.desktop import mcp_server as ms

    tool = ms._tools_for_tests()["keyboard_command"]
    with patch.object(ms, "get_bot") as get_bot:
        with pytest.raises(ValueError, match="win\\+l is blocked"):
            tool("Win+L")
        get_bot.assert_not_called()


# --- UIPI ---------------------------------------------------------------------------

def test_integridade_so_desce_ou_fica():
    assert input_guard.integrity_permits_input(0x2000, 0x2000)
    assert input_guard.integrity_permits_input(0x3000, 0x2000)
    assert not input_guard.integrity_permits_input(0x2000, 0x3000)
    assert input_guard.integrity_permits_input(None, 0x3000)  # sem saber, permite


def test_uipi_bloqueia_programa_administrador(monkeypatch):
    levels = {None: 0x2000, 4242: 0x3000}
    monkeypatch.setattr(input_guard, "process_integrity", lambda pid=None: levels.get(pid))
    assert input_guard.uipi_blocks(4242)
    assert not input_guard.uipi_blocks(None)
    assert not input_guard.uipi_blocks("não é pid")


@pytest.mark.skipif(sys.platform != "win32", reason="token do Windows")
def test_integridade_deste_processo_e_lida():
    assert input_guard.process_integrity() in (0x1000, 0x2000, 0x2100, 0x3000, 0x4000)


# --- antes do mouse de verdade ----------------------------------------------------

def _ctrl(pid=10, handle=777):
    rect = SimpleNamespace(left=0, top=0, right=100, bottom=40)
    return SimpleNamespace(
        element_info=SimpleNamespace(process_id=pid, handle=handle),
        rectangle=lambda: rect,
    )


def test_mouse_recusado_quando_o_programa_e_administrador(monkeypatch):
    monkeypatch.setattr(input_guard, "uipi_blocks", lambda pid: True)
    out = native_rpa._physical_check(_ctrl())
    assert out is not None and not out.ok and out.retry_safe
    assert out.details["kind"] == "elevated"


def test_mouse_recusado_com_janela_de_outro_programa_por_cima(monkeypatch):
    monkeypatch.setattr(input_guard, "uipi_blocks", lambda pid: False)
    monkeypatch.setattr(input_guard, "covering_window", lambda hwnd, x, y: "Aviso")
    fronted = []
    monkeypatch.setattr("visus.desktop.core.window._bring_to_front", fronted.append)
    out = native_rpa._physical_check(_ctrl())
    assert out is not None and out.details["kind"] == "occluded"
    assert "'Aviso' is over the control" in out.reason
    assert fronted  # tentou trazer a janela para a frente antes de recusar


def test_mouse_segue_quando_trazer_para_a_frente_resolve(monkeypatch):
    monkeypatch.setattr(input_guard, "uipi_blocks", lambda pid: False)
    answers = iter(["Aviso", None])
    monkeypatch.setattr(input_guard, "covering_window", lambda hwnd, x, y: next(answers))
    monkeypatch.setattr("visus.desktop.core.window._bring_to_front", lambda hwnd: True)
    assert native_rpa._physical_check(_ctrl()) is None


def test_mouse_mira_o_centro_do_controle(monkeypatch):
    monkeypatch.setattr(input_guard, "uipi_blocks", lambda pid: False)
    seen = []
    monkeypatch.setattr(
        input_guard, "covering_window", lambda hwnd, x, y: seen.append((x, y)) or None
    )
    native_rpa._physical_check(_ctrl())
    assert seen == [(50, 20)]


# --- uma entrada física por vez -------------------------------------------------------

def test_trava_de_entrada_entre_processos(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUS_CONFIG", str(tmp_path / "config.json"))
    holder = textwrap.dedent(
        """
        import sys, time
        from visus.desktop.core.input_guard import input_lease
        with input_lease():
            print("held", flush=True)
            time.sleep(4)
        """
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", holder], stdout=subprocess.PIPE, text=True,
        env=dict(os.environ, VISUS_CONFIG=str(tmp_path / "config.json")),
    )
    try:
        assert proc.stdout.readline().strip() == "held"
        start = time.monotonic()
        with pytest.raises(input_guard.InputBusy):
            with input_guard.input_lease(timeout=0.3):
                pass
        assert time.monotonic() - start < 3
    finally:
        proc.kill()
        proc.wait(10)
    with input_guard.input_lease(timeout=2):  # o outro morreu: a trava solta
        pass


def test_trava_de_entrada_solta_depois_do_bloco(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUS_CONFIG", str(tmp_path / "config.json"))
    with input_guard.input_lease(timeout=1):
        pass
    with input_guard.input_lease(timeout=1):
        pass


# --- identidade mais rígida e leitura incompleta ------------------------------------

def _snap_item(**extra):
    item = {"control_type": "Button", "title": "Excluir", "auto_id": "", "found_index": 0,
            "match_count": 1}
    item.update(extra)
    return {"window": "App"}, item


def _nodes(*nodes, unreadable=0, truncated=False):
    out = native_rpa.NodeList(nodes)
    out.unreadable, out.truncated = unreadable, truncated
    return out


def _button(**extra):
    node = {"control_type": "Button", "title": "Excluir", "auto_id": ""}
    node.update(extra)
    return node


def test_mesmo_nome_com_outra_descricao_e_recusado(monkeypatch):
    monkeypatch.setattr(
        native_rpa, "native_snapshot_nodes",
        lambda **kw: ("App", _nodes(_button(help="Excluir a pasta"))),
    )
    snap, item = _snap_item(help="Excluir o arquivo")
    reason = native_rpa.verify_snapshot_item(snap, item)
    assert reason and "description" in reason


def test_mesmo_nome_com_outra_classe_e_recusado(monkeypatch):
    monkeypatch.setattr(
        native_rpa, "native_snapshot_nodes",
        lambda **kw: ("App", _nodes(_button(class_name="Hyperlink"))),
    )
    snap, item = _snap_item(class_name="Button")
    assert "kind" in native_rpa.verify_snapshot_item(snap, item)


def test_identidade_igual_confere(monkeypatch):
    monkeypatch.setattr(
        native_rpa, "native_snapshot_nodes",
        lambda **kw: ("App", _nodes(_button(class_name="Button", help="Excluir o arquivo"))),
    )
    snap, item = _snap_item(class_name="Button", help="Excluir o arquivo")
    assert native_rpa.verify_snapshot_item(snap, item) is None


def test_controle_sumido_numa_leitura_incompleta_pede_novo_snapshot(monkeypatch):
    monkeypatch.setattr(
        native_rpa, "native_snapshot_nodes", lambda **kw: ("App", _nodes(unreadable=2))
    )
    snap, item = _snap_item()
    assert "could not be read" in native_rpa.verify_snapshot_item(snap, item)


def test_select_actionable_guarda_classe_e_descricao():
    (item,) = native_rpa.select_actionable([_button(class_name="Button", help="Apaga")])
    assert item["class_name"] == "Button" and item["help"] == "Apaga"


def test_snapshot_da_cli_avisa_leitura_incompleta(tmp_path, monkeypatch):
    monkeypatch.setenv("VISUS_CONFIG", str(tmp_path / "config.json"))
    nodes = _nodes(_button(), unreadable=1, truncated=True)
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("App", nodes)):
        r = runner.invoke(cli, ["native", "snapshot", "--window", "App"])
    assert r.exit_code == 0, r.output
    assert "! partial read: 1 part(s) of the window did not answer" in r.output
    assert "node limit" in r.output


def test_snapshot_do_mcp_avisa_leitura_incompleta():
    from visus.desktop import mcp_server as ms

    nodes = _nodes(_button(), unreadable=3)
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=("App", nodes)):
        out = ms._tools_for_tests()["native_snapshot"](window="App")
    assert out["unreadable"] == 3 and "truncated" not in out


# --- leitura em lote ------------------------------------------------------------------

_DLL = SimpleNamespace(
    TreeScope_Children=2,
    **{name: i for i, name in enumerate(
        (*uia_batch._BASE_PROPS, *uia_batch.PATTERN_FLAGS.values()), start=30000)},
)


class _El:
    """Um IUIAutomationElement falso: propriedades em cache e filhos."""

    def __init__(self, props=None, children=(), fail=False):
        self.props = props or {}
        self.children = list(children)
        self.fail = fail

    def GetCachedPropertyValue(self, pid):  # noqa: N802 - nome do COM
        for name, value in self.props.items():
            if getattr(_DLL, name) == pid:
                return value
        return None

    def FindAllBuildCache(self, scope, condition, request):  # noqa: N802
        if self.fail:
            raise OSError("COMError: o provedor deu erro")
        kids = self.children
        return SimpleNamespace(Length=len(kids), GetElement=lambda i: kids[i])


def _iuia():
    client = MagicMock()
    return SimpleNamespace(UIA_dll=_DLL, iuia=client, known_control_type_ids={50000: "Button", 50033: "Pane"})


def _btn(name, **props):
    base = {
        "UIA_NamePropertyId": name, "UIA_ControlTypePropertyId": 50000,
        "UIA_BoundingRectanglePropertyId": (10, 20, 30, 40),
        "UIA_IsEnabledPropertyId": True, "UIA_IsInvokePatternAvailablePropertyId": True,
    }
    base.update(props)
    return _El(base)


def _walk(top, max_nodes=100):
    return uia_batch.walk(
        top, max_depth=25, max_nodes=max_nodes, max_raw_depth=50,
        with_extras=native_rpa._with_extras, skip_level=lambda node: False, iuia=_iuia(),
    )


def test_lote_le_o_no_no_formato_do_walk():
    read = _walk(_El(children=[_btn("OK", UIA_HelpTextPropertyId="Confirma")]))
    (node,) = read.nodes
    assert node["control_type"] == "Button" and node["title"] == "OK"
    assert node["rect"] == {"x": 10, "y": 20, "width": 30, "height": 40}
    assert node["actions"] == ["invoke"] and node["enabled"] is True
    assert node["help"] == "Confirma" and "toggle" not in node
    assert not read.partial


def test_lote_so_le_estado_de_padrao_anunciado():
    # ToggleState sem o TogglePattern anunciado é valor "padrão" (A15-7): não entra
    read = _walk(_El(children=[_btn("OK", UIA_ToggleToggleStatePropertyId=2)]))
    assert "toggle" not in read.nodes[0]
    read = _walk(_El(children=[_btn(
        "Lembrar", UIA_IsTogglePatternAvailablePropertyId=True, UIA_ToggleToggleStatePropertyId=1,
    )]))
    assert read.nodes[0]["toggle"] == 1


def test_lote_conta_ramo_que_nao_respondeu():
    broken = _El({"UIA_NamePropertyId": "painel", "UIA_ControlTypePropertyId": 50033}, fail=True)
    read = _walk(_El(children=[broken, _btn("OK")]))
    assert [n["title"] for n in read.nodes] == ["painel", "OK"]
    assert read.unreadable == 1 and read.partial


def test_lote_diz_quando_o_limite_cortou():
    read = _walk(_El(children=[_btn(str(i)) for i in range(5)]), max_nodes=3)
    assert len(read.nodes) == 3 and read.truncated


def test_lote_em_pre_ordem():
    tree = _El(children=[
        _El({"UIA_NamePropertyId": "a", "UIA_ControlTypePropertyId": 50033}, children=[_btn("a1")]),
        _btn("b"),
    ])
    read = _walk(tree)
    assert [(n["title"], n["depth"]) for n in read.nodes] == [("a", 1), ("a1", 2), ("b", 1)]


def test_caixa_do_retangulo():
    assert uia_batch._box((1, 2, 3, 4)) == {"x": 1, "y": 2, "width": 3, "height": 4}
    rect = SimpleNamespace(left=1, top=2, right=11, bottom=22)
    assert uia_batch._box(rect) == {"x": 1, "y": 2, "width": 10, "height": 20}
    assert uia_batch._box(None) is None


@pytest.mark.skipif(sys.platform != "win32", reason="UIA só no Windows")
def test_cliente_uia_com_prazo():
    pytest.importorskip("pywinauto")
    from pywinauto.uia_defines import IUIA

    assert uia_batch.harden_client()
    client = IUIA().iuia
    assert client.ConnectionTimeout == uia_batch.CONNECTION_TIMEOUT_MS
    assert client.TransactionTimeout == uia_batch.TRANSACTION_TIMEOUT_MS


# --- esperas --------------------------------------------------------------------------

def test_espera_janela_aparecer(monkeypatch):
    seen = iter([None, None, 99])
    monkeypatch.setattr("visus.desktop.core.window.find_window", lambda t: next(seen))
    monkeypatch.setattr(waits, "_title_of", lambda hwnd: "Salvar como")
    monkeypatch.setattr(waits, "POLL", 0)
    assert waits.wait_window("Salvar", timeout=5) == "Salvar como"


def test_espera_janela_sumir_e_prazo(monkeypatch):
    monkeypatch.setattr("visus.desktop.core.window.find_window", lambda t: 5)
    monkeypatch.setattr(waits, "POLL", 0.01)
    assert waits.wait_window("X", gone=True, timeout=0.05) is False
    monkeypatch.setattr(waits, "_title_of", lambda hwnd: "")
    assert waits.wait_window("Y", timeout=0) == "Y"  # sem título lido: o pedido


def test_espera_menu(monkeypatch):
    states = iter([False, False, True])
    monkeypatch.setattr(waits, "menu_open", lambda pid: next(states))
    monkeypatch.setattr(waits, "POLL", 0)
    assert waits.wait_menu(1, open=True, timeout=5)
    monkeypatch.setattr(waits, "menu_open", lambda pid: True)
    assert not waits.wait_menu(1, open=False, timeout=0)


def test_cli_window_wait(monkeypatch):
    monkeypatch.setattr(waits, "wait_window", lambda title, gone, timeout: None)
    r = runner.invoke(cli, ["window", "wait", "Salvar", "--timeout", "0"])
    assert r.exit_code != 0 and "no window 'Salvar'" in r.output
    monkeypatch.setattr(waits, "wait_window", lambda title, gone, timeout: True)
    r = runner.invoke(cli, ["window", "wait", "Salvar", "--gone"])
    assert r.exit_code == 0 and "closed" in r.output


def test_cli_wait_menu_sem_janela(monkeypatch):
    monkeypatch.setattr(waits, "window_pid", lambda title: None)
    r = runner.invoke(cli, ["native", "wait-menu", "--window", "Nada"])
    assert r.exit_code != 0 and "no visible window" in r.output


def test_cli_wait_menu_aberto(monkeypatch):
    monkeypatch.setattr(waits, "window_pid", lambda title: 7)
    monkeypatch.setattr(waits, "wait_menu", lambda pid, open, timeout: pid == 7 and open)
    r = runner.invoke(cli, ["native", "wait-menu", "--window", "Bloco"])
    assert r.exit_code == 0 and "menu open" in r.output


def test_menu_fora_do_windows_ou_sem_pid():
    assert waits.menu_open(None) is False


def test_menu_por_qualquer_um_dos_sinais(monkeypatch):
    if sys.platform != "win32":
        pytest.skip("sinais do Windows")
    monkeypatch.setattr(waits, "_top_windows_of", lambda pid: [(1, 11, "Notepad"), (2, 11, "Bridge")])
    monkeypatch.setattr(waits, "_thread_in_menu_mode", lambda tid: False)
    monkeypatch.setattr(waits, "_uia_menu_on_top", lambda pid: False)
    monkeypatch.setattr("visus.desktop.core.win_health.is_tool_window", lambda h: h == 2)
    monkeypatch.setattr("visus.desktop.core.win_health.window_is_pumping", lambda h, t=0: h != 3)
    probed = []
    monkeypatch.setattr(waits, "_window_has_open_menu", lambda hwnds: probed.append(hwnds) or False)
    assert waits.menu_open(5) is False and probed == [[2, 1]]  # o popup primeiro
    monkeypatch.setattr(waits, "_window_has_open_menu", lambda hwnds: True)
    assert waits.menu_open(5) is True
    monkeypatch.setattr(waits, "_top_windows_of", lambda pid: [(3, 12, "#32768")])
    monkeypatch.setattr(waits, "_window_has_open_menu", lambda hwnds: False)
    assert waits.menu_open(5) is True  # a janela de menu clássica basta


def test_janela_travada_nao_e_lida(monkeypatch):
    if sys.platform != "win32":
        pytest.skip("sinais do Windows")
    monkeypatch.setattr(waits, "_top_windows_of", lambda pid: [(3, 12, "App")])
    monkeypatch.setattr(waits, "_thread_in_menu_mode", lambda tid: False)
    monkeypatch.setattr(waits, "_uia_menu_on_top", lambda pid: False)
    monkeypatch.setattr("visus.desktop.core.win_health.window_is_pumping", lambda h, t=0: False)
    probed = []
    monkeypatch.setattr(waits, "_window_has_open_menu", lambda hwnds: probed.append(hwnds) or False)
    assert waits.menu_open(5) is False and probed == [[]]

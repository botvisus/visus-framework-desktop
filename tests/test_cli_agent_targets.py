"""Achar e clicar como um agente de IA faz: listar, escolher pelo número, clicar
sem roubar o mouse da pessoa.

- `find-all` numera; `--occurrence N` explícito é SEMPRE o #N dessa lista — no
  texto e na imagem, inclusive o 1 (sem a flag, o 1º acerto rápido de sempre).
- A ordem de leitura tolera tremidas: dois botões na mesma linha, um 2 px mais
  alto, não trocam de lugar.
- `--virtual`: clique por mensagens do Windows, o cursor não se mexe; se a janela
  recusar, FALHA em vez de usar o mouse real escondido.
- `--window TÍTULO`: OCR/imagem só na janela (bem mais rápido que a tela toda).
"""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core.reading_order import reading_order

runner = CliRunner()


# --- ordem de leitura ---------------------------------------------------------


def test_reading_order_mesma_linha_tolera_tremida() -> None:
    # o da direita está 2 px mais alto: continua depois do da esquerda
    boxes = [(250, 58, 60, 24), (50, 60, 60, 24), (50, 140, 60, 24)]
    assert reading_order(boxes) == [(50, 60, 60, 24), (250, 58, 60, 24), (50, 140, 60, 24)]


def test_reading_order_com_chave() -> None:
    items = [(0.9, (300, 10, 40, 20)), (0.8, (10, 12, 40, 20))]
    assert reading_order(items, key=lambda c: c[1]) == [items[1], items[0]]


def test_image_find_all_numera_em_ordem_de_leitura() -> None:
    unsorted = [(250, 58, 60, 24), (50, 140, 60, 24), (50, 60, 60, 24)]
    with patch("visus.desktop.find_all", return_value=unsorted):
        r = runner.invoke(cli, ["image", "find-all", "botao.png", "--json"])
    assert r.exit_code == 0, r.output
    assert [(m["occurrence"], m["x"], m["y"]) for m in json.loads(r.output)] == [
        (1, 50, 60), (2, 250, 58), (3, 50, 140),
    ]


def test_image_find_all_conta_cada_ocorrencia_uma_vez() -> None:
    from visus.desktop.core.locate import find_all

    # o OpenCV devolve todo deslocamento acima da confiança: um "platô" ao redor
    # de cada botão (assim saíram 10.000 caixas para 2 botões)
    plateau = [(x, y, 90, 40) for x in range(100, 106) for y in range(200, 204)]
    plateau += [(x, y, 90, 40) for x in range(350, 353) for y in range(199, 201)]
    with patch("pyautogui.locateAllOnScreen", return_value=iter(plateau)):
        boxes = find_all("b.png")
    assert boxes == [(102, 202, 90, 40), (351, 200, 90, 40)]


# --- --occurrence explícito = #N do find-all -------------------------------------


def _fake_bot(**methods: object) -> MagicMock:
    bot = MagicMock()
    bot.executor.virtual_mouse.last_click = None
    for name, value in methods.items():
        getattr(bot, name).return_value = value
    return bot


def test_text_click_occurrence_explicito_conta_na_lista_do_find_all() -> None:
    bot = _fake_bot(click_text=True)
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["text", "click", "Salvar", "--occurrence", "1"])
    assert r.exit_code == 0, r.output
    kw = bot.click_text.call_args.kwargs
    assert (kw["occurrence"], kw["enumerate_all"]) == (1, True)


def test_text_click_sem_occurrence_mantem_o_caminho_rapido() -> None:
    bot = _fake_bot(click_text=True)
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["text", "click", "Salvar"])
    assert r.exit_code == 0, r.output
    kw = bot.click_text.call_args.kwargs
    assert (kw["occurrence"], kw["enumerate_all"]) == (1, False)
    # mesma confiança do find-all: a da config, não um 75 fixo só no click
    assert kw["confidence_threshold"] is None


def test_text_find_occurrence_explicito() -> None:
    bot = _fake_bot(find_text=(10, 20, 30, 40))
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["text", "find", "Salvar", "--occurrence", "2"])
    assert r.exit_code == 0, r.output
    assert bot.find_text.call_args.kwargs["enumerate_all"] is True


def test_image_click_occurrence_explicito() -> None:
    bot = _fake_bot(click_image=True)
    with patch("visus.desktop.cli.commands.image.build_bot", return_value=bot):
        r = runner.invoke(cli, ["image", "click", "b.png", "--occurrence", "1"])
    assert r.exit_code == 0, r.output
    assert bot.click_image.call_args.kwargs["enumerate_all"] is True


def test_bot_find_text_enumerate_all_usa_a_lista_mesmo_no_1() -> None:
    from PIL import Image

    from visus.desktop import VisusBot

    bot = VisusBot()
    bot.ocr_engine = MagicMock()
    bot.ocr_engine.find_all_text.return_value = [(60.0, (5, 5, 10, 10)), (99.0, (5, 50, 10, 10))]
    bot.ocr_engine.find_text.return_value = ([(5, 50, 10, 10)], [99.0], True)
    bot.executor._capture_region = lambda region: Image.new("RGB", (100, 100))
    box = bot.find_text("Salvar", region=(100, 200, 100, 100), occurrence=1, enumerate_all=True)
    assert box == (105, 205, 10, 10), "o #1 da lista, não o acerto mais confiante"
    bot.ocr_engine.find_text.assert_not_called()


def test_bot_find_image_occurrence_em_ordem_de_leitura(tmp_path) -> None:
    from PIL import Image

    from visus.desktop import VisusBot

    template = tmp_path / "b.png"
    Image.new("RGB", (60, 24)).save(template)
    bot = VisusBot()
    with patch("visus.desktop.core.locate.find_all", return_value=[(250, 58, 60, 24), (50, 60, 60, 24)]):
        assert bot.find_image(str(template), occurrence=1, enumerate_all=True) == (50, 60, 60, 24)
        assert bot.find_image(str(template), occurrence=2) == (250, 58, 60, 24)


# --- --virtual: o cursor não se mexe, e sem volta escondida ao mouse real ----------


def test_virtual_mouse_estrito_nao_usa_o_mouse_real() -> None:
    from visus.desktop.core.virtual_mouse import VirtualMouse

    vm = VirtualMouse({"use_virtual_mouse": True, "virtual_mouse_strict": True})
    vm.virtual_available = True
    with patch.object(vm, "_click_virtual_windows", return_value=False), patch.object(
        vm, "_click_virtual_linux", return_value=False
    ), patch.object(vm, "_click_virtual_macos", return_value=False), patch.object(
        vm, "_click_physical", return_value=True
    ) as physical:
        assert vm.click(10, 10) is False
    physical.assert_not_called()
    assert vm.last_click == "virtual-refused"


def test_virtual_mouse_nao_estrito_continua_com_fallback() -> None:
    from visus.desktop.core.virtual_mouse import VirtualMouse

    vm = VirtualMouse({"use_virtual_mouse": True})
    vm.virtual_available = False
    with patch.object(vm, "_click_physical", return_value=True):
        assert vm.click(10, 10) is True
    assert vm.last_click == "physical"


def _executor():
    from visus.desktop.core.task_executor import TaskExecutor

    return TaskExecutor.__new__(TaskExecutor)


def test_sendtext_apos_clique_virtual_vai_por_mensagens_nao_pelo_teclado() -> None:
    ex = _executor()
    ex.virtual_mouse = MagicMock(last_click="virtual", last_hwnd=4242)
    with patch("visus.desktop.core.virtual_keyboard.send_text", return_value=True) as send, patch(
        "pyautogui.hotkey"
    ) as hotkey, patch("pyperclip.copy") as copy:
        ex._process_sendtext("{ctrl}aolá")
    send.assert_called_once_with(4242, "{ctrl}aolá")
    hotkey.assert_not_called()
    copy.assert_not_called()


def test_sendtext_fisico_devolve_a_area_de_transferencia() -> None:
    ex = _executor()
    ex.virtual_mouse = MagicMock(last_click="physical", last_hwnd=None)
    with patch("pyperclip.paste", return_value="o que a pessoa copiou"), patch(
        "pyperclip.copy"
    ) as copy, patch("pyautogui.hotkey"), patch("time.sleep"):
        ex._process_sendtext("texto")
    assert [c.args[0] for c in copy.call_args_list] == ["texto", "o que a pessoa copiou"]


def test_type_virtual_exige_window() -> None:
    r = runner.invoke(cli, ["type", "olá", "--virtual"])
    assert r.exit_code == 1
    assert "--window" in r.output


def test_send_text_um_wm_char_por_unidade_utf16() -> None:
    from visus.desktop.core import virtual_keyboard

    posted: list[tuple] = []
    fake = types.SimpleNamespace(PostMessage=lambda *a: posted.append(a))
    with patch.dict(sys.modules, {"win32gui": fake}), patch.object(virtual_keyboard, "_post_key") as key, patch.object(
        virtual_keyboard.sys, "platform", "win32"
    ):
        assert virtual_keyboard.send_text(7, "{ctrl}aç😀{enter}") is True
    import win32con

    assert posted[0] == (7, virtual_keyboard._EM_SETSEL, 0, -1)
    assert [p[2] for p in posted[1:]] == [0xE7, 0xD83D, 0xDE00]
    assert all(p[1] == win32con.WM_CHAR for p in posted[1:])
    key.assert_called_once_with(7, win32con.VK_RETURN)


@pytest.mark.parametrize(
    ("argv", "target"),
    [
        (["mouse", "click", "10", "20", "--virtual"], "visus.desktop.cli._common.build_bot"),
        (["text", "click", "Salvar", "--virtual"], "visus.desktop.cli._common.build_bot"),
        (["image", "click", "b.png", "--virtual"], "visus.desktop.cli.commands.image.build_bot"),
    ],
)
def test_flag_virtual_liga_o_mouse_virtual_estrito(argv: list[str], target: str) -> None:
    bot = _fake_bot(click_at=True, click_text=True, click_image=True)
    bot.executor.virtual_mouse.last_click = "virtual"
    with patch(target, return_value=bot) as build:
        r = runner.invoke(cli, argv)
    assert r.exit_code == 0, r.output
    assert build.call_args.kwargs == {"use_virtual_mouse": True, "virtual_mouse_strict": True}
    assert "virtual mouse" in r.output


def test_virtual_recusado_explica_o_que_fazer() -> None:
    bot = _fake_bot(click_text=False)
    bot.executor.virtual_mouse.last_click = "virtual-refused"
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["text", "click", "Salvar", "--virtual"])
    assert r.exit_code == 1
    assert "native click" in r.output


def test_mouse_click_que_falha_nao_diz_clicked() -> None:
    bot = _fake_bot(click_at=False)
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["mouse", "click", "10", "20"])
    assert r.exit_code == 1
    assert "clicked (" not in r.output


# --- --window: busca só na janela --------------------------------------------------


def test_text_find_all_window_vira_regiao() -> None:
    bot = _fake_bot(find_all_text=[])
    with patch("visus.desktop.cli._common.build_bot", return_value=bot), patch(
        "visus.desktop.core.window.window_region", return_value=(100, 50, 800, 600)
    ):
        r = runner.invoke(cli, ["text", "find-all", "Salvar", "--window", "Bloco", "--no-overlay"])
    assert bot.find_all_text.call_args.kwargs["region"] == (100, 50, 800, 600), r.output


def test_window_inexistente_erro_claro() -> None:
    with patch("visus.desktop.core.window.window_region", return_value=None):
        r = runner.invoke(cli, ["text", "click", "Salvar", "--window", "Nada"])
    assert r.exit_code == 1
    assert "window list" in r.output


# --- snapshot sem janela -------------------------------------------------------------


def test_snapshot_sem_janela_e_erro() -> None:
    with patch("visus.desktop.core.native_rpa.native_snapshot_nodes", return_value=(None, [])):
        r = runner.invoke(cli, ["native", "snapshot", "--window", "Nada"])
    assert r.exit_code == 1
    assert "no window" in r.output.lower()


# --- find-all: destaque na tela segue a config -----------------------------------------


def test_find_all_sem_overlay_quando_a_config_desliga(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = _fake_bot(find_all_text=[], show_text_occurrences=[])
    bot.config.show_overlay = False
    with patch("visus.desktop.cli._common.build_bot", return_value=bot):
        r = runner.invoke(cli, ["text", "find-all", "Salvar"])
    assert r.exit_code == 1  # nada achado
    bot.show_text_occurrences.assert_not_called()


# --- OCR: um RapidOCR por processo, sem log de INFO ---------------------------------------


def test_rapidocr_carrega_uma_vez_e_quieto(monkeypatch: pytest.MonkeyPatch) -> None:
    from visus.desktop.core import ocr_engine

    built: list[dict] = []
    fake = types.ModuleType("rapidocr")
    fake.RapidOCR = lambda params=None: built.append(params or {}) or object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rapidocr", fake)
    monkeypatch.setattr(ocr_engine, "_RAPIDOCR_ENGINES", {})
    a = ocr_engine._RapidOCRBackend({"log_level": "INFO"})
    b = ocr_engine._RapidOCRBackend({"log_level": "INFO"})
    assert built == [], "carrega só no 1º uso"
    assert a.engine is b.engine
    # quiet, and without the text-angle classifier (screen text is never upside down)
    assert built == [{"Global.log_level": "warning", "Global.use_cls": False}]


def test_cli_loga_so_warning_por_padrao() -> None:
    from visus.desktop.cli._common import build_bot

    with patch("visus.desktop.VisusBot") as bot_cls:
        build_bot()
    assert bot_cls.call_args.kwargs["config"]["log_level"] == "WARNING"

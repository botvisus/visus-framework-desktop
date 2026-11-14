"""As teclas de navegação vão com a marca de "estendida" (KEYEVENTF_EXTENDEDKEY).

Medido no Excel: sem ela, com o NumLock ligado, o Windows lê a seta como a do teclado
numérico e SOLTA o Shift -- ``key Shift+Right`` andava uma célula em vez de selecionar,
e o agente nunca conseguia selecionar nada pelo teclado."""

from __future__ import annotations

import sys
from typing import Any

import pytest

from visus.desktop.core import human_typing as ht

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="SendInput é do Windows"
)

RIGHT, HOME, DELETE, SHIFT, CTRL, A = 0x27, 0x24, 0x2E, 0x10, 0x11, 0x41


def test_setas_home_delete_sao_estendidas_letras_e_modificadores_nao() -> None:
    for vk in (RIGHT, HOME, DELETE, 0x21, 0x22, 0x23, 0x2D):
        assert ht.key_event(vk, 0)[2] & ht._KEYEVENTF_EXTENDEDKEY, hex(vk)
    for vk in (SHIFT, CTRL, A, 0x0D):
        assert not ht.key_event(vk, 0)[2] & ht._KEYEVENTF_EXTENDEDKEY, hex(vk)


def test_evento_leva_o_scan_code_e_mantem_o_keyup() -> None:
    vk, scan, flags = ht.key_event(RIGHT, ht._KEYEVENTF_KEYUP)
    assert vk == RIGHT and scan == 0x4D, "o scan code da seta direita"
    assert flags & ht._KEYEVENTF_KEYUP


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    """Os eventos que iriam ao Windows, sem apertar nada de verdade."""
    events: list[tuple[int, int]] = []
    monkeypatch.setattr(ht, "_keybd", lambda vk, flags: events.append((vk, flags)))
    return events


def test_pyautogui_shift_right_vira_shift_e_seta_estendida(
    sent: list[tuple[int, int]],
) -> None:
    import pyautogui

    ht.fix_pyautogui_keys()
    pyautogui.hotkey("shift", "right", _pause=False)
    assert [vk for vk, _ in sent] == [SHIFT, RIGHT, RIGHT, SHIFT]
    assert sent[1][1] == 0 and sent[2][1] == ht._KEYEVENTF_KEYUP, "desce e sobe a seta"


def test_caractere_que_pede_shift_continua_com_shift(
    sent: list[tuple[int, int]],
) -> None:
    ht._pyautogui_key("A", up=False)
    assert sent[0] == (SHIFT, 0) and sent[-1] == (SHIFT, ht._KEYEVENTF_KEYUP)


def test_tecla_desconhecida_nao_manda_nada(sent: list[tuple[int, int]]) -> None:
    ht._pyautogui_key("nao-existe", up=False)
    assert sent == []


def test_troca_uma_vez_so() -> None:
    from pyautogui import _pyautogui_win as pwin  # type: ignore[attr-defined]

    ht.fix_pyautogui_keys()
    first: Any = pwin._keyDown
    ht.fix_pyautogui_keys()
    assert pwin._keyDown is first

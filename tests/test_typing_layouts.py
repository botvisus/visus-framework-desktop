"""Digitar certo em qualquer teclado: a tecla de verdade só quando ela é PROVADA no layout
da janela da frente (sozinha ou com Shift, faz exatamente o caractere); o resto -- AltGr,
tecla morta, CapsLock que inverte, caractere que o teclado não tem -- vai pelo Unicode.

O pyautogui mandava Ctrl+Alt+Q para o "/" de um ABNT2 (a Calculadora recebia "4422" em
vez de "44/22") e montava o mapa no layout do script, não no da janela."""

from __future__ import annotations

import ctypes
import sys
from typing import Any

import pytest

from visus.desktop.core import human_typing as ht

windows = pytest.mark.skipif(
    sys.platform != "win32", reason="SendInput/ToUnicodeEx: Windows"
)

# um teclado de mentira: (VkKeyScanEx, o que o ToUnicodeEx faz com Shift/CapsLock)
_LAYOUT = {
    "4": 0x034,  # tecla sozinha
    "A": 0x141,  # Shift + A
    "a": 0x041,
    "/": 0x651,  # Ctrl+Alt (AltGr) + Q: o caso do ABNT2
    "~": 0x0DE,  # tecla morta
}


class _FakeUser32:
    def __init__(self) -> None:
        self.layout_seen: list[Any] = []

    def VkKeyScanExW(self, char: str, layout: Any) -> int:  # noqa: N802
        self.layout_seen.append(layout)
        return _LAYOUT.get(char, -1)

    def MapVirtualKeyExW(self, vk: int, kind: int, layout: Any) -> int:  # noqa: N802
        return vk + 0x100

    def ToUnicodeEx(self, vk, scan, state, out, size, flags, layout) -> int:  # noqa: N802
        assert flags & 0x4, "só consultar: não mexer no estado do teclado"
        if vk == 0xDE:
            return -1  # tecla morta
        shift = bool(state[0x10] & 0x80)
        caps = bool(state[0x14] & 0x01)
        char = chr(vk)
        if char.isalpha():
            char = char.upper() if shift != caps else char.lower()
        out.value = char
        return 1


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeUser32:
    user32 = _FakeUser32()
    monkeypatch.setattr(ht, "_user32", lambda: user32)
    return user32


def test_only_a_proven_key_is_pressed(fake: _FakeUser32) -> None:
    assert ht._real_key("4", 7, caps_lock=False) == (0x34, 0x134, False)
    assert ht._real_key("A", 7, caps_lock=False) == (0x41, 0x141, True)
    assert ht._real_key("/", 7, caps_lock=False) is None, "AltGr: pelo Unicode"
    assert ht._real_key("~", 7, caps_lock=False) is None, "tecla morta: pelo Unicode"
    assert ht._real_key("ж", 7, caps_lock=False) is None, "o teclado não tem: Unicode"
    assert ht._real_key("a", 7, caps_lock=True) is None, "CapsLock inverteria a caixa"
    assert ht._real_key("4", 7, caps_lock=True) == (0x34, 0x134, False)
    assert set(fake.layout_seen) == {7}, "sempre o teclado da janela, nunca o do script"


def test_typing_sends_real_keys_or_unicode(
    fake: _FakeUser32, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pyautogui

    sent: list[Any] = []
    checks: list[int] = []
    monkeypatch.setattr(ht, "_front_layout", lambda: 7)
    monkeypatch.setattr(fake, "GetKeyState", lambda vk: 0, raising=False)
    monkeypatch.setattr(
        ht, "_send_key", lambda vk, scan, shift: sent.append((vk, shift))
    )
    monkeypatch.setattr(ht, "_send_unicode", lambda ch: sent.append(ch))
    monkeypatch.setattr(pyautogui, "press", lambda key, **k: sent.append(f"<{key}>"))
    monkeypatch.setattr(pyautogui, "failSafeCheck", lambda: checks.append(1))
    ht._type_chars_windows("44/A~\n", 0)
    assert sent == [(0x34, False), (0x34, False), "/", (0x41, True), "~", "<enter>"]
    assert len(checks) == 6, "o mouse no canto da tela continua parando a digitação"


def test_type_literally_keeps_tokens_as_text(monkeypatch: pytest.MonkeyPatch) -> None:
    typed: list[str] = []
    monkeypatch.setattr(ht, "_chars", lambda: lambda text, interval: typed.append(text))
    ht.type_literally("a{enter}b\r\nc", 0)
    assert typed == ["a{enter}b\nc"]


@windows
def test_on_a_real_us_layout() -> None:
    """O teclado US (o dos runners do CI): o "/" é uma tecla, o "´" não existe."""
    u = ctypes.WinDLL("user32")  # type: ignore[attr-defined]
    u.LoadKeyboardLayoutW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint]
    u.LoadKeyboardLayoutW.restype = ctypes.c_void_p
    u.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.c_void_p]
    count = u.GetKeyboardLayoutList(0, None)
    loaded = (ctypes.c_void_p * count)()
    u.GetKeyboardLayoutList(count, loaded)
    us = next((h for h in loaded if h and int(h) & 0xFFFFFFFF == 0x04090409), None)
    if us is None:
        pytest.skip("o teclado US não está carregado aqui")
    slash = ht._real_key("/", us, caps_lock=False)
    assert slash is not None and slash[0] == 0xBF and slash[2] is False
    question = ht._real_key("?", us, caps_lock=False)
    assert question is not None and question[2] is True, "? = Shift + /"
    assert ht._real_key("´", us, caps_lock=False) is None
    assert ht._real_key("a", us, caps_lock=True) is None


def test_typing_paths_never_use_pyautogui_typewrite() -> None:
    """Os planos B (sem área de transferência) digitam pelo mesmo caminho certo."""
    from pathlib import Path

    import visus.desktop as desktop

    src = Path(desktop.__file__).parent
    for name in ("__init__.py", "core/keyboard_commands.py", "core/human_typing.py"):
        text = (src / name).read_text(encoding="utf-8")
        assert "pyautogui.typewrite(" not in text, name
        code = [line for line in text.splitlines() if "pyautogui.write(" in line]
        if (
            name == "core/human_typing.py"
        ):  # só o último recurso: sem Windows e sem xdotool
            assert len(code) == 1, code
        else:
            assert not code, (name, code)

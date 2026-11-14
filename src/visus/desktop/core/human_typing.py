"""Digitar como uma pessoa no teclado: uma tecla por caractere, na fila de entrada do
sistema -- nada de área de transferência nem de mensagens para uma janela.

* no Windows, a tecla de verdade (o que jogos, área de trabalho remota e Citrix
  esperam) só quando ela é PROVADA no teclado da janela da frente: a tecla, sozinha ou
  com Shift, faz exatamente aquele caractere ali (``ToUnicodeEx`` no layout dela, com o
  CapsLock de agora). O resto -- AltGr, tecla morta (til, circunflexo, acento agudo),
  CapsLock que inverte, caractere que o teclado não tem -- vai por ``SendInput`` com
  ``KEYEVENTF_UNICODE`` (a mesma fila do teclado físico, independente de idioma e
  layout). O pyautogui mandava Ctrl+Alt+Q para o "/" de um ABNT2 e a Calculadora recebia
  "4422" em vez de "44/22"; e montava o mapa no layout do script, não no da janela;
* no Linux, ``xdotool type`` (Unicode);
* ``\\n`` e ``\\t`` são Enter e Tab, e os marcadores ``{enter}``, ``{tab}``, ``{esc}``,
  ``{backspace}``, ``{del}`` e ``{ctrl}a`` valem em QUALQUER posição do texto.

Colar pela área de transferência entre teclas rápidas atropela (o app ainda não leu o
que foi colado quando o próximo pedaço o substitui): medido no Excel, metade sumia.
"""

from __future__ import annotations

import ctypes
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

__all__ = ["type_like_a_person", "type_literally"]

_TOKENS = {
    "{enter}": "enter",
    "{tab}": "tab",
    "{esc}": "esc",
    "{escape}": "esc",
    "{backspace}": "backspace",
    "{del}": "delete",
    "{delete}": "delete",
}
_SPLIT = re.compile(
    r"(\{ctrl\}a|\{enter\}|\{tab\}|\{esc(?:ape)?\}|\{backspace\}|\{del(?:ete)?\})",
    re.IGNORECASE,
)

# --- Windows: SendInput com KEYEVENTF_UNICODE -------------------------------------------
_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002
_KEYEVENTF_UNICODE = 0x0004


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _INPUTUNION(ctypes.Union):
    # o MOUSEINPUT é o maior membro: sem ele o INPUT fica menor que o do Windows e o
    # SendInput recusa (cbSize errado)
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("u", _INPUTUNION)]


def _send_unicode(char: str) -> None:
    """Uma tecla Unicode (descer e subir); fora do BMP vai como par substituto."""
    data = char.encode("utf-16-le")
    units = [int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2)]
    events = []
    for unit in units:
        for flags in (_KEYEVENTF_UNICODE, _KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP):
            event = _INPUT(type=_INPUT_KEYBOARD)
            event.u.ki = _KEYBDINPUT(0, unit, flags, 0, 0)
            events.append(event)
    array = (_INPUT * len(events))(*events)
    sent = ctypes.windll.user32.SendInput(len(events), array, ctypes.sizeof(_INPUT))  # type: ignore[attr-defined]
    if sent != len(events):
        raise OSError(f"SendInput typed {sent} of {len(events)} events for {char!r}")


_VK_SHIFT = 0x10
_VK_CAPITAL = 0x14
_TOUNICODE_KEEP_STATE = 0x4  # o ToUnicodeEx só consulta: não mexe no estado do teclado
_user32_typed: Any = None


def _user32() -> Any:
    """O user32 com os tipos certos (uma instância própria: o ``ctypes.windll`` é de todos,
    e trocar os tipos dele mudaria o pyautogui e quem mais o usa)."""
    global _user32_typed
    if _user32_typed is None:
        u = ctypes.WinDLL("user32")  # type: ignore[attr-defined]
        u.GetForegroundWindow.restype = ctypes.c_void_p
        u.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        u.GetWindowThreadProcessId.restype = ctypes.c_ulong
        u.GetKeyboardLayout.argtypes = [ctypes.c_ulong]
        u.GetKeyboardLayout.restype = ctypes.c_void_p
        u.VkKeyScanExW.argtypes = [ctypes.c_wchar, ctypes.c_void_p]
        u.VkKeyScanExW.restype = ctypes.c_short
        u.MapVirtualKeyExW.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p]
        u.MapVirtualKeyExW.restype = ctypes.c_uint
        u.ToUnicodeEx.argtypes = [
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.POINTER(ctypes.c_ubyte),
            ctypes.c_wchar_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_void_p,
        ]
        u.ToUnicodeEx.restype = ctypes.c_int
        u.GetKeyState.argtypes = [ctypes.c_int]
        u.GetKeyState.restype = ctypes.c_short
        _user32_typed = u
    return _user32_typed


def _front_layout() -> int | None:
    """O teclado (HKL) da janela da frente -- quem recebe as teclas. Cada janela pode ter
    o seu (o Windows deixa um idioma por app); sem janela, o do script."""
    u = _user32()
    thread = u.GetWindowThreadProcessId(u.GetForegroundWindow(), None)
    layout: int | None = u.GetKeyboardLayout(thread) or u.GetKeyboardLayout(0)
    return layout


def _real_key(
    char: str, layout: int | None, caps_lock: bool
) -> tuple[int, int, bool] | None:
    """``(vk, scan, shift)`` da tecla que faz EXATAMENTE ``char`` nesse teclado, sozinha ou
    com Shift; ``None`` quando não há uma assim (vai pelo Unicode). Conferido com o
    ``ToUnicodeEx``: tecla morta, AltGr, Ctrl e o CapsLock que inverte ficam de fora."""
    if len(char) != 1 or ord(char) > 0xFFFF or not char.isprintable():
        return None
    u = _user32()
    found = int(u.VkKeyScanExW(char, layout))
    if found == -1:
        return None  # esse teclado não tem o caractere
    vk, mods = found & 0xFF, (found >> 8) & 0xFF
    if mods & ~0x01:
        return None  # pede Ctrl, Alt ou AltGr: um app pode ler como atalho
    scan = int(u.MapVirtualKeyExW(vk, 0, layout))  # MAPVK_VK_TO_VSC
    state = (ctypes.c_ubyte * 256)()
    if mods & 0x01:
        state[_VK_SHIFT] = 0x80
    if caps_lock:
        state[_VK_CAPITAL] = 0x01
    out = ctypes.create_unicode_buffer(8)
    made = u.ToUnicodeEx(vk, scan, state, out, 8, _TOUNICODE_KEEP_STATE, layout)
    if made != 1 or out.value[:1] != char:
        return None  # tecla morta (-1), outro caractere, CapsLock trocando a caixa
    return vk, scan, bool(mods & 0x01)


def _send_key(vk: int, scan: int, shift: bool) -> None:
    """A tecla de verdade (com o scan code, que jogos e Citrix leem), Shift em volta se
    precisar -- num SendInput só, sem tecla da pessoa no meio."""
    keys = [(vk, scan)]
    if shift:
        shift_scan = int(_user32().MapVirtualKeyExW(_VK_SHIFT, 0, None))
        keys = [(_VK_SHIFT, shift_scan), *keys]
    events = []
    for code, sc in keys:
        event = _INPUT(type=_INPUT_KEYBOARD)
        event.u.ki = _KEYBDINPUT(code, sc, 0, 0, 0)
        events.append(event)
    for code, sc in reversed(keys):
        event = _INPUT(type=_INPUT_KEYBOARD)
        event.u.ki = _KEYBDINPUT(code, sc, _KEYEVENTF_KEYUP, 0, 0)
        events.append(event)
    array = (_INPUT * len(events))(*events)
    sent = ctypes.windll.user32.SendInput(len(events), array, ctypes.sizeof(_INPUT))  # type: ignore[attr-defined]
    if sent != len(events):
        raise OSError(f"SendInput pressed {sent} of {len(events)} key events")


_KEYEVENTF_EXTENDEDKEY = 0x0001
# as teclas "estendidas": sem a marca, o Windows as lê como as do teclado numérico e,
# com o NumLock ligado, SOLTA o Shift -- medido: o Shift+Right do pyautogui andava uma
# célula no Excel em vez de selecionar
_EXTENDED_VKS = frozenset(
    {
        0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,  # PgUp PgDn End Home setas
        0x2C, 0x2D, 0x2E,  # PrintScreen Insert Delete
        0x5B, 0x5C, 0x5D,  # Win esquerdo/direito, Apps
        0x6F, 0x90,  # / do teclado numérico, NumLock
        0xA3, 0xA5,  # Ctrl e Alt da direita
        *range(0xA6, 0xB8),  # navegador, volume e mídia
    }
)  # fmt: skip


def key_event(vk: int, flags: int) -> tuple[int, int, int]:
    """``(vk, scan, flags)`` de um evento de tecla: o scan code de verdade (jogos e Citrix
    o leem) e a marca de estendida nas teclas que a têm."""
    scan = (
        int(_user32().MapVirtualKeyExW(vk, 0, None)) if sys.platform == "win32" else 0
    )
    return vk, scan, flags | (_KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED_VKS else 0)


def _keybd(vk: int, flags: int) -> None:
    code, scan, all_flags = key_event(vk, flags)
    ctypes.windll.user32.keybd_event(code, scan, all_flags, 0)  # type: ignore[attr-defined]


def _pyautogui_key(key: str, *, up: bool) -> None:
    """O ``_keyDown``/``_keyUp`` do pyautogui no Windows, com scan code e a marca de
    estendida: o original manda setas, Home, End, PgUp/PgDn, Insert e Delete sem ela, e
    com o NumLock ligado o Windows SOLTA o Shift -- o Shift+Right andava em vez de
    selecionar (medido no Excel). Fora isso, igual ao original (o Shift dos caracteres
    que pedem Shift)."""
    import pyautogui
    from pyautogui import _pyautogui_win as pwin  # type: ignore[attr-defined]

    code = pwin.keyboardMapping.get(key)
    if code is None:
        return
    needs_shift = pyautogui.isShiftCharacter(key)
    mods, vk = divmod(code, 0x100)
    held = [
        m
        for on, m in (
            (mods & 4, 0x12),
            (mods & 2, 0x11),
            (mods & 1 or needs_shift, 0x10),
        )
        if on
    ]
    for mod in held:
        _keybd(mod, 0)
    _keybd(vk, _KEYEVENTF_KEYUP if up else 0)
    for mod in reversed(held):
        _keybd(mod, _KEYEVENTF_KEYUP)


def fix_pyautogui_keys() -> None:
    """Troca as teclas do pyautogui no Windows pelas com a marca de estendida (uma vez)."""
    if sys.platform != "win32":
        return
    from pyautogui import _pyautogui_win as pwin  # type: ignore[attr-defined]

    if getattr(pwin, "_visus_extended", False):
        return
    pwin._keyDown = lambda key: _pyautogui_key(key, up=False)
    pwin._keyUp = lambda key: _pyautogui_key(key, up=True)
    pwin._visus_extended = True


def _type_chars_windows(chunk: str, interval: float) -> None:
    import pyautogui

    layout = _front_layout()
    caps_lock = bool(_user32().GetKeyState(_VK_CAPITAL) & 1)
    for char in chunk:
        pyautogui.failSafeCheck()  # o mouse no canto da tela para tudo, como antes
        if char == "\n":
            pyautogui.press("enter", _pause=False)
        elif char == "\t":
            pyautogui.press("tab", _pause=False)
        else:
            key = _real_key(char, layout, caps_lock)
            if key is not None:
                _send_key(*key)
            else:
                _send_unicode(char)
        if interval:
            time.sleep(interval)


def _type_chars_linux(chunk: str, interval: float) -> None:
    # o xdotool digita Unicode e trata "\n"/"\t" como Return/Tab
    delay = str(max(0, int(interval * 1000)))
    subprocess.run(["xdotool", "type", "--delay", delay, "--", chunk], check=True)  # noqa: S603,S607


def _type_chars_fallback(chunk: str, interval: float) -> None:
    import pyautogui

    pyautogui.write(chunk, interval=interval)


def _chars() -> Callable[[str, float], None]:
    if sys.platform == "win32":
        return _type_chars_windows
    if shutil.which("xdotool"):
        return _type_chars_linux
    return _type_chars_fallback


def type_literally(text: str, interval: float = 0.02) -> None:
    """Digita ``text`` como está: só a quebra de linha e o Tab viram Enter/Tab, e
    ``{enter}`` e afins saem como texto -- o que o ``typewrite`` do pyautogui fazia, certo
    em qualquer teclado."""
    _chars()(text.replace("\r\n", "\n"), interval)


def type_like_a_person(text: str, interval: float = 0.02) -> None:
    """Digita ``text`` tecla por tecla, como uma pessoa (ver o módulo)."""
    import pyautogui

    chars = _chars()
    for piece in _SPLIT.split(text.replace("\r\n", "\n")):
        if not piece:
            continue
        token = piece.lower()
        if token == "{ctrl}a":
            pyautogui.hotkey("ctrl", "a", _pause=False)
        elif token in _TOKENS:
            pyautogui.press(_TOKENS[token], _pause=False)
        else:
            chars(piece, interval)
            continue
        if interval:
            time.sleep(interval)

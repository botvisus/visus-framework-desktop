"""Digitar como uma pessoa no teclado: uma tecla por caractere, na fila de entrada do
sistema -- nada de área de transferência nem de mensagens para uma janela.

* letras e símbolos ASCII: a tecla de verdade (``pyautogui``), o que jogos, área de
  trabalho remota e Citrix esperam;
* acentos e o resto do Unicode: no Windows, ``SendInput`` com ``KEYEVENTF_UNICODE``
  (a mesma fila do teclado físico, independente do layout -- o ``typewrite`` do
  pyautogui erra "á" num teclado ABNT2); no Linux, ``xdotool type``;
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

__all__ = ["type_like_a_person"]

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


def _type_chars_windows(chunk: str, interval: float) -> None:
    import pyautogui

    for char in chunk:
        if char == "\n":
            pyautogui.press("enter", _pause=False)
        elif char == "\t":
            pyautogui.press("tab", _pause=False)
        elif char.isascii() and char.isprintable():
            pyautogui.write(
                char, _pause=False
            )  # a tecla de verdade (VK), com Shift se for o caso
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


def type_like_a_person(text: str, interval: float = 0.02) -> None:
    """Digita ``text`` tecla por tecla, como uma pessoa (ver o módulo)."""
    import pyautogui

    if sys.platform == "win32":
        chars = _type_chars_windows
    elif shutil.which("xdotool"):
        chars = _type_chars_linux
    else:
        chars = _type_chars_fallback
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

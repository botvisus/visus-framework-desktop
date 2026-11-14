"""Perguntas baratas ao Windows antes de tocar numa janela.

* ``window_is_pumping`` -- a janela está atendendo mensagens? Um app travado (Excel
  congelado) faz ``ElementFromHandle`` -- o ``WM_GETOBJECT`` por trás do UIA --
  bloquear sem prazo; perguntar antes com ``SendMessageTimeoutW(WM_NULL,
  SMTO_ABORTIFHUNG)`` vira um "o programa não está respondendo" em até 2 s, no lugar
  de esperar o timeout inteiro e devolver ``False`` sem dizer por quê.
* ``passes_window_filter`` -- a janela é uma que a pessoa VÊ: visível, com área, não
  escondida pelo shell (cloaked: UWP suspenso, outra área de trabalho virtual) e não
  janela de ferramenta. Só ``IsWindowVisible`` deixa passar todas essas fantasmas.

Medido no agent-desktop (Vercel Labs, Apache-2.0), ``probes/windows/FINDINGS.md``:
A14-11 (um app que parou de atender trava ``ElementFromHandle`` sem prazo), A21-4
(``SendMessageTimeout`` é o sinal de travamento confiável) e A16-1 (de 147 janelas de
topo, 137 invisíveis, 93 de tamanho zero, 6 cloaked e 51 de ferramenta -- só 66 reais).
"""

from __future__ import annotations

import sys

WM_NULL = 0x0000
SMTO_ABORTIFHUNG = 0x0002
DWMWA_CLOAKED = 14
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080

PUMP_PROBE_MS = 2000


def window_is_pumping(hwnd: int, timeout_ms: int = PUMP_PROBE_MS) -> bool:
    """True se a janela respondeu a um ``WM_NULL`` dentro de ``timeout_ms``.

    Fora do Windows (ou se a chamada nem pôde ser feita) responde True: a pergunta é
    uma proteção, não um portão -- sem ela, segue o caminho de sempre.
    """
    if sys.platform != "win32" or not hwnd:
        return True
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        # uma janela que não existe não está "travada": quem pergunta trata a ausência
        # (separar as duas evita mandar alguém esperar por uma janela que fechou)
        if not user32.IsWindow(ctypes.c_void_p(int(hwnd))):
            return True
        user32.SendMessageTimeoutW.argtypes = [
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
            wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t),
        ]
        user32.SendMessageTimeoutW.restype = ctypes.c_ssize_t
        answer = ctypes.c_size_t(0)
        sent = user32.SendMessageTimeoutW(
            int(hwnd), WM_NULL, 0, 0, SMTO_ABORTIFHUNG, max(1, int(timeout_ms)),
            ctypes.byref(answer),
        )
        return bool(sent)
    except Exception:  # pragma: no cover - defensivo: sem ctypes, sem proteção
        return True


def is_cloaked(hwnd: int) -> bool:
    """A janela está escondida pelo shell (DWM "cloaked")?"""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        import ctypes

        value = ctypes.c_int(0)
        hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(  # type: ignore[attr-defined]
            ctypes.c_void_p(int(hwnd)), DWMWA_CLOAKED, ctypes.byref(value), ctypes.sizeof(value)
        )
        return hr == 0 and value.value != 0
    except Exception:  # pragma: no cover - defensivo
        return False


def is_tool_window(hwnd: int) -> bool:
    """A janela tem ``WS_EX_TOOLWINDOW`` (paleta flutuante, sombra, bandeja)?"""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        import ctypes

        style = ctypes.windll.user32.GetWindowLongW(  # type: ignore[attr-defined]
            ctypes.c_void_p(int(hwnd)), GWL_EXSTYLE
        )
        return bool(style & WS_EX_TOOLWINDOW)
    except Exception:  # pragma: no cover - defensivo
        return False


def passes_window_filter(
    *, visible: bool, width: int, height: int, cloaked: bool, tool: bool
) -> bool:
    """A regra (pura) de uma janela que a pessoa vê -- o filtro A16-1."""
    return visible and width > 0 and height > 0 and not cloaked and not tool

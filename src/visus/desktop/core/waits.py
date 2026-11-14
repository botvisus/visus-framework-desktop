"""Esperas de que um agente precisa entre um passo e outro: uma janela aparecer/sumir e um
menu abrir/fechar.

Depois de "Salvar como" o próximo passo é o diálogo; depois de abrir um menu, os itens
dele. Agir antes disso clica no vazio. Ambas são consultas repetidas com prazo (o próprio
agent-desktop mede que esperar por evento do UIA não é confiável e faz o mesmo).

``menu_open(pid)`` junta três sinais, qualquer um basta:

1. o Windows diz que a thread de interface do programa está em modo de menu
   (``GetGUIThreadInfo``: ``GUI_INMENUMODE`` / ``GUI_POPUPMENUMODE``) -- menus clássicos;
2. uma janela de menu clássica (classe ``#32768``) visível do programa;
3. um elemento UIA do tipo ``Menu`` no topo, do programa, ou um ``Menu``/``MenuItem``
   dentro de uma janela popup (de ferramenta) dele -- menus WPF/WinUI/Chromium.

Ideia do agent-desktop (Vercel Labs, Apache-2.0): ``system/menu/menu_state.rs`` (o
predicado de várias fontes) e ``wait --menu`` / ``wait --window``.
"""

from __future__ import annotations

import sys
import time

GUI_INMENUMODE = 0x0004
GUI_POPUPMENUMODE = 0x0010
_MENU_CLASS = "#32768"
POLL = 0.1


def _thread_in_menu_mode(tid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
            ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
            ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
            ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
            ("rcCaret", wintypes.RECT),
        ]

    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(GUITHREADINFO)
    if not ctypes.windll.user32.GetGUIThreadInfo(int(tid), ctypes.byref(info)):  # type: ignore[attr-defined]
        return False
    return bool(info.flags & (GUI_INMENUMODE | GUI_POPUPMENUMODE))


def _top_windows_of(pid: int) -> list[tuple[int, int, str]]:
    """``(hwnd, tid, classe)`` das janelas de topo VISÍVEIS do processo."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32  # type: ignore[attr-defined]
    found: list[tuple[int, int, str]] = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _each(hwnd, _):
        owner = wintypes.DWORD(0)
        tid = user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, buf, 64)
            found.append((int(hwnd), int(tid), buf.value))
        return True

    user32.EnumWindows(proc(_each), 0)
    return found


def _window_has_open_menu(hwnds: list[int]) -> bool:
    """Um ``Menu`` visível dentro de uma janela do programa. ``Menu`` (não ``MenuBar`` nem
    ``MenuItem``, que a barra de menus tem sempre) só existe com um menu ABERTO: o flyout do
    WinUI abre numa janela ``PopupWindowSiteBridge`` (com título "PopupHost", sem
    ``WS_EX_TOOLWINDOW``) e aparece também sob a janela principal -- medido no Bloco de
    Notas do Windows 11."""
    try:
        from pywinauto.uia_defines import IUIA

        iuia = IUIA()
        dll = iuia.UIA_dll
        client = iuia.iuia
        condition = client.CreateAndCondition(
            client.CreatePropertyCondition(dll.UIA_ControlTypePropertyId, dll.UIA_MenuControlTypeId),
            client.CreatePropertyCondition(dll.UIA_IsOffscreenPropertyId, False),
        )
        for hwnd in hwnds:
            try:
                element = client.ElementFromHandle(hwnd)
                if bool(element.FindFirst(dll.TreeScope_Subtree, condition)):
                    return True
            except Exception:
                continue
    except Exception:
        return False
    return False


def _uia_menu_on_top(pid: int) -> bool:
    try:
        from pywinauto.uia_defines import IUIA

        iuia = IUIA()
        dll = iuia.UIA_dll
        client = iuia.iuia
        condition = client.CreateAndCondition(
            client.CreatePropertyCondition(dll.UIA_ProcessIdPropertyId, int(pid)),
            client.CreatePropertyCondition(dll.UIA_ControlTypePropertyId, dll.UIA_MenuControlTypeId),
        )
        found = client.GetRootElement().FindFirst(dll.TreeScope_Children, condition)
        return bool(found)  # "não achou" volta como ponteiro COM NULO, não None
    except Exception:
        return False


def menu_open(pid: int | None) -> bool:
    """Algum menu do programa ``pid`` está aberto agora?"""
    if sys.platform != "win32" or not pid:
        return False
    try:
        windows = _top_windows_of(int(pid))
    except Exception:
        windows = []
    if any(cls == _MENU_CLASS for _, _, cls in windows):
        return True
    if any(_thread_in_menu_mode(tid) for tid in {tid for _, tid, _ in windows}):
        return True
    if _uia_menu_on_top(int(pid)):
        return True
    from .win_health import is_tool_window, window_is_pumping

    # popups primeiro (de ferramenta / os que não são a janela principal), e só janelas
    # que atendem: ler a árvore de uma janela travada bloquearia
    ordered = sorted((h for h, _, _ in windows), key=lambda h: not is_tool_window(h))
    return _window_has_open_menu([h for h in ordered if window_is_pumping(h, 500)])


def wait_menu(pid: int | None, *, open: bool = True, timeout: float = 5.0) -> bool:  # noqa: A002
    """Espera um menu do programa abrir (``open``) ou fechar. True quando aconteceu."""
    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        if menu_open(pid) == open:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL)


def wait_window(title: str, *, gone: bool = False, timeout: float = 10.0) -> str | None | bool:
    """Espera uma janela com ``title`` (pedaço do título) aparecer -- devolve o título
    dela, ou None no prazo -- ou, com ``gone``, sumir -- devolve True/False."""
    from .window import find_window

    deadline = time.monotonic() + max(0.0, timeout)
    while True:
        hwnd = find_window(title)
        if gone and not hwnd:
            return True
        if not gone and hwnd:
            return _title_of(hwnd) or title
        if time.monotonic() >= deadline:
            return False if gone else None
        time.sleep(POLL)


def _title_of(hwnd: int) -> str:
    try:
        import win32gui

        return str(win32gui.GetWindowText(int(hwnd)) or "")
    except Exception:
        return ""


def window_pid(title: str) -> int | None:
    """O processo da janela com ``title`` (pedaço do título), ou None."""
    from .window import _window_pid, find_window

    hwnd = find_window(title)
    return int(_window_pid(hwnd)) if hwnd else None

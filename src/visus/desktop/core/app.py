"""Visus Desktop - ``use_app``: o programa na frente, aberto se estiver fechado.

Uma automação que passa por vários programas (Excel → Word → Excel) chama ``use_app``
na hora de trocar: acha uma janela aberta do programa e a traz para a frente; se não
houver, abre (o programa ou um arquivo) e espera a janela ficar pronta. Devolve a
:class:`AppWindow` -- passada como ``window=`` aos ``native_*``, prende a ação NAQUELE
handle, seja qual for o título (um Excel aberto em branco é "Pasta1 - Excel", não o
"vendas.xlsx - Excel" da captura).
"""

from __future__ import annotations

import ntpath
import os
import time

from . import process as _process
from . import window as _w

# ganchos de tempo (os testes simulam o relógio)
_sleep = time.sleep
_now = time.monotonic

_LOOK_INTERVAL = 0.5  # entre as olhadas na janela que está abrindo
_STEADY_LOOKS = 3  # título igual em 3 olhadas seguidas = janela pronta


class UseAppError(RuntimeError):
    """O programa não pôde ser achado, trazido para a frente ou aberto."""


class AppWindow(str):
    """A janela do programa: o título vivo (é um ``str``) + ``hwnd``, ``pid`` e
    ``opened`` (abriu agora?). Passada como ``window=`` aos ``native_*``, eles se
    prendem ao ``hwnd``."""

    hwnd: int
    pid: int
    opened: bool

    def __new__(cls, title: str, *, hwnd: int, pid: int, opened: bool) -> AppWindow:
        obj = super().__new__(cls, title)
        obj.hwnd = int(hwnd)
        obj.pid = int(pid)
        obj.opened = bool(opened)
        return obj

    def __repr__(self) -> str:
        return (
            f"AppWindow({str(self)!r}, hwnd={self.hwnd}, pid={self.pid}, "
            f"opened={self.opened})"
        )


def _is_app_id(app: str) -> bool:
    """Id de app empacotado (AUMID): ``Família_hash!App`` -- tem ``!``, não é caminho."""
    return "!" in app and "\\" not in app and "/" not in app


def _exe_name(app: str) -> str:
    return ntpath.basename(app.replace("/", "\\"))


def _find(app: str | None, window: str | None) -> tuple[int, str, int] | None:
    """A melhor janela visível do programa: ``(hwnd, título, pid)`` ou None.

    exe → processo com o MESMO nome (igualdade: ``calc.exe`` não casa
    ``calcengine.exe``); id de app → janelas daquele app; só ``window`` → título.
    Com ``window``, prefere o título exato › prefixo › substring › qualquer uma do
    programa, mantendo a ordem Z como desempate."""
    entries = _w._enum_visible_windows()
    if app is None:
        needle = (window or "").lower()
        hits = [e for e in entries if needle and needle in e[1].lower()]
    elif _is_app_id(app):
        hits = [e for e in entries if e[1] and _w.window_app_id(e[0]) == app]
    else:
        exe = _exe_name(app).lower()
        hits = [e for e in entries if e[1] and _w._process_name(e[2]).lower() == exe]
    if window:
        hits.sort(key=lambda e: _w._title_rank(e[1], window))  # estável: ordem Z
    return hits[0] if hits else None


def _front(hwnd: int, *, timeout: float = 3.0) -> bool:
    """Restaura (se minimizada), traz para a frente e CONFERE que ficou em foco."""
    import win32gui

    deadline = _now() + timeout
    while True:
        if win32gui.IsIconic(hwnd):
            _w._restore(hwnd)
        _w._bring_to_front(hwnd)
        if int(win32gui.GetForegroundWindow() or 0) == int(hwnd):
            return True
        if _now() >= deadline:
            return False
        _sleep(0.25)


def _open(app: str, file: str | None) -> None:
    """Abre ``file`` (no programa padrão dele) ou o programa: id de app por
    ``shell:AppsFolder``; exe pelo caminho e, se o caminho não existe nesta
    máquina, pelo nome (o App Paths do Windows acha ``EXCEL.EXE``)."""
    if file:
        if not os.path.exists(file):
            raise UseAppError(f"File not found: {file}")
        target = file
    elif _is_app_id(app):
        target = "shell:AppsFolder\\" + app
    elif os.path.exists(app):
        target = app
    else:
        target = _exe_name(app)
    try:
        _process.launch(target)
    except OSError as exc:
        raise UseAppError(f"Could not open '{app}': {exc}") from exc


def _wait_ready(app: str, window: str | None, timeout: float, label: str) -> AppWindow:
    """Espera a janela do programa aparecer, vir para a frente e o título parar de
    mudar (a tela "Opening - Excel" troca de título)."""
    deadline = _now() + timeout
    seen: tuple[int, str] | None = None
    steady = 0
    while True:
        hit = _find(app, window)
        if hit is not None and _front(hit[0], timeout=0.0):
            steady = steady + 1 if (hit[0], hit[1]) == seen else 1
            seen = (hit[0], hit[1])
            if steady >= _STEADY_LOOKS:
                return AppWindow(hit[1], hwnd=hit[0], pid=hit[2], opened=True)
        else:
            seen, steady = None, 0
        if _now() >= deadline:
            raise UseAppError(
                f"'{label}' was opened but its window did not show up within {timeout}s"
            )
        _sleep(_LOOK_INTERVAL)


def use_app(
    app: str | None = None,
    *,
    window: str | None = None,
    file: str | None = None,
    timeout: float = 30.0,
) -> AppWindow:
    """Traz o programa para a frente; se estiver fechado, abre e espera ficar pronto.

    Args:
        app: o que identifica e abre o programa -- caminho do exe, nome do exe
            (``"EXCEL.EXE"``) ou id de app empacotado
            (``"Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"``). ``None``: só pelo
            ``window`` (traz para a frente; não sabe abrir).
        window: título (ou parte) preferido entre as janelas do programa; sem
            nenhuma com ele, serve qualquer janela do programa.
        file: documento a abrir quando o programa estiver fechado.
        timeout: segundos para a janela aparecer depois de abrir.

    Returns:
        AppWindow: a janela (título vivo, ``hwnd``, ``pid``, ``opened``).

    Raises:
        UseAppError: não achou e não pôde abrir, a janela não apareceu no prazo, o
            ``file`` não existe, ou a janela achada não veio para a frente.
    """
    if app is None and not window:
        raise ValueError("use_app needs an app, a window title, or both")
    hit = _find(app, window)
    if hit is not None:
        hwnd, title, pid = hit
        if not _front(hwnd):
            raise UseAppError(f"'{title}' was found but did not come to the front")
        return AppWindow(title, hwnd=hwnd, pid=pid, opened=False)
    if app is None:
        raise UseAppError(f"'{window}' is not open - open it before running")
    _open(app, file)
    return _wait_ready(app, window, timeout, window or _exe_name(app))

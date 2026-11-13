"""``use_app``: traz o programa para a frente e, se estiver fechado, abre e espera.

Uma área de trabalho simulada (janelas, processos, ids de app, relógio, ``launch`` e o
"trazer para frente") -- nada toca a tela de verdade.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from visus.desktop.core import app as app_mod
from visus.desktop.core import process, window
from visus.desktop.core.app import AppWindow, UseAppError, use_app

CALC = "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"


class FakeDesktop:
    """Janelas ``(hwnd, título, pid)`` em ordem Z + processo e id de app por pid/hwnd."""

    def __init__(self) -> None:
        self.windows: list[tuple[int, str, int]] = []
        self.procs: dict[int, str] = {}
        self.app_ids: dict[int, str] = {}
        self.launched: list[str] = []
        self.fronted: list[int] = []
        self.front_ok = True
        self.now = 0.0
        self.on_sleep: list[Callable[[], None]] = []  # um passo da "vida" por sleep
        self.on_launch: Callable[[str], None] | None = None

    def add(self, hwnd: int, title: str, pid: int, proc: str, app_id: str = "") -> None:
        self.windows.append((hwnd, title, pid))
        self.procs[pid] = proc
        if app_id:
            self.app_ids[hwnd] = app_id

    def retitle(self, hwnd: int, title: str) -> None:
        self.windows = [(h, title if h == hwnd else t, p) for h, t, p in self.windows]

    # ganchos
    def launch(self, target: str) -> None:
        self.launched.append(target)
        if self.on_launch is not None:
            self.on_launch(target)

    def front(self, hwnd: int, *, timeout: float = 3.0) -> bool:
        self.fronted.append(hwnd)
        return self.front_ok

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        if self.on_sleep:
            self.on_sleep.pop(0)()


@pytest.fixture
def desk(monkeypatch: pytest.MonkeyPatch) -> FakeDesktop:
    d = FakeDesktop()
    monkeypatch.setattr(window, "_enum_visible_windows", lambda: list(d.windows))
    monkeypatch.setattr(window, "_process_name", lambda pid: d.procs.get(pid, ""))
    monkeypatch.setattr(window, "window_app_id", lambda hwnd: d.app_ids.get(hwnd, ""))
    monkeypatch.setattr(process, "launch", d.launch)
    monkeypatch.setattr(app_mod, "_front", d.front)
    monkeypatch.setattr(app_mod, "_sleep", d.sleep)
    monkeypatch.setattr(app_mod, "_now", lambda: d.now)
    return d


def _opens_as(desk: FakeDesktop, hwnd: int, title: str, pid: int, proc: str) -> None:
    """O próximo ``launch`` faz a janela aparecer (já com o título final)."""
    desk.on_launch = lambda _target: desk.add(hwnd, title, pid, proc)


# -- achar o que já está aberto ------------------------------------------------------
def test_use_app_finds_by_process_and_prefers_the_title(desk: FakeDesktop) -> None:
    desk.add(1, "Pasta1 - Excel", 10, "EXCEL.EXE")
    desk.add(2, "vendas.xlsx - Excel", 10, "EXCEL.EXE")
    got = use_app("EXCEL.EXE", window="vendas.xlsx - Excel")
    assert (got, got.hwnd) == ("vendas.xlsx - Excel", 2)


def test_use_app_two_windows_no_title_match_takes_first(desk: FakeDesktop) -> None:
    desk.add(1, "Pasta1 - Excel", 10, "EXCEL.EXE")
    desk.add(2, "Pasta2 - Excel", 10, "EXCEL.EXE")
    got = use_app(r"C:\Office\EXCEL.EXE", window="vendas.xlsx - Excel")
    assert got.hwnd == 1  # nenhuma com o título: a primeira em ordem Z
    assert desk.launched == []


def test_use_app_process_match_is_exact_not_substring(desk: FakeDesktop) -> None:
    desk.add(1, "Motor", 10, "calcengine.exe")
    _opens_as(desk, 2, "Calc", 20, "calc.exe")
    desk.on_sleep = [lambda: None] * 5
    got = use_app("calc.exe")
    assert got.hwnd == 2
    assert desk.launched == ["calc.exe"]


def test_use_app_found_brings_to_front_and_is_not_opened(desk: FakeDesktop) -> None:
    desk.add(1, "Pasta1 - Excel", 10, "EXCEL.EXE")
    got = use_app("EXCEL.EXE")
    assert got.opened is False
    assert desk.fronted == [1]
    assert desk.launched == []


def test_use_app_found_but_not_in_front_fails(desk: FakeDesktop) -> None:
    desk.add(1, "Pasta1 - Excel", 10, "EXCEL.EXE")
    desk.front_ok = False
    with pytest.raises(UseAppError, match="'Pasta1 - Excel' was found but did not come to"):
        use_app("EXCEL.EXE")


def test_use_app_finds_packaged_app_by_app_id(desk: FakeDesktop) -> None:
    desk.add(1, "Calculadora", 10, "ApplicationFrameHost.exe", app_id=CALC)
    desk.add(2, "Configurações", 10, "ApplicationFrameHost.exe", app_id="Other!App")
    got = use_app(CALC, window="Calculadora")
    assert got.hwnd == 1


# -- abrir o que está fechado ----------------------------------------------------------
def test_use_app_opens_by_path_then_waits(desk: FakeDesktop, tmp_path: Path) -> None:
    exe = tmp_path / "EXCEL.EXE"
    exe.write_text("")
    _opens_as(desk, 5, "Pasta1 - Excel", 50, "EXCEL.EXE")
    desk.on_sleep = [lambda: None] * 5
    got = use_app(str(exe), window="vendas.xlsx - Excel")
    assert desk.launched == [str(exe)]
    assert (got, got.hwnd, got.pid, got.opened) == ("Pasta1 - Excel", 5, 50, True)


def test_use_app_missing_path_falls_back_to_exe_name(desk: FakeDesktop) -> None:
    _opens_as(desk, 5, "Pasta1 - Excel", 50, "EXCEL.EXE")
    desk.on_sleep = [lambda: None] * 5
    use_app(r"C:\nao\existe\EXCEL.EXE")
    assert desk.launched == ["EXCEL.EXE"]


def test_use_app_opens_the_file_when_given(desk: FakeDesktop, tmp_path: Path) -> None:
    doc = tmp_path / "vendas.xlsx"
    doc.write_text("")
    _opens_as(desk, 5, "vendas.xlsx - Excel", 50, "EXCEL.EXE")
    desk.on_sleep = [lambda: None] * 5
    got = use_app("EXCEL.EXE", window="vendas.xlsx - Excel", file=str(doc))
    assert desk.launched == [str(doc)]
    assert got.opened is True


def test_use_app_missing_file_fails_before_opening(desk: FakeDesktop) -> None:
    with pytest.raises(UseAppError, match=r"File not found: C:\\nao\\vendas.xlsx"):
        use_app("EXCEL.EXE", file=r"C:\nao\vendas.xlsx")
    assert desk.launched == []


def test_use_app_store_app_opens_by_shell_apps_folder(desk: FakeDesktop) -> None:
    desk.on_launch = lambda _t: desk.add(
        7, "Calculadora", 70, "ApplicationFrameHost.exe", app_id=CALC
    )
    desk.on_sleep = [lambda: None] * 5
    got = use_app(CALC, window="Calculadora")
    assert desk.launched == ["shell:AppsFolder\\" + CALC]
    assert got.hwnd == 7


def test_use_app_launch_error_is_a_use_app_error(desk: FakeDesktop) -> None:
    def boom(_target: str) -> None:
        raise OSError("no association")

    desk.on_launch = boom
    with pytest.raises(UseAppError, match="Could not open 'nada.exe': no association"):
        use_app("nada.exe")


def test_use_app_title_only_not_open_fails(desk: FakeDesktop) -> None:
    with pytest.raises(UseAppError, match="'Calculadora' is not open - open it before"):
        use_app(window="Calculadora")
    assert desk.launched == []


def test_use_app_title_only_open_is_found(desk: FakeDesktop) -> None:
    desk.add(1, "Calculadora", 10, "ApplicationFrameHost.exe")
    assert use_app(window="Calculadora").hwnd == 1


def test_use_app_window_never_shows_up_fails(desk: FakeDesktop) -> None:
    desk.on_sleep = [lambda: None] * 100
    with pytest.raises(UseAppError, match=r"did not show up within 2\.0s"):
        use_app("EXCEL.EXE", window="Excel", timeout=2.0)
    assert desk.launched == ["EXCEL.EXE"]


def test_use_app_waits_for_a_steady_title(desk: FakeDesktop) -> None:
    _opens_as(desk, 5, "Opening - Excel", 50, "EXCEL.EXE")
    desk.on_sleep = [lambda: desk.retitle(5, "Pasta1 - Excel")] + [lambda: None] * 5
    got = use_app("EXCEL.EXE")
    assert got == "Pasta1 - Excel"


def test_use_app_needs_app_or_window() -> None:
    with pytest.raises(ValueError):
        use_app()


def test_app_window_is_a_str_with_handle() -> None:
    win = AppWindow("Pasta1 - Excel", hwnd=10, pid=20, opened=True)
    assert win == "Pasta1 - Excel"
    assert isinstance(win, str)
    assert (win.hwnd, win.pid, win.opened) == (10, 20, True)

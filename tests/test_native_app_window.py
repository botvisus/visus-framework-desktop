"""``native_*(window=<AppWindow>)``: a ação se prende ao HANDLE da janela do ``use_app``.

O título capturado ("vendas.xlsx - Excel") pode não existir quando o script abre o
programa em branco ("Pasta1 - Excel"): com a ``AppWindow`` o título não importa. Handle
morto (a janela fechou) cai para o título, como antes. Sem UIA de verdade.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pywinauto")

import pywinauto

from visus.desktop.core import locators, native_rpa
from visus.desktop.core.app import AppWindow


class _Spec:
    def __init__(self, handle: int) -> None:
        self.handle = handle

    def exists(self, timeout: float = 0) -> bool:
        return True


class _Desktop:
    def __init__(self, backend: str = "uia") -> None:
        self.backend = backend

    def window(self, *, handle: int) -> _Spec:
        return _Spec(handle)


@pytest.fixture
def titles(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Os títulos procurados por ``find_window_handle`` (que devolve 99)."""
    asked: list[str] = []

    def find(title: str) -> int:
        asked.append(title)
        return 99

    monkeypatch.setattr(pywinauto, "Desktop", _Desktop)
    monkeypatch.setattr(locators, "find_window_handle", find)
    return asked


def test_app_window_binds_to_its_handle(
    titles: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_rpa, "_is_window", lambda hwnd: True)
    win = AppWindow("Pasta1 - Excel", hwnd=10, pid=20, opened=True)
    top = native_rpa._connect_top(win, None, 1.0)
    assert top.handle == 10
    assert titles == []  # nem procurou pelo título


def test_dead_handle_falls_back_to_the_title(
    titles: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(native_rpa, "_is_window", lambda hwnd: False)
    win = AppWindow("Pasta1 - Excel", hwnd=10, pid=20, opened=False)
    top = native_rpa._connect_top(win, None, 1.0)
    assert top.handle == 99
    assert titles == ["Pasta1 - Excel"]


def test_plain_title_is_unchanged(titles: list[str]) -> None:
    top = native_rpa._connect_top("Calculadora", None, 1.0)
    assert top.handle == 99
    assert titles == ["Calculadora"]

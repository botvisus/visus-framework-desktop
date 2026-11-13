"""Antes do teclado, a janela do use_app vale pelo PROGRAMA na frente: o Excel troca a
tela inicial ("Microsoft Excel") pela pasta ("Book1 - Excel") e é o mesmo programa."""

from __future__ import annotations

import pytest

import visus.desktop as vd
from visus.desktop.core import app as core_app
from visus.desktop.core import window as core_window


def test_use_app_window_is_checked_by_its_program(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[object] = []
    monkeypatch.setattr(
        core_window,
        "front_program",
        lambda pid, **k: seen.append(pid) or "Book1 - Excel",
    )
    monkeypatch.setattr(
        core_window, "front_window", lambda *a, **k: None
    )  # o título já não bate
    excel = core_app.AppWindow("Microsoft Excel", hwnd=10, pid=4321, opened=True)
    assert vd._window_in_front(excel) is True
    assert seen == [4321]


def test_a_title_typed_by_hand_is_still_checked_by_title(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []
    monkeypatch.setattr(
        core_window, "front_program", lambda *a, **k: called.append("program")
    )
    monkeypatch.setattr(
        core_window, "front_window", lambda title, **k: called.append(title)
    )
    assert vd._window_in_front("Bloco de Notas") is False
    assert called == ["Bloco de Notas"]


def test_another_program_in_front_sends_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_window, "front_program", lambda pid, **k: None)
    excel = core_app.AppWindow("Microsoft Excel", hwnd=10, pid=4321, opened=True)
    assert vd._window_in_front(excel) is False

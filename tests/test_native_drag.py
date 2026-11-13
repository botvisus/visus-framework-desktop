"""``native_drag`` e ``native_click(at=)``: o mouse de verdade num ponto DENTRO do controle.

Os pontos são deslocamentos a partir do canto superior esquerdo do controle — o arrasto
segue o controle onde a janela estiver (desenhar no Paint, mover um slider). Sem UIA nem
mouse de verdade: o controle e o mouse são simulados.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from visus.desktop.cli import cli
from visus.desktop.core import native_rpa


class _Ctrl:
    def exists(self, timeout: float = 0) -> bool:
        return True

    def rectangle(self) -> SimpleNamespace:
        return SimpleNamespace(left=100, top=200, right=900, bottom=700)

    def click_input(self, **kw: object) -> None:
        raise AssertionError("with at= the click is at the point, not the center")

    def invoke(self) -> None:
        raise AssertionError("with at= the click is at the point, not invoke")


@pytest.fixture
def mouse(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    calls: dict[str, list] = {"drag": [], "click": [], "wheel": []}

    class _Top:
        def child_window(self, **kwargs: object) -> _Ctrl:
            return _Ctrl()

    monkeypatch.setattr(native_rpa, "_ensure_pywinauto", lambda: True)
    monkeypatch.setitem(native_rpa._last_mouse_target, "rect", (100, 200, 900, 700))
    monkeypatch.setattr(native_rpa, "_connect_top", lambda *a, **k: _Top())
    monkeypatch.setattr(native_rpa, "_on_target", lambda ctrl, highlight=True: None)
    monkeypatch.setattr(
        native_rpa, "_mouse_drag", lambda src, dst, button, duration: calls["drag"].append(
            (src, dst, button, duration)
        )
    )
    monkeypatch.setattr(
        native_rpa, "_mouse_click", lambda point, button, clicks: calls["click"].append(
            (point, button, clicks)
        )
    )
    monkeypatch.setattr(
        native_rpa, "_wheel", lambda point, amount: calls["wheel"].append((point, amount))
    )
    return calls


def test_drag_goes_from_start_to_end_inside_the_control(mouse: dict[str, list]) -> None:
    assert native_rpa.native_drag(window="Paint", auto_id="canvas", start=(40, 30), end=(240, 130))
    assert mouse["drag"] == [((140, 230), (340, 330), "left", 0.4)]


def test_click_at_a_point_inside_the_control(mouse: dict[str, list]) -> None:
    assert native_rpa.native_click(window="Paint", auto_id="canvas", at=(10, 20))
    assert native_rpa.native_click(window="Paint", auto_id="canvas", at=(10, 20), double=True)
    assert mouse["click"] == [((110, 220), "left", 1), ((110, 220), "left", 2)]


def test_drag_points_are_offsets_from_the_corner() -> None:
    assert native_rpa._drag_points((5, 7), (1, 2), (3, 4)) == ((6, 9), (8, 11))


def test_cli_native_drag(mouse: dict[str, list]) -> None:
    result = CliRunner().invoke(
        cli,
        ["native", "drag", "--window", "Paint", "--auto-id", "canvas",
         "--start", "40,30", "--end", "240,130", "--json"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) is True
    assert mouse["drag"][0][:2] == ((140, 230), (340, 330))


def test_cli_native_drag_needs_x_comma_y(mouse: dict[str, list]) -> None:
    result = CliRunner().invoke(
        cli, ["native", "drag", "--auto-id", "c", "--start", "40", "--end", "1,1"]
    )
    assert result.exit_code != 0
    assert "X,Y" in result.output


def test_mcp_native_drag_passes_the_points() -> None:
    from visus.desktop import mcp_server as server

    with patch("visus.desktop.core.native_rpa.native_drag", return_value=True) as drag:
        assert server.native_drag(start=[1, 2], end=[3, 4], window="Paint", auto_id="c")
    assert drag.call_args.kwargs["start"] == (1, 2)
    assert drag.call_args.kwargs["end"] == (3, 4)


def test_scroll_at_the_center_or_at_a_point(mouse: dict[str, list]) -> None:
    assert native_rpa.native_scroll(window="Paint", auto_id="canvas", amount=-3)
    assert native_rpa.native_scroll(window="Paint", auto_id="canvas", amount=2, at=(10, 20))
    assert mouse["wheel"] == [((500, 450), -3), ((110, 220), 2)]


def test_cli_native_scroll(mouse: dict[str, list]) -> None:
    result = CliRunner().invoke(
        cli, ["native", "scroll", "--auto-id", "canvas", "--amount", "-2", "--json"]
    )
    assert result.exit_code == 0, result.output
    assert mouse["wheel"] == [((500, 450), -2)]


def test_drag_coming_from_another_control_clicks_its_start_first(
    mouse: dict[str, list], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tela do Paint gasta o 1º aperto depois de o mouse agir na faixa de ferramentas."""
    monkeypatch.setitem(native_rpa._last_mouse_target, "rect", (480, 70, 510, 98))  # a Oval
    monkeypatch.setattr(native_rpa.time, "sleep", lambda s: None)
    native_rpa.native_drag(window="Paint", auto_id="canvas", start=(40, 30), end=(240, 130))
    assert mouse["click"] == [((140, 230), "left", 1)]  # a ativação, no ponto de início
    assert mouse["drag"][0][:2] == ((140, 230), (340, 330))
    # o 2º arrasto na mesma tela já não ganha o clique extra
    native_rpa.native_drag(window="Paint", auto_id="canvas", start=(400, 30), end=(500, 130))
    assert len(mouse["click"]) == 1

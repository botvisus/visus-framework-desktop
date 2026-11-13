"""``window_app_id``: o id (AUMID) do app empacotado dono de uma janela.

A Calculadora e os outros apps da loja rodam dentro do ``ApplicationFrameHost.exe``,
que hospeda todos eles: o id certo está no processo da ``CoreWindow`` filha. Um app
empacotado comum (o Bloco de Notas do Windows 11) tem o id no próprio processo.
Sem Win32 de verdade: os três ganchos são simulados.
"""

from __future__ import annotations

from unittest.mock import patch

from visus.desktop.core import window as w

CALC = "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"


def test_app_id_of_uwp_frame_reads_the_corewindow_process() -> None:
    with patch.object(w, "_frame_child_pid", return_value=42), patch.object(
        w, "_window_pid", return_value=7
    ), patch.object(w, "_process_app_id", return_value=CALC) as app_id:
        assert w.window_app_id(100) == CALC
    app_id.assert_called_once_with(42)


def test_app_id_of_packaged_desktop_app_reads_its_own_process() -> None:
    notepad = "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"
    with patch.object(w, "_frame_child_pid", return_value=None), patch.object(
        w, "_window_pid", return_value=7
    ), patch.object(w, "_process_app_id", return_value=notepad) as app_id:
        assert w.window_app_id(100) == notepad
    app_id.assert_called_once_with(7)


def test_app_id_of_plain_win32_app_is_empty() -> None:
    with patch.object(w, "_frame_child_pid", return_value=None), patch.object(
        w, "_window_pid", return_value=7
    ), patch.object(w, "_process_app_id", return_value=""):
        assert w.window_app_id(100) == ""


def test_app_id_never_raises() -> None:
    with patch.object(w, "_frame_child_pid", return_value=None), patch.object(
        w, "_window_pid", return_value=7
    ), patch.object(w, "_process_app_id", side_effect=OSError("access denied")):
        assert w.window_app_id(100) == ""


def test_title_rank_exact_prefix_substring() -> None:
    assert w._title_rank("Calculadora", "calculadora") == 0
    assert w._title_rank("Calculadora - x", "calculadora") == 1
    assert w._title_rank("example-calculadora", "calculadora") == 2
    assert w._title_rank("Bloco de Notas", "calculadora") == 3  # não casa

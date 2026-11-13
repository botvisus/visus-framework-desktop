"""``visus use-app`` -- o programa na frente; fechado, abre e espera a janela.

Para fluxos que passam por vários programas: ao contrário do ``open``, não abre uma
segunda cópia de um programa que já está rodando. ``APP`` é o caminho do exe, o nome
(``EXCEL.EXE``) ou o id de um app da loja; sem ``APP``, ``--window`` só traz a janela.
"""

from __future__ import annotations

import click

from .._common import json_option
from .._output import done, fail


@click.command(
    name="use-app",
    help="Bring a program to the front; when it is closed, open it and wait for it.",
)
@click.argument("app", required=False)
@click.option(
    "--window",
    help="Preferred window title (any window of the program serves without a match).",
)
@click.option(
    "--file",
    "file",
    help="Document to open when the program is closed.",
)
@click.option(
    "--timeout",
    type=float,
    default=30.0,
    show_default=True,
    help="Seconds to wait for the window after opening.",
)
@json_option
def use_app_cmd(app, window, file, timeout, json_mode):
    from visus.desktop.core import app as _app

    try:
        win = _app.use_app(app, window=window, file=file, timeout=timeout)
    except (_app.UseAppError, ValueError) as exc:
        fail(str(exc), json_mode=json_mode)
        return
    result = {"title": str(win), "hwnd": win.hwnd, "pid": win.pid, "opened": win.opened}
    verb = "opened" if win.opened else "in front"
    done(result, json_mode=json_mode, ok=True, human=f"{verb}: {win}")

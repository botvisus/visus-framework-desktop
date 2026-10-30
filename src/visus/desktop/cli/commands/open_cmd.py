"""``visus open`` -- abrir um app ou um arquivo como o "Executar" do Windows.

``process launch`` roda um executável cru (``Popen``): ``excel`` falha (não está no
PATH) e um ``.xlsx`` não abre. ``open`` usa a associação do sistema
(:func:`visus.desktop.core.process.launch`): ``excel``, ``notepad``, ``calc`` pelo
App Paths, um documento no programa padrão dele, uma URL no navegador. Com
``--wait-window`` espera a janela aparecer e a traz para a frente -- um app leva
segundos para abrir, e procurar a janela cedo demais dá "não está aberto".
"""

from __future__ import annotations

import click

from .._common import json_option
from .._output import done, fail


@click.command(
    name="open",
    help="Open an app or a file as Windows Run does (excel, notepad, report.xlsx, a URL).",
)
@click.argument("target")
@click.option(
    "--wait-window",
    "wait_window",
    help="Wait for a window whose title contains this text, then bring it to the front.",
)
@click.option(
    "--timeout",
    type=float,
    default=30.0,
    show_default=True,
    help="Seconds to wait for the window.",
)
@json_option
def open_cmd(target, wait_window, timeout, json_mode):
    from visus.desktop.core.process import open_app

    try:
        result = open_app(target, wait_window=wait_window, timeout=timeout)
    except OSError as exc:
        fail(f"could not open {target!r}: {exc}", json_mode=json_mode)
        return
    if not wait_window:
        done(result, json_mode=json_mode, ok=True, human=f"opened {target}")
    elif result["window"]:
        done(
            result,
            json_mode=json_mode,
            ok=True,
            human=f"opened {target}; window in front: {result['window']}",
        )
    else:
        fail(
            f"opened {target}, but no window titled {wait_window!r} showed up in "
            f"{timeout:g}s (see `visus window list`)",
            json_mode=json_mode,
        )

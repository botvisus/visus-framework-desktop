"""``visus clipboard`` -- read / write the system clipboard."""

from __future__ import annotations

import click

from .._common import json_option
from .._output import done


@click.group(help="Clipboard access.")
def clipboard():
    pass


@clipboard.command(name="get", help="Read the clipboard text.")
@json_option
def get(json_mode):
    from visus.desktop.utils.clipboard import get_clipboard

    text = get_clipboard() or ""
    done(text, json_mode=json_mode, ok=True, human=text)


@clipboard.command(name="set", help="Put TEXT on the clipboard.")
@click.argument("text")
@json_option
def set_(text, json_mode):
    from visus.desktop.utils.clipboard import copy as _copy

    _copy(text)
    done(True, json_mode=json_mode, ok=True, human="copied")

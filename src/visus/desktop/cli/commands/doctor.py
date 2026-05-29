"""``visus doctor`` -- environment health checks."""

from __future__ import annotations

import contextlib
import io

import click

from .._common import json_option
from .._output import done


@click.command(help="Run environment health checks (Tesseract, display, deps).")
@json_option
def doctor(json_mode):
    from visus.desktop import doctor as _doctor

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _doctor.main()
    output = buf.getvalue()
    if json_mode:
        done(
            {"exit_code": int(code), "output": output},
            json_mode=True,
            exit_code=int(code),
        )
    click.echo(output, nl=False)
    click.get_current_context().exit(int(code))

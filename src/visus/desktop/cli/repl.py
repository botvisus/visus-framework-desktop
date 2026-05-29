"""``visus repl`` -- the interactive Visus CLI Pro shell.

A dependency-free loop: read a line, split it, and dispatch through the same
``visus`` command group. Type commands without the ``visus`` prefix.
"""

from __future__ import annotations

import shlex
import sys

import click

_BANNER = "Visus CLI Pro -- interactive shell. Type 'help', or 'exit' to leave."


@click.command(help="Start the interactive Visus CLI Pro shell.")
def repl():
    click.echo(_BANNER)
    from visus.desktop.cli import main as _run

    while True:
        click.echo("visus > ", nl=False)
        line = sys.stdin.readline()
        if not line:  # EOF (Ctrl-D / Ctrl-Z)
            click.echo("")
            break
        line = line.strip()
        if not line:
            continue
        if line in {"exit", "quit"}:
            break
        if line == "help":
            _run(["--help"])
            continue
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            click.echo(f"error: {exc}", err=True)
            continue
        if parts and parts[0] == "repl":
            click.echo("Already in the REPL.", err=True)
            continue
        _run(parts)

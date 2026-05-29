"""Output helpers for Visus CLI Pro.

Every command renders human-readable text by default and machine-readable
JSON when ``--json`` is passed. ``done`` also maps a result to the process
exit code (0 = success, 1 = operation failed) so the CLI scripts cleanly.
"""

from __future__ import annotations

import json as _json

import click


def emit(result, *, json_mode, human=None):
    """Print ``result`` as JSON (``--json``) or as readable text."""
    if json_mode:
        click.echo(_json.dumps(result, default=str, ensure_ascii=False))
    elif human is not None:
        click.echo(human)
    else:
        click.echo(_render(result))


def _render(result):
    if result is None:
        return "(none)"
    if isinstance(result, bool):
        return "OK" if result else "FAILED"
    if isinstance(result, str):
        return result
    if isinstance(result, (list, tuple)):
        return "\n".join(_render(item) for item in result) if result else "(empty)"
    if isinstance(result, dict):
        return "\n".join(f"{k}: {v}" for k, v in result.items())
    return str(result)


def done(result, *, json_mode, ok=True, human=None, exit_code=None):
    """Emit ``result`` then exit with the appropriate code.

    ``ok`` maps to exit 0 (truthy) / 1 (falsy); pass ``exit_code`` to
    override (e.g. propagate ``doctor``'s own code).
    """
    emit(result, json_mode=json_mode, human=human)
    code = exit_code if exit_code is not None else (0 if ok else 1)
    click.get_current_context().exit(code)


def fail(message, *, json_mode, exit_code=1):
    """Print an error (to stderr) in the active format and exit non-zero."""
    if json_mode:
        click.echo(_json.dumps({"error": message}), err=True)
    else:
        click.echo(f"error: {message}", err=True)
    click.get_current_context().exit(exit_code)

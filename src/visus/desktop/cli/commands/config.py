"""``visus configure`` -- validate a config dict and show the active config."""

from __future__ import annotations

import json as _json
from pathlib import Path

import click

from .._common import json_option
from .._output import done, fail


@click.command(help="Validate a JSON config and print the resulting active config.")
@click.argument("config")
@json_option
def configure(config, json_mode):
    """CONFIG is a JSON object, or '@path' to read it from a file."""
    raw = config
    if raw.startswith("@"):
        raw = Path(raw[1:]).read_text(encoding="utf-8")
    try:
        cfg = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}", json_mode=json_mode)
        return
    if not isinstance(cfg, dict):
        fail("config must be a JSON object", json_mode=json_mode)
        return
    from visus.desktop import VisusBot

    bot = VisusBot(cfg)
    active = dict(bot.config.config)
    done(active, json_mode=json_mode, ok=True)

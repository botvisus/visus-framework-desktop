"""``visus configure`` -- read, set (persist), or reset the CLI config."""

from __future__ import annotations

import json as _json
from pathlib import Path

import click

from .._common import config_path, json_option, load_persisted_config
from .._output import done, fail


def _coerce(value: str):
    """Turn a ``--set`` string value into a typed Python value.

    Tries JSON first (so ``true``/``false``/``null``/numbers/``["a","b"]`` work),
    then falls back to the raw string (so ``rapidocr`` stays a string without
    needing quotes).
    """
    try:
        return _json.loads(value)
    except (_json.JSONDecodeError, ValueError):
        return value


@click.command(help="Read, set (persisted), or reset the CLI config.")
@click.argument("config", required=False)
@click.option(
    "--set", "set_pairs", multiple=True, metavar="KEY=VALUE",
    help="Set one key (repeatable), quote-free: --set ocr_backend=rapidocr "
         "--set show_overlay=false. Values are typed (true/false/null/numbers/"
         "JSON), else kept as a string. Merges over CONFIG if both are given.",
)
@click.option(
    "--dry-run", "dry_run", is_flag=True,
    help="Preview the resulting config WITHOUT persisting it.",
)
@click.option(
    "--reset", is_flag=True,
    help="Delete the saved config (back to library defaults).",
)
@click.option(
    "--save", is_flag=True, hidden=True,
    help="Deprecated: --set/CONFIG now persist automatically. Kept so "
         "`configure --save` still writes the current config.",
)
@json_option
def configure(config, set_pairs, dry_run, reset, save, json_mode):
    """Show, change, or reset the persisted CLI config.

    \b
    * `visus configure`                         -> show the active config.
    * `visus configure --set ocr_backend=rapidocr`  -> set it AND PERSIST it
      (later `visus` commands pick it up — each call is a separate process).
    * `visus configure --set ... --dry-run`     -> preview without saving.
    * `visus configure --reset`                 -> wipe the saved config.

    CONFIG is a JSON object (or '@path' to read it from a file); --set KEY=VALUE
    is the quote-free way (best on Windows cmd.exe / PowerShell). Both merge
    onto the already-saved config (--set wins). Anything you pass is persisted
    by default — there is no separate "save" step. The file lives in the
    per-user config dir, or $VISUS_CONFIG.
    """
    from visus.desktop import VisusBot

    path = config_path()

    # --reset: delete the saved config and report the resulting defaults.
    if reset:
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            fail(f"could not remove {path}: {exc}", json_mode=json_mode)
            return
        active = dict(VisusBot().config.config)
        if not json_mode:
            click.echo(f"reset (removed {path})")
        done(active, json_mode=json_mode, ok=True)
        return

    # Start from whatever is already persisted, so changes are additive.
    cfg: dict = load_persisted_config()
    has_input = config is not None or bool(set_pairs)

    # 1. Base from a JSON CONFIG argument, if present.
    if config is not None:
        raw = config.strip()
        # cmd.exe keeps literal single quotes; strip one matching wrapping pair.
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
            raw = raw[1:-1].strip()
        if raw.startswith("@"):
            raw = Path(raw[1:]).read_text(encoding="utf-8")
        try:
            parsed = _json.loads(raw)
        except _json.JSONDecodeError as exc:
            fail(
                f"invalid JSON: {exc}. Tip: use --set key=value (no quoting), "
                'or "@file.json". On cmd.exe a literal JSON arg loses its inner '
                'quotes — prefer --set.',
                json_mode=json_mode,
            )
            return
        if not isinstance(parsed, dict):
            fail("config must be a JSON object", json_mode=json_mode)
            return
        cfg.update(parsed)

    # 2. Overlay any --set key=value pairs (these win over CONFIG).
    for pair in set_pairs:
        if "=" not in pair:
            fail(f"--set expects KEY=VALUE, got: {pair!r}", json_mode=json_mode)
            return
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            fail(f"--set has an empty key: {pair!r}", json_mode=json_mode)
            return
        cfg[key] = _coerce(value.strip())

    # 3. Persist by default whenever the user passed input (unless --dry-run),
    #    so "set it" actually sticks — no separate save step. ``--save`` is
    #    deprecated but still honored so `configure --save` (no input) writes
    #    the current effective config.
    saved = False
    if (has_input or save) and not dry_run:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_json.dumps(cfg, indent=2), encoding="utf-8")
            saved = True
        except OSError as exc:
            fail(f"could not write {path}: {exc}", json_mode=json_mode)
            return

    bot = VisusBot(cfg) if cfg else VisusBot()
    active = dict(bot.config.config)
    if not json_mode:
        if saved:
            click.echo(f"saved to {path}")
        elif has_input and dry_run:
            click.echo("(dry-run: not saved)")
    done(active, json_mode=json_mode, ok=True)

"""Shared Click option groups and value parsers for Visus CLI Pro."""

from __future__ import annotations

import json as _json
import os
import sys
from pathlib import Path

import click


def config_path() -> Path:
    """Where the CLI persists / reads config — a per-user, OS-appropriate path.

    Precedence:
      1. ``$VISUS_CONFIG`` — explicit override (any path you choose).
      2. The platform user-config dir, so it stays out of the project tree
         and out of sight:
           * Windows: ``%APPDATA%\\visus\\config.json``
           * macOS:   ``~/Library/Application Support/visus/config.json``
           * Linux:   ``$XDG_CONFIG_HOME/visus/config.json`` (else
             ``~/.config/visus/config.json``)
    """
    env = os.environ.get("VISUS_CONFIG")
    if env:
        return Path(env)

    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser(r"~\AppData\Roaming")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "visus" / "config.json"


def load_persisted_config() -> dict:
    """Return the persisted CLI config dict, or ``{}`` if none/invalid.

    Each ``visus`` invocation is its own process, so this file is how
    ``visus configure --save`` settings reach later commands.
    """
    path = config_path()
    if not path.exists():
        return {}
    try:
        data = _json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def build_bot(**overrides):
    """Build a ``VisusBot`` from the persisted config + explicit overrides.

    Overrides whose value is ``None`` are dropped, so a command's flag
    default of ``None`` means "use the persisted/library default" rather
    than forcing a value over a saved config.
    """
    from visus.desktop import VisusBot

    cfg = load_persisted_config()
    cfg.update({k: v for k, v in overrides.items() if v is not None})
    return VisusBot(config=cfg) if cfg else VisusBot()


def _int_csv(expected_len, label):
    """Build a Click callback parsing 'a,b,c' into a list of ints."""

    def cb(ctx, param, value):
        if value is None:
            return None
        try:
            parts = [int(p.strip()) for p in str(value).split(",")]
        except ValueError as exc:
            raise click.BadParameter(
                f"{label} must be comma-separated integers"
            ) from exc
        if expected_len and len(parts) != expected_len:
            raise click.BadParameter(
                f"{label} must have {expected_len} integers (got {len(parts)})"
            )
        return parts

    return cb


def _str_csv(ctx, param, value):
    if value is None:
        return None
    return [p.strip() for p in str(value).split(",") if p.strip()]


region_cb = _int_csv(4, "--region")
coords_cb = _int_csv(2, "--coords")


def json_option(f):
    return click.option(
        "--json",
        "json_mode",
        is_flag=True,
        help="Emit the raw result as JSON (for scripts and agents).",
    )(f)


def dry_run_option(f):
    return click.option(
        "--dry-run",
        "dry_run",
        is_flag=True,
        help="Resolve and report the target without acting (no mouse/keyboard).",
    )(f)


def _stack(f, options):
    for opt in reversed(options):
        f = opt(f)
    return f


def smart_options(f):
    """Locating options shared by ``smart find`` and ``smart click``."""
    return _stack(
        f,
        [
            click.option("--query", help="Text/title to match (native title + OCR)."),
            click.option("--image", help="Template PNG path."),
            click.option(
                "--coords", "coordinates", callback=coords_cb,
                help="Fallback coordinates 'X,Y'.",
            ),
            click.option("--window", help="Window title substring (sharpens native)."),
            click.option("--pid", type=int, help="Process id (native)."),
            click.option(
                "--control-type", "control_type", help="UIA control type (native)."
            ),
            click.option("--auto-id", "auto_id", help="UIA automation id (native)."),
            click.option(
                "--region", "search_region", callback=region_cb,
                help="Search region 'X,Y,W,H'.",
            ),
            click.option(
                "--confidence", type=float, default=0.9, show_default=True,
                help="Image-match confidence (0-1).",
            ),
            click.option(
                "--confidence-threshold", "confidence_threshold", type=float,
                default=75.0, show_default=True, help="OCR confidence threshold.",
            ),
            click.option(
                "--order", callback=_str_csv,
                help="Override cascade order, e.g. 'native,ocr'.",
            ),
            click.option(
                "--timeout", type=float, default=5.0, show_default=True,
                help="Per-method timeout (s).",
            ),
        ],
    )


def native_selector_options(f):
    """Directed-selector options shared by every ``native`` subcommand."""
    return _stack(
        f,
        [
            click.option("--window", help="Window title substring (else foreground)."),
            click.option("--pid", type=int, help="Process id (else foreground)."),
            click.option("--title", help="Control title/name."),
            click.option(
                "--control-type", "control_type",
                help="Control type: Button, MenuItem, Edit, ...",
            ),
            click.option("--auto-id", "auto_id", help="UIA automation id."),
            click.option(
                "--found-index", "found_index", type=int,
                help="Disambiguate multiple matches (0-based).",
            ),
        ],
    )

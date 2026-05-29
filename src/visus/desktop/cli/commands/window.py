"""``visus window`` -- window management by title substring."""

from __future__ import annotations

import click

from .._common import json_option
from .._output import done, fail


@click.group(help="Window management by title substring.")
def window():
    pass


@window.command(help="Bring a window to the foreground.")
@click.argument("title")
@json_option
def focus(title, json_mode):
    from visus.desktop.core.window import focus_window

    result = bool(focus_window(title))
    done(
        result, json_mode=json_mode, ok=result,
        human=("focused" if result else "window not found"),
    )


@window.command(help="Maximize a window.")
@click.argument("title")
@json_option
def maximize(title, json_mode):
    from visus.desktop.core.window import maximize_window

    result = bool(maximize_window(title))
    done(
        result, json_mode=json_mode, ok=result,
        human=("maximized" if result else "window not found"),
    )


@window.command(help="Minimize a window.")
@click.argument("title")
@json_option
def minimize(title, json_mode):
    from visus.desktop.core.window import minimize_window

    result = bool(minimize_window(title))
    done(
        result, json_mode=json_mode, ok=result,
        human=("minimized" if result else "window not found"),
    )


@window.command(help="Close a window (destructive -- requires confirmation).")
@click.argument("title")
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt.")
@json_option
def close(title, yes, json_mode):
    if not yes:
        if json_mode:
            fail("refusing to close without --yes in JSON mode", json_mode=True)
            return
        if not click.confirm(f"Close window matching '{title}'?"):
            click.echo("Aborted.", err=True)
            click.get_current_context().exit(1)
    from visus.desktop.core.window import close_window

    result = bool(close_window(title))
    done(
        result, json_mode=json_mode, ok=result,
        human=("close requested" if result else "window not found"),
    )


@window.command(
    name="ensure",
    help="Fast: is the app open/minimized? -- and bring it to the front.",
)
@click.option("--title", help="Window title substring.")
@click.option("--process", help="Process name, e.g. 'notepad.exe' (avoids title false-positives).")
@click.option("--no-show", "no_show", is_flag=True, help="Read-only: do not restore/raise.")
@click.option("--no-foreground", "no_foreground", is_flag=True, help="Restore but do not raise to front.")
@json_option
def ensure(title, process, no_show, no_foreground, json_mode):
    if not title and not process:
        fail("provide --title and/or --process", json_mode=json_mode)
        return
    from visus.desktop.core.window import ensure_window

    result = ensure_window(
        title=title, process=process, show=not no_show, foreground=not no_foreground
    )
    ok = bool(result.get("found"))
    if ok:
        state = "minimized" if result.get("minimized") else "visible"
        human = (
            f"found pid {result.get('pid')} ({state}"
            f"{', shown' if result.get('shown') else ''}) -- {result.get('title')}"
        )
        if result.get("matches", 0) > 1:
            human += f"  [! {result['matches']} windows matched -- narrow with --process]"
    else:
        running = result.get("running")
        human = (
            "not found; process is running but has no window"
            if running
            else "not found (app not open)"
        )
    done(result, json_mode=json_mode, ok=ok, human=human)


@window.command(name="list", help="List visible windows (read-only).")
@click.option("--title", help="Filter by window title substring.")
@click.option("--process", help="Filter by process name.")
@json_option
def list_(title, process, json_mode):
    from visus.desktop.core.window import list_windows

    rows = list_windows(title=title, process=process)
    if json_mode:
        done(rows, json_mode=True, ok=True)
        return
    if not rows:
        done(rows, json_mode=False, ok=True, human="(no windows)")
        return
    lines = [
        f"{r['pid']}\t{'min' if r['minimized'] else 'vis'}\t{r['title']}" for r in rows
    ]
    done(rows, json_mode=False, ok=True, human="\n".join(lines))


@window.command(name="get", help="Resolve a window's rect/pid/hwnd (no focus).")
@click.argument("title")
@json_option
def get(title, json_mode):
    from visus.desktop.core.locators import get_window

    result = get_window(title)
    ok = result is not None
    human = (
        "\n".join(f"{k}: {v}" for k, v in result.items())
        if ok
        else "window not found"
    )
    done(result, json_mode=json_mode, ok=ok, human=human)

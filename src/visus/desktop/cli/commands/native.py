"""``visus native`` -- no-pixel RPA through the accessibility tree."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from .._common import dry_run_option, json_option, native_selector_options
from .._output import done, fail


@click.group(help="Native RPA via the accessibility tree (no pixels).")
def native():
    pass


# --- snapshot: the window numbered, then act by number ---------------------


def _snapshot_path() -> Path:
    """Where the last snapshot lives: next to $VISUS_CONFIG when set (keeps tests
    and parallel profiles apart), else ~/.visus/desktop/."""
    config = os.environ.get("VISUS_CONFIG")
    base = Path(config).parent if config else Path.home() / ".visus" / "desktop"
    return base / "last-snapshot.json"


def _selector_for_index(index, json_mode):
    """The stored selector of item ``index`` of the last snapshot, or exit 1 with
    what to do next (an agent reads this and simply snapshots again)."""
    path = _snapshot_path()
    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        fail(
            "no snapshot yet — run `native snapshot --window <title>` first, then act by number",
            json_mode=json_mode,
        )
    items = snap.get("items") or []
    if not 0 <= index < len(items):
        fail(
            f"index {index} is not in the last snapshot ({len(items)} items) — "
            "run `native snapshot` again",
            json_mode=json_mode,
        )
    item = items[index]
    return {
        "window": snap.get("window"),
        "pid": snap.get("pid"),
        "backend": snap.get("backend") or "uia",
        "title": item.get("title") or None,
        "control_type": item.get("control_type") or None,
        "auto_id": item.get("auto_id") or None,
        "found_index": item.get("found_index"),
    }


def _format_item(item):
    line = f"{item['index']:>3}  {item['control_type']:<12} {item['title']}".rstrip()
    return f"{line} #{item['auto_id']}" if item.get("auto_id") else line


@native.command(name="snapshot", help="List the window's actionable controls, numbered (act with `click N`).")
@click.option("--window", help="Window title substring (else foreground).")
@click.option("--pid", type=int, help="Process id (else foreground).")
@click.option("--max-depth", "max_depth", type=int, default=8, show_default=True)
@click.option("--max", "max_items", type=int, default=200, show_default=True, help="Print at most this many.")
@click.option("--timeout", type=float, default=10.0, show_default=True)
@click.option(
    "--backend", default="uia", show_default=True, type=click.Choice(["uia", "win32"]),
    help="Accessibility backend: 'uia' (modern apps) or 'win32' (classic Win32).",
)
@json_option
def snapshot(window, pid, max_depth, max_items, timeout, backend, json_mode):
    """One line per control an agent can act on — type, name, #auto_id — numbered.

    The numbers stay valid for `native click N`, `set-text N TEXT`, `get-text N`
    and `get-state N` until the next snapshot: each one is stored with the exact
    selector (title, type, auto_id, found_index) that finds that control again.
    """
    from visus.desktop.core import native_rpa

    title, nodes = native_rpa.native_snapshot_nodes(
        window=window, pid=pid, max_depth=max_depth, timeout=timeout, backend=backend
    )
    items = native_rpa.select_actionable(nodes)
    snap = {"window": window or title, "pid": pid, "backend": backend, "title": title, "items": items}
    path = _snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")

    data = {"window": title or window, "items": items}
    if json_mode:
        done(data, json_mode=True, ok=True)
        return
    lines = [f"Window: {title or window or '(foreground)'}"]
    lines += [_format_item(i) for i in items[:max_items]] or ["(no actionable controls)"]
    if len(items) > max_items:
        lines.append(f"… {len(items) - max_items} more (raise --max)")
    done(data, json_mode=False, ok=True, human="\n".join(lines))


@native.command(name="dump-tree", help="Print the accessibility control tree.")
@click.option("--window", help="Window title substring (else foreground).")
@click.option("--pid", type=int, help="Process id (else foreground).")
@click.option("--max-depth", "max_depth", type=int, default=3, show_default=True)
@click.option("--timeout", type=float, default=5.0, show_default=True)
@click.option(
    "--backend", default="uia", show_default=True,
    type=click.Choice(["uia", "win32"]),
    help="Accessibility backend: 'uia' (modern apps) or 'win32' (classic Win32 "
         "controls like Notepad, where UIA can stall).",
)
@json_option
def dump_tree(window, pid, max_depth, timeout, backend, json_mode):
    from visus.desktop.core.native_rpa import native_dump_tree

    nodes = native_dump_tree(
        window=window, pid=pid, max_depth=max_depth, timeout=timeout, backend=backend
    )
    if json_mode:
        done(nodes, json_mode=True, ok=True)
        return
    if not nodes:
        done(nodes, json_mode=False, ok=True, human="(no accessible controls)")
        return
    lines = []
    for n in nodes:
        indent = "  " * int(n.get("depth", 0))
        title = n.get("title") or ""
        ctype = n.get("control_type") or ""
        aid = n.get("auto_id") or ""
        suffix = f" #{aid}" if aid else ""
        lines.append(f"{indent}{ctype}: {title!r}{suffix} {n.get('rect')}")
    done(nodes, json_mode=False, ok=True, human="\n".join(lines))


@native.command(name="click", help="Click a control by snapshot number or by selector.")
@click.argument("index", type=int, required=False)
@native_selector_options
@click.option("--button", default="left", show_default=True)
@click.option("--double", is_flag=True)
@click.option(
    "--method", default="auto", show_default=True,
    type=click.Choice(["invoke", "click", "auto"]),
)
@click.option("--timeout", type=float, default=5.0, show_default=True)
@click.option("--retries", type=int, default=0, show_default=True)
@click.option("--delay", type=float, default=0.3, show_default=True)
@dry_run_option
@json_option
def click_cmd(
    index, window, pid, title, control_type, auto_id, found_index, backend,
    button, double, method, timeout, retries, delay, dry_run, json_mode,
):
    from visus.desktop.core.native_rpa import native_click, native_get_state

    if index is not None:
        sel = _selector_for_index(index, json_mode)
        window, pid, backend = sel["window"], sel["pid"], sel["backend"]
        title, control_type, auto_id, found_index = (
            sel["title"], sel["control_type"], sel["auto_id"], sel["found_index"]
        )

    if dry_run:
        state = native_get_state(
            window=window, pid=pid, title=title, control_type=control_type,
            auto_id=auto_id, found_index=found_index, timeout=timeout, backend=backend,
        )
        ok = bool(state and state.get("exists"))
        human = (
            f"[dry-run] would click control at {state.get('rect')}"
            if ok
            else "[dry-run] control not found"
        )
        done(state, json_mode=json_mode, ok=ok, human=human)
        return

    result = native_click(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, button=button, double=double,
        method=method, timeout=timeout, retries=retries, delay=delay, backend=backend,
    )
    ok = bool(result)
    done(result, json_mode=json_mode, ok=ok, human=("clicked" if ok else "not clicked"))


@native.command(name="set-text", help="Set a control's text: `set-text N TEXT` or `set-text TEXT --title …`.")
@click.argument("args", nargs=-1, required=True)
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@click.option("--retries", type=int, default=0, show_default=True)
@click.option("--delay", type=float, default=0.3, show_default=True)
@dry_run_option
@json_option
def set_text(
    args, window, pid, title, control_type, auto_id, found_index, backend,
    timeout, retries, delay, dry_run, json_mode,
):
    from visus.desktop.core.native_rpa import native_get_state, native_set_text

    if len(args) == 2 and args[0].isdigit():
        sel = _selector_for_index(int(args[0]), json_mode)
        window, pid, backend = sel["window"], sel["pid"], sel["backend"]
        title, control_type, auto_id, found_index = (
            sel["title"], sel["control_type"], sel["auto_id"], sel["found_index"]
        )
        text = args[1]
    elif len(args) == 1:
        text = args[0]
    else:
        fail("usage: native set-text N TEXT  (or: native set-text TEXT --title …)", json_mode=json_mode)

    if dry_run:
        state = native_get_state(
            window=window, pid=pid, title=title, control_type=control_type,
            auto_id=auto_id, found_index=found_index, timeout=timeout, backend=backend,
        )
        ok = bool(state and state.get("exists"))
        human = (
            f"[dry-run] would set text on control at {state.get('rect')}"
            if ok
            else "[dry-run] control not found"
        )
        done(state, json_mode=json_mode, ok=ok, human=human)
        return

    result = native_set_text(
        text=text, window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, timeout=timeout,
        retries=retries, delay=delay, backend=backend,
    )
    ok = bool(result)
    done(
        result, json_mode=json_mode, ok=ok,
        human=("text set" if ok else "failed to set text"),
    )


@native.command(name="get-text", help="Read a control's text/value (by snapshot number or selector).")
@click.argument("index", type=int, required=False)
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def get_text(index, window, pid, title, control_type, auto_id, found_index, backend, timeout, json_mode):
    from visus.desktop.core.native_rpa import native_get_text

    if index is not None:
        sel = _selector_for_index(index, json_mode)
        window, pid, backend = sel["window"], sel["pid"], sel["backend"]
        title, control_type, auto_id, found_index = (
            sel["title"], sel["control_type"], sel["auto_id"], sel["found_index"]
        )

    result = native_get_text(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, timeout=timeout, backend=backend,
    )
    ok = result is not None
    done(
        result, json_mode=json_mode, ok=ok,
        human=(result if ok else "(no text / control not found)"),
    )


@native.command(name="get-state", help="A control's state (by snapshot number or selector).")
@click.argument("index", type=int, required=False)
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def get_state(index, window, pid, title, control_type, auto_id, found_index, backend, timeout, json_mode):
    from visus.desktop.core.native_rpa import native_get_state

    if index is not None:
        sel = _selector_for_index(index, json_mode)
        window, pid, backend = sel["window"], sel["pid"], sel["backend"]
        title, control_type, auto_id, found_index = (
            sel["title"], sel["control_type"], sel["auto_id"], sel["found_index"]
        )

    result = native_get_state(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, timeout=timeout, backend=backend,
    )
    ok = bool(result and result.get("exists"))
    done(result, json_mode=json_mode, ok=ok)


@native.command(name="wait", help="Wait until a control reaches a state.")
@native_selector_options
@click.option(
    "--state", default="exists", show_default=True,
    type=click.Choice(["exists", "visible", "enabled", "ready"]),
)
@click.option("--timeout", type=float, default=10.0, show_default=True)
@click.option("--poll-interval", "poll_interval", type=float, default=0.3, show_default=True)
@json_option
def wait(
    window, pid, title, control_type, auto_id, found_index, backend,
    state, timeout, poll_interval, json_mode,
):
    from visus.desktop.core.native_rpa import native_wait

    result = native_wait(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, state=state,
        timeout=timeout, poll_interval=poll_interval, backend=backend,
    )
    ok = bool(result)
    done(
        result, json_mode=json_mode, ok=ok,
        human=(f"reached '{state}'" if ok else f"timed out waiting for '{state}'"),
    )

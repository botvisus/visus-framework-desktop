"""``visus native`` -- no-pixel RPA through the accessibility tree."""

from __future__ import annotations

import click

from .._common import dry_run_option, json_option, native_selector_options
from .._output import done


@click.group(help="Native RPA via the accessibility tree (no pixels).")
def native():
    pass


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


@native.command(name="click", help="Click a control by selector.")
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
    window, pid, title, control_type, auto_id, found_index, backend,
    button, double, method, timeout, retries, delay, dry_run, json_mode,
):
    from visus.desktop.core.native_rpa import native_click, native_get_state

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


@native.command(name="set-text", help="Set the text of an editable control.")
@click.argument("text")
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@click.option("--retries", type=int, default=0, show_default=True)
@click.option("--delay", type=float, default=0.3, show_default=True)
@dry_run_option
@json_option
def set_text(
    text, window, pid, title, control_type, auto_id, found_index, backend,
    timeout, retries, delay, dry_run, json_mode,
):
    from visus.desktop.core.native_rpa import native_get_state, native_set_text

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


@native.command(name="get-text", help="Read a control's text/value.")
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def get_text(window, pid, title, control_type, auto_id, found_index, backend, timeout, json_mode):
    from visus.desktop.core.native_rpa import native_get_text

    result = native_get_text(
        window=window, pid=pid, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index, timeout=timeout, backend=backend,
    )
    ok = result is not None
    done(
        result, json_mode=json_mode, ok=ok,
        human=(result if ok else "(no text / control not found)"),
    )


@native.command(name="get-state", help="Snapshot a control's state.")
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def get_state(window, pid, title, control_type, auto_id, found_index, backend, timeout, json_mode):
    from visus.desktop.core.native_rpa import native_get_state

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

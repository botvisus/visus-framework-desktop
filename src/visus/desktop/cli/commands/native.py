"""``visus native`` -- no-pixel RPA through the accessibility tree.

Snapshot first, then act by number: ``native snapshot --window X`` numbers the
controls (``3``, or ``s1a2b3:3`` to pin that snapshot) and every action checks, before
sending anything, that the numbered control is still the one the snapshot saw. Each
action answers whether it reached the app and whether repeating it is safe.
"""

from __future__ import annotations

import click

from .._common import dry_run_option, json_option, native_selector_options
from .._output import done, fail


@click.group(help="Native RPA via the accessibility tree (no pixels).")
def native():
    pass


# --- snapshot: the window numbered, then act by number ---------------------

_SELECTOR_KEYS = ("title", "control_type", "auto_id", "found_index")


def _target(ref, json_mode, *, verify=True):
    """The stored selector of snapshot item ``ref`` (``3`` or ``s1a2b3:3``) -- checked
    against the live window first when ``verify`` -- or exit 1 with what to do next
    (an agent reads this and simply snapshots again)."""
    from visus.desktop.core.native_rpa import verify_snapshot_item
    from visus.desktop.core.native_session import SnapshotError, load_ref

    try:
        snap, item = load_ref(ref)
    except SnapshotError as exc:
        fail(str(exc), json_mode=json_mode)
        return None
    if verify:
        reason = verify_snapshot_item(snap, item)
        if reason:
            fail(
                f"not sent: {reason} -- run `native snapshot` again and use the new number "
                "(nothing reached the app, safe to retry)",
                json_mode=json_mode,
            )
            return None
    sel = {
        "window": snap.get("window"),
        "pid": snap.get("pid"),
        "backend": snap.get("backend") or "uia",
        "item": item,
    }
    for key in _SELECTOR_KEYS:
        value = item.get(key)
        sel[key] = value if value not in ("", None) else None
    return sel


def _apply(sel, kwargs):
    """Overwrite the command's selector options with the snapshot item's."""
    for key in ("window", "pid", "backend", *_SELECTOR_KEYS):
        kwargs[key] = sel[key]
    return kwargs


def _format_item(item):
    line = f"{item['index']:>3}  {item['control_type']:<12} {item['title']}".rstrip()
    if item.get("auto_id"):
        line = f"{line} #{item['auto_id']}"
    if item.get("states"):
        line = f"{line} [{', '.join(item['states'])}]"
    return line


def _report(outcome, success, json_mode):
    """An ``ActionOutcome`` as the command's answer: exit 0 only when it worked."""
    done(outcome.to_dict(), json_mode=json_mode, ok=outcome.ok, human=outcome.human(success))


@native.command(name="snapshot", help="List the window's actionable controls, numbered (act with `click N`).")
@click.option("--window", help="Window title substring (else foreground).")
@click.option("--pid", type=int, help="Process id (else foreground).")
# 25: a faixa de opções do Office põe os botões (Bold, Shading, a paleta de cores) além
# do nível 8 -- medido no Excel, ~1 s do mesmo jeito
@click.option("--max-depth", "max_depth", type=int, default=25, show_default=True)
@click.option("--max", "max_items", type=int, default=400, show_default=True, help="Print at most this many.")
@click.option("--timeout", type=float, default=10.0, show_default=True)
@click.option(
    "--backend", default="uia", show_default=True, type=click.Choice(["uia", "win32"]),
    help="Accessibility backend: 'uia' (modern apps) or 'win32' (classic Win32).",
)
@json_option
def snapshot(window, pid, max_depth, max_items, timeout, backend, json_mode):
    """One line per control an agent can act on — type, name, #auto_id, [states] —
    numbered.

    The numbers stay valid for `native click N`, `toggle N`, `select N VALUE`,
    `set-text N TEXT`, `get-text N`... until the window changes: each is stored with
    the selector (title, type, auto_id, found_index) that finds that control again, and
    an action whose control changed since is refused before anything is sent.
    Snapshots are kept per session (VISUS_DESKTOP_SESSION), so parallel agents never
    act on each other's numbers; `s1a2b3:3` pins one snapshot.
    """
    from visus.desktop.core import native_rpa
    from visus.desktop.core.native_session import save_snapshot

    title, nodes = native_rpa.native_snapshot_nodes(
        window=window, pid=pid, max_depth=max_depth, timeout=timeout, backend=backend
    )
    if title is None:
        target = f"window {window!r}" if window else (f"pid {pid}" if pid else "foreground window")
        fail(
            f"no {target} answered (no window matches, it is not responding, or it did "
            f"not answer within {timeout:g}s) -- `window list` shows the open ones",
            json_mode=json_mode,
        )
    items = native_rpa.select_actionable(nodes)
    snapshot_id = save_snapshot(
        {
            "window": window or title,
            "pid": pid,
            "backend": backend,
            "title": title,
            "max_depth": max_depth,
            "items": items,
        }
    )

    data = {"window": title or window, "snapshot_id": snapshot_id, "items": items}
    if json_mode:
        done(data, json_mode=True, ok=True)
        return
    lines = [f"Window: {title or window or '(foreground)'}  (snapshot {snapshot_id})"]
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


def _selector(index, json_mode, kwargs, *, verify=True):
    """Fill ``kwargs`` (window/pid/backend/selector) from snapshot item ``index`` when
    given; selector options stay as typed otherwise."""
    if index is not None:
        sel = _target(index, json_mode, verify=verify)
        if sel is not None:
            _apply(sel, kwargs)
    return kwargs


@native.command(name="click", help="Click a control by snapshot number or by selector.")
@click.argument("index", required=False)
@native_selector_options
@click.option("--button", default="left", show_default=True)
@click.option("--double", is_flag=True)
@click.option("--at", "at", default=None, help="X,Y offset inside the control to click.")
@click.option(
    "--method", default="auto", show_default=True,
    type=click.Choice(["invoke", "click", "auto"]),
    help="auto: Invoke, then the control's default action (both without the mouse), "
         "then the real mouse; invoke: never the mouse; click: the real mouse.",
)
@click.option("--timeout", type=float, default=5.0, show_default=True)
@click.option("--retries", type=int, default=0, show_default=True)
@click.option("--delay", type=float, default=0.3, show_default=True)
@dry_run_option
@json_option
def click_cmd(
    index, window, pid, title, control_type, auto_id, found_index, backend,
    button, double, at, method, timeout, retries, delay, dry_run, json_mode,
):
    from visus.desktop.core.native_rpa import native_click_ex, native_get_state

    sel = _selector(index, json_mode, dict(
        window=window, pid=pid, backend=backend, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index,
    ), verify=not dry_run)

    if dry_run:
        state = native_get_state(timeout=timeout, **sel)
        ok = bool(state and state.get("exists"))
        human = (
            f"[dry-run] would click control at {state.get('rect')}"
            if ok
            else "[dry-run] control not found"
        )
        done(state, json_mode=json_mode, ok=ok, human=human)
        return

    try:
        point = _xy(at) if at else None
    except ValueError:
        fail("--at must be X,Y (e.g. 40,30)", json_mode=json_mode)
        return
    outcome = native_click_ex(
        button=button, double=double, method=method, timeout=timeout,
        retries=retries, delay=delay, at=point, **sel,
    )
    _report(outcome, "clicked", json_mode)


def _xy(value: str) -> tuple[int, int]:
    x, _, y = value.partition(",")
    return int(x), int(y)


@native.command(
    name="drag",
    help="Drag inside a control: --start X,Y --end X,Y (offsets from its top-left corner).",
)
@click.argument("index", required=False)
@native_selector_options
@click.option("--start", "start", required=True, help="X,Y offset where the drag starts.")
@click.option("--end", "end", required=True, help="X,Y offset where the drag ends.")
@click.option("--button", default="left", show_default=True)
@click.option("--duration", type=float, default=0.4, show_default=True)
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def drag_cmd(
    index, window, pid, title, control_type, auto_id, found_index, backend,
    start, end, button, duration, timeout, json_mode,
):
    from visus.desktop.core.native_rpa import native_drag

    sel = _selector(index, json_mode, dict(
        window=window, pid=pid, backend=backend, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index,
    ))
    try:
        src, dst = _xy(start), _xy(end)
    except ValueError:
        fail("--start/--end must be X,Y (e.g. 40,30)", json_mode=json_mode)
        return
    result = native_drag(
        start=src, end=dst, button=button, duration=duration, timeout=timeout, **sel,
    )
    ok = bool(result)
    done(result, json_mode=json_mode, ok=ok, human=("dragged" if ok else "not dragged"))


@native.command(
    name="scroll",
    help="Turn the mouse wheel over a control: --amount N (up +, down -), --at X,Y.",
)
@click.argument("index", required=False)
@native_selector_options
@click.option("--amount", type=int, required=True, help="Wheel notches: + up, - down.")
@click.option("--at", "at", default=None, help="X,Y offset inside the control (default: center).")
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def scroll_cmd(
    index, window, pid, title, control_type, auto_id, found_index, backend,
    amount, at, timeout, json_mode,
):
    from visus.desktop.core.native_rpa import native_scroll

    sel = _selector(index, json_mode, dict(
        window=window, pid=pid, backend=backend, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index,
    ))
    try:
        point = _xy(at) if at else None
    except ValueError:
        fail("--at must be X,Y (e.g. 40,30)", json_mode=json_mode)
        return
    result = native_scroll(amount=amount, at=point, timeout=timeout, **sel)
    ok = bool(result)
    done(result, json_mode=json_mode, ok=ok, human=("scrolled" if ok else "not scrolled"))


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
    from visus.desktop.core.native_rpa import native_get_state, native_set_text_ex
    from visus.desktop.core.native_session import is_ref

    kwargs = dict(
        window=window, pid=pid, backend=backend, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index,
    )
    if len(args) == 2 and is_ref(args[0]):
        _selector(args[0], json_mode, kwargs, verify=not dry_run)
        text = args[1]
    elif len(args) == 1:
        text = args[0]
    else:
        fail("usage: native set-text N TEXT  (or: native set-text TEXT --title …)", json_mode=json_mode)
        return

    if dry_run:
        state = native_get_state(timeout=timeout, **kwargs)
        ok = bool(state and state.get("exists"))
        human = (
            f"[dry-run] would set text on control at {state.get('rect')}"
            if ok
            else "[dry-run] control not found"
        )
        done(state, json_mode=json_mode, ok=ok, human=human)
        return

    outcome = native_set_text_ex(
        text=text, timeout=timeout, retries=retries, delay=delay, **kwargs,
    )
    _report(outcome, "text set", json_mode)


def _semantic_command(name, help_text, success, call):
    """A no-mouse UIA action by snapshot number or selector (toggle, select...)."""

    @native.command(name=name, help=help_text)
    @click.argument("index", required=False)
    @native_selector_options
    @click.option("--timeout", type=float, default=8.0, show_default=True)
    @json_option
    def _command(index, window, pid, title, control_type, auto_id, found_index, backend,
                 timeout, json_mode):
        sel = _selector(index, json_mode, dict(
            window=window, pid=pid, backend=backend, title=title,
            control_type=control_type, auto_id=auto_id, found_index=found_index,
        ))
        _report(call(timeout=timeout, **sel), success, json_mode)

    return _command


def _toggle(checked):
    def call(**kwargs):
        from visus.desktop.core.native_rpa import native_toggle

        return native_toggle(checked=checked, **kwargs)

    return call


def _expand(expand):
    def call(**kwargs):
        from visus.desktop.core.native_rpa import native_expand

        return native_expand(expand=expand, **kwargs)

    return call


def _scroll_into_view(**kwargs):
    from visus.desktop.core.native_rpa import native_scroll_into_view

    return native_scroll_into_view(**kwargs)


_semantic_command(
    "toggle", "Flip a checkbox/toggle/switch (no mouse).", "toggled", _toggle(None)
)
_semantic_command(
    "check", "Check a checkbox/toggle (no mouse; nothing sent if already checked).",
    "checked", _toggle(True),
)
_semantic_command(
    "uncheck", "Uncheck a checkbox/toggle (no mouse; nothing sent if already unchecked).",
    "unchecked", _toggle(False),
)
_semantic_command(
    "expand", "Expand a tree node, combo box or menu button (no mouse).", "expanded",
    _expand(True),
)
_semantic_command(
    "collapse", "Collapse a tree node, combo box or menu button (no mouse).", "collapsed",
    _expand(False),
)
_semantic_command(
    "scroll-into-view", "Scroll a list/grid until the control is visible (no mouse).",
    "scrolled into view", _scroll_into_view,
)


@native.command(
    name="select",
    help="Pick an option of a combo box/list/tab strip by its name: `select N VALUE` (no mouse).",
)
@click.argument("args", nargs=-1, required=True)
@native_selector_options
@click.option("--timeout", type=float, default=8.0, show_default=True)
@json_option
def select_cmd(
    args, window, pid, title, control_type, auto_id, found_index, backend, timeout, json_mode,
):
    from visus.desktop.core.native_rpa import native_select
    from visus.desktop.core.native_session import is_ref

    kwargs = dict(
        window=window, pid=pid, backend=backend, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index,
    )
    if len(args) == 2 and is_ref(args[0]):
        _selector(args[0], json_mode, kwargs)
        value = args[1]
    elif len(args) == 1:
        value = args[0]
    else:
        fail("usage: native select N VALUE  (or: native select VALUE --title …)", json_mode=json_mode)
        return
    _report(native_select(value=value, timeout=timeout, **kwargs), f"selected {value!r}", json_mode)


@native.command(name="get-text", help="Read a control's text/value (by snapshot number or selector).")
@click.argument("index", required=False)
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def get_text(index, window, pid, title, control_type, auto_id, found_index, backend, timeout, json_mode):
    from visus.desktop.core.native_rpa import native_get_text

    kwargs = dict(
        window=window, pid=pid, backend=backend, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index,
    )
    if index is not None:
        sel = _target(index, json_mode, verify=False)
        if sel is not None:
            if "password" in (sel["item"].get("states") or ()):
                # o conteúdo de um campo de senha nunca vai para o agente (nem para o log)
                done(None, json_mode=json_mode, ok=True, human="(password field: value hidden)")
                return
            _apply(sel, kwargs)

    result = native_get_text(timeout=timeout, **kwargs)
    ok = result is not None
    done(
        result, json_mode=json_mode, ok=ok,
        human=(result if ok else "(no text / control not found)"),
    )


@native.command(name="get-state", help="A control's state (by snapshot number or selector).")
@click.argument("index", required=False)
@native_selector_options
@click.option("--timeout", type=float, default=5.0, show_default=True)
@json_option
def get_state(index, window, pid, title, control_type, auto_id, found_index, backend, timeout, json_mode):
    from visus.desktop.core.native_rpa import native_get_state

    sel = _selector(index, json_mode, dict(
        window=window, pid=pid, backend=backend, title=title, control_type=control_type,
        auto_id=auto_id, found_index=found_index,
    ), verify=False)
    result = native_get_state(timeout=timeout, **sel)
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

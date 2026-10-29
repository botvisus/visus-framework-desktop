"""``visus type`` / ``visus key`` -- send text and key chords to the focused app."""

from __future__ import annotations

import click

from .._common import json_option
from .._output import done, fail


@click.command(name="type", help="Type TEXT into the currently focused field.")
@click.argument("text")
@click.option(
    "--interval", type=float, default=0.05, show_default=True,
    help="Per-character delay (raise it for apps that drop fast keystrokes).",
)
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after typing (s).")
@click.option("--backtrack", is_flag=True, help="Retry within a task session on failure.")
@click.option(
    "--virtual", is_flag=True,
    help="Type by window messages into --window's focused control: no keystrokes, "
         "no focus change, the clipboard untouched (the person keeps the PC).",
)
@click.option("--window", "window_title", help="With --virtual: the window (title substring) to type into.")
@json_option
def type_cmd(text, interval, delay, backtrack, virtual, window_title, json_mode):
    """Inline tokens expand: {ctrl}a, {tab}, {enter}, {escape}. Focus the field first
    (with --virtual: a `--virtual` click on the field focuses it, in the background)."""
    from .._common import build_bot

    if virtual:
        _type_virtual(text, window_title, json_mode)
        return
    ok = bool(build_bot().type_text(text, interval=interval, delay=delay, backtrack=backtrack))
    done(ok, json_mode=json_mode, ok=ok, human=("typed" if ok else "type failed"))


def _type_virtual(text, window_title, json_mode):
    if not window_title:
        fail("--virtual needs --window TITLE: the window whose focused control gets the text", json_mode=json_mode)
    from visus.desktop.core import virtual_keyboard
    from visus.desktop.core import window as _window

    hwnd = _window.find_window(window_title)
    if hwnd is None:
        fail(f"no visible window matches {window_title!r} -- `window list` shows the open ones", json_mode=json_mode)
    ok = virtual_keyboard.send_text(virtual_keyboard.focused_control(hwnd), text)
    done(
        ok, json_mode=json_mode, ok=ok,
        human=(
            f"typed into {window_title!r} (virtual keyboard: focus and clipboard untouched -- check the result)"
            if ok else "virtual typing failed"
        ),
    )


@click.command(name="key", help="Press a key or chord (token is CASE-SENSITIVE).")
@click.argument("command")
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after the key (s).")
@click.option("--backtrack", is_flag=True, help="Retry within a task session on failure.")
@json_option
def key_cmd(command, delay, backtrack, json_mode):
    """COMMAND examples: Enter, Escape, Tab, F5, Ctrl+S, Alt+F4, Shift+Tab."""
    from .._common import build_bot

    ok = bool(build_bot().keyboard_command(command, delay=delay, backtrack=backtrack))
    done(
        ok, json_mode=json_mode, ok=ok,
        human=(f"sent {command}" if ok else f"unknown token: {command}"),
    )


@click.command(
    name="keys", help="List the valid keyboard_command tokens (case-sensitive)."
)
@json_option
def keys_cmd(json_mode):
    from visus.desktop import get_available_keyboard_commands

    tokens = list(get_available_keyboard_commands())
    done(tokens, json_mode=json_mode, ok=True, human="\n".join(tokens))

"""``visus type`` / ``visus key`` -- send text and key chords to the focused app."""

from __future__ import annotations

import click

from .._common import json_option
from .._output import done, fail


@click.command(name="type", help="Type TEXT into the currently focused field.")
@click.argument("text")
@click.option(
    "--interval", type=float, default=0.02, show_default=True,
    help="Per-character delay (raise it for apps that drop fast keystrokes).",
)
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after typing (s).")
@click.option("--backtrack", is_flag=True, help="Retry within a task session on failure.")
@click.option(
    "--virtual", is_flag=True,
    help="Type by window messages into --window's focused control: no keystrokes, "
         "no focus change, the clipboard untouched (the person keeps the PC).",
)
@click.option(
    "--window", "window_title",
    help="The window (title substring) to type into: it is brought to the front and "
         "checked first -- nothing is typed while another window is in front. "
         "With --virtual: the window whose focused control gets the text.",
)
@json_option
def type_cmd(text, interval, delay, backtrack, virtual, window_title, json_mode):
    """Inline tokens expand: {ctrl}a, {tab}, {enter}, {escape}. Focus the field first
    (with --virtual: a `--virtual` click on the field focuses it, in the background)."""
    from .._common import build_bot

    if virtual:
        _type_virtual(text, window_title, json_mode)
        return
    if window_title:
        _require_front(window_title, json_mode)
    ok = bool(build_bot().type_text(text, interval=interval, delay=delay, backtrack=backtrack))
    done(ok, json_mode=json_mode, ok=ok, human=("typed" if ok else "type failed"))


def _require_front(window_title, json_mode):
    """Como uma pessoa olha antes de digitar: a janela certa na frente, ou nada sai."""
    from visus.desktop.core.window import foreground_title, front_window

    if front_window(window_title) is None:
        fail(
            f"{window_title!r} is not the window in front (now: {foreground_title()!r}) "
            "-- nothing was typed. Is it open? `window list` shows the open ones.",
            json_mode=json_mode,
        )


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


@click.command(
    name="key",
    help="Press ANY key, chord or sequence -- no fixed list: Enter, Alt, F5, PrintScreen, "
         "Ctrl+S, Ctrl+Shift+;, Win+Shift+S, \"Alt, H, O, I\" (comma = one after another, "
         "e.g. Office key tips). `keys` lists named shortcuts, not a limit.",
)
@click.argument("command")
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after the key (s).")
@click.option("--backtrack", is_flag=True, help="Retry within a task session on failure.")
@click.option(
    "--window", "window_title",
    help="The window (title substring) that gets the key: brought to the front and "
         "checked first -- nothing is pressed while another window is in front.",
)
@json_option
def key_cmd(command, delay, backtrack, window_title, json_mode):
    """COMMAND examples: Enter, Escape, Tab, F5, Ctrl+S, Alt+F4, Shift+Tab, Alt,
    "Alt, H, O, I"."""
    from .._common import build_bot

    if window_title:
        _require_front(window_title, json_mode)

    ok = bool(build_bot().keyboard_command(command, delay=delay, backtrack=backtrack))
    done(
        ok, json_mode=json_mode, ok=ok,
        human=(
            f"sent {command}"
            if ok
            else f"not a key: {command!r} -- any key name works (Enter, Esc, F5, "
            "PageDown, PrintScreen, a single character), joined with + (Ctrl+Shift+S, "
            'Ctrl+;) or separated by commas to press one after another ("Alt, H, O, I")'
        ),
    )


@click.command(
    name="keys", help="List the valid keyboard_command tokens (case-sensitive)."
)
@json_option
def keys_cmd(json_mode):
    from visus.desktop import get_available_keyboard_commands

    tokens = list(get_available_keyboard_commands())
    done(tokens, json_mode=json_mode, ok=True, human="\n".join(tokens))

"""``visus mouse`` -- low-level coordinate-based mouse gestures."""

from __future__ import annotations

import click

from .._common import json_option, virtual_option
from .._output import done

# Negative numbers are values here, not options: scrolling DOWN is `scroll -3`, and a
# monitor left of the primary one has negative X. Without this Click reads `-3` as an
# unknown option and the command fails ("No such option '-3'").
_NUMBERS = {"ignore_unknown_options": True}


@click.group(help="Low-level mouse gestures (coordinate-based).")
def mouse():
    pass


@mouse.command(context_settings=_NUMBERS, name="scroll", help="Scroll the wheel (positive = up, negative = down).")
@click.argument("amount", type=int)
@click.option("--x", type=int, default=None, help="Move to this X before scrolling.")
@click.option("--y", type=int, default=None, help="Move to this Y before scrolling.")
@json_option
def scroll_cmd(amount, x, y, json_mode):
    from visus.desktop import scroll as _scroll

    _scroll(amount, x=x, y=y)
    done(True, json_mode=json_mode, ok=True, human=f"scrolled {amount}")


@mouse.command(context_settings=_NUMBERS, name="drag", help="Drag from (X1,Y1) to (X2,Y2).")
@click.argument("x1", type=int)
@click.argument("y1", type=int)
@click.argument("x2", type=int)
@click.argument("y2", type=int)
@click.option("--duration", type=float, default=0.5, show_default=True, help="Drag duration (s).")
@click.option(
    "--button", default="left", show_default=True,
    type=click.Choice(["left", "middle", "right"]),
)
@json_option
def drag_cmd(x1, y1, x2, y2, duration, button, json_mode):
    from visus.desktop import drag as _drag

    _drag(x1, y1, x2, y2, duration=duration, button=button)
    done(True, json_mode=json_mode, ok=True, human=f"dragged ({x1},{y1}) -> ({x2},{y2})")


@mouse.command(context_settings=_NUMBERS, name="triple-click", help="Triple-click at (X,Y) (or current cursor).")
@click.option("--x", type=int, default=None, help="X coordinate (else current position).")
@click.option("--y", type=int, default=None, help="Y coordinate (else current position).")
@click.option("--interval", type=float, default=0.05, show_default=True, help="Delay between clicks (s).")
@json_option
def triple_click_cmd(x, y, interval, json_mode):
    from visus.desktop import triple_click as _triple

    _triple(x=x, y=y, interval=interval)
    done(True, json_mode=json_mode, ok=True, human="triple-clicked")


@mouse.command(context_settings=_NUMBERS, name="click", help="Click at absolute coordinates (X,Y). Last resort.")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--width", type=int, default=0, help="Box width (clicks the center if given).")
@click.option("--height", type=int, default=0, help="Box height (clicks the center if given).")
@click.option(
    "--button", "mouse_button", default="left", show_default=True,
    type=click.Choice(["left", "right", "double", "move_to"]),
)
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after the click (s).")
@virtual_option
@json_option
def click_cmd(x, y, width, height, mouse_button, delay, virtual, json_mode):
    from .._common import build_bot, click_human, virtual_overrides

    bot = build_bot(**virtual_overrides(virtual))
    ok = bool(bot.click_at((x, y, width, height), mouse_button=mouse_button, delay=delay))
    done(
        ok, json_mode=json_mode, ok=ok,
        human=click_human(bot, ok, f"clicked ({x}, {y})", f"click at ({x}, {y}) failed"),
    )


@mouse.command(context_settings=_NUMBERS, name="move", help="Move the cursor to (X,Y) with a light human jitter.")
@click.argument("x", type=int)
@click.argument("y", type=int)
@click.option("--max-offset", "max_offset", type=int, default=3, show_default=True)
@click.option("--duration", type=float, default=0.2, show_default=True)
@json_option
def move_cmd(x, y, max_offset, duration, json_mode):
    from visus.desktop import move_random as _move

    _move(x, y, max_offset=max_offset, duration=duration)
    done(True, json_mode=json_mode, ok=True, human=f"moved to ({x}, {y})")


@mouse.command(context_settings=_NUMBERS, name="down", help="Press a mouse button without releasing (pair with 'up').")
@click.option("--x", type=int, default=None, help="X (else current position).")
@click.option("--y", type=int, default=None, help="Y (else current position).")
@click.option(
    "--button", default="left", show_default=True,
    type=click.Choice(["left", "middle", "right"]),
)
@json_option
def down_cmd(x, y, button, json_mode):
    from visus.desktop import mouse_down as _down

    _down(x=x, y=y, button=button)
    done(True, json_mode=json_mode, ok=True, human="button down")


@mouse.command(context_settings=_NUMBERS, name="up", help="Release a previously-pressed mouse button.")
@click.option("--x", type=int, default=None, help="X (else current position).")
@click.option("--y", type=int, default=None, help="Y (else current position).")
@click.option(
    "--button", default="left", show_default=True,
    type=click.Choice(["left", "middle", "right"]),
)
@json_option
def up_cmd(x, y, button, json_mode):
    from visus.desktop import mouse_up as _up

    _up(x=x, y=y, button=button)
    done(True, json_mode=json_mode, ok=True, human="button up")

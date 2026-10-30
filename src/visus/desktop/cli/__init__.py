"""Visus CLI Pro -- the agent-native terminal interface for visus-desktop.

A thin Click shell over the already-tested library functions: smart cascade,
native RPA, coordinate-free capture, screenshots, window/process/clipboard
control, project scaffolding, diagnostics, and configuration. Every command
supports ``--json`` for machine-readable output.

The console script is ``visus`` (``visus.desktop.cli:main``).
"""

from __future__ import annotations

import sys

import click

from .commands import capture as capture_cmd
from .commands import clipboard as clipboard_cmd
from .commands import config as config_cmd
from .commands import doctor as doctor_cmd
from .commands import image as image_cmd
from .commands import keyboard as keyboard_cmd
from .commands import mouse as mouse_cmd
from .commands import native as native_cmd
from .commands import open_cmd
from .commands import process as process_cmd
from .commands import project as project_cmd
from .commands import screen as screen_cmd
from .commands import smart as smart_cmd
from .commands import text as text_cmd
from .commands import window as window_cmd
from .repl import repl as repl_cmd

_HELP = """Visus CLI Pro -- agent-native desktop automation.

Drive desktop apps from the shell: the smart cascade (native -> image -> OCR ->
coordinates), no-pixel native RPA, coordinate-free element capture, screenshots,
window / process / clipboard control, project scaffolding, and diagnostics.
Add --json to any command for machine-readable output, or run `visus repl`
for an interactive shell.
"""


@click.group(
    name="visus",
    help=_HELP,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(
    package_name="visus-desktop",
    prog_name="Visus CLI Pro",
    message="%(prog)s %(version)s",
)
def cli():
    pass


cli.add_command(smart_cmd.smart)
cli.add_command(text_cmd.text)
cli.add_command(image_cmd.image)
cli.add_command(mouse_cmd.mouse)
cli.add_command(keyboard_cmd.type_cmd)
cli.add_command(keyboard_cmd.key_cmd)
cli.add_command(keyboard_cmd.keys_cmd)
cli.add_command(native_cmd.native)
cli.add_command(capture_cmd.capture)
cli.add_command(screen_cmd.screenshot)
cli.add_command(screen_cmd.monitors)
cli.add_command(screen_cmd.display_size)
cli.add_command(window_cmd.window)
cli.add_command(process_cmd.process)
cli.add_command(open_cmd.open_cmd)
cli.add_command(clipboard_cmd.clipboard)
cli.add_command(project_cmd.new)
cli.add_command(project_cmd.run)
cli.add_command(project_cmd.report)
cli.add_command(doctor_cmd.doctor)
cli.add_command(config_cmd.configure)
cli.add_command(repl_cmd)


def _prepare_process():
    """What every CLI process needs before it touches the screen or prints.

    DPI: on a Windows display scaled above 100%, a process that never declares
    itself DPI aware gets virtualized coordinates -- a screenshot (physical
    pixels) and a ``mouse click`` disagree. Per-monitor awareness has to be
    claimed before pyautogui/mss/pywinauto import (each claims a weaker mode on
    import, and the first claim wins), so it happens here, first thing.

    UTF-8: read through a pipe -- how an AI agent reads us -- Python falls back
    to the Windows code page and "ação" arrives as garbage.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # pre-8.1 fallback: system aware
        except (AttributeError, OSError):
            pass


def main(argv=None):
    """Entry point for the ``visus`` console script and programmatic callers.

    Returns an integer exit code (it never raises ``SystemExit`` to the
    caller), so it is safe to call from tests, the REPL, and scripts.
    """
    _prepare_process()
    try:
        rv = cli.main(args=argv, prog_name="visus", standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except click.exceptions.Abort:
        click.echo("Aborted.", err=True)
        return 1
    except SystemExit as exc:  # belt-and-suspenders if a command sys.exit()s
        code = exc.code
        return 0 if code is None else (code if isinstance(code, int) else 1)
    # ``standalone_mode=False`` makes ``ctx.exit(code)`` return the code here.
    return rv if isinstance(rv, int) else 0


if __name__ == "__main__":  # pragma: no cover - exercised via the console script
    sys.exit(main(sys.argv[1:]))

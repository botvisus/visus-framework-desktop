"""``visus process`` -- launch / find / kill processes."""

from __future__ import annotations

import os
import shlex
import subprocess

import click

from .._common import interactive, json_option
from .._output import done, fail


@click.group(help="Process management.")
def process():
    pass


@click.command(help="Launch a process. Returns {pid, command}.")
@click.argument("command")
@click.argument("args", nargs=-1)
@json_option
def launch(command, args, json_mode):
    if args:
        argv = [command, *args]
    else:
        argv = shlex.split(command, posix=(os.name != "nt"))
    proc = subprocess.Popen(argv)  # noqa: S603 - caller-controlled command
    result = {"pid": int(proc.pid), "command": argv}
    done(
        result, json_mode=json_mode, ok=True,
        human=f"launched pid {proc.pid}: {' '.join(argv)}",
    )


@click.command(help="Find processes whose name contains NAME.")
@click.argument("name")
@json_option
def find(name, json_mode):
    import psutil

    needle = (name or "").lower()
    matches = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            pname = proc.info.get("name") or ""
            if needle and needle in pname.lower():
                matches.append({"pid": int(proc.pid), "name": pname})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    human = "\n".join(f"{m['pid']}\t{m['name']}" for m in matches) or "(no matches)"
    done(matches, json_mode=json_mode, ok=True, human=human)


@click.command(help="Terminate a process by PID (destructive -- requires confirmation).")
@click.argument("pid", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip the confirmation prompt.")
@json_option
def kill(pid, yes, json_mode):
    if not yes:
        if json_mode or not interactive():
            fail(
                f"not killed: pass --yes to end it without asking (process kill {pid} --yes). "
                "Nothing was killed, safe to retry.",
                json_mode=json_mode,
            )
            return
        if not click.confirm(f"Kill process {pid}?"):
            click.echo("Aborted.", err=True)
            click.get_current_context().exit(1)
    from visus.desktop.core.process import kill_process

    result = bool(kill_process(pid))
    done(
        result, json_mode=json_mode, ok=result,
        human=(f"killed {pid}" if result else f"failed to kill {pid}"),
    )


@click.command(name="is-running", help="Check whether any process name contains NAME.")
@click.argument("name")
@json_option
def is_running(name, json_mode):
    from visus.desktop.core.process import is_process_running

    result = bool(is_process_running(name))
    done(
        result, json_mode=json_mode, ok=result,
        human=("running" if result else "not running"),
    )


process.add_command(launch)
process.add_command(find)
process.add_command(kill)
process.add_command(is_running)

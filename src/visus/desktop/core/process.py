"""Visus Desktop - Process management utilities.

Cross-platform helpers for launching, locating, and terminating operating
system processes. The optional dependency :mod:`psutil` is imported lazily
inside each function so this module can be imported even in environments
where ``psutil`` is not installed (the relevant function will simply raise
``ImportError`` only when actually called).
"""

from __future__ import annotations

import os
import platform
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    import psutil


def launch(path: str) -> None:
    """Launch an application or open a file/document.

    On Windows the platform's default association is used via
    :func:`os.startfile`. On other platforms the command is parsed with
    :func:`shlex.split` (POSIX-quoted) and executed with
    :class:`subprocess.Popen`, so a path containing spaces stays intact
    when surrounded by single or double quotes.

    Args:
        path: Path to the executable, file, or command line to launch.

    Returns:
        None
    """
    if platform.system() == "Windows":
        # ``os.startfile`` is only available on Windows.
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606
    else:
        import shlex

        subprocess.Popen(shlex.split(path))  # noqa: S603


def find_process(
    name: str | None = None, pid: int | None = None
) -> psutil.Process | None:
    """Find the first running process matching ``name`` or ``pid``.

    Iterates over :func:`psutil.process_iter` and returns the first process
    whose name contains ``name`` (case-insensitive) or whose pid equals
    ``pid``. ``psutil.NoSuchProcess`` and ``psutil.AccessDenied`` errors
    raised while inspecting individual processes are swallowed so a single
    inaccessible process does not abort the search.

    Args:
        name: Optional substring to match against each process name
            (case-insensitive).
        pid: Optional exact process id to match.

    Returns:
        psutil.Process | None: The first matching process, or ``None`` if no
        process matched.
    """
    import psutil

    name_lower = name.lower() if name is not None else None

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if pid is not None and proc.pid == pid:
                return proc
            if name_lower is not None:
                proc_name = proc.info.get("name") or ""
                if name_lower in proc_name.lower():
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process vanished or is inaccessible; skip it and keep searching.
            continue

    return None


def is_process_running(name: str) -> bool:
    """Return whether a process whose name contains ``name`` is running.

    Args:
        name: Substring to match against process names (case-insensitive).

    Returns:
        bool: ``True`` if a matching process is running, ``False`` otherwise.
    """
    return find_process(name=name) is not None


def kill_process(target: psutil.Process | int | str) -> bool:
    """Terminate a process identified by a Process object, pid, or name.

    The ``target`` is resolved to a :class:`psutil.Process`:

    * a :class:`psutil.Process` is used directly;
    * an ``int`` is treated as a pid;
    * a ``str`` is treated as a name substring (case-insensitive).

    The process is asked to terminate gracefully via ``terminate()``; if it is
    still alive after a short wait, ``kill()`` is used as a fallback.

    Args:
        target: A :class:`psutil.Process`, a pid (``int``), or a name
            substring (``str``).

    Returns:
        bool: ``True`` if a process was found and terminated, ``False`` if no
        matching process could be found.
    """
    import psutil

    # Resolve the target to a Process instance.
    if isinstance(target, psutil.Process):
        proc: psutil.Process | None = target
    elif isinstance(target, bool):
        # ``bool`` is a subclass of ``int``; reject it explicitly to avoid
        # treating ``True``/``False`` as pids.
        proc = None
    elif isinstance(target, int):
        proc = find_process(pid=target)
    elif isinstance(target, str):
        proc = find_process(name=target)
    else:
        proc = None

    if proc is None:
        return False

    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            # Graceful termination did not complete in time; force kill.
            proc.kill()
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                return False
        return True
    except psutil.NoSuchProcess:
        # The process already exited; treat as a successful termination.
        return True
    except psutil.AccessDenied:
        return False

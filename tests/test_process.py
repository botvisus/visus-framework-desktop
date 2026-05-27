"""Tests for :mod:`visus.desktop.core.process`.

These tests are deliberately non-destructive: they only ever inspect the
current Python process and a guaranteed-nonexistent pid/name. No real user
process is ever terminated.
"""

from __future__ import annotations

import os

import psutil

from visus.desktop.core.process import (
    find_process,
    is_process_running,
    kill_process,
)


def test_find_process_by_name_finds_current_process() -> None:
    """The current interpreter should be discoverable by its own name."""
    current_name = psutil.Process(os.getpid()).name()

    found = find_process(name=current_name)

    assert found is not None
    # The match is case-insensitive and substring-based, so the resolved
    # process name must contain the queried name.
    assert current_name.lower() in (found.info.get("name") or found.name()).lower()


def test_find_process_by_pid_returns_matching_process() -> None:
    """Searching by the current pid should return a process with that pid."""
    found = find_process(pid=os.getpid())

    assert found is not None
    assert found.pid == os.getpid()


def test_is_process_running_false_for_unknown_name() -> None:
    """A clearly bogus process name must report as not running."""
    assert is_process_running("definitely_not_a_real_proc_xyz") is False


def test_kill_process_returns_false_for_nonexistent_pid() -> None:
    """Killing a nonexistent pid must return ``False`` and not raise."""
    assert kill_process(99999999) is False

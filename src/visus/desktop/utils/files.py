"""
Visus Desktop - File Utilities

Helper functions for waiting on files to appear and to stop changing, which is
useful when automating downloads or watching for output produced by external
processes.
"""

from __future__ import annotations

import os
import time


def wait_for_file(path: str, timeout: float = 10.0, poll_interval: float = 0.5) -> bool:
    """
    Wait until a file exists and is readable.

    The path is considered ready when it exists on disk and the current process
    has read access to it (``os.access(path, os.R_OK)``).

    Args:
        path: Filesystem path to wait for.
        timeout: Maximum number of seconds to wait before giving up.
        poll_interval: Number of seconds to sleep between existence checks.

    Returns:
        True if the file appeared and became readable before ``timeout``
        elapsed, otherwise False.
    """
    deadline = time.monotonic() + timeout
    while True:
        if os.path.exists(path) and os.access(path, os.R_OK):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)


def wait_for_file_stable(
    path: str,
    timeout: float = 30.0,
    stable_for: float = 1.0,
    poll_interval: float = 0.5,
) -> bool:
    """
    Wait until a file exists and its size stops changing.

    This is typically used to detect that a download (or any incremental write)
    has finished: the file size is sampled on each poll and considered stable
    once it has not changed for at least ``stable_for`` seconds.

    Args:
        path: Filesystem path to monitor.
        timeout: Maximum number of seconds to wait before giving up.
        stable_for: Number of seconds the size must remain unchanged to be
            considered stable.
        poll_interval: Number of seconds to sleep between size checks.

    Returns:
        True if the file existed and its size stabilized before ``timeout``
        elapsed, otherwise False.
    """
    deadline = time.monotonic() + timeout
    last_size: int | None = None
    stable_since: float | None = None

    while True:
        now = time.monotonic()
        try:
            current_size = os.path.getsize(path)
        except OSError:
            # File does not exist yet (or is temporarily inaccessible); reset
            # the stability tracking and keep waiting.
            current_size = None

        if current_size is None:
            last_size = None
            stable_since = None
        elif current_size != last_size:
            # Size changed (or first observation): restart the stability timer.
            last_size = current_size
            stable_since = now
        elif stable_since is not None and (now - stable_since) >= stable_for:
            return True

        if now >= deadline:
            return False
        time.sleep(poll_interval)

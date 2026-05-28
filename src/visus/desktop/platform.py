"""Platform detection helpers (Phase 4 / X4).

Tiny module dedicated to runtime "where am I running?" checks that are
useful across several subsystems (doctor, screen capture, native
automation). Today it focuses on WSL detection so the diagnostic CLI
can show a useful hint when the user expects a display but no X server
is reachable.
"""

from __future__ import annotations

import os
import sys


def _read_proc_version() -> str | None:
    """Return ``/proc/version`` contents or ``None`` when unavailable."""
    if sys.platform != "linux":
        return None
    try:
        with open("/proc/version", encoding="utf-8") as fh:
            return fh.read()
    except OSError:  # pragma: no cover - unreadable in restrictive envs
        return None


def is_wsl() -> bool:
    """Return True when the current process runs inside WSL (1 or 2)."""
    content = _read_proc_version()
    if not content:
        return False
    lowered = content.lower()
    return "microsoft" in lowered or "wsl" in lowered


def wsl_display_hint() -> str | None:
    """Return a short setup hint when WSL has no X server reachable.

    Returns None outside of WSL or when ``$DISPLAY`` is already set.
    The string is meant to be shown verbatim by ``visus-doctor`` and
    any other diagnostic surface.
    """
    if not is_wsl():
        return None
    if os.environ.get("DISPLAY"):
        return None
    return (
        "WSL detected without DISPLAY set. Install an X server "
        "(WSLg on Windows 11+, or VcXsrv / X410 on Windows 10) and "
        "export DISPLAY=:0 so visus-desktop can reach a display."
    )

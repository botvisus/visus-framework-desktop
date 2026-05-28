"""Linux WindowManager backend (Phase 4, X1).

Shells out to ``xdotool`` (find / focus / minimize / close) and
``wmctrl`` (maximize). Both are tiny CLI utilities that ship on every
mainstream X11 desktop:

    sudo apt-get install xdotool wmctrl

On a Wayland-only session these commands are unavailable; the helpers
return ``False`` (or ``None`` for the lookup) so callers can branch.
``visus-doctor`` reports missing tools when the active backend needs
them.
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def _run(cmd: list[str]) -> subprocess.CompletedProcess | None:
    """Run ``cmd``; return CompletedProcess or ``None`` if the binary is missing."""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        logger.debug("CLI tool missing for window management: %s", exc)
        return None


def find_window_linux(title_substring: str) -> str | None:
    """Return the first X11 window id whose title matches, or ``None``."""
    result = _run(["xdotool", "search", "--name", title_substring])
    if result is None or result.returncode != 0:
        return None
    first = (result.stdout or "").splitlines()
    return first[0].strip() if first else None


def focus_window_linux(title_substring: str) -> bool:
    """Bring a matching window to the foreground via ``xdotool windowactivate``."""
    wid = find_window_linux(title_substring)
    if wid is None:
        return False
    result = _run(["xdotool", "windowactivate", wid])
    return bool(result and result.returncode == 0)


def maximize_window_linux(title_substring: str) -> bool:
    """Maximize a matching window via ``wmctrl -i -r ID -b add,maximized_*``."""
    wid = find_window_linux(title_substring)
    if wid is None:
        return False
    result = _run(
        [
            "wmctrl",
            "-i",
            "-r",
            wid,
            "-b",
            "add,maximized_vert,maximized_horz",
        ]
    )
    return bool(result and result.returncode == 0)


def minimize_window_linux(title_substring: str) -> bool:
    """Minimize a matching window via ``xdotool windowminimize``."""
    wid = find_window_linux(title_substring)
    if wid is None:
        return False
    result = _run(["xdotool", "windowminimize", wid])
    return bool(result and result.returncode == 0)


def close_window_linux(title_substring: str) -> bool:
    """Request that a matching window close via ``xdotool windowclose``."""
    wid = find_window_linux(title_substring)
    if wid is None:
        return False
    result = _run(["xdotool", "windowclose", wid])
    return bool(result and result.returncode == 0)

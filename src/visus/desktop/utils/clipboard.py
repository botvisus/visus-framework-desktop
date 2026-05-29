"""
Visus Desktop - Clipboard Utilities

Thin wrappers around :mod:`pyperclip` for copying and pasting text. The
``pyperclip`` import is performed lazily inside each function so that importing
this module never fails even when ``pyperclip`` is not installed.
"""

from __future__ import annotations


def copy(text: str, retries: int = 5, delay: float = 0.1) -> None:
    """
    Copy text to the system clipboard, retrying on transient Windows locks.

    Windows allows only one process to own the clipboard at a time, so a
    clipboard manager / browser / editor briefly holding it makes
    ``OpenClipboard`` fail with a (often misleadingly worded) error. We retry
    with a short backoff before giving up.

    Args:
        text: The text to place on the clipboard.
        retries: How many attempts before re-raising the last error.
        delay: Initial backoff in seconds (doubles each attempt, capped).

    Raises:
        The underlying ``pyperclip`` error if every attempt fails.
    """
    import time

    import pyperclip

    wait = delay
    last_exc: Exception | None = None
    for _ in range(max(1, retries)):
        try:
            pyperclip.copy(text)
            return
        except Exception as exc:  # pyperclip raises PyperclipWindowsException etc.
            last_exc = exc
            time.sleep(wait)
            wait = min(wait * 2, 1.0)
    if last_exc is not None:
        raise last_exc


def paste() -> str:
    """
    Return the current text contents of the system clipboard.

    Returns:
        The text currently held on the clipboard.
    """
    import pyperclip

    return pyperclip.paste()


def get_clipboard() -> str:
    """
    Return the current text contents of the system clipboard.

    This is an alias of :func:`paste`.

    Returns:
        The text currently held on the clipboard.
    """
    return paste()

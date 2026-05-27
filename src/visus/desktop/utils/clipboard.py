"""
Visus Desktop - Clipboard Utilities

Thin wrappers around :mod:`pyperclip` for copying and pasting text. The
``pyperclip`` import is performed lazily inside each function so that importing
this module never fails even when ``pyperclip`` is not installed.
"""

from __future__ import annotations


def copy(text: str) -> None:
    """
    Copy text to the system clipboard.

    Args:
        text: The text to place on the clipboard.
    """
    import pyperclip

    pyperclip.copy(text)


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

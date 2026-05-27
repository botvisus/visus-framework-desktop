"""Visus Desktop - Native (accessibility) automation.

A self-contained wrapper around `pywinauto <https://pywinauto.readthedocs.io>`_
that exposes a small, BotCity-like API for connecting to running applications
and interacting with their windows and controls through the Windows
accessibility layers (WIN32 and UIA).

This mirrors the ``connect_to_app`` / ``find_app_window`` / ``find_app_element``
workflow: connect to an already-running application, locate a top-level window,
drill into a child control, and then click, read, or type into it.

``pywinauto`` is imported lazily inside each function so this module can be
imported on any platform (including non-Windows or environments where
``pywinauto`` is not installed). The relevant function will only fail when it
is actually called.
"""

from __future__ import annotations

import enum
import time
from typing import Any


class Backend(str, enum.Enum):
    """Supported pywinauto accessibility backends.

    The enum subclasses :class:`str` so a member compares equal to its plain
    string value and can be passed transparently where a string is expected.

    Attributes:
        WIN32: The classic Win32 backend (``"win32"``). Fast and reliable for
            native Win32 controls.
        UIA: The Microsoft UI Automation backend (``"uia"``). Required for
            modern frameworks such as WPF, WinForms, Qt, and UWP applications.
    """

    WIN32 = "win32"
    UIA = "uia"


class NativeError(Exception):
    """Raised when native (accessibility) automation fails."""


def _backend_value(backend: Backend | str) -> str:
    """Return the plain string value of a backend specifier.

    Args:
        backend: A :class:`Backend` member or a raw backend string.

    Returns:
        str: The backend's string value (for example ``"uia"`` or ``"win32"``).
    """
    if isinstance(backend, Backend):
        return backend.value
    return str(backend)


def connect_to_app(
    backend: Backend | str = Backend.UIA,
    timeout: float = 60.0,
    poll_interval: float = 0.5,
    **selectors: Any,
):
    """Connect to an already-running application, retrying until it appears.

    Repeatedly attempts ``Application(backend=...).connect(**selectors)`` until
    it succeeds or ``timeout`` seconds elapse. Between failed attempts the call
    sleeps for ``poll_interval`` seconds. This is useful when the target
    application is still starting up.

    Args:
        backend: The accessibility backend to use, either a :class:`Backend`
            member or its string value (``"uia"`` or ``"win32"``). Defaults to
            :attr:`Backend.UIA`.
        timeout: Maximum number of seconds to keep retrying the connection
            before giving up. Defaults to ``60.0``.
        poll_interval: Number of seconds to sleep between connection attempts.
            Defaults to ``0.5``.
        **selectors: Selector keyword arguments forwarded directly to
            ``pywinauto`` ``Application.connect`` (for example ``title``,
            ``title_re``, ``class_name``, ``process``, ``handle``, ``path``).

    Returns:
        pywinauto.application.Application: The connected ``Application`` object.

    Raises:
        NativeError: If no connection could be established within ``timeout``
            seconds. The last underlying exception is chained as the cause.
    """
    from pywinauto.application import Application

    backend_value = _backend_value(backend)

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while True:
        try:
            app = Application(backend=backend_value)
            app.connect(**selectors)
            return app
        except Exception as exc:  # noqa: BLE001 - retried until timeout, then re-raised
            last_error = exc

        if time.monotonic() >= deadline:
            raise NativeError(
                f"Could not connect to application within {timeout} seconds "
                f"using backend {backend_value!r} and selectors {selectors!r}: "
                f"{last_error}"
            ) from last_error

        time.sleep(poll_interval)


def find_window(app, timeout: float = 10.0, **selectors: Any):
    """Find a top-level window of a connected application.

    Resolves a window specification via ``app.window(**selectors)`` and waits
    for it to exist and be ready.

    Args:
        app: A connected ``pywinauto`` ``Application`` (typically the return
            value of :func:`connect_to_app`).
        timeout: Maximum number of seconds to wait for the window to exist and
            become ready. Defaults to ``10.0``.
        **selectors: Selector keyword arguments forwarded to ``app.window``
            (for example ``title``, ``title_re``, ``class_name``,
            ``auto_id``, ``control_type``).

    Returns:
        pywinauto.application.WindowSpecification | None: The matching window
        specification, or ``None`` if no matching window appeared within
        ``timeout`` seconds.
    """
    # Imported only to reference pywinauto's exception types.
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto.timings import TimeoutError as PywinautoTimeoutError

    try:
        dialog = app.window(**selectors)
        dialog.wait("exists ready", timeout=timeout)
        return dialog
    except (PywinautoTimeoutError, ElementNotFoundError):
        return None


def find_element(
    app_or_window,
    from_parent_window=None,
    timeout: float = 10.0,
    **selectors: Any,
):
    """Find a window or a child control within a parent window.

    Behaves in one of two modes:

    * When ``from_parent_window`` is ``None`` this is equivalent to
      :func:`find_window`, treating ``app_or_window`` as a connected
      ``Application`` and locating a top-level window.
    * When ``from_parent_window`` is provided it locates a descendant control
      via ``from_parent_window.child_window(**selectors)`` and waits for it to
      exist and be ready.

    Args:
        app_or_window: A connected ``Application`` used to locate a top-level
            window when ``from_parent_window`` is ``None``. When
            ``from_parent_window`` is provided this argument is unused.
        from_parent_window: Optional parent window specification to search
            within. When provided, the lookup uses ``child_window`` instead of
            ``window``.
        timeout: Maximum number of seconds to wait for the element to exist and
            become ready. Defaults to ``10.0``.
        **selectors: Selector keyword arguments forwarded to ``window`` or
            ``child_window`` (for example ``title``, ``auto_id``,
            ``control_type``, ``class_name``).

    Returns:
        The matching window or child-control specification, or ``None`` if no
        matching element appeared within ``timeout`` seconds.
    """
    if from_parent_window is None:
        return find_window(app_or_window, timeout=timeout, **selectors)

    # Imported only to reference pywinauto's exception types.
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto.timings import TimeoutError as PywinautoTimeoutError

    try:
        element = from_parent_window.child_window(**selectors)
        element.wait("exists ready", timeout=timeout)
        return element
    except (PywinautoTimeoutError, ElementNotFoundError):
        return None


def click_element(element) -> None:
    """Perform a real mouse click on a control.

    Uses ``click_input`` which moves the physical mouse cursor and clicks,
    producing a genuine input event (as opposed to a synthesized message).

    Args:
        element: A ``pywinauto`` control wrapper or window specification.

    Returns:
        None
    """
    element.click_input()


def set_text(element, text: str) -> None:
    """Set the text content of an editable control.

    Prefers ``set_edit_text`` (which replaces the whole content atomically) when
    the control exposes it; otherwise falls back to simulating keystrokes via
    ``type_keys`` with spaces preserved.

    Args:
        element: A ``pywinauto`` control wrapper or window specification.
        text: The text to write into the control.

    Returns:
        None
    """
    set_edit_text = getattr(element, "set_edit_text", None)
    if callable(set_edit_text):
        set_edit_text(text)
    else:
        element.type_keys(text, with_spaces=True)


def get_text(element) -> str:
    """Return the visible text of a control.

    Args:
        element: A ``pywinauto`` control wrapper or window specification.

    Returns:
        str: The control's window text as reported by ``window_text``.
    """
    return element.window_text()

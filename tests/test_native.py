"""Tests for :mod:`visus.desktop.core.native`.

The entire ``pywinauto`` layer is monkeypatched so no real application is ever
launched or connected to. ``pywinauto.application.Application`` is replaced with
a fake whose ``connect`` either succeeds or raises, and fake window/control
objects record the calls made against them.

The module is skipped on non-Windows platforms and when ``pywinauto`` cannot be
imported.
"""

from __future__ import annotations

import sys

import pytest

try:  # pragma: no cover - import guard
    import pywinauto  # noqa: F401
    from pywinauto.findwindows import ElementNotFoundError
    from pywinauto.timings import TimeoutError as PywinautoTimeoutError

    _PYWINAUTO_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    _PYWINAUTO_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or not _PYWINAUTO_AVAILABLE,
    reason="Native automation requires Windows and pywinauto",
)

from visus.desktop.core.native import (  # noqa: E402 - imported after skip guard
    Backend,
    NativeError,
    click_element,
    connect_to_app,
    find_element,
    find_window,
    get_text,
    set_text,
)


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeApp:
    """A stand-in for a connected pywinauto Application."""

    def __init__(self) -> None:
        self.window_calls: list[dict] = []
        self.window_return = None

    def window(self, **selectors):
        self.window_calls.append(selectors)
        return self.window_return


class _FakeWindow:
    """A stand-in for a WindowSpecification with ``wait``/``child_window``."""

    def __init__(self, wait_exc: Exception | None = None) -> None:
        self.wait_calls: list[tuple[str, float]] = []
        self.wait_exc = wait_exc
        self.child_calls: list[dict] = []
        self.child_return = None

    def wait(self, condition, timeout=None):
        self.wait_calls.append((condition, timeout))
        if self.wait_exc is not None:
            raise self.wait_exc
        return self

    def child_window(self, **selectors):
        self.child_calls.append(selectors)
        return self.child_return


class _FakeElement:
    """A control wrapper recording click/text interactions.

    ``set_edit_text`` is intentionally *not* defined on the class. It is only
    attached as an instance attribute via
    :func:`_make_element_with_set_edit_text`, so that
    :func:`_make_element_without_set_edit_text` produces an element on which
    ``getattr(element, "set_edit_text", None)`` returns ``None`` and the
    ``type_keys`` fallback is exercised.
    """

    def __init__(self) -> None:
        self.click_input_called = 0
        self.set_edit_text_arg = None
        self.type_keys_calls: list[tuple] = []

    def click_input(self):
        self.click_input_called += 1

    def type_keys(self, text, with_spaces=False):
        self.type_keys_calls.append((text, with_spaces))

    def window_text(self):
        return "hello world"


def _make_element_with_set_edit_text() -> _FakeElement:
    el = _FakeElement()

    def set_edit_text(text):
        el.set_edit_text_arg = text

    el.set_edit_text = set_edit_text  # type: ignore[attr-defined]
    return el


def _make_element_without_set_edit_text() -> _FakeElement:
    # No ``set_edit_text`` attribute -> falls back to type_keys.
    return _FakeElement()


# --------------------------------------------------------------------------- #
# connect_to_app
# --------------------------------------------------------------------------- #
def test_connect_to_app_success_passes_backend_and_selectors(monkeypatch):
    created_backends: list[str] = []
    connect_calls: list[dict] = []
    fake_app = _FakeApp()

    class FakeApplication:
        def __init__(self, backend=None):
            created_backends.append(backend)

        def connect(self, **selectors):
            connect_calls.append(selectors)
            return fake_app

    monkeypatch.setattr(pywinauto.application, "Application", FakeApplication)

    result = connect_to_app(
        backend=Backend.UIA,
        timeout=5.0,
        poll_interval=0.1,
        title="Calculator",
        process=1234,
    )

    # The connect() return value is ignored; the Application instance is what
    # connect_to_app returns. With our fake, that is the FakeApplication.
    assert isinstance(result, FakeApplication)
    assert created_backends == ["uia"]
    assert connect_calls == [{"title": "Calculator", "process": 1234}]


def test_connect_to_app_accepts_backend_string(monkeypatch):
    created_backends: list[str] = []

    class FakeApplication:
        def __init__(self, backend=None):
            created_backends.append(backend)

        def connect(self, **selectors):
            return self

    monkeypatch.setattr(pywinauto.application, "Application", FakeApplication)

    connect_to_app(backend="win32", timeout=1.0, poll_interval=0.1, title="x")
    assert created_backends == ["win32"]


def test_connect_to_app_timeout_raises_native_error(monkeypatch):
    attempts = {"count": 0}

    class FakeApplication:
        def __init__(self, backend=None):
            pass

        def connect(self, **selectors):
            attempts["count"] += 1
            raise RuntimeError("not running yet")

    monkeypatch.setattr(pywinauto.application, "Application", FakeApplication)

    with pytest.raises(NativeError) as excinfo:
        connect_to_app(backend=Backend.UIA, timeout=0.3, poll_interval=0.1, title="x")

    # The last underlying error is chained as the cause.
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    # It retried more than once before giving up.
    assert attempts["count"] >= 2


# --------------------------------------------------------------------------- #
# find_window
# --------------------------------------------------------------------------- #
def test_find_window_returns_ready_dialog():
    app = _FakeApp()
    dialog = _FakeWindow()
    app.window_return = dialog

    result = find_window(app, timeout=3.0, title="Main", auto_id="main")

    assert result is dialog
    assert app.window_calls == [{"title": "Main", "auto_id": "main"}]
    assert dialog.wait_calls == [("exists ready", 3.0)]


def test_find_window_returns_none_on_timeout():
    app = _FakeApp()
    app.window_return = _FakeWindow(wait_exc=PywinautoTimeoutError())

    assert find_window(app, timeout=0.5, title="Missing") is None


def test_find_window_returns_none_on_element_not_found():
    app = _FakeApp()
    app.window_return = _FakeWindow(wait_exc=ElementNotFoundError())

    assert find_window(app, title="Missing") is None


# --------------------------------------------------------------------------- #
# find_element
# --------------------------------------------------------------------------- #
def test_find_element_without_parent_behaves_like_find_window():
    app = _FakeApp()
    dialog = _FakeWindow()
    app.window_return = dialog

    result = find_element(app, timeout=2.0, title="Main")

    assert result is dialog
    assert app.window_calls == [{"title": "Main"}]
    assert dialog.wait_calls == [("exists ready", 2.0)]


def test_find_element_with_parent_uses_child_window_and_forwards_selectors():
    parent = _FakeWindow()
    child = _FakeWindow()
    parent.child_return = child

    result = find_element(
        None,
        from_parent_window=parent,
        timeout=4.0,
        auto_id="okButton",
        control_type="Button",
    )

    assert result is child
    assert parent.child_calls == [
        {"auto_id": "okButton", "control_type": "Button"}
    ]
    assert child.wait_calls == [("exists ready", 4.0)]


def test_find_element_with_parent_returns_none_on_timeout():
    parent = _FakeWindow()
    parent.child_return = _FakeWindow(wait_exc=PywinautoTimeoutError())

    result = find_element(
        None, from_parent_window=parent, timeout=0.5, auto_id="x"
    )
    assert result is None


def test_find_element_with_parent_returns_none_on_element_not_found():
    parent = _FakeWindow()
    parent.child_return = _FakeWindow(wait_exc=ElementNotFoundError())

    result = find_element(None, from_parent_window=parent, auto_id="x")
    assert result is None


# --------------------------------------------------------------------------- #
# click_element / set_text / get_text
# --------------------------------------------------------------------------- #
def test_click_element_calls_click_input():
    element = _make_element_with_set_edit_text()
    click_element(element)
    assert element.click_input_called == 1


def test_set_text_prefers_set_edit_text():
    element = _make_element_with_set_edit_text()
    set_text(element, "abc def")
    assert element.set_edit_text_arg == "abc def"
    assert element.type_keys_calls == []


def test_set_text_falls_back_to_type_keys():
    element = _make_element_without_set_edit_text()
    set_text(element, "abc def")
    assert element.type_keys_calls == [("abc def", True)]


def test_get_text_returns_window_text():
    element = _make_element_with_set_edit_text()
    assert get_text(element) == "hello world"

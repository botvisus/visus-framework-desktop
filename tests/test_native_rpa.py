"""Tests for the native RPA module (no-pixel automation via UIA)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from visus.desktop.core import native_rpa as nr


def _fake_pywinauto(top):
    """Build a fake pywinauto whose Application().top_window() == top."""
    app = MagicMock()
    app.connect = MagicMock()
    app.top_window = MagicMock(return_value=top)
    return MagicMock(Application=MagicMock(return_value=app))


def _ctrl(exists=True, rect=(10, 20, 60, 40)):
    c = MagicMock()
    c.exists = MagicMock(return_value=exists)
    r = MagicMock(left=rect[0], top=rect[1], right=rect[2], bottom=rect[3])
    c.rectangle = MagicMock(return_value=r)
    return c


def _patch(top, *, foreground=None):
    """Context: patch sys.modules pywinauto + (optional) foreground window."""
    fake = _fake_pywinauto(top)
    patches = [patch.dict(sys.modules, {"pywinauto": fake})]
    if foreground is not None:
        patches.append(
            patch(
                "visus.desktop.core.locators.get_foreground_window",
                return_value=foreground,
            )
        )
    return patches


def _enter(patches):
    for p in patches:
        p.start()


def _exit(patches):
    for p in reversed(patches):
        p.stop()


# ---------------------------------------------------------------------------
# Missing dependency
# ---------------------------------------------------------------------------


class TestNoPywinauto:
    def test_all_functions_degrade_gracefully(self):
        real_import = __import__

        def fake_import(name, *a, **k):
            if name == "pywinauto":
                raise ImportError(name)
            return real_import(name, *a, **k)

        with patch("builtins.__import__", side_effect=fake_import):
            assert nr.native_dump_tree(pid=1) == []
            assert nr.native_click(pid=1, title="X") is False
            assert nr.native_set_text(pid=1, title="X", text="y") is False
            assert nr.native_get_text(pid=1, title="X") is None
            assert nr.native_get_state(pid=1, title="X") is None
            assert nr.native_wait(pid=1, title="X") is False


# ---------------------------------------------------------------------------
# dump_tree
# ---------------------------------------------------------------------------


class TestDumpTree:
    def test_walks_children_to_max_depth(self):
        leaf = MagicMock()
        leaf.element_info.control_type = "Button"
        leaf.element_info.name = "Salvar"
        leaf.element_info.automation_id = "btnSave"
        leaf.children = MagicMock(return_value=[])
        leaf.rectangle = MagicMock(
            return_value=MagicMock(left=1, top=2, right=3, bottom=4)
        )

        top = MagicMock()
        top.children = MagicMock(return_value=[leaf])

        patches = _patch(top)
        _enter(patches)
        try:
            nodes = nr.native_dump_tree(pid=42, max_depth=2)
        finally:
            _exit(patches)

        assert len(nodes) == 1
        assert nodes[0]["control_type"] == "Button"
        assert nodes[0]["title"] == "Salvar"
        assert nodes[0]["auto_id"] == "btnSave"
        assert nodes[0]["depth"] == 1

    def test_returns_empty_when_no_top_window(self):
        # top_window() returns None -> dump must be empty, not crash.
        fake = _fake_pywinauto(None)
        fake.Application.return_value.top_window.return_value = None
        with patch.dict(sys.modules, {"pywinauto": fake}):
            assert nr.native_dump_tree(pid=1) == []


# ---------------------------------------------------------------------------
# click
# ---------------------------------------------------------------------------


class TestClick:
    def test_invoke_path(self):
        ctrl = _ctrl()
        ctrl.invoke = MagicMock()
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_click(pid=1, title="Salvar", method="invoke")
        finally:
            _exit(patches)
        assert ok is True
        ctrl.invoke.assert_called_once()

    def test_auto_falls_back_to_click_input(self):
        ctrl = _ctrl()
        ctrl.invoke = MagicMock(side_effect=RuntimeError("no invoke pattern"))
        ctrl.click_input = MagicMock()
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_click(pid=1, title="X", method="auto")
        finally:
            _exit(patches)
        assert ok is True
        ctrl.click_input.assert_called_once()

    def test_missing_control_returns_false(self):
        ctrl = _ctrl(exists=False)
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_click(pid=1, title="Ghost", retries=0)
        finally:
            _exit(patches)
        assert ok is False

    def test_selector_kwargs_forwarded(self):
        ctrl = _ctrl()
        ctrl.invoke = MagicMock()
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            nr.native_click(
                pid=1, title="Salvar", control_type="Button", auto_id="btn1"
            )
        finally:
            _exit(patches)
        kwargs = top.child_window.call_args.kwargs
        assert kwargs == {
            "title": "Salvar",
            "control_type": "Button",
            "auto_id": "btn1",
        }

    def test_retries_then_succeeds(self):
        # exists() returns False the first attempt, True the second.
        ctrl = MagicMock()
        ctrl.exists = MagicMock(side_effect=[False, True])
        ctrl.invoke = MagicMock()
        ctrl.rectangle = MagicMock(
            return_value=MagicMock(left=0, top=0, right=1, bottom=1)
        )
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_click(pid=1, title="X", retries=1, delay=0)
        finally:
            _exit(patches)
        assert ok is True

    def test_double_click(self):
        ctrl = _ctrl()
        ctrl.double_click_input = MagicMock()
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_click(pid=1, title="X", double=True)
        finally:
            _exit(patches)
        assert ok is True
        ctrl.double_click_input.assert_called_once()


# ---------------------------------------------------------------------------
# set_text
# ---------------------------------------------------------------------------


class TestSetText:
    def test_set_edit_text(self):
        ctrl = _ctrl()
        ctrl.set_edit_text = MagicMock()
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_set_text(pid=1, auto_id="edit", text="hello")
        finally:
            _exit(patches)
        assert ok is True
        ctrl.set_edit_text.assert_called_once_with("hello")

    def test_falls_back_to_type_keys(self):
        ctrl = _ctrl()
        ctrl.set_edit_text = MagicMock(side_effect=RuntimeError("no value pattern"))
        ctrl.set_focus = MagicMock()
        ctrl.type_keys = MagicMock()
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_set_text(pid=1, auto_id="edit", text="hi")
        finally:
            _exit(patches)
        assert ok is True
        ctrl.type_keys.assert_called_once()


# ---------------------------------------------------------------------------
# get_text / get_state
# ---------------------------------------------------------------------------


class TestGetTextState:
    def test_get_text_window_text(self):
        ctrl = _ctrl()
        ctrl.window_text = MagicMock(return_value="hello world")
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            txt = nr.native_get_text(pid=1, auto_id="edit")
        finally:
            _exit(patches)
        assert txt == "hello world"

    def test_get_text_missing_returns_none(self):
        ctrl = _ctrl(exists=False)
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            assert nr.native_get_text(pid=1, title="Ghost") is None
        finally:
            _exit(patches)

    def test_get_state_snapshot(self):
        ctrl = _ctrl()
        ctrl.is_visible = MagicMock(return_value=True)
        ctrl.is_enabled = MagicMock(return_value=True)
        ctrl.get_toggle_state = MagicMock(return_value=1)
        ctrl.window_text = MagicMock(return_value="On")
        ctrl.element_info.control_type = "CheckBox"
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            st = nr.native_get_state(pid=1, title="Wrap")
        finally:
            _exit(patches)
        assert st["exists"] is True
        assert st["visible"] is True
        assert st["enabled"] is True
        assert st["checked"] is True
        assert st["control_type"] == "CheckBox"
        assert st["rect"] == {"x": 10, "y": 20, "width": 50, "height": 20}

    def test_get_state_not_found(self):
        ctrl = _ctrl(exists=False)
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            st = nr.native_get_state(pid=1, title="Ghost")
        finally:
            _exit(patches)
        assert st == {"exists": False}


# ---------------------------------------------------------------------------
# wait
# ---------------------------------------------------------------------------


class TestWait:
    def test_wait_success(self):
        ctrl = MagicMock()
        ctrl.wait = MagicMock()
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_wait(pid=1, title="X", state="ready", timeout=1)
        finally:
            _exit(patches)
        assert ok is True
        # The pywinauto wait spec for "ready" includes all flags.
        assert "ready" in ctrl.wait.call_args.args[0]

    def test_wait_timeout_returns_false(self):
        ctrl = MagicMock()
        ctrl.wait = MagicMock(side_effect=RuntimeError("timed out"))
        top = MagicMock(child_window=MagicMock(return_value=ctrl))
        patches = _patch(top)
        _enter(patches)
        try:
            ok = nr.native_wait(pid=1, title="X", timeout=1)
        finally:
            _exit(patches)
        assert ok is False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_selector_kwargs_omits_none(self):
        assert nr._selector_kwargs("T", None, "id", None) == {
            "title": "T",
            "auto_id": "id",
        }

    def test_with_retries_stops_on_success(self):
        calls = {"n": 0}

        def action():
            calls["n"] += 1
            return calls["n"] == 2

        assert nr._with_retries(action, retries=3, delay=0) is True
        assert calls["n"] == 2

    def test_run_with_timeout_returns_sentinel_on_slow(self):
        import time as _t

        def slow():
            _t.sleep(2)
            return "done"

        assert nr._run_with_timeout(slow, 0.2) is nr._TIMEOUT_SENTINEL

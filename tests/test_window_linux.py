"""Tests for the Linux WindowManager backend (Phase 4, X1).

The implementation shells out to ``xdotool`` and ``wmctrl`` via
subprocess. The unit tests mock subprocess entirely so they exercise
the wiring on any OS; real-Linux integration testing happens in CI.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from visus.desktop.core.window_linux import (
    close_window_linux,
    find_window_linux,
    focus_window_linux,
    maximize_window_linux,
    minimize_window_linux,
)


def _ok(stdout: str = ""):
    return MagicMock(returncode=0, stdout=stdout, stderr="")


def _fail(returncode: int = 1, stderr: str = ""):
    return MagicMock(returncode=returncode, stdout="", stderr=stderr)


class TestFindWindowLinux:
    def test_finds_window_id_via_xdotool(self):
        with patch(
            "subprocess.run", return_value=_ok("12345\n")
        ) as run:
            wid = find_window_linux("Login")
        assert wid == "12345"
        cmd = run.call_args[0][0]
        assert cmd[0] == "xdotool"
        assert "Login" in " ".join(cmd)

    def test_returns_none_when_no_match(self):
        with patch("subprocess.run", return_value=_ok("")):
            assert find_window_linux("Nothing") is None

    def test_returns_none_when_xdotool_missing(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("xdotool")):
            assert find_window_linux("Login") is None


class TestFocusMaximizeMinimizeClose:
    def test_focus_calls_xdotool_windowactivate(self):
        with patch(
            "visus.desktop.core.window_linux.find_window_linux",
            return_value="42",
        ), patch("subprocess.run", return_value=_ok()) as run:
            ok = focus_window_linux("Login")
        assert ok is True
        cmd = run.call_args[0][0]
        assert "windowactivate" in cmd

    def test_focus_returns_false_when_no_window(self):
        with patch(
            "visus.desktop.core.window_linux.find_window_linux",
            return_value=None,
        ):
            assert focus_window_linux("Missing") is False

    def test_maximize_calls_wmctrl_with_maximized_states(self):
        with patch(
            "visus.desktop.core.window_linux.find_window_linux",
            return_value="42",
        ), patch("subprocess.run", return_value=_ok()) as run:
            ok = maximize_window_linux("Login")
        assert ok is True
        joined = " ".join(run.call_args[0][0])
        assert "wmctrl" in joined
        assert "maximized" in joined

    def test_minimize_uses_xdotool_windowminimize(self):
        with patch(
            "visus.desktop.core.window_linux.find_window_linux",
            return_value="42",
        ), patch("subprocess.run", return_value=_ok()) as run:
            ok = minimize_window_linux("Login")
        assert ok is True
        cmd = run.call_args[0][0]
        assert "windowminimize" in cmd

    def test_close_uses_xdotool_windowclose(self):
        with patch(
            "visus.desktop.core.window_linux.find_window_linux",
            return_value="42",
        ), patch("subprocess.run", return_value=_ok()) as run:
            ok = close_window_linux("Login")
        assert ok is True
        cmd = run.call_args[0][0]
        assert "windowclose" in cmd

    def test_failure_when_subprocess_returns_nonzero(self):
        with patch(
            "visus.desktop.core.window_linux.find_window_linux",
            return_value="42",
        ), patch("subprocess.run", return_value=_fail(stderr="X error")):
            assert focus_window_linux("Login") is False


class TestPublicWindowDispatch:
    """The Linux-only helpers should be called by the public API on Linux."""

    def test_public_focus_dispatches_to_linux_backend_on_linux(self):
        from visus.desktop.core import window

        with patch.object(window, "sys") as mocked_sys, patch(
            "visus.desktop.core.window_linux.focus_window_linux",
            return_value=True,
        ) as linux:
            mocked_sys.platform = "linux"
            ok = window.focus_window("Login")
        assert ok is True
        linux.assert_called_once_with("Login")

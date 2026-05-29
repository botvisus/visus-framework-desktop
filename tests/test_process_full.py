"""Full coverage for ``visus.desktop.core.process``.

Targets the missing line ranges 36-42 (Linux launch path), 77-79
(find_process pid match), 120-151 (kill_process branches).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from visus.desktop.core import process as _process


def _proc(pid=1, name="x", info=None):
    p = MagicMock()
    p.pid = pid
    p.info = info if info is not None else {"pid": pid, "name": name}
    return p


class TestLaunch:
    def test_launch_on_windows_uses_startfile(self):
        with patch.object(_process.platform, "system", return_value="Windows"):
            with patch.object(_process.os, "startfile", create=True) as sf:
                _process.launch("notepad.exe")
        sf.assert_called_once_with("notepad.exe")

    def test_launch_on_linux_uses_shlex_split(self):
        with patch.object(_process.platform, "system", return_value="Linux"):
            with patch.object(_process.subprocess, "Popen") as popen:
                _process.launch('echo "hello world"')
        argv = popen.call_args[0][0]
        assert argv == ["echo", "hello world"]


class TestFindProcess:
    def test_find_by_pid_match(self):
        target = _proc(pid=42, name="target")
        with patch("psutil.process_iter", return_value=iter([_proc(1), target, _proc(3)])):
            result = _process.find_process(pid=42)
        assert result is target

    def test_find_by_name_case_insensitive(self):
        match = _proc(pid=2, name="Chrome.exe")
        with patch(
            "psutil.process_iter",
            return_value=iter([_proc(1, name="explorer.exe"), match]),
        ):
            result = _process.find_process(name="chrome")
        assert result is match

    def test_find_returns_none_when_no_match(self):
        with patch("psutil.process_iter", return_value=iter([_proc(1)])):
            assert _process.find_process(name="missing") is None

    def test_find_swallows_no_such_process(self):
        import psutil

        bad = MagicMock()
        bad.info = {"pid": 1, "name": "x"}
        bad.pid = 1
        type(bad).pid = property(
            MagicMock(side_effect=psutil.NoSuchProcess(1))
        )
        match = _proc(pid=2, name="target")
        with patch(
            "psutil.process_iter", return_value=iter([bad, match])
        ):
            result = _process.find_process(pid=2)
        assert result is match


class TestIsProcessRunning:
    def test_is_running_true_when_match(self):
        with patch.object(_process, "find_process", return_value=_proc()):
            assert _process.is_process_running("x") is True

    def test_is_running_false_when_no_match(self):
        with patch.object(_process, "find_process", return_value=None):
            assert _process.is_process_running("x") is False


class TestKillProcess:
    def test_kill_accepts_a_psutil_process_directly(self):
        import psutil

        real_proc = MagicMock(spec=psutil.Process)
        real_proc.terminate = MagicMock()
        real_proc.wait = MagicMock()
        assert _process.kill_process(real_proc) is True
        real_proc.terminate.assert_called_once()

    def test_kill_rejects_bool(self):
        """``bool`` subclasses ``int`` -- must NOT be treated as a pid."""
        assert _process.kill_process(True) is False

    def test_kill_by_pid_int(self):
        import psutil

        target = MagicMock(spec=psutil.Process)
        target.terminate = MagicMock()
        target.wait = MagicMock()
        with patch.object(_process, "find_process", return_value=target):
            assert _process.kill_process(123) is True

    def test_kill_by_name_str(self):
        import psutil

        target = MagicMock(spec=psutil.Process)
        target.terminate = MagicMock()
        target.wait = MagicMock()
        with patch.object(_process, "find_process", return_value=target):
            assert _process.kill_process("chrome") is True

    def test_kill_returns_false_when_target_unknown_type(self):
        assert _process.kill_process([1, 2]) is False

    def test_kill_returns_false_when_no_match(self):
        with patch.object(_process, "find_process", return_value=None):
            assert _process.kill_process(999) is False

    def test_kill_falls_back_to_kill_when_terminate_times_out(self):
        import psutil

        target = MagicMock(spec=psutil.Process)
        target.terminate = MagicMock()
        target.kill = MagicMock()
        # First wait (after terminate) times out; second wait (after kill) ok.
        target.wait = MagicMock(side_effect=[psutil.TimeoutExpired(0), None])
        assert _process.kill_process(target) is True
        target.kill.assert_called_once()

    def test_kill_returns_false_when_kill_also_times_out(self):
        import psutil

        target = MagicMock(spec=psutil.Process)
        target.terminate = MagicMock()
        target.kill = MagicMock()
        target.wait = MagicMock(
            side_effect=[psutil.TimeoutExpired(0), psutil.TimeoutExpired(0)]
        )
        assert _process.kill_process(target) is False

    def test_kill_returns_true_when_process_already_gone(self):
        import psutil

        target = MagicMock(spec=psutil.Process)
        target.terminate = MagicMock(side_effect=psutil.NoSuchProcess(0))
        assert _process.kill_process(target) is True

    def test_kill_returns_false_on_access_denied(self):
        import psutil

        target = MagicMock(spec=psutil.Process)
        target.terminate = MagicMock(side_effect=psutil.AccessDenied(0))
        assert _process.kill_process(target) is False

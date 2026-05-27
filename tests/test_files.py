"""
Tests for ``visus.desktop.utils.files``.

These tests use only the local filesystem (via ``tmp_path``) and short
sub-second timeouts so they run quickly without any network or GUI access.
"""

from __future__ import annotations

import threading
import time

from visus.desktop.utils.files import wait_for_file, wait_for_file_stable


class TestWaitForFile:
    """wait_for_file polls until a readable file exists or timeout elapses."""

    def test_returns_true_for_existing_file(self, tmp_path):
        target = tmp_path / "present.txt"
        target.write_text("hello")
        assert wait_for_file(str(target), timeout=0.5, poll_interval=0.1) is True

    def test_returns_false_for_missing_file(self, tmp_path):
        missing = tmp_path / "never.txt"
        assert wait_for_file(str(missing), timeout=0.5, poll_interval=0.1) is False

    def test_detects_file_created_from_background_thread(self, tmp_path):
        target = tmp_path / "delayed.txt"

        def create_later():
            time.sleep(0.2)
            target.write_text("data")

        worker = threading.Thread(target=create_later)
        worker.start()
        try:
            assert wait_for_file(str(target), timeout=2.0, poll_interval=0.05) is True
        finally:
            worker.join()


class TestWaitForFileStable:
    """wait_for_file_stable waits for the file size to stop changing."""

    def test_returns_true_when_size_is_stable(self, tmp_path):
        target = tmp_path / "stable.txt"
        target.write_text("finished content")
        assert (
            wait_for_file_stable(
                str(target), timeout=2.0, stable_for=0.2, poll_interval=0.05
            )
            is True
        )

    def test_returns_false_for_missing_file(self, tmp_path):
        missing = tmp_path / "nope.txt"
        assert (
            wait_for_file_stable(
                str(missing), timeout=0.5, stable_for=0.2, poll_interval=0.1
            )
            is False
        )

    def test_detects_stability_after_growth_stops(self, tmp_path):
        target = tmp_path / "growing.txt"
        target.write_bytes(b"")

        def grow_then_stop():
            for _ in range(3):
                with open(target, "ab") as fh:
                    fh.write(b"chunk")
                time.sleep(0.1)
            # After this point the size stays constant.

        worker = threading.Thread(target=grow_then_stop)
        worker.start()
        try:
            assert (
                wait_for_file_stable(
                    str(target), timeout=3.0, stable_for=0.25, poll_interval=0.05
                )
                is True
            )
        finally:
            worker.join()

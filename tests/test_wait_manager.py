"""Tests for ``visus.desktop.core.wait_manager.WaitManager``.

These tests drive the wait loops with a fake monotonic clock and a patched
``time.sleep`` so they never wait in real time, and use synthetic finder
callables (hit after N calls, or never).
"""

from __future__ import annotations

import visus.desktop.core.wait_manager as wm_module
from visus.desktop.core.wait_manager import WaitManager
from visus.desktop.utils.config import BotVisionConfig


class FakeClock:
    """A deterministic stand-in for ``time.time`` that advances on sleep."""

    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def _patch_clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(wm_module.time, "time", clock.time)
    monkeypatch.setattr(wm_module.time, "sleep", clock.sleep)
    return clock


def _manager():
    return WaitManager(BotVisionConfig({"wait_timeout": 5}))


# --------------------------------------------------------------------------- #
# wait_until_found
# --------------------------------------------------------------------------- #
def test_wait_until_found_returns_immediately_when_hit(monkeypatch):
    """A finder that succeeds on the first call returns its result at once."""
    _patch_clock(monkeypatch)
    manager = _manager()

    result = manager.wait_until_found(lambda: "found!", timeout=5)

    assert result == "found!"


def test_wait_until_found_returns_after_n_calls(monkeypatch):
    """A finder that succeeds on the Nth call returns once it hits."""
    _patch_clock(monkeypatch)
    manager = _manager()
    calls = {"n": 0}

    def finder():
        calls["n"] += 1
        return (10, 20) if calls["n"] >= 3 else None

    result = manager.wait_until_found(finder, timeout=5, check_interval=0.5)

    assert result == (10, 20)
    assert calls["n"] == 3


def test_wait_until_found_returns_none_on_timeout(monkeypatch):
    """A finder that never succeeds returns None when the timeout elapses."""
    _patch_clock(monkeypatch)
    manager = _manager()

    result = manager.wait_until_found(lambda: None, timeout=2, check_interval=0.5)

    assert result is None


def test_wait_until_found_swallows_finder_exceptions(monkeypatch):
    """Exceptions from the finder are caught; loop continues until timeout."""
    _patch_clock(monkeypatch)
    manager = _manager()

    def finder():
        raise RuntimeError("backend exploded")

    # Should not raise; just times out and returns None.
    assert manager.wait_until_found(finder, timeout=1, check_interval=0.5) is None


def test_wait_until_found_uses_config_timeout_when_none(monkeypatch):
    """When timeout is None the configured ``wait_timeout`` is used."""
    _patch_clock(monkeypatch)
    manager = WaitManager(BotVisionConfig({"wait_timeout": 3}))
    calls = {"n": 0}

    def finder():
        calls["n"] += 1
        return None

    assert manager.wait_until_found(finder, timeout=None, check_interval=1.0) is None
    # timeout=3, interval=1.0 -> loop iterates while elapsed < 3 (3 checks).
    assert calls["n"] == 3


# --------------------------------------------------------------------------- #
# wait_until_disappears
# --------------------------------------------------------------------------- #
def test_wait_until_disappears_true_when_already_gone(monkeypatch):
    """A finder returning a falsy value immediately reports disappearance."""
    _patch_clock(monkeypatch)
    manager = _manager()

    assert manager.wait_until_disappears(lambda: None, timeout=5) is True


def test_wait_until_disappears_after_n_calls(monkeypatch):
    """Returns True once the element is no longer found."""
    _patch_clock(monkeypatch)
    manager = _manager()
    calls = {"n": 0}

    def finder():
        calls["n"] += 1
        return "still here" if calls["n"] < 3 else None

    assert manager.wait_until_disappears(finder, timeout=5, check_interval=0.1) is True
    assert calls["n"] == 3


def test_wait_until_disappears_false_on_timeout(monkeypatch):
    """A persistently-visible element returns False after the timeout."""
    _patch_clock(monkeypatch)
    manager = _manager()

    result = manager.wait_until_disappears(
        lambda: "always visible", timeout=2, check_interval=0.5
    )

    assert result is False


def test_wait_until_disappears_treats_exception_as_gone(monkeypatch):
    """If the finder raises, the element is considered to have disappeared."""
    _patch_clock(monkeypatch)
    manager = _manager()

    def finder():
        raise RuntimeError("search failed")

    assert manager.wait_until_disappears(finder, timeout=5) is True


# --------------------------------------------------------------------------- #
# wait_with_condition / smart_retry
# --------------------------------------------------------------------------- #
def test_wait_with_condition_true_when_met(monkeypatch):
    """Returns True as soon as the condition holds."""
    _patch_clock(monkeypatch)
    manager = _manager()

    assert manager.wait_with_condition(lambda: True, timeout=5) is True


def test_wait_with_condition_false_on_timeout(monkeypatch):
    """Never-met condition returns False after the timeout."""
    _patch_clock(monkeypatch)
    manager = _manager()

    assert (
        manager.wait_with_condition(lambda: False, timeout=2, check_interval=0.5)
        is False
    )


def test_smart_retry_returns_on_success(monkeypatch):
    """smart_retry returns the action result once the success condition holds."""
    _patch_clock(monkeypatch)
    manager = _manager()
    attempts = {"n": 0}

    def action():
        attempts["n"] += 1
        return attempts["n"]  # 1, 2, 3...

    # Success when the action returns >= 2 (i.e. on the second attempt).
    result = manager.smart_retry(
        action, lambda r: r >= 2, max_attempts=5, retry_delay=0.1, timeout=10
    )

    assert result == 2
    assert attempts["n"] == 2


def test_smart_retry_returns_none_after_max_attempts(monkeypatch):
    """smart_retry returns None when the success condition never holds."""
    _patch_clock(monkeypatch)
    manager = _manager()
    attempts = {"n": 0}

    def action():
        attempts["n"] += 1
        return None

    result = manager.smart_retry(
        action, lambda r: r is not None, max_attempts=3, retry_delay=0.1, timeout=10
    )

    assert result is None
    assert attempts["n"] == 3

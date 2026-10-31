"""Tests for the standalone ``@retry`` decorator (Phase 1, R1).

``retry`` lives in ``visus.desktop.utils.retry`` and is independent of the
task-list backtrack mechanism. It re-invokes the wrapped callable on
configured exceptions, with either a fixed or exponential backoff, until
``attempts`` is exhausted.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from visus.desktop.utils.retry import retry


class TestRetry:
    """Behavioural contract for the ``@retry`` decorator."""

    def test_success_on_first_try_does_not_retry(self):
        calls = {"n": 0}

        @retry(attempts=3, base_delay=0.0)
        def ok():
            calls["n"] += 1
            return "ok"

        assert ok() == "ok"
        assert calls["n"] == 1

    def test_success_after_two_failures(self):
        """After two failures the third call succeeds and is returned."""
        calls = {"n": 0}

        @retry(attempts=3, base_delay=0.0)
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("transient")
            return "eventually"

        assert flaky() == "eventually"
        assert calls["n"] == 3

    def test_exhausted_attempts_raises_last_exception(self):
        """Exhausting all attempts re-raises the most recent exception."""
        calls = {"n": 0}

        @retry(attempts=2, base_delay=0.0)
        def always_fails():
            calls["n"] += 1
            raise ValueError(f"boom {calls['n']}")

        with pytest.raises(ValueError, match="boom 2"):
            always_fails()
        assert calls["n"] == 2

    def test_exception_allow_list_excludes_unlisted(self):
        """Exceptions outside ``exceptions=`` propagate without retry."""
        calls = {"n": 0}

        @retry(attempts=5, base_delay=0.0, exceptions=(ConnectionError,))
        def picky():
            calls["n"] += 1
            raise ValueError("not a connection error")

        with pytest.raises(ValueError):
            picky()
        assert calls["n"] == 1

    def test_expo_backoff_doubles_delay(self):
        """Exponential backoff sleeps ``base_delay * 2**attempt``."""
        sleeps: list = []

        with patch(
            # not "visus.desktop.utils.retry.time.sleep": utils re-exports the
            # retry FUNCTION under the module's name and Python 3.10's patch
            # resolves the dotted path to it ("'retry' is not a package")
            "time.sleep",
            side_effect=lambda s: sleeps.append(s),
        ):

            @retry(attempts=4, backoff="expo", base_delay=0.1)
            def fails():
                raise RuntimeError("nope")

            with pytest.raises(RuntimeError):
                fails()

        # 3 sleeps between 4 attempts: 0.1, 0.2, 0.4
        assert sleeps == pytest.approx([0.1, 0.2, 0.4])

    def test_fixed_backoff_uses_constant_delay(self):
        """Fixed backoff sleeps ``base_delay`` between every attempt."""
        sleeps: list = []

        with patch(
            # not "visus.desktop.utils.retry.time.sleep": utils re-exports the
            # retry FUNCTION under the module's name and Python 3.10's patch
            # resolves the dotted path to it ("'retry' is not a package")
            "time.sleep",
            side_effect=lambda s: sleeps.append(s),
        ):

            @retry(attempts=4, backoff="fixed", base_delay=0.25)
            def fails():
                raise RuntimeError("nope")

            with pytest.raises(RuntimeError):
                fails()

        assert sleeps == pytest.approx([0.25, 0.25, 0.25])

    def test_invalid_backoff_strategy_raises_value_error(self):
        """Passing an unknown ``backoff`` strategy is a programmer error."""
        with pytest.raises(ValueError, match="backoff"):
            retry(attempts=3, backoff="nonsense")

    def test_invalid_attempts_raises_value_error(self):
        """``attempts`` must be at least 1."""
        with pytest.raises(ValueError, match="attempts"):
            retry(attempts=0)

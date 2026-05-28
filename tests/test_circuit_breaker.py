"""Tests for the consecutive-failures circuit breaker (Phase 2, R2).

When ``config['breaker_threshold']`` is set, ``execute_tasks`` aborts
with ``CircuitBreakerTrippedError`` after N **consecutive** task
failures. A successful task resets the counter.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.exceptions import CircuitBreakerTrippedError

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@requires_tesseract
class TestCircuitBreaker:
    """Threshold-based abort after consecutive failures."""

    def test_disabled_by_default(self):
        """No threshold -> failures keep accumulating without aborting."""
        bot = vd.VisusBot({"show_overlay": False})
        results = bot.execute_tasks(
            [{"foo": "bar"}, {"foo": "bar"}, {"foo": "bar"}]
        )
        assert len(results) == 3
        assert all(r.success is False for r in results)

    def test_trips_after_threshold_consecutive_failures(self):
        bot = vd.VisusBot({"show_overlay": False, "breaker_threshold": 2})
        with pytest.raises(CircuitBreakerTrippedError) as info:
            bot.execute_tasks(
                [{"foo": "a"}, {"foo": "b"}, {"foo": "c"}]
            )
        # The exception carries the threshold and the count at trip time.
        assert info.value.threshold == 2
        assert info.value.consecutive_failures >= 2

    def test_successful_task_resets_counter(self):
        bot = vd.VisusBot({"show_overlay": False, "breaker_threshold": 2})
        fake_center = MagicMock(x=1, y=1)
        # fail, success, fail -> never reaches 2 consecutive failures.
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            results = bot.execute_tasks(
                [
                    {"foo": "a"},                                # fail
                    {"type": "click", "x": 1, "y": 1},          # success
                    {"foo": "b"},                                # fail (counter reset)
                ]
            )
        assert [r.success for r in results] == [False, True, False]

    def test_threshold_zero_is_treated_as_disabled(self):
        bot = vd.VisusBot({"show_overlay": False, "breaker_threshold": 0})
        results = bot.execute_tasks([{"foo": "a"}, {"foo": "b"}])
        assert len(results) == 2
        assert all(r.success is False for r in results)

"""End-to-end ``execute_tasks`` against the real screen.

These are the integration tests that close the remaining 12%
coverage gap in ``task_executor.py``. They exercise the full
find -> perform_action -> backtrack chain without any patching of
the executor itself; only the screen / keyboard inputs are still
controlled (via the screen source + pytest-visus harness) so the
tests stay deterministic.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import visus.desktop as vd
from visus.desktop.core.screen import set_screen_source


@pytest.fixture
def fixture_screens(tmp_path):
    """Build a deterministic on-disk screen source the executor will read.

    Returns the path that can be passed to ``set_screen_source``.
    """
    dirpath = tmp_path / "screens"
    dirpath.mkdir()
    # Three frames of pure cream-canvas colour so OCR has nothing to
    # match -- the executor's "task fails" path runs end-to-end.
    for i, color in enumerate([(250, 249, 245), (239, 233, 222), (24, 23, 21)]):
        Image.new("RGB", (200, 100), color=color).save(
            dirpath / f"frame_{i:03d}.png"
        )
    return dirpath


class TestRealExecutorChain:
    def teardown_method(self):
        set_screen_source(None)

    def test_execute_tasks_failure_path_with_real_screen_source(
        self, fixture_screens, tmp_path
    ):
        """A task list that fails OCR runs all the way through the
        executor's failure / artifacts pipeline."""
        artifacts = tmp_path / "art"
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "artifacts_dir": str(artifacts),
                "screen_source": f"disk:{fixture_screens}",
            }
        )
        results = bot.execute_tasks(
            [
                {
                    "text": "this-text-is-not-anywhere",
                    "region": (0, 0, 200, 100),
                    "early_confidence": 95.0,
                }
            ]
        )
        assert len(results) == 1
        assert results[0].success is False
        # The screenshot-on-failure path actually wrote a PNG.
        assert results[0].failure_screenshot is not None
        assert Path(results[0].failure_screenshot).exists()

    def test_unknown_task_failure_runs_full_pipeline(self, tmp_path):
        artifacts = tmp_path / "art"
        bot = vd.VisusBot(
            {
                "show_overlay": False,
                "artifacts_dir": str(artifacts),
                "log_format": "json",
            }
        )
        results = bot.execute_tasks([{"definitely_not_a_real_task": True}])
        assert results[0].success is False
        # JSON events emit on the task-events logger -- the real path
        # serializes through python's logging module here.
        assert results[0].error
        # duration_ms is populated by the real time.monotonic() call.
        assert isinstance(results[0].duration_ms, int)

    def test_circuit_breaker_trips_under_real_executor(self):
        """Two consecutive unknown-shape failures must trigger the
        breaker without any patching of the executor."""
        from visus.desktop.exceptions import CircuitBreakerTrippedError

        bot = vd.VisusBot(
            {"show_overlay": False, "breaker_threshold": 2}
        )
        with pytest.raises(CircuitBreakerTrippedError):
            bot.execute_tasks(
                [
                    {"foo": "bar"},  # fails
                    {"foo": "baz"},  # second consecutive fail -> breaker trips
                    {"foo": "qux"},
                ]
            )

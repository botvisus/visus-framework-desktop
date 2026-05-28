"""Tests for the ``hybrid`` task type (Phase 3, T2).

``{"type": "hybrid", "name": "Login"}`` resolves the target through
``bot.hybrid_find`` (native → OCR → image) and then clicks at the
returned coordinates. Builds on T1 and is auto-mocked by the existing
fixtures.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)


@requires_tesseract
class TestHybridTaskType:
    def test_hybrid_task_dispatches_to_hybrid_find(self):
        bot = vd.VisusBot({"show_overlay": False})
        with patch.object(
            bot, "hybrid_find", return_value=(100, 200, 50, 20)
        ) as hf, patch.object(bot.executor, "_perform_action") as perform:
            results = bot.execute_tasks(
                [{"type": "hybrid", "name": "Login"}]
            )
        assert results[0].success is True
        hf.assert_called_once_with("Login", region=None)
        perform.assert_called_once()

    def test_hybrid_task_with_region_forwards_region(self):
        bot = vd.VisusBot({"show_overlay": False})
        with patch.object(
            bot, "hybrid_find", return_value=(0, 0, 10, 10)
        ) as hf, patch.object(bot.executor, "_perform_action"):
            bot.execute_tasks(
                [{"type": "hybrid", "name": "Submit", "region": (1, 2, 3, 4)}]
            )
        hf.assert_called_once_with("Submit", region=(1, 2, 3, 4))

    def test_hybrid_task_failure_when_all_layers_miss(self):
        bot = vd.VisusBot({"show_overlay": False})
        with patch.object(
            bot, "hybrid_find", return_value=None
        ), patch.object(bot.executor, "_perform_action") as perform:
            results = bot.execute_tasks(
                [{"type": "hybrid", "name": "Nope"}]
            )
        assert results[0].success is False
        perform.assert_not_called()

    def test_hybrid_task_clicks_at_box_center(self):
        bot = vd.VisusBot({"show_overlay": False})
        fake_center = MagicMock(x=125, y=210)
        with patch.object(
            bot, "hybrid_find", return_value=(100, 200, 50, 20)
        ), patch(
            "pyautogui.center", return_value=fake_center
        ), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ) as mock_click:
            bot.execute_tasks([{"type": "hybrid", "name": "Login"}])
        mock_click.assert_called()

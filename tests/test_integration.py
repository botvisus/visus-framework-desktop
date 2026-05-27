"""
Integration tests for ``visus.desktop``.

These wire together the public functions/classes. Anything that would touch a
real screen, mouse, or Tesseract is either driven with empty input (which
returns early) or mocked at the REAL module paths. Tesseract-dependent paths are
guarded with a skip marker.
"""

from unittest.mock import MagicMock, patch

import pytest

import visus.desktop as vd
from tests import tesseract_available

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed",
)


class TestEmptyTaskHandling:
    """Empty / invalid task input returns early without touching the screen."""

    def test_execute_tasks_empty_list(self):
        assert vd.execute_tasks([]) == []

    def test_execute_tasks_non_list(self):
        # The top-level helper validates the type and returns [] for non-lists.
        assert vd.execute_tasks("not a list") == []

    def test_run_automation_empty_list_does_not_raise(self):
        # run_automation just logs for empty input and returns None.
        assert vd.run_automation([]) is None


class TestOverlayHelpers:
    """Overlay-related public helpers that need no display."""

    def test_get_available_overlay_colors(self):
        colors = vd.VisusBot.get_available_overlay_colors()
        assert colors == [
            "red",
            "blue",
            "green",
            "yellow",
            "purple",
            "orange",
            "cyan",
            "magenta",
            "white",
            "black",
        ]

    def test_show_overlay_dispatches_to_visual_overlay(self):
        """show_overlay() builds a VisualOverlay and calls .show() (non-blocking)."""
        with patch("visus.desktop.core.overlay.VisualOverlay") as MockOverlay:
            instance = MockOverlay.return_value
            vd.show_overlay((10, 20, 30, 40), duration=500, color="green", width=5)
            MockOverlay.assert_called_once_with(color="green", width=5, duration=500)
            instance.show.assert_called_once()
            # Non-blocking dispatch.
            _, kwargs = instance.show.call_args
            assert kwargs.get("blocking") is False


@requires_tesseract
class TestVisusBotIntegration:
    """End-to-end-ish behavior of VisusBot with the screen/mouse mocked out."""

    def test_execute_tasks_method_with_empty_list(self):
        bot = vd.VisusBot()
        assert bot.execute_tasks([]) == []

    def test_coordinate_click_task_clicks_via_virtual_mouse(self):
        """A 'click' task resolves to coordinates and triggers a mouse click.

        The virtual mouse is patched at its real path so no physical click
        happens, and overlay is disabled to avoid spawning a Tk window.
        """
        bot = vd.VisusBot({"show_overlay": False})

        fake_center = MagicMock()
        fake_center.x = 100
        fake_center.y = 200

        # pyautogui is imported lazily inside _perform_click, so patch the real
        # module attribute rather than a name on the task_executor module.
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ) as mock_click:
            results = bot.execute_tasks(
                [{"type": "click", "x": 100, "y": 200, "mouse_button": "left"}]
            )

            assert len(results) == 1
            assert results[0].success is True
            # The click went through the (mocked) virtual mouse at (100, 200).
            mock_click.assert_called()
            _, kwargs = mock_click.call_args
            assert kwargs["x"] == 100
            assert kwargs["y"] == 200

    def test_get_available_keyboard_commands(self):
        bot = vd.VisusBot()
        commands = bot.get_available_keyboard_commands()
        assert isinstance(commands, list)
        assert "Ctrl+S" in commands

    def test_overlay_config_round_trip(self):
        """configure_overlay updates config and get_overlay_config reflects it."""
        bot = vd.VisusBot()
        bot.configure_overlay(enabled=True, color="green", duration=2000, width=6)
        cfg = bot.get_overlay_config()
        assert cfg["color"] == "green"
        assert cfg["duration"] == 2000
        assert cfg["width"] == 6
        assert cfg["enabled"] is True

    def test_configure_overlay_rejects_invalid_color(self):
        bot = vd.VisusBot()
        with pytest.raises(ValueError):
            bot.configure_overlay(color="not-a-color")

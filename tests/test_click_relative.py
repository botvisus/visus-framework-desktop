"""Tests for click_relative (find an image, click at a coordinate offset from it)."""

from __future__ import annotations

from visus.desktop.core.capabilities import CapabilitiesMixin


class _Bot(CapabilitiesMixin):
    """Host providing the find_image/click_coordinates that VisusBot supplies."""

    def __init__(self, location):
        self._location = location
        self.found = None
        self.clicked = None

    def find_image(self, image, region=None, confidence=0.9):
        self.found = (image, region, confidence)
        return self._location

    def click_coordinates(self, x, y, mouse_button="left", delay=0):
        self.clicked = (x, y, mouse_button, delay)
        return True


def test_click_relative_top_left_offset():
    bot = _Bot((100, 200, 40, 20))
    assert bot.click_relative("btn.png", 5, 10) is True
    # top-left (100, 200) + (5, 10)
    assert bot.clicked == (105, 210, "left", 0)


def test_click_relative_centered_offset():
    bot = _Bot((100, 200, 40, 20))
    bot.click_relative("btn.png", 0, 0, centered=True)
    # center = (100 + 20, 200 + 10)
    assert bot.clicked == (120, 210, "left", 0)


def test_click_relative_not_found_returns_false():
    bot = _Bot(None)
    assert bot.click_relative("btn.png", 5, 10) is False
    assert bot.clicked is None


def test_click_relative_forwards_image_and_search_args():
    bot = _Bot((0, 0, 10, 10))
    bot.click_relative("my_label", 1, 2, region=(1, 2, 3, 4), confidence=0.8)
    # The image arg (label or path) and search args reach find_image,
    # which is where label resolution happens.
    assert bot.found == ("my_label", (1, 2, 3, 4), 0.8)


def test_click_relative_passes_button_and_delay():
    bot = _Bot((10, 10, 4, 4))
    bot.click_relative("btn.png", 0, 0, mouse_button="double", delay=1.5)
    assert bot.clicked == (10, 10, "double", 1.5)

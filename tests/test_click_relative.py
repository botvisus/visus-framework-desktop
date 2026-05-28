"""Tests for click_relative (image + coordinate offset).

Mirrors the rich parameter style of ``click_image`` / ``click_text``: backtrack,
wait, show_overlay, sendtext, and routing through ``click_at`` (which respects
the virtual mouse + overlay pipeline).
"""

from __future__ import annotations

from visus.desktop.core.capabilities import CapabilitiesMixin


class _KeyboardCommander:
    def __init__(self):
        self.sendtexts: list[str] = []

    def process_sendtext_command(self, text: str) -> None:
        self.sendtexts.append(text)


class _Executor:
    def __init__(self):
        self.keyboard_commander = _KeyboardCommander()


class _Bot(CapabilitiesMixin):
    """Host providing the VisusBot surface click_relative depends on."""

    def __init__(self, location, click_returns: bool = True):
        self._location = location
        self._click_returns = click_returns
        self.found: dict | None = None
        self.clicked: dict | None = None
        self.executor = _Executor()

    def find_image(self, image, **kwargs):
        # Accept any of the rich find_image kwargs (region/confidence/max_attempts/
        # backtrack/wait_until_found/wait_until_disappears/wait_timeout/...).
        self.found = {"image": image, **kwargs}
        return self._location

    def click_at(self, location, mouse_button="left", delay=0, show_overlay=None):
        self.clicked = {
            "location": location,
            "mouse_button": mouse_button,
            "delay": delay,
            "show_overlay": show_overlay,
        }
        return self._click_returns


# --- Coordinates ------------------------------------------------------------

def test_top_left_offset_lands_on_target_point():
    bot = _Bot((100, 200, 40, 20))
    assert bot.click_relative("btn.png", 5, 10) is True
    # Synthetic 20x20 location centered on (105, 210)
    assert bot.clicked["location"] == (95, 200, 20, 20)


def test_centered_offset_uses_image_center():
    bot = _Bot((100, 200, 40, 20))
    bot.click_relative("btn.png", 0, 0, centered=True)
    # center = (120, 210) -> synthetic (110, 200, 20, 20)
    assert bot.clicked["location"] == (110, 200, 20, 20)


def test_not_found_returns_false_and_does_not_click():
    bot = _Bot(None)
    assert bot.click_relative("btn.png", 5, 10) is False
    assert bot.clicked is None


# --- Parameter pass-through -------------------------------------------------

def test_forwards_image_region_and_confidence_to_find_image():
    bot = _Bot((0, 0, 10, 10))
    bot.click_relative("my_label", 1, 2, region=(1, 2, 3, 4), confidence=0.8)
    assert bot.found["image"] == "my_label"
    assert bot.found["region"] == (1, 2, 3, 4)
    assert bot.found["confidence"] == 0.8


def test_forwards_wait_backtrack_and_max_attempts_to_find_image():
    bot = _Bot((0, 0, 10, 10))
    bot.click_relative(
        "btn.png",
        max_attempts=5,
        backtrack=True,
        wait_until_found=True,
        wait_until_disappears=False,
        wait_timeout=15,
    )
    assert bot.found["max_attempts"] == 5
    assert bot.found["backtrack"] is True
    assert bot.found["wait_until_found"] is True
    assert bot.found["wait_until_disappears"] is False
    assert bot.found["wait_timeout"] == 15


def test_passes_mouse_button_and_delay_to_click_at():
    bot = _Bot((10, 10, 4, 4))
    bot.click_relative("btn.png", 0, 0, mouse_button="double", delay=1.5)
    assert bot.clicked["mouse_button"] == "double"
    assert bot.clicked["delay"] == 1.5


def test_show_overlay_forwarded_to_click_at():
    bot = _Bot((0, 0, 10, 10))
    bot.click_relative("btn.png", show_overlay=False)
    assert bot.clicked["show_overlay"] is False
    bot2 = _Bot((0, 0, 10, 10))
    bot2.click_relative("btn.png", show_overlay=True)
    assert bot2.clicked["show_overlay"] is True


# --- sendtext ---------------------------------------------------------------

def test_sendtext_typed_after_successful_click():
    bot = _Bot((0, 0, 10, 10))
    bot.click_relative("btn.png", sendtext="hello{enter}")
    assert bot.executor.keyboard_commander.sendtexts == ["hello{enter}"]


def test_sendtext_skipped_when_click_returns_false():
    bot = _Bot((0, 0, 10, 10), click_returns=False)
    bot.click_relative("btn.png", sendtext="hello")
    assert bot.executor.keyboard_commander.sendtexts == []


def test_sendtext_skipped_when_image_not_found():
    bot = _Bot(None)
    bot.click_relative("btn.png", sendtext="hello")
    assert bot.executor.keyboard_commander.sendtexts == []

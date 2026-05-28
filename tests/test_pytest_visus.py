"""Tests for the bundled ``pytest-visus`` plugin (Phase 2, TS1).

The plugin lives at ``src/visus_pytest/`` and is auto-discovered by
pytest via the ``[project.entry-points."pytest11"]`` table in
``pyproject.toml``. It exposes three fixtures:

  * ``mock_screen``  -- push pre-baked PIL frames; ``capture_screen``
                        returns them in sequence.
  * ``fake_ocr``     -- queue text/box/confidence triples;
                        ``OCREngine.find_text`` matches against them.
  * ``record_clicks`` -- captures every pyautogui mouse call so a
                         test can assert on intent without a real mouse.
"""

from __future__ import annotations

from PIL import Image

# Use the plugin's fixtures directly -- pytest's auto-discovery via
# entry points only applies after the package is installed, but the
# fixtures live in ``visus_pytest`` so we can import them in tests
# explicitly without needing a re-install.
pytest_plugins = ["visus_pytest"]


def test_mock_screen_returns_pushed_frames(mock_screen):
    red = Image.new("RGB", (8, 8), color="red")
    green = Image.new("RGB", (8, 8), color="green")
    mock_screen.push(red)
    mock_screen.push(green)

    from visus.desktop.core.screen import capture_screen

    first = capture_screen()
    second = capture_screen()
    assert first.getpixel((0, 0)) == (255, 0, 0)
    assert second.getpixel((0, 0)) == (0, 128, 0)


def test_mock_screen_default_white_canvas(mock_screen):
    """With no frames queued the mock falls back to a plain white canvas."""
    from visus.desktop.core.screen import capture_screen

    img = capture_screen()
    assert img.getpixel((0, 0)) == (255, 255, 255)


def test_fake_ocr_matches_queued_text(fake_ocr):
    fake_ocr.returns("Login", box=(10, 20, 50, 18), confidence=92)
    fake_ocr.returns("Cancel", box=(90, 20, 50, 18), confidence=88)

    from visus.desktop.core.ocr_engine import OCREngine

    engine = OCREngine.__new__(OCREngine)  # bypass tesseract setup
    engine._backend = None  # patched by the fixture's monkeypatch
    boxes, scores, early = engine.find_text(
        None, "Login", filter_type="both", early_confidence_threshold=75
    )
    assert boxes == [(10, 20, 50, 18)]
    assert scores == [92]
    assert early is True


def test_fake_ocr_no_match_returns_empty(fake_ocr):
    fake_ocr.returns("Login")

    from visus.desktop.core.ocr_engine import OCREngine

    engine = OCREngine.__new__(OCREngine)
    engine._backend = None
    boxes, scores, _ = engine.find_text(
        None, "Submit", filter_type="both", early_confidence_threshold=75
    )
    assert boxes == []
    assert scores == []


def test_record_clicks_captures_pyautogui_clicks(record_clicks):
    import pyautogui

    pyautogui.click(100, 200, button="left")
    pyautogui.click(300, 400, button="right")
    assert len(record_clicks) == 2
    assert record_clicks[0]["args"] == (100, 200)
    assert record_clicks[0]["kwargs"]["button"] == "left"
    assert record_clicks[1]["args"] == (300, 400)


def test_record_clicks_captures_mouse_down_up(record_clicks):
    import pyautogui

    pyautogui.mouseDown(button="left")
    pyautogui.mouseUp(button="left")
    events = [c.get("event") for c in record_clicks if "event" in c]
    assert events == ["down", "up"]

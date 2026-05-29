"""Tests for ``capture_element`` (library + MCP tool).

``capture_element`` locates a UI element by text (OCR), native (UIA), or
an explicit region, saves a tight template PNG to a reusable elements
library, saves an annotated full-screen PNG (rectangle around the located
box) to a trace folder, and optionally clicks the element's center.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from visus.desktop.core import elements as _elements


@pytest.fixture(autouse=True)
def _fake_screen(monkeypatch):
    """Patch capture_screen + save_screenshot at the screen module so no
    real display is touched. capture_screen returns a fixed 200x100 frame."""
    frame = Image.new("RGB", (200, 100), color="white")
    monkeypatch.setattr(
        _elements, "capture_screen", lambda region=None, monitor=None: frame.copy()
    )

    saved = {}

    def fake_save(path, region=None, monitor=None):
        # Record + actually write a tiny PNG so existence checks pass.
        saved[path] = {"region": region, "monitor": monitor}
        img = frame.copy()
        if region:
            x, y, w, h = region
            img = img.crop((x, y, x + w, y + h))
        import os

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        img.save(path)
        return path

    monkeypatch.setattr(_elements, "save_screenshot", fake_save)
    return saved


def _bot_with(box=None):
    """A fake bot whose find_text / _hybrid_native_lookup return ``box``."""
    bot = MagicMock()
    bot.find_text = MagicMock(return_value=box)
    bot._hybrid_native_lookup = MagicMock(return_value=box)
    bot.click_at = MagicMock(return_value=True)
    return bot


class TestLocatorValidation:
    def test_no_locator_raises(self, tmp_path):
        with pytest.raises(ValueError, match="exactly one"):
            _elements.capture_element("x", bot=_bot_with(), elements_dir=str(tmp_path))

    def test_two_locators_raises(self, tmp_path):
        with pytest.raises(ValueError, match="exactly one"):
            _elements.capture_element(
                "x",
                text="Arquivo",
                region=[0, 0, 10, 10],
                bot=_bot_with(),
                elements_dir=str(tmp_path),
            )


class TestRegionMode:
    def test_region_saves_template_and_annotated(self, tmp_path):
        result = _elements.capture_element(
            "arquivo", region=[10, 20, 60, 18], bot=_bot_with(),
            elements_dir=str(tmp_path),
        )
        assert result["found"] is True
        assert result["located_by"] == "region"
        assert result["box"] == {"x": 10, "y": 20, "width": 60, "height": 18}
        assert (tmp_path / "arquivo.png").exists()
        assert (tmp_path / "trace" / "arquivo_annotated.png").exists()
        assert result["clicked"] is False

    def test_region_with_click_clicks_center(self, tmp_path):
        bot = _bot_with()
        result = _elements.capture_element(
            "arquivo", region=[10, 20, 60, 20], click=True, bot=bot,
            elements_dir=str(tmp_path),
        )
        assert result["clicked"] is True
        bot.click_at.assert_called_once()
        # center = (10 + 60//2, 20 + 20//2) = (40, 30)
        args = bot.click_at.call_args
        assert args is not None


class TestTextMode:
    def test_text_uses_find_text(self, tmp_path):
        bot = _bot_with(box=(30, 40, 50, 16))
        result = _elements.capture_element(
            "login", text="Login", bot=bot, elements_dir=str(tmp_path)
        )
        assert result["found"] is True
        assert result["located_by"] == "text"
        assert result["box"] == {"x": 30, "y": 40, "width": 50, "height": 16}
        bot.find_text.assert_called_once()

    def test_text_forwards_search_region_and_confidence(self, tmp_path):
        bot = _bot_with(box=(0, 0, 10, 10))
        _elements.capture_element(
            "login", text="Login", search_region=[5, 5, 100, 50],
            confidence_threshold=60.0, bot=bot, elements_dir=str(tmp_path),
        )
        kwargs = bot.find_text.call_args.kwargs
        assert tuple(kwargs["region"]) == (5, 5, 100, 50)
        assert kwargs["confidence_threshold"] == 60.0

    def test_text_not_found_returns_found_false(self, tmp_path):
        bot = _bot_with(box=None)
        result = _elements.capture_element(
            "missing", text="Nope", bot=bot, elements_dir=str(tmp_path)
        )
        assert result["found"] is False
        assert result["clicked"] is False
        # No template saved on a miss...
        assert not (tmp_path / "missing.png").exists()
        # ...but the annotated full-screen IS saved so the user sees why.
        assert (tmp_path / "trace" / "missing_annotated.png").exists()

    def test_text_not_found_does_not_click(self, tmp_path):
        bot = _bot_with(box=None)
        _elements.capture_element(
            "missing", text="Nope", click=True, bot=bot,
            elements_dir=str(tmp_path),
        )
        bot.click_at.assert_not_called()


class TestNativeMode:
    def test_native_uses_hybrid_lookup(self, tmp_path):
        bot = _bot_with(box=(1, 2, 3, 4))
        result = _elements.capture_element(
            "btn", native="SaveButton", bot=bot, elements_dir=str(tmp_path)
        )
        assert result["located_by"] == "native"
        assert result["box"] == {"x": 1, "y": 2, "width": 3, "height": 4}
        bot._hybrid_native_lookup.assert_called_once_with("SaveButton")


class TestPadding:
    def test_padding_expands_box_clamped_to_screen(self, tmp_path):
        # Box near the top-left corner; padding must clamp at 0.
        result = _elements.capture_element(
            "x", region=[2, 2, 20, 20], padding=10, bot=_bot_with(),
            elements_dir=str(tmp_path),
        )
        box = result["box"]
        # Expanded by 10 each side but clamped to >= 0.
        assert box["x"] == 0
        assert box["y"] == 0
        assert box["width"] >= 20
        # Should not exceed the 200x100 frame.
        assert box["x"] + box["width"] <= 200
        assert box["y"] + box["height"] <= 100


class TestAnnotatedImage:
    def test_annotated_is_full_screen_size(self, tmp_path):
        _elements.capture_element(
            "x", region=[10, 10, 30, 30], bot=_bot_with(),
            elements_dir=str(tmp_path),
        )
        annotated = Image.open(tmp_path / "trace" / "x_annotated.png")
        assert annotated.size == (200, 100)


# ---------------------------------------------------------------------------
# MCP tool wrapper
# ---------------------------------------------------------------------------


class TestMcpCaptureElementTool:
    def test_tool_registered(self):
        from visus.desktop import mcp_server as ms

        assert "capture_element" in ms._tools_for_tests()

    def test_tool_forwards_and_returns_dict(self, tmp_path):
        from visus.desktop import mcp_server as ms

        ms.reset_bot_for_tests()
        fake_result = {
            "found": True,
            "label": "arquivo",
            "located_by": "text",
            "box": {"x": 1, "y": 2, "width": 3, "height": 4},
            "template_path": str(tmp_path / "arquivo.png"),
            "annotated_path": str(tmp_path / "trace" / "arquivo_annotated.png"),
            "clicked": True,
        }
        with patch(
            "visus.desktop.core.elements.capture_element",
            return_value=fake_result,
        ) as ce:
            out = ms._tools_for_tests()["capture_element"](
                label="arquivo", text="Arquivo", click=True
            )
        assert out == fake_result
        kwargs = ce.call_args.kwargs
        assert kwargs["text"] == "Arquivo"
        assert kwargs["click"] is True

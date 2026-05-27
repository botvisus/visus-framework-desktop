"""
Tests for ``visus.desktop.utils.config.BotVisionConfig``.

The config constructor auto-detects Tesseract and raises
``TesseractNotFoundError`` when it is missing, so the whole module is guarded
by the Tesseract availability check.
"""
import pytest

from visus.desktop.utils.config import BotVisionConfig, get_default_config

from tests import tesseract_available


pytestmark = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (BotVisionConfig requires it at construction)",
)


def test_default_values_via_get():
    cfg = BotVisionConfig()
    assert cfg.get("confidence_threshold") == 75.0
    assert cfg.get("retry_attempts") == 3
    assert cfg.get("default_delay") == 1.0
    assert cfg.get("overlay_color") == "red"
    assert cfg.get("overlay_duration") == 1000
    assert cfg.get("overlay_width") == 4
    assert cfg.get("default_mouse_button") == "left"
    assert cfg.get("use_virtual_mouse") is False
    assert cfg.get("wait_timeout") == 30


def test_get_returns_default_for_unknown_key():
    cfg = BotVisionConfig()
    assert cfg.get("does_not_exist", "fallback") == "fallback"


def test_attribute_access_for_known_keys():
    cfg = BotVisionConfig()
    assert cfg.confidence_threshold == 75.0
    assert cfg.default_mouse_button == "left"


def test_unknown_attribute_raises():
    cfg = BotVisionConfig()
    with pytest.raises(AttributeError):
        _ = cfg.totally_unknown_attribute


def test_set_and_get():
    cfg = BotVisionConfig()
    cfg.set("confidence_threshold", 88.0)
    assert cfg.get("confidence_threshold") == 88.0


def test_update_multiple():
    cfg = BotVisionConfig()
    cfg.update({"confidence_threshold": 60.0, "retry_attempts": 5})
    assert cfg.get("confidence_threshold") == 60.0
    assert cfg.get("retry_attempts") == 5


def test_to_dict_returns_copy():
    cfg = BotVisionConfig()
    d = cfg.to_dict()
    assert isinstance(d, dict)
    assert d["confidence_threshold"] == 75.0
    # Mutating the returned dict must not affect the config.
    d["confidence_threshold"] = 1.0
    assert cfg.get("confidence_threshold") == 75.0


def test_invalid_overlay_color_coerced_to_red():
    cfg = BotVisionConfig({"overlay_color": "invalid"})
    assert cfg.get("overlay_color") == "red"


def test_valid_overlay_color_kept():
    cfg = BotVisionConfig({"overlay_color": "blue"})
    assert cfg.get("overlay_color") == "blue"


def test_invalid_mouse_button_coerced_to_left():
    cfg = BotVisionConfig({"default_mouse_button": "invalid"})
    assert cfg.get("default_mouse_button") == "left"


def test_valid_mouse_button_kept():
    cfg = BotVisionConfig({"default_mouse_button": "right"})
    assert cfg.get("default_mouse_button") == "right"


def test_get_default_config_is_singleton():
    first = get_default_config()
    second = get_default_config()
    assert isinstance(first, BotVisionConfig)
    assert first is second

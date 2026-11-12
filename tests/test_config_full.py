"""
Full configuration tests for ``visus.desktop.utils.config.BotVisionConfig``
plus a few ``text_filters`` edge cases not already covered elsewhere.

``BotVisionConfig.__init__`` auto-detects Tesseract and raises
``TesseractNotFoundError`` when it is missing, so the config portion of this
module is guarded by the Tesseract availability check. The text_filters tests
are pure-Python and run unconditionally.

These config tests intentionally focus on angles such as attribute access,
to_dict copy semantics, AttributeError on unknown attributes, dict overrides,
and singleton identity. The text_filters tests stay distinct from
``tests/test_text_filters.py`` (no duplicate identical cases).
"""

import pytest

from tests import tesseract_available
from visus.desktop.utils.config import BotVisionConfig, get_default_config
from visus.desktop.utils.text_filters import (
    clean_text,
    matches_filter,
    validate_text_input,
)

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (BotVisionConfig requires it at construction)",
)


@requires_tesseract
class TestBotVisionConfig:
    """Behaviour of the main configuration container."""

    def test_defaults_via_get(self):
        cfg = BotVisionConfig()
        assert cfg.get("confidence_threshold") == 75.0
        assert cfg.get("retry_attempts") == 3
        assert cfg.get("default_delay") == 1.0
        assert cfg.get("log_level") == "INFO"
        assert cfg.get("ocr_languages") == ["eng"]
        assert cfg.get("show_overlay") is True

    def test_defaults_via_attribute_access(self):
        cfg = BotVisionConfig()
        # __getattr__ proxies known keys straight to the underlying dict.
        assert cfg.confidence_threshold == 75.0
        assert cfg.default_mouse_button == "left"
        assert cfg.overlay_color == "green"
        assert cfg.wait_timeout == 30

    def test_get_unknown_key_returns_default(self):
        cfg = BotVisionConfig()
        assert cfg.get("nope") is None
        assert cfg.get("nope", 123) == 123

    def test_unknown_attribute_raises(self):
        cfg = BotVisionConfig()
        with pytest.raises(AttributeError):
            _ = cfg.this_attribute_does_not_exist

    def test_set_updates_value(self):
        cfg = BotVisionConfig()
        cfg.set("confidence_threshold", 90.0)
        assert cfg.get("confidence_threshold") == 90.0
        # And it is visible through attribute access too.
        assert cfg.confidence_threshold == 90.0

    def test_attribute_assignment_for_known_key(self):
        cfg = BotVisionConfig()
        cfg.confidence_threshold = 82.5
        assert cfg.get("confidence_threshold") == 82.5

    def test_update_multiple_keys(self):
        cfg = BotVisionConfig()
        cfg.update({"confidence_threshold": 60.0, "retry_attempts": 7})
        assert cfg.get("confidence_threshold") == 60.0
        assert cfg.get("retry_attempts") == 7

    def test_to_dict_is_a_copy(self):
        cfg = BotVisionConfig()
        snapshot = cfg.to_dict()
        assert isinstance(snapshot, dict)
        assert snapshot["confidence_threshold"] == 75.0
        # Mutating the copy must not leak back into the live config.
        snapshot["confidence_threshold"] = 0.0
        snapshot["a_brand_new_key"] = "x"
        assert cfg.get("confidence_threshold") == 75.0
        assert cfg.get("a_brand_new_key") is None

    def test_config_dict_overrides_defaults(self):
        cfg = BotVisionConfig(
            {"confidence_threshold": 95.0, "retry_attempts": 1, "wait_timeout": 120}
        )
        assert cfg.get("confidence_threshold") == 95.0
        assert cfg.get("retry_attempts") == 1
        assert cfg.get("wait_timeout") == 120
        # Untouched keys keep their defaults.
        assert cfg.get("default_delay") == 1.0

    def test_invalid_overlay_color_coerced_to_green(self):
        cfg = BotVisionConfig({"overlay_color": "chartreuse"})
        assert cfg.get("overlay_color") == "green"

    def test_valid_overlay_color_is_kept(self):
        cfg = BotVisionConfig({"overlay_color": "magenta"})
        assert cfg.get("overlay_color") == "magenta"

    def test_invalid_mouse_button_coerced_to_left(self):
        cfg = BotVisionConfig({"default_mouse_button": "middle"})
        assert cfg.get("default_mouse_button") == "left"

    def test_valid_mouse_button_is_kept(self):
        cfg = BotVisionConfig({"default_mouse_button": "double"})
        assert cfg.get("default_mouse_button") == "double"

    def test_wait_timeout_custom_value(self):
        cfg = BotVisionConfig({"wait_timeout": 300})
        assert cfg.get("wait_timeout") == 300

    def test_confidence_threshold_custom_value(self):
        cfg = BotVisionConfig({"confidence_threshold": 88.0})
        assert cfg.confidence_threshold == 88.0

    def test_get_default_config_is_singleton(self):
        a = get_default_config()
        b = get_default_config()
        assert a is b
        assert isinstance(a, BotVisionConfig)


# ---------------------------------------------------------------------------
# text_filters edge cases (distinct from tests/test_text_filters.py)
# ---------------------------------------------------------------------------


class TestTextFiltersEdgeCases:
    """A handful of edge cases not already exercised by test_text_filters.py."""

    def test_clean_text_accented_input_both_filter(self):
        # 'both' keeps accented letters and digits, drops the rest.
        assert clean_text(" Olá, Mundo 2024! ", "both") == "OláMundo2024"

    def test_clean_text_accented_numbers_filter_drops_letters(self):
        assert clean_text("Ação42", "numbers") == "42"

    def test_clean_text_empty_string_returns_empty(self):
        assert clean_text("", "both") == ""
        assert clean_text("   ", "letters") == ""

    def test_clean_text_non_str_float_returns_empty(self):
        # A float (not covered by the int/None cases in the sibling module).
        assert clean_text(3.14, "both") == ""

    def test_clean_text_non_str_list_returns_empty(self):
        assert clean_text(["x"], "letters") == ""

    def test_matches_filter_lower_boundary_one(self):
        assert matches_filter("1", "numbers") is True

    def test_matches_filter_upper_boundary_thirtyone(self):
        assert matches_filter("31", "numbers") is True

    def test_matches_filter_just_above_boundary(self):
        # 32 is one past the documented 1..31 range.
        assert matches_filter("32", "numbers") is False

    def test_matches_filter_accented_letters(self):
        assert matches_filter("Olá", "letters") is True

    def test_validate_text_input_whitespace_only_raises(self):
        # Whitespace is stripped to nothing during cleaning -> ValueError.
        with pytest.raises(ValueError):
            validate_text_input("    ", "both")

    def test_validate_text_input_keeps_accents(self):
        assert validate_text_input("  Ação!  ", "letters") == "Ação"

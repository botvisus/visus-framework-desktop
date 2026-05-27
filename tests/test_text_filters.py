"""
Tests for ``visus.desktop.utils.text_filters``.

This module is pure Python (regex based) and imports cleanly without Tesseract
or a display, so every test here runs unconditionally.
"""
import pytest

from visus.desktop.utils.text_filters import (
    clean_text,
    limpar_texto,
    matches_filter,
    validate_text_input,
    extract_numbers_from_text,
    extract_letters_from_text,
)


class TestCleanText:
    """clean_text filters characters by type after stripping the ends."""

    def test_numbers_keeps_only_digits(self):
        assert clean_text("  123abc!  ", "numbers") == "123"

    def test_letters_keeps_only_letters(self):
        assert clean_text("  123abc!  ", "letters") == "abc"

    def test_both_keeps_letters_and_digits(self):
        assert clean_text("  123abc!  ", "both") == "123abc"

    def test_default_filter_is_both(self):
        assert clean_text("  123abc!  ") == "123abc"

    def test_letters_keeps_accented_characters(self):
        # Accented letters fall inside the configured unicode ranges.
        assert clean_text("ção123", "letters") == "ção"

    def test_other_filter_only_strips_edges(self):
        # An unrecognized filter strips leading/trailing special chars only,
        # keeping inner punctuation/spaces intact.
        assert clean_text("  --a b.c!--  ", "other") == "a b.c"

    def test_non_string_returns_empty(self):
        assert clean_text(123, "both") == ""
        assert clean_text(None, "letters") == ""

    def test_limpar_texto_is_same_function(self):
        assert limpar_texto is clean_text


class TestMatchesFilter:
    """matches_filter validates whole words against a filter type."""

    def test_numbers_within_range(self):
        assert matches_filter("15", "numbers") is True
        assert matches_filter("1", "numbers") is True
        assert matches_filter("31", "numbers") is True

    def test_numbers_out_of_range(self):
        assert matches_filter("32", "numbers") is False
        assert matches_filter("0", "numbers") is False

    def test_numbers_rejects_non_digits(self):
        assert matches_filter("12a", "numbers") is False

    def test_letters_only(self):
        assert matches_filter("abc", "letters") is True
        assert matches_filter("abc1", "letters") is False

    def test_both_accepts_alphanumeric(self):
        assert matches_filter("abc123", "both") is True
        assert matches_filter("abc 123", "both") is False  # space breaks fullmatch

    def test_unknown_filter_returns_true(self):
        assert matches_filter("anything!", "whatever") is True

    def test_non_string_returns_false(self):
        assert matches_filter(15, "numbers") is False
        assert matches_filter(None, "both") is False


class TestValidateTextInput:
    """validate_text_input returns cleaned text or raises ValueError."""

    def test_success_returns_cleaned_text(self):
        assert validate_text_input("  abc123!  ", "both") == "abc123"

    def test_success_numbers_filter(self):
        assert validate_text_input("page 12", "numbers") == "12"

    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            validate_text_input("", "both")

    def test_no_valid_chars_after_clean_raises(self):
        # Only digits present, but filter is "letters" -> nothing remains.
        with pytest.raises(ValueError):
            validate_text_input("12345", "letters")


class TestExtractNumbers:
    def test_extracts_digit_runs(self):
        assert extract_numbers_from_text("Page 5 of 10") == ["5", "10"]

    def test_no_numbers_returns_empty(self):
        assert extract_numbers_from_text("no digits here") == []

    def test_non_string_returns_empty(self):
        assert extract_numbers_from_text(None) == []


class TestExtractLetters:
    def test_extracts_letter_runs(self):
        assert extract_letters_from_text("Item123abc456def") == ["Item", "abc", "def"]

    def test_no_letters_returns_empty(self):
        assert extract_letters_from_text("123 456") == []

    def test_non_string_returns_empty(self):
        assert extract_letters_from_text(42) == []

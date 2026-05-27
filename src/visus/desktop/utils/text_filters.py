"""
Visus Desktop - Text Filters

This module contains functions for cleaning and filtering text extracted via OCR.
"""

import logging
import re

logger = logging.getLogger(__name__)


def clean_text(texto, filter_type="both"):
    """
    Remove characters from the text according to the desired filter.

    Args:
        texto (str): Text to be cleaned
        filter_type (str): Type of filter to apply:
            - "numbers": removes everything except digits
            - "letters": removes everything except letters (including accented ones)
            - "both": removes all characters that are not letters or digits
            - other: removes only special characters from the start and end

    Returns:
        str: Text cleaned according to the specified filter

    Examples:
        >>> limpar_texto("  123abc!  ", "numbers")
        "123"
        >>> limpar_texto("  123abc!  ", "letters")
        "abc"
        >>> limpar_texto("  123abc!  ", "both")
        "123abc"
    """
    if not isinstance(texto, str):
        logger.warning(f"Input is not a string: {type(texto)}")
        return ""

    texto = texto.strip()

    if filter_type == "numbers":
        texto = re.sub(r"[^\d]", "", texto)
    elif filter_type == "letters":
        texto = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ]", "", texto)
    elif filter_type == "both":
        # Allow letters and numbers
        texto = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ0-9]", "", texto)
    else:
        # Remove only special characters from the start and end
        texto = re.sub(r"^[\W_]+|[\W_]+$", "", texto)

    return texto


def matches_filter(word, filter_type):
    """
    Check whether the word matches the desired filter.

    Args:
        word (str): Word to be checked
        filter_type (str): Type of filter:
            - "numbers": only digits between 1 and 31
            - "letters": only letters (including accented ones)
            - "both": only letters and numbers
            - other: returns True

    Returns:
        bool: True if the word matches the filter, False otherwise

    Examples:
        >>> matches_filter("123", "numbers")
        True
        >>> matches_filter("abc", "letters")
        True
        >>> matches_filter("abc123", "both")
        True
        >>> matches_filter("32", "numbers")  # Outside the 1-31 range
        False
    """
    if not isinstance(word, str):
        return False

    filter_type = filter_type.lower()

    if filter_type == "numbers":
        if not re.fullmatch(r"\d+", word):
            return False
        try:
            num = int(word)
            return 1 <= num <= 31
        except ValueError:
            return False
    elif filter_type == "letters":
        return re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", word) is not None
    elif filter_type == "both":
        return re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+", word) is not None

    return True


def validate_text_input(text, filter_type="both"):
    """
    Validate and clean an input text.

    Args:
        text (str): Text to be validated
        filter_type (str): Type of filter to apply

    Returns:
        str: Validated and cleaned text

    Raises:
        ValueError: If the text is invalid after cleaning
    """
    if not text:
        raise ValueError("Text cannot be empty")

    cleaned_text = clean_text(text, filter_type)

    if not cleaned_text:
        raise ValueError(
            f"Text '{text}' does not contain valid characters for filter '{filter_type}'"
        )

    return cleaned_text


def extract_numbers_from_text(text):
    """
    Extract all numbers from a text.

    Args:
        text (str): Source text

    Returns:
        list: List of numbers found as strings

    Examples:
        >>> extract_numbers_from_text("Page 5 of 10 items")
        ["5", "10"]
    """
    if not isinstance(text, str):
        return []

    return re.findall(r"\d+", text)


def extract_letters_from_text(text):
    """
    Extract all letter sequences from a text.

    Args:
        text (str): Source text

    Returns:
        list: List of letter sequences found

    Examples:
        >>> extract_letters_from_text("Item123abc456def")
        ["Item", "abc", "def"]
    """
    if not isinstance(text, str):
        return []

    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", text)


# Backward-compatibility alias (previous Portuguese name)
limpar_texto = clean_text

"""
Tests for ``visus.desktop.exceptions``.

The exceptions module has no heavy dependencies, so these tests always run.
"""

import pytest

from visus.desktop.exceptions import (
    BotVisionError,
    ConfigurationError,
    ImageNotFoundError,
    ImageProcessingError,
    InvalidRegionError,
    OCRProcessingError,
    TaskExecutionError,
    TesseractNotFoundError,
    TextNotFoundError,
)

ALL_EXCEPTIONS = [
    TesseractNotFoundError,
    ImageNotFoundError,
    TextNotFoundError,
    InvalidRegionError,
    TaskExecutionError,
    ConfigurationError,
    OCRProcessingError,
    ImageProcessingError,
]


@pytest.mark.parametrize("exc_cls", ALL_EXCEPTIONS)
def test_subclasses_base_error(exc_cls):
    """Every custom exception inherits from BotVisionError (and Exception)."""
    assert issubclass(exc_cls, BotVisionError)
    assert issubclass(exc_cls, Exception)


def test_base_is_exception():
    assert issubclass(BotVisionError, Exception)


@pytest.mark.parametrize("exc_cls", [BotVisionError] + ALL_EXCEPTIONS)
def test_message_is_preserved(exc_cls):
    """str(exception) returns the message it was created with."""
    message = "something went wrong"
    err = exc_cls(message)
    assert str(err) == message


def test_raise_and_catch_specific_as_base():
    """A specific error can be caught via the base class."""
    with pytest.raises(BotVisionError):
        raise TextNotFoundError("text not found")


def test_raise_and_catch_specific_directly():
    with pytest.raises(ImageNotFoundError) as info:
        raise ImageNotFoundError("missing image")
    assert "missing image" in str(info.value)


def test_distinct_exceptions_do_not_alias():
    """The specific subclasses are genuinely distinct types."""
    assert OCRProcessingError is not ImageProcessingError
    assert TesseractNotFoundError is not ConfigurationError

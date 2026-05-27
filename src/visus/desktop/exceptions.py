"""
Visus Desktop - Custom Exceptions

This module defines all the custom exceptions used by the library.
"""


class BotVisionError(Exception):
    """Base exception for all Visus Desktop errors."""

    pass


class TesseractNotFoundError(BotVisionError):
    """Raised when Tesseract OCR is not found on the system."""

    pass


class ImageNotFoundError(BotVisionError):
    """Raised when an image is not found on the screen."""

    pass


class TextNotFoundError(BotVisionError):
    """Raised when a text is not found in the specified region."""

    pass


class InvalidRegionError(BotVisionError):
    """Raised when an invalid region is specified."""

    pass


class TaskExecutionError(BotVisionError):
    """Raised when there is an error executing a task."""

    pass


class ConfigurationError(BotVisionError):
    """Raised when there is an error in the library configuration."""

    pass


class OCRProcessingError(BotVisionError):
    """Raised when there is an error during OCR processing."""

    pass


class ImageProcessingError(BotVisionError):
    """Raised when there is an error during image processing."""

    pass

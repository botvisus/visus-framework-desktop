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


class NotSupportedOnThisOS(BotVisionError):
    """Raised when a feature is not available on the current operating system.

    Some capabilities (native UIA automation, Win32 window management) are
    Windows-only for now. They raise this instead of a low-level ImportError so
    callers get a clear, actionable message and can branch per platform.
    """

    pass


class CircuitBreakerTrippedError(BotVisionError):
    """Raised when ``execute_tasks`` aborts due to consecutive failures.

    The ``breaker_threshold`` config knob caps how many task failures in
    a row the executor tolerates before refusing to continue. The
    exception carries both the configured threshold and the failure
    count at trip time so callers can decide how to react.
    """

    def __init__(self, threshold: int, consecutive_failures: int):
        super().__init__(
            f"circuit breaker tripped: {consecutive_failures} consecutive "
            f"failures (threshold={threshold})"
        )
        self.threshold = threshold
        self.consecutive_failures = consecutive_failures

"""
Smoke tests for the public ``visus.desktop`` API.

These checks are pure import / identity assertions and require neither a real
screen nor Tesseract, except for the few that build a ``VisusBot``/config (which
detect Tesseract in their constructor and are therefore guarded).
"""

import pytest

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop import exceptions as exc

# Skip marker for anything that instantiates BotVisionConfig / VisusBot,
# because the config constructor raises TesseractNotFoundError otherwise.
requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed",
)


def test_version():
    """``__version__`` matches the installed distribution (pyproject's version),
    so a version bump can't leave the two disagreeing."""
    from importlib.metadata import version

    assert vd.__version__ == version("visus-desktop")


def test_visusbot_is_botvision_alias():
    """``BotVision`` is a backward-compatibility alias of ``VisusBot``."""
    assert vd.VisusBot is vd.BotVision


def test_clean_text_is_limpar_texto_alias():
    """``limpar_texto`` is the legacy alias of ``clean_text``."""
    assert vd.clean_text is vd.limpar_texto


@pytest.mark.parametrize(
    "name",
    [
        "execute_tasks",
        "run_automation",
        "click_images",
        "find_text",
        "click_text",
        "find_image",
        "click_image",
        "click_at",
        "type_text",
        "find_relative_image",
        "click_relative_image",
        "click_coordinates",
        "type_text_standalone",
        "keyboard_command_standalone",
        "get_available_keyboard_commands",
        "extract_text_from_region_standalone",
        "start_individual_session",
        "run_individual_tasks_with_backtrack",
        "clean_text",
        "limpar_texto",
        "matches_filter",
        "get_default_config",
        "show_overlay",
    ],
)
def test_public_callables_are_callable(name):
    """A representative set of public functions are importable and callable."""
    obj = getattr(vd, name)
    assert callable(obj), f"{name} should be callable"


@pytest.mark.parametrize(
    "name",
    [
        "VisusBot",
        "BotVision",
        "TaskExecutor",
        "TaskResult",
        "OCREngine",
        "OCRResult",
        "ImageProcessor",
        "VisualOverlay",
        "RelativeImageDetector",
        "KeyboardCommander",
        "BotVisionConfig",
    ],
)
def test_public_classes_are_classes(name):
    """Core classes are exported and are actual classes."""
    obj = getattr(vd, name)
    assert isinstance(obj, type), f"{name} should be a class"


@pytest.mark.parametrize(
    "name",
    [
        "BotVisionError",
        "TesseractNotFoundError",
        "ImageNotFoundError",
        "TextNotFoundError",
        "InvalidRegionError",
        "TaskExecutionError",
        "ConfigurationError",
        "OCRProcessingError",
        "ImageProcessingError",
    ],
)
def test_exception_classes_subclass_base(name):
    """Every documented exception exists and inherits from BotVisionError."""
    cls = getattr(exc, name)
    assert isinstance(cls, type)
    assert issubclass(cls, exc.BotVisionError)


def test_no_legacy_exception_names():
    """The wrong names used by the original (fictional) tests must not exist."""
    assert not hasattr(exc, "OCRError")
    assert not hasattr(exc, "ElementNotFoundError")


@requires_tesseract
def test_visusbot_instantiation_builds_components():
    """A default VisusBot wires up its config and executor components."""
    bot = vd.VisusBot()
    assert isinstance(bot.config, vd.BotVisionConfig)
    assert isinstance(bot.executor, vd.TaskExecutor)
    assert isinstance(bot.ocr_engine, vd.OCREngine)
    assert isinstance(bot.image_processor, vd.ImageProcessor)

"""
Tests for the core modules of ``visus.desktop``.

Most of these exercise parts that need neither a real screen nor Tesseract
(pure image preprocessing, data containers, command mappings). The few pieces
that require Tesseract or a Tk display are guarded with skip markers.
"""

import numpy as np
import pytest
from PIL import Image

from tests import tesseract_available
from visus.desktop.core.image_processing import (
    ImageProcessor,
    get_available_methods,
    preprocess_image_for_ocr,
)
from visus.desktop.core.keyboard_commands import KeyboardCommander
from visus.desktop.core.ocr_engine import OCRResult
from visus.desktop.core.relative_image import RelativeImageDetector
from visus.desktop.core.task_executor import TaskResult

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed",
)


def _tkinter_available():
    """Return True if a working Tk display can be created."""
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


requires_tk = pytest.mark.skipif(
    not _tkinter_available(),
    reason="Tkinter / display not available",
)


@pytest.fixture
def rgb_image():
    """A small white RGB PIL image (no screen capture needed)."""
    return Image.fromarray(np.full((40, 80, 3), 255, dtype=np.uint8))


class TestImageProcessor:
    """ImageProcessor works purely on in-memory PIL images via OpenCV/PIL."""

    def test_default_methods(self):
        processor = ImageProcessor()
        assert processor.methods == "all"
        assert isinstance(processor.available_methods, list)
        assert "hsv_enhancement" in processor.available_methods

    def test_custom_methods_argument_is_stored(self):
        processor = ImageProcessor(methods=["hsv_enhancement"])
        assert processor.methods == ["hsv_enhancement"]

    def test_preprocess_returns_list_of_images(self, rgb_image):
        processor = ImageProcessor()
        out = processor.preprocess_for_ocr(rgb_image)
        assert isinstance(out, list)
        assert len(out) == 19  # 19 documented preprocessing variants
        assert all(isinstance(img, Image.Image) for img in out)
        assert all(img.mode in ("RGB", "L", "1") for img in out)

    def test_standalone_preprocess_function(self, rgb_image):
        out = preprocess_image_for_ocr(rgb_image)
        assert isinstance(out, list)
        assert len(out) == 19

    def test_get_available_methods_helper(self):
        methods = get_available_methods()
        assert isinstance(methods, list)
        assert "combinations" in methods


class TestOCRResult:
    """OCRResult is a plain data container."""

    def test_attributes(self):
        result = OCRResult("hello", 87.5, (1, 2, 3, 4), method_index=2, config_index=5)
        assert result.text == "hello"
        assert result.confidence == 87.5
        assert result.box == (1, 2, 3, 4)
        assert result.method_index == 2
        assert result.config_index == 5

    def test_repr_contains_text_and_confidence(self):
        result = OCRResult("hi", 90.0, (0, 0, 1, 1))
        text = repr(result)
        assert "hi" in text
        assert "90.00" in text


class TestTaskResult:
    """TaskResult records the outcome of a single task execution."""

    def test_success_result(self):
        result = TaskResult(0, True, "find login", location=(10, 20, 30, 40))
        assert result.task_index == 0
        assert result.success is True
        assert result.task_name == "find login"
        assert result.location == (10, 20, 30, 40)
        assert result.error is None
        assert result.attempts == 0

    def test_failure_result_with_error(self):
        result = TaskResult(2, False, "click save", error="not found")
        assert result.success is False
        assert result.error == "not found"
        assert result.location is None


class TestKeyboardCommander:
    """KeyboardCommander only builds a command map at construction."""

    def test_available_commands_present(self):
        commander = KeyboardCommander()
        commands = commander.get_available_commands()
        assert isinstance(commands, list)
        assert "Ctrl+S" in commands
        assert "Ctrl+C" in commands
        assert len(commands) > 50

    def test_unknown_command_is_not_listed(self):
        commander = KeyboardCommander()
        assert "NotARealCommand" not in commander.get_available_commands()


class TestRelativeImageDetector:
    """The detector constructs without any external dependency."""

    def test_construction(self):
        detector = RelativeImageDetector()
        assert hasattr(detector, "locate_relative_image")


@requires_tk
class TestVisualOverlay:
    """VisualOverlay stores its visual parameters; we do not call show()."""

    def test_construction_stores_parameters(self):
        from visus.desktop.core.overlay import VisualOverlay

        overlay = VisualOverlay(color="blue", width=6, duration=500)
        assert overlay.color == "blue"
        assert overlay.width == 6
        assert overlay.duration == 500

    def test_default_parameters(self):
        from visus.desktop.core.overlay import VisualOverlay

        overlay = VisualOverlay()
        assert overlay.color == "red"
        assert overlay.width == 4
        assert overlay.duration == 1000


@requires_tesseract
class TestOCREngine:
    """OCREngine needs Tesseract configured at construction time."""

    def test_construction_builds_configs(self):
        from visus.desktop.core.ocr_engine import OCREngine

        engine = OCREngine()
        # The engine ships several Tesseract configs and method descriptions.
        assert len(engine.ocr_configs) == 7
        assert len(engine.config_names) == 7
        assert engine.image_processor is not None

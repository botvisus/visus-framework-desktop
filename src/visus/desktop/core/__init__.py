"""
Visus Desktop - Core Modules

This module contains the main classes and functions of Visus Desktop.
"""

from .image_processing import (
    ImageProcessor,
    get_available_methods,
    preprocess_image_for_ocr,
)
from .keyboard_commands import KeyboardCommander
from .ocr_engine import (
    OCREngine,
    OCRResult,
    extract_text_from_image,
    find_text_with_multiple_preprocessing,
)
from .overlay import (
    VisualOverlay,
    show_multiple_overlays,
    show_overlay,
    show_overlay_blocking,
)
from .relative_image import RelativeImageDetector
from .task_executor import TaskExecutor, TaskResult, click_images, execute_tasks

__all__ = [
    # Image processing
    "ImageProcessor",
    "preprocess_image_for_ocr",
    "get_available_methods",
    # OCR
    "OCREngine",
    "OCRResult",
    "find_text_with_multiple_preprocessing",
    "extract_text_from_image",
    # Overlay
    "VisualOverlay",
    "show_overlay",
    "show_overlay_blocking",
    "show_multiple_overlays",
    # Task executor
    "TaskExecutor",
    "TaskResult",
    "execute_tasks",
    "click_images",
    # Relative image detection (NEW!)
    "RelativeImageDetector",
    # Keyboard commands (NEW!)
    "KeyboardCommander",
]

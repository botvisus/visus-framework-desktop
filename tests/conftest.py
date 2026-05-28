"""
Test configuration and fixtures for the visus.desktop test suite.
"""

# Fully warm up cv2 before pytest collects any test module that imports
# ``visus.desktop`` (and before pytest-cov's import hooks run). Some cv2 builds
# ship a lazy ``cv2.typing`` module that references
# ``cv2.gapi.wip.draw.Text`` during a partial import; under coverage the import
# ordering can hit that half-initialized state and raise AttributeError.
# Importing eagerly here resolves it once, cleanly, for the whole session.
try:  # pragma: no cover - environment shim, not part of the tested code
    import cv2  # noqa: F401
    import cv2.typing  # noqa: F401
except Exception:  # pragma: no cover - cv2 is optional at import time
    pass

import tempfile
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

# Re-export the Tesseract detection helper so tests can import it from either
# ``tests`` or this conftest.
from tests import tesseract_available  # noqa: F401


@pytest.fixture(autouse=True)
def _isolate_failure_artifacts(monkeypatch, tmp_path_factory):
    """Redirect the default ``artifacts_dir`` to a per-session temp directory.

    The default value of ``BotVisionConfig['artifacts_dir']`` is
    ``./visus-artifacts/`` so failure screenshots land next to the user's bot.
    Inside the test suite that would dump PNGs into the project root whenever
    an existing test deliberately triggers a failure path. We patch the
    default once, per test, to a writable tmp location; tests that exercise
    the failure-screenshot feature explicitly still override ``artifacts_dir``
    with their own ``tmp_path``.
    """
    from visus.desktop.utils import config as _config

    real_load = _config.BotVisionConfig._load_default_config

    def _patched(self):
        defaults = real_load(self)
        defaults["artifacts_dir"] = str(tmp_path_factory.mktemp("visus-artifacts"))
        return defaults

    monkeypatch.setattr(_config.BotVisionConfig, "_load_default_config", _patched)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a simple white image with black text
    img = Image.new("RGB", (200, 100), color="white")
    # Note: In real tests, you might want to draw actual text
    return np.array(img)


@pytest.fixture
def mock_tesseract():
    """Mock Tesseract for testing without requiring installation."""
    with patch("pytesseract.image_to_string") as mock:
        mock.return_value = "Sample text from image"
        yield mock


@pytest.fixture
def mock_pyautogui():
    """Mock pyautogui for testing without GUI interactions."""
    with patch("pyautogui.screenshot") as mock_screenshot, patch(
        "pyautogui.click"
    ) as mock_click, patch("pyautogui.moveTo") as mock_move:
        # Create a mock screenshot
        mock_img = Image.new("RGB", (1920, 1080), color="white")
        mock_screenshot.return_value = mock_img

        yield {"screenshot": mock_screenshot, "click": mock_click, "moveTo": mock_move}


@pytest.fixture
def sample_task():
    """Sample task configuration for testing."""
    return {
        "task_name": "test_task",
        "description": "A test task",
        "steps": [
            {"action": "find_text", "text": "test_text", "region": [0, 0, 100, 100]}
        ],
    }


@pytest.fixture
def sample_tasks():
    """Multiple sample tasks for testing."""
    return [
        {
            "task_name": "task1",
            "description": "First test task",
            "steps": [
                {"action": "find_text", "text": "button1", "region": [0, 0, 200, 200]}
            ],
        },
        {
            "task_name": "task2",
            "description": "Second test task",
            "steps": [
                {
                    "action": "click_text",
                    "text": "submit",
                    "region": [100, 100, 300, 300],
                }
            ],
        },
    ]

"""
Visus Desktop - Configuration

This module manages the library configuration, including automatic Tesseract
detection and operating-system-specific settings.
"""

import logging
import os
import platform
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from ..exceptions import ConfigurationError, TesseractNotFoundError

logger = logging.getLogger(__name__)


class BotVisionConfig:
    """
    Main configuration class for Visus Desktop.

    Automatically manages:
    - Tesseract OCR detection
    - OS-specific settings
    - Dependency validation
    - Default settings
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration.

        Args:
            config_dict (dict, optional): Dictionary of custom settings
        """
        self.config = self._load_default_config()

        if config_dict:
            self.config.update(config_dict)

        self._detect_tesseract()
        self._validate_dependencies()
        self._validate_overlay_config()
        self._validate_mouse_button_config()

    def _validate_overlay_config(self) -> None:
        """Validate the overlay settings."""
        valid_colors = [
            "red",
            "blue",
            "green",
            "yellow",
            "purple",
            "orange",
            "cyan",
            "magenta",
            "white",
            "black",
        ]

        overlay_color = self.config.get("overlay_color", "red")
        if overlay_color not in valid_colors:
            logger.warning(
                f"Invalid overlay color '{overlay_color}'. Using 'red'. "
                f"Valid colors: {', '.join(valid_colors)}"
            )
            self.config["overlay_color"] = "red"

        # Validate duration
        overlay_duration = self.config.get("overlay_duration", 1000)
        if not isinstance(overlay_duration, (int, float)) or overlay_duration <= 0:
            logger.warning(
                f"Invalid overlay duration '{overlay_duration}'. Using 1000ms."
            )
            self.config["overlay_duration"] = 1000

        # Validate width
        overlay_width = self.config.get("overlay_width", 4)
        if not isinstance(overlay_width, (int, float)) or overlay_width <= 0:
            logger.warning(f"Invalid overlay width '{overlay_width}'. Using 4.")
            self.config["overlay_width"] = 4

    def _validate_mouse_button_config(self) -> None:
        """Validate the mouse_button settings."""
        valid_mouse_buttons = ["left", "right", "double", "move_to"]

        default_mouse_button = self.config.get("default_mouse_button", "left")
        if default_mouse_button not in valid_mouse_buttons:
            logger.warning(
                f"Invalid default mouse button '{default_mouse_button}'. Using 'left'. "
                f"Valid options: {', '.join(valid_mouse_buttons)}"
            )
            self.config["default_mouse_button"] = "left"

    def _load_default_config(self) -> Dict[str, Any]:
        """Load the default settings."""
        return {
            "tesseract_path": None,
            "tesseract_data_path": None,
            "confidence_threshold": 75.0,
            "retry_attempts": 3,
            "default_delay": 1.0,
            "overlay_duration": 1000,
            "overlay_color": "red",  # red, blue, green, yellow, purple, orange, cyan, magenta, white
            "overlay_width": 4,
            "show_overlay": True,  # Controls whether a visual overlay is shown before the click
            "overlay_enabled": True,  # Controls whether the overlay system is active
            "default_mouse_button": "left",  # Default mouse button: 'left', 'right', 'double', 'move_to'
            "log_level": "INFO",
            "ocr_languages": ["eng"],
            "image_processing_methods": "all",  # or a specific list
            "click_duration": 0.1,
            "movement_duration": 0.1,
            # 🆕 NEW PARAMETERS v1.3.0+
            "use_virtual_mouse": False,  # Virtual mouse (cursor does not move)
            "wait_timeout": 30,  # Global timeout for wait parameters (30-300s)
            "screenshot_delay": 0.1,  # Delay for screen capture
        }

    def _detect_tesseract(self) -> None:
        """
        Automatically detect the Tesseract installation on the system.
        """
        tesseract_paths = self._get_tesseract_paths()

        for path in tesseract_paths:
            if self._validate_tesseract_path(path):
                self.config["tesseract_path"] = path
                self.config["tesseract_data_path"] = self._get_tessdata_path(path)
                logger.info(f"Tesseract found at: {path}")
                return

        # If not found, try using the one from PATH
        tesseract_cmd = shutil.which("tesseract")
        if tesseract_cmd and self._validate_tesseract_path(tesseract_cmd):
            self.config["tesseract_path"] = tesseract_cmd
            logger.info(f"Tesseract found in PATH: {tesseract_cmd}")
            return

        # If we got here, Tesseract was not found
        logger.error("Tesseract OCR not found on the system")
        raise TesseractNotFoundError(
            "Tesseract OCR was not found. Please install Tesseract OCR:\n"
            "Windows: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "Linux: sudo apt-get install tesseract-ocr\n"
            "macOS: brew install tesseract"
        )

    def _get_tesseract_paths(self) -> list:
        """Return a list of possible Tesseract paths based on the OS."""
        system = platform.system().lower()

        if system == "windows":
            return [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(
                    os.getenv("USERNAME", "")
                ),
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            ]
        elif system == "linux":
            return [
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract",
                "/opt/tesseract/bin/tesseract",
                "/snap/bin/tesseract",
            ]
        elif system == "darwin":  # macOS
            return [
                "/usr/local/bin/tesseract",
                "/opt/homebrew/bin/tesseract",
                "/usr/bin/tesseract",
                "/Applications/Tesseract.app/Contents/MacOS/tesseract",
            ]
        else:
            return ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]

    def _validate_tesseract_path(self, path: str) -> bool:
        """Validate whether a Tesseract path is valid."""
        if not path or not os.path.exists(path):
            return False

        try:
            import subprocess

            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Error validating Tesseract at {path}: {e}")
            return False

    def _get_tessdata_path(self, tesseract_path: str) -> Optional[str]:
        """Determine the tessdata path based on the Tesseract path."""
        tesseract_dir = os.path.dirname(tesseract_path)

        # Possible tessdata locations
        possible_paths = [
            os.path.join(tesseract_dir, "tessdata"),
            os.path.join(os.path.dirname(tesseract_dir), "tessdata"),
            os.path.join(tesseract_dir, "..", "share", "tessdata"),
            "/usr/share/tesseract-ocr/5/tessdata",  # Linux
            "/usr/share/tesseract-ocr/4/tessdata",  # Linux
            "/usr/local/share/tessdata",  # macOS
        ]

        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                return path

        logger.warning("Could not determine the tessdata path")
        return None

    def _validate_dependencies(self) -> None:
        """Validate that all dependencies are installed."""
        required_modules = [
            "pyautogui",
            "pytesseract",
            "cv2",
            "PIL",
            "numpy",
            "pyperclip",
        ]

        missing_modules = []

        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)

        if missing_modules:
            raise ConfigurationError(
                f"Required modules not found: {', '.join(missing_modules)}\n"
                f"Run: pip install visus-desktop[dev]"
            )

    def setup_tesseract(self) -> None:
        """Configure Tesseract with the current settings."""
        try:
            import pytesseract

            if self.config["tesseract_path"]:
                pytesseract.pytesseract.tesseract_cmd = self.config["tesseract_path"]

            if self.config["tesseract_data_path"]:
                os.environ["TESSDATA_PREFIX"] = self.config["tesseract_data_path"]

            logger.info("Tesseract configured successfully")

        except ImportError as e:
            raise ConfigurationError("pytesseract is not installed") from e

    def setup_logging(self) -> None:
        """Configure the logging system."""
        log_level = getattr(logging, self.config["log_level"].upper(), logging.INFO)
        logging.basicConfig(
            level=log_level, format="[%(levelname)s] %(name)s: %(message)s"
        )

    def __getattr__(self, name):
        """Allow direct access to configuration values as attributes."""
        if name == "config":
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
        if hasattr(self, "config") and name in self.config:
            return self.config[name]
        raise AttributeError(f"Setting '{name}' not found")

    def __setattr__(self, name, value):
        """Allow setting configuration values as attributes."""
        if name in ["config"] or not hasattr(self, "config"):
            super().__setattr__(name, value)
        elif name in self.config:
            self.config[name] = value
        else:
            super().__setattr__(name, value)

    def get(self, key, default=None):
        """Get a configuration value with a default."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set a configuration value."""
        self.config[key] = value

    def update(self, config_dict):
        """Update multiple settings."""
        self.config.update(config_dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return all settings as a dictionary."""
        return self.config.copy()


def create_config_from_file(config_path: str) -> BotVisionConfig:
    """
    Create a configuration from a file.

    Args:
        config_path (str): Path to the configuration file (JSON or YAML)

    Returns:
        BotVisionConfig: Configured instance
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    if config_path.suffix.lower() == ".json":
        import json

        with open(config_path, encoding="utf-8") as f:
            config_dict = json.load(f)
    elif config_path.suffix.lower() in [".yml", ".yaml"]:
        try:
            import yaml

            with open(config_path, encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)
        except ImportError as e:
            raise ConfigurationError(
                "PyYAML is not installed. Run: pip install PyYAML"
            ) from e
    else:
        raise ConfigurationError(f"Unsupported file format: {config_path.suffix}")

    return BotVisionConfig(config_dict)


# Global default instance
default_config = None


def get_default_config() -> BotVisionConfig:
    """Return the default configuration instance (singleton)."""
    global default_config
    if default_config is None:
        default_config = BotVisionConfig()
    return default_config

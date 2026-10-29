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


def get_tesseract_candidate_paths() -> list:
    """Return the OS-appropriate Tesseract install paths to probe.

    Shared by ``BotVisionConfig`` (full validation, runs the binary) and
    ``visus.desktop.doctor`` (cheap existence-only diagnostic), so both
    paths stay in lock-step. Each list is deduplicated while preserving
    order.
    """
    system = platform.system().lower()
    if system == "windows":
        user_local = (
            r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(
                os.getenv("USERNAME", "")
            )
        )
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            user_local,
        ]
    elif system == "linux":
        candidates = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/tesseract/bin/tesseract",
            "/snap/bin/tesseract",
        ]
    elif system == "darwin":
        candidates = [
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
            "/usr/bin/tesseract",
            "/Applications/Tesseract.app/Contents/MacOS/tesseract",
        ]
    else:
        candidates = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]
    # Preserve first-occurrence order while deduplicating.
    seen: set = set()
    return [p for p in candidates if not (p in seen or seen.add(p))]


class BotVisionConfig:
    """Configuration for :class:`VisusBot` -- defaults + every tunable knob.

    Holds a dict of settings and validates them at construction:

        * **Auto-detects Tesseract** on the standard install paths only when
          ``ocr_backend == "tesseract"``. The default backend is ``rapidocr``
          (bundled ONNX models, no external binary), which skips detection;
          if rapidocr isn't installed the OCR engine falls back to Tesseract.
        * **Validates** overlay color, overlay duration, overlay width,
          and default mouse button; invalid values fall back with a
          warning instead of raising.
        * **Forward-compatible**: unknown keys are accepted silently so
          configs survive Visus upgrades.
        * **Back-compat**: the legacy ``overlay_enabled`` key (now
          deprecated) is folded into ``show_overlay`` via logical AND.

    Pass a partial dict to override only what you care about; everything
    else uses the library defaults. **For the full key reference grouped
    by topic (OCR, matching, mouse, overlay, waits, diagnostics) hover
    or jump to :meth:`__init__` below.**

    Reads / writes:

        * Dict-style: ``cfg.get(key, default)``, ``cfg.config[key] = v``.
        * Attribute-style: ``cfg.confidence_threshold`` proxies to
          ``cfg.config["confidence_threshold"]``.
        * Setattr on a known key writes back into the underlying dict.

    Examples:
        Defaults::

            from visus.desktop import BotVisionConfig, VisusBot
            cfg = BotVisionConfig()
            bot = VisusBot(config=cfg)

        Override a few keys::

            cfg = BotVisionConfig({
                "overlay_color": "green",
                "overlay_duration": 1500,
                "matcher": "cv2",
                "confidence_threshold": 85.0,
            })

        Read or mutate after construction::

            cfg.confidence_threshold        # attribute proxy -> 85.0
            cfg.get("overlay_duration")     # dict-style -> 1500
            cfg.config["log_level"] = "DEBUG"   # in-place update

        Production preset (no overlay, JSON logs to ingest downstream)::

            cfg = BotVisionConfig({
                "show_overlay": False,
                "log_format": "json",
                "log_level": "WARNING",
            })
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """Initialize the Visus Desktop configuration.

        Pass any subset of the keys below in ``config_dict``; missing keys
        fall back to the defaults shown. Unknown keys are accepted and
        ignored, except for the legacy ``overlay_enabled`` which is folded
        into ``show_overlay`` for back-compat.

        Args:
            config_dict (dict, optional): Custom settings. Recognized keys:

                **OCR / Tesseract**

                * ``tesseract_path`` (str | None, default ``None`` -- auto-detected):
                  Path to ``tesseract.exe``/``tesseract``. Leave ``None`` to let
                  Visus probe the standard install locations.
                * ``tesseract_data_path`` (str | None, default ``None`` -- auto-detected):
                  Path to the ``tessdata`` directory containing language data.
                * ``ocr_languages`` (list[str], default ``["eng"]``): Tesseract
                  language codes to load (e.g. ``["eng", "por"]``).
                * ``ocr_backend`` (str, default ``"tesseract"``): OCR engine.
                  ``"tesseract"`` (default; requires the binary) or
                  ``"rapidocr"`` (PP-OCR via ONNX Runtime, no external binary;
                  install with ``pip install 'visus-desktop[rapidocr]'``).
                * ``image_processing_methods`` (str | list, default ``"all"``):
                  Preprocessing pipeline before OCR. ``"all"`` runs every method,
                  or pass a list to restrict (e.g. ``["original", "grayscale"]``).

                **Matching / detection**

                * ``confidence_threshold`` (float, default ``75.0``): Default OCR
                  confidence (0--100). Words below this are discarded.
                * ``matcher`` (str, default ``"cv2"``): Image-template backend.
                  ``"cv2"`` (fast: cv2.matchTemplate over mss; falls back to
                  pyscreeze if it misses) or ``"pyscreeze"`` (legacy).
                * ``retry_attempts`` (int, default ``3``): Default retry attempts
                  for find/click methods.

                **Mouse / click**

                * ``default_mouse_button`` (str, default ``"left"``): One of
                  ``"left"``, ``"right"``, ``"double"``, ``"move_to"``.
                * ``click_duration`` (float, default ``0.1``): Seconds the click
                  takes (passed to pyautogui).
                * ``movement_duration`` (float, default ``0.1``): Seconds to move
                  the cursor to the target before clicking.
                * ``use_virtual_mouse`` (bool, default ``False``): If ``True``,
                  click via ``PostMessage`` so the physical cursor does not move
                  (Windows; falls back to physical if the target window cannot
                  receive synthetic input).
                * ``virtual_mouse_strict`` (bool, default ``False``): With
                  ``use_virtual_mouse``, a virtual click that fails returns
                  False instead of falling back to the physical mouse -- for
                  background automation, where the person keeps the real one.
                * ``default_delay`` (float, default ``1.0``): Default pause (s)
                  between actions in higher-level flows.

                **Overlay (visual feedback)**

                * ``show_overlay`` (bool, default ``True``): Master toggle.
                  When ``True``, every click first paints a click-through
                  overlay around the target. On Windows it uses ``WS_EX_LAYERED``
                  + ``WS_EX_TRANSPARENT`` so the click passes through to the
                  host below (works over native, Java, Electron, browsers).
                * ``overlay_color`` (str, default ``"red"``): One of ``red``,
                  ``blue``, ``green``, ``yellow``, ``purple``, ``orange``,
                  ``cyan``, ``magenta``, ``white``, ``black``.
                * ``overlay_duration`` (int, default ``1000``): How long the
                  overlay stays on screen, in milliseconds.
                * ``overlay_width`` (int, default ``4``): Outline thickness
                  in pixels.

                **Waits / timeouts**

                * ``wait_timeout`` (int, default ``30``): Default timeout in
                  seconds for ``wait_until_found`` / ``wait_until_disappears``.
                * ``screenshot_delay`` (float, default ``0.1``): Pause before
                  capturing the screen (lets late repaints settle).

                **Diagnostics / artifacts**

                * ``log_level`` (str, default ``"INFO"``): Standard ``logging``
                  level (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
                * ``log_format`` (str, default ``"text"``): Task event format.
                  ``"text"`` (human-readable ``[INFO]`` lines) or ``"json"``
                  (one JSON object per task on logger ``visus.desktop.task_events``).
                * ``artifacts_dir`` (str, default ``"./visus-artifacts"``):
                  Folder for failure screenshots / diagnostic dumps.
                * ``screenshot_on_failure`` (bool, default ``True``): If
                  ``True``, save a screenshot to ``artifacts_dir`` whenever a
                  task fails.

        Examples:
            Defaults only::

                config = BotVisionConfig()

            Tune the overlay and matcher::

                config = BotVisionConfig({
                    "overlay_color": "green",
                    "overlay_duration": 1500,
                    "matcher": "cv2",
                    "confidence_threshold": 85.0,
                })

            Headless / production (no visual feedback, JSON logs)::

                config = BotVisionConfig({
                    "show_overlay": False,
                    "log_level": "WARNING",
                    "log_format": "json",
                })
        """
        self.config = self._load_default_config()

        if config_dict:
            # Back-compat: the old ``overlay_enabled`` flag has been folded
            # into ``show_overlay`` (they were AND-gated, identical effect).
            # If the caller still passes it, intersect it with show_overlay
            # so disabling via either key keeps disabling the overlay.
            if "overlay_enabled" in config_dict:
                legacy = bool(config_dict.pop("overlay_enabled"))
                config_dict["show_overlay"] = (
                    bool(config_dict.get("show_overlay", True)) and legacy
                )
            self.config.update(config_dict)

        # Tesseract is only required when it is the active OCR backend (Phase 3 / E5).
        # The default backend is now ``rapidocr`` (bundled ONNX models, no
        # external binary); it skips this gate. Tesseract is detected only when
        # explicitly selected — and the OCR engine falls back to Tesseract at
        # construction if rapidocr isn't installed (it detects then).
        if self.config.get("ocr_backend", "rapidocr") == "tesseract":
            self._detect_tesseract()
        self._validate_dependencies()
        self._validate_overlay_config()
        self._validate_mouse_button_config()
        # Apply ``log_level`` to the active logging setup. Without this
        # call, the config key is stored but never takes effect because
        # the library installs a default INFO handler at import time and
        # ``logging.basicConfig`` is a no-op once any handler exists.
        self.setup_logging()

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
            "show_overlay": True,  # Master toggle: show the overlay before clicks
            "default_mouse_button": "left",  # Default mouse button: 'left', 'right', 'double', 'move_to'
            "log_level": "INFO",
            "ocr_languages": ["eng"],
            "image_processing_methods": "all",  # or a specific list
            "click_duration": 0.1,
            "movement_duration": 0.1,
            # 🆕 NEW PARAMETERS v1.3.0+
            "use_virtual_mouse": False,  # Virtual mouse (cursor does not move)
            "virtual_mouse_strict": False,  # With it: a failed virtual click fails (no physical fallback)
            "wait_timeout": 30,  # Global timeout for wait parameters (30-300s)
            "screenshot_delay": 0.1,  # Delay for screen capture
            # Failure artifacts (Phase 1 / O1)
            "artifacts_dir": "./visus-artifacts",
            "screenshot_on_failure": True,
            # Draw the matched (x, y, w, h) box + crosshair on saved
            # step / failure screenshots, in the same overlay_color /
            # overlay_width style. Independent of the on-screen overlay
            # timing -- always present in the PNG when a location is known.
            "screenshot_annotate": True,
            # Structured task event logging (Phase 1 / O2)
            #   'text' -> human-readable [INFO] lines (the default)
            #   'json' -> one JSON object per task on logger
            #            ``visus.desktop.task_events``
            "log_format": "text",
            # Pluggable OCR backend (Phase 3 / E5).
            #   'rapidocr'  -> DEFAULT; PP-OCR models via ONNX Runtime, no
            #                  external binary, more robust on styled text.
            #                  Ships with the [rapidocr] extra; if it isn't
            #                  installed the OCR engine falls back to tesseract.
            #   'tesseract' -> pytesseract + multi-PSM pipeline (needs the
            #                  Tesseract binary on PATH).
            "ocr_backend": "rapidocr",
            # Image-matching backend (Phase 3 / E1).
            #   'cv2'       -> default; cv2.matchTemplate over mss-captured
            #                  haystack; ~2-5x faster than pyscreeze on
            #                  1080p haystacks. Falls back to pyscreeze
            #                  when matchTemplate misses.
            #   'pyscreeze' -> legacy pyautogui.locateOnScreen path only.
            "matcher": "cv2",
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
        return get_tesseract_candidate_paths()

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
        """Apply ``config["log_level"]`` to the active logging setup.

        Idempotent and safe to call any number of times. The library
        installs an INFO-level root handler at import time (in
        ``_setup_library``), so by the time ``BotVisionConfig`` is
        constructed, ``logging.basicConfig`` is already a no-op. To make
        ``log_level`` actually take effect we have to:

            1. ``basicConfig`` if no handler exists yet (cold start);
            2. otherwise update the root logger's level **and** the level
               of every handler attached to it (the root level alone is
               not enough because each handler has its own filter).
        """
        level_name = str(self.config.get("log_level", "INFO")).upper()
        log_level = getattr(logging, level_name, logging.INFO)
        root = logging.getLogger()
        if not root.handlers:
            logging.basicConfig(
                level=log_level,
                format="[%(levelname)s] %(name)s: %(message)s",
            )
            return
        root.setLevel(log_level)
        for handler in root.handlers:
            handler.setLevel(log_level)

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
            if name == "log_level":
                self.setup_logging()
        else:
            super().__setattr__(name, value)

    def get(self, key, default=None):
        """Get a configuration value with a default."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set a configuration value."""
        self.config[key] = value
        if key == "log_level":
            self.setup_logging()

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

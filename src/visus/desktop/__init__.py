r"""
Visus Desktop - Advanced GUI Automation with OCR

An advanced Python library for graphical interface automation that combines
optimized optical character recognition (OCR) with image detection
to run automated tasks on desktop applications.

⚠️  IMPORTANT REQUIREMENT: TESSERACT OCR MUST BE INSTALLED! ⚠️

📥 TESSERACT INSTALLATION:
    1. Download: https://github.com/UB-Mannheim/tesseract/wiki
    2. Install to: C:\\Program Files\\Tesseract-OCR\\
    3. Add it to the system PATH
    4. Test: tesseract --version

🚀 COMPLETE FEATURES - INDIVIDUAL METHODS AND LISTS 🚀

═══════════════════════════════════════════════════════════════════════════════

🔥 BACKTRACK BETWEEN INDIVIDUAL METHODS (NEW!):

    >>> from visus.desktop import VisusBot
    >>>
    >>> bot = VisusBot()
    >>>
    >>> # OPTION 1: Auto-starts a session when backtrack=True
    >>> success1 = bot.click_image('button1.png', backtrack=True)
    >>> success2 = bot.click_text('Save', backtrack=True)  # If it fails, goes back to button1
    >>> success3 = bot.click_text('Confirm', backtrack=True)  # If it fails, goes back to Save
    >>>
    >>> # OPTION 2: Manual session control
    >>> bot.start_task_session()  # Starts a backtrack session
    >>> bot.click_image('button1.png', backtrack=True)
    >>> bot.click_text('agent', backtrack=True)
    >>> bot.click_text('Claude Sonnet 4', backtrack=True)
    >>> successful, total = bot.end_task_session()  # Ends and shows statistics

═══════════════════════════════════════════════════════════════════════════════

📋 TASK LIST EXECUTION (Original Method + NEW FEATURES):

    >>> from visus.desktop import VisusBot, execute_tasks
    >>>
    >>> # Tasks with ALL features (including the NEW ones!)
    >>> tasks = [
    ...     # 1. Traditional image search
    ...     {
    ...         'image': 'button.png',
    ...         'region': (100, 100, 200, 50),
    ...         'confidence': 0.9,
    ...         'specific': False,       # Allows scale variations
    ...         'backtrack': True,       # Automatic retry
    ...         'delay': 1,
    ...         'mouse_button': 'left'   # 'left', 'right', 'double', 'move_to'
    ...     },
    ...     # 2. OCR text search
    ...     {
    ...         'text': 'Login',
    ...         'region': (50, 50, 300, 100),
    ...         'occurrence': 1,         # First occurrence
    ...         'char_type': 'letters',  # Character filter
    ...         'backtrack': True,       # Automatic retry
    ...         'delay': 0.5,
    ...         'sendtext': 'usuario123' # Types after clicking
    ...     },
    ...     # 3. NEW! Relative image search (anchor + target)
    ...     {
    ...         'type': 'relative_image',
    ...         'anchor_image': 'warning_icon.png',    # Unique anchor image
    ...         'target_image': 'ok_button.png',       # Nearby target image
    ...         'max_distance': 200,                   # Maximum distance in pixels
    ...         'confidence': 0.9,
    ...         'target_region': (0, 0, 800, 600),     # Region to search for the target (optional)
    ...         'specific': True,
    ...         'backtrack': True,
    ...         'delay': 1
    ...     },
    ...     # 4. NEW! Click on specific coordinates
    ...     {
    ...         'type': 'click',
    ...         'x': 500,                              # X coordinate
    ...         'y': 300,                              # Y coordinate
    ...         'mouse_button': 'right',               # 'left', 'right', 'double', 'move_to'
    ...         'delay': 0.5,
    ...         'backtrack': False
    ...     },
    ...     # 5. NEW! Direct text typing
    ...     {
    ...         'type': 'type_text',
    ...         'text': 'Hello World!',               # Text to type
    ...         'interval': 0.05,                     # Interval between characters
    ...         'delay': 1
    ...     },
    ...     # 6. NEW! Keyboard command
    ...     {
    ...         'type': 'keyboard_command',
    ...         'command': 'Ctrl+S',                  # Command to run
    ...         'delay': 1
    ...     }
    ... ]
    >>>
    >>> # Simple execution
    >>> execute_tasks(tasks)
    >>>
    >>> # Advanced execution with control
    >>> bot = VisusBot()
    >>> results = bot.execute_tasks(tasks)

═══════════════════════════════════════════════════════════════════════════════

🎯 INDIVIDUAL METHODS WITH ALL FEATURES:

📸 IMAGE SEARCH AND CLICK (FULL DETAILS):

    >>> bot = VisusBot()
    >>>
    >>> # Basic image search
    >>> location = bot.find_image('button.png',
    ...                          region=(100, 100, 300, 200),
    ...                          confidence=0.9)
    >>>
    >>> # Click an image WITH ALL PARAMETERS:
    >>> success = bot.click_image('element_1_2.png',
    ...                          region=(3, 664, 41, 46),      # x, y, width, height
    ...                          confidence=0.9,               # 0.0 to 1.0 (90% accuracy)
    ...                          delay=1,                      # Pause 1 sec after clicking
    ...                          mouse_button='left',          # 'left', 'right', 'double', 'move_to'
    ...                          backtrack=True,               # Smart retry
    ...                          specific=False,               # False = allows variations
    ...                          max_attempts=3)               # Maximum 3 attempts
    >>>
    >>> # DETAILED PARAMETERS:
    >>> # region:       Defines the search area (x, y, width, height)
    >>> # confidence:   Detection accuracy (0.8=80%, 0.95=95%)
    >>> # delay:        Pause in seconds after the action
    >>> # mouse_button: Type of click to perform
    >>> # backtrack:    If it fails, re-runs the previous task
    >>> # specific:     True=searches in the region, False=searches the whole screen + variations
    >>> # max_attempts: How many times to try before giving up

📝 OCR TEXT SEARCH AND CLICK (FULL DETAILS):

    >>> # Basic text search
    >>> location = bot.find_text('Login',
    ...                         region=(0, 0, 800, 600),
    ...                         filter_type='letters',        # 'letters', 'numbers', 'both'
    ...                         confidence_threshold=75.0,
    ...                         occurrence=1)                 # Which occurrence
    >>>
    >>> # Click text WITH ALL PARAMETERS:
    >>> success = bot.click_text('Claude Sonnet 4',
    ...                         region=(1363, 965, 85, 23),   # x, y, width, height
    ...                         filter_type='letters',        # Letters only (no numbers)
    ...                         delay=1,                       # Pause 1 sec after clicking
    ...                         mouse_button='left',           # Left click
    ...                         occurrence=1,                  # First occurrence
    ...                         backtrack=True,                # Smart retry
    ...                         max_attempts=3,                # Maximum 3 attempts
    ...                         sendtext=None)                 # Text to type afterwards
    >>>
    >>> # DETAILED PARAMETERS:
    >>> # region:               Defines the search area on screen
    >>> # filter_type:          'letters'=letters only, 'numbers'=numbers only, 'both'=both
    >>> # delay:                Pause after the click
    >>> # mouse_button:         Type of click ('left', 'right', 'double', 'move_to')
    >>> # occurrence:           Which occurrence to click (1=first, 2=second, etc.)
    >>> # backtrack:            Smart retry that re-runs previous tasks
    >>> # max_attempts:         Number of attempts before giving up
    >>> # sendtext:             Text to type after the click (None=does not type)
    >>> # confidence_threshold: OCR accuracy (75.0=75%, 90.0=90%)

🖱️ CLICKS AND ACTIONS (FULL DETAILS):

    >>> # Click on specific coordinates WITH ALL PARAMETERS:
    >>> bot.click_at((100, 200, 50, 30),              # x, y, width, height
    ...              mouse_button='left',              # 'left', 'right', 'double', 'move_to'
    ...              delay=1)                          # Pause after clicking
    >>>
    >>> # Type text WITH SPECIAL COMMANDS:
    >>> bot.type_text('Hello World')                   # Plain text
    >>> bot.type_text('{ctrl}a{del}New Text{enter}')   # Special commands
    >>>
    >>> # SUPPORTED SPECIAL COMMANDS:
    >>> # {ctrl}a     = Ctrl+A (select all)
    >>> # {del}       = Delete
    >>> # {tab}       = Tab
    >>> # {enter}     = Enter
    >>> # Normal text = Typed via the clipboard for greater reliability

🎯 RELATIVE IMAGES (NEW! - Search a Target near an Anchor):

    >>> # Locates a target image near a specific anchor image
    >>> location = bot.find_relative_image(
    ...     anchor_image='menu_button.png',     # Anchor image (unique on screen)
    ...     target_image='option.png',          # Target image (there may be several)
    ...     max_distance=150,                   # Maximum distance in pixels
    ...     confidence=0.9,                     # Detection confidence
    ...     target_region=(0, 0, 800, 600)      # Region to search for the target (optional)
    ... )
    >>>
    >>> # Click a relative image WITH ALL PARAMETERS:
    >>> success = bot.click_relative_image(
    ...     anchor_image='anchor.png',          # Reference anchor
    ...     target_image='target.png',          # Target to click
    ...     max_distance=200,                   # At most 200px from the anchor
    ...     confidence=0.9,                     # 90% accuracy
    ...     target_region=None,                 # None = searches the whole screen
    ...     delay=1,                           # Pause after clicking
    ...     mouse_button='left',               # Type of click
    ...     backtrack=True,                    # Smart retry
    ...     max_attempts=3                     # Maximum attempts
    ... )
    >>>
    >>> # PRACTICAL USE: Useful when there are multiple identical options on screen
    >>> # Example: Several "OK" images but you want the one near "Warning"

⌨️ COMPLETE KEYBOARD COMMANDS (NEW! - Expanded List):

    >>> # Runs a specific keyboard command
    >>> bot.keyboard_command('Ctrl+S')          # Save
    >>> bot.keyboard_command('F7')              # Clear Block (Oracle Forms)
    >>> bot.keyboard_command('Alt+Tab')         # Switch window
    >>>
    >>> # FULL LIST OF SUPPORTED COMMANDS:
    >>> #
    >>> # === SYSTEM COMMANDS (Oracle Forms, etc.) ===
    >>> # F5, F6, F7, F8, F12 - Specific functions
    >>> # Ctrl+S, Ctrl+E, Ctrl+F11 - Commit, Edit, Enter Query
    >>> # Shift+F5, Shift+F6 - Duplicate Field/Record
    >>> # Ctrl+Up, Ctrl+Down - Delete/Insert Record
    >>> #
    >>> # === GENERAL COMMANDS ===
    >>> # Ctrl+C, Ctrl+V, Ctrl+X - Copy, Paste, Cut
    >>> # Ctrl+A, Ctrl+Z, Ctrl+Y - Select All, Undo, Redo
    >>> # Tab, Enter, Escape, Delete, Backspace
    >>> # Arrow Up/Down/Left/Right, Home, End
    >>> # Page Up, Page Down
    >>> #
    >>> # === BROWSER COMMANDS ===
    >>> # Ctrl+T, Ctrl+W, Ctrl+R - New Tab, Close Tab, Refresh
    >>> # Ctrl+Shift+T - Reopen Closed Tab
    >>> #
    >>> # === SYSTEM COMMANDS ===
    >>> # Alt+Tab, Alt+F4 - Switch/Close Window
    >>> # Windows+D, Windows+L - Desktop, Lock
    >>> #
    >>> # See the full list with: bot.get_available_keyboard_commands()

📍 CLICK ON SPECIFIC COORDINATES (NEW!):

    >>> # Direct click on coordinates (without searching for an image or text)
    >>> success = bot.click_coordinates(x=100, y=200,
    ...                                delay=1,
    ...                                mouse_button='left',
    ...                                backtrack=False)
    >>>
    >>> # Useful when you know exactly where to click

═══════════════════════════════════════════════════════════════════════════════

🔧 CONVENIENCE FUNCTIONS (Quick Use WITHOUT Instantiating the Class):

    >>> from visus.desktop import (find_text, click_text, find_image, click_image,
    ...                         find_relative_image, click_relative_image,     # NEW!
    ...                         click_coordinates, type_text_standalone,        # NEW!
    ...                         keyboard_command_standalone)                    # NEW!
    >>>
    >>> # Quick search (traditional standalone functions)
    >>> location = find_text("Login", region=(100, 100, 500, 300))
    >>> location = find_image("button.png", confidence=0.9)
    >>>
    >>> # Quick click (traditional standalone functions)
    >>> success = click_text("Confirmar", region=(200, 200, 600, 400))
    >>> success = click_image("button.png", backtrack=True)
    >>>
    >>> # NEW FEATURES - Standalone
    >>> # Relative image
    >>> location = find_relative_image("anchor.png", "target.png", max_distance=150)
    >>> success = click_relative_image("anchor.png", "target.png", backtrack=True)
    >>>
    >>> # Specific coordinates
    >>> success = click_coordinates(100, 200, delay=1, backtrack=True)
    >>>
    >>> # Typing and keyboard commands
    >>> success = type_text_standalone("Hello World!", backtrack=True)
    >>> success = keyboard_command_standalone("Ctrl+S", delay=1, backtrack=True)
    >>>
    >>> # List of available commands
    >>> commands = get_available_keyboard_commands()
    >>> print(f"Total commands: {len(commands)}")
    >>>
    >>> # NOTE: These functions create a temporary VisusBot instance

═══════════════════════════════════════════════════════════════════════════════

📋 SUPPORTED TASK TYPES (For use in lists):

    🔸 TYPE: 'text' (Search and click text via OCR)
       Fields: text, region, char_type, occurrence, confidence, backtrack, delay, sendtext

    🔸 TYPE: 'image' (Search and click an image)
       Fields: image, region, confidence, specific, backtrack, delay, mouse_button

    🔸 TYPE: 'relative_image' (NEW! - Search a target near an anchor)
       Fields: anchor_image, target_image, max_distance, confidence, target_region,
               specific, backtrack, delay, mouse_button

    🔸 TYPE: 'click' (NEW! - Click on specific coordinates)
       Fields: x, y, mouse_button, delay, backtrack

    🔸 TYPE: 'type_text' (NEW! - Direct text typing)
       Fields: text, interval, delay

    🔸 TYPE: 'keyboard_command' (NEW! - Keyboard command)
       Fields: command, delay

    🔸 TYPE: 'extract_text' (NEW! - Extract text from a specific region)
       Fields: region, filter_type, confidence_threshold, return_full_data, backtrack, delay

═══════════════════════════════════════════════════════════════════════════════

⚙️ ADVANCED CONFIGURATION (Customize the Behavior):

    >>> # FULL custom configuration:
    >>> config = {
    ...     "confidence_threshold": 80.0,        # Default OCR threshold (75-95)
    ...     "tesseract_lang": "por",             # Language: 'eng', 'por', 'spa'
    ...     "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    ...     "tessdata_path": r"C:\Program Files\Tesseract-OCR\tessdata",
    ...     "preprocessing_enabled": True,        # Improves OCR (recommended)
    ...     "retry_attempts": 5,                 # Default attempts
    ...     "default_delay": 1.5,               # Default delay between actions
    ...     "show_overlay": False,               # Disables the red overlay globally
    ...     "screenshot_delay": 0.1              # Delay for screen capture
    ... }
    >>>
    >>> bot = VisusBot(config=config)
    >>>
    >>> # CONFIGURATION PARAMETERS EXPLAINED:
    >>> # confidence_threshold: Minimum accuracy to recognize text
    >>> # tesseract_lang:       Language for OCR ('eng'=English, 'por'=Portuguese)
    >>> # tesseract_path:       Path to the Tesseract executable
    >>> # tessdata_path:        Folder with language data
    >>> # preprocessing_enabled: Improves the image before OCR
    >>> # retry_attempts:       Default attempts when not specified
    >>> # default_delay:        Default pause between actions
    >>> # show_overlay:         Controls displaying the red marker before clicks

═══════════════════════════════════════════════════════════════════════════════

🌟 ADVANCED FEATURES (DETAILED EXPLANATION):

✅ BACKTRACK: A smart retry system that, when a task fails,
              re-runs the previous task and tries again. It works both
              in task lists and between individual methods.

✅ OCCURRENCE: Lets you choose which text occurrence to click on screen.
               occurrence=1 = first occurrence found
               occurrence=2 = second occurrence found, etc.

✅ SPECIFIC: Controls where to search for images on screen.
             specific=True  = searches only in the defined region (faster)
             specific=False = searches the whole screen + allows scale variations
                             (ignores the region, more flexible)

✅ FILTER_TYPE/CHAR_TYPE: Filters characters during OCR.
                          'letters' = letters only (A-Z, a-z)
                          'numbers' = numbers only (0-9)
                          'both'    = letters and numbers

✅ SENDTEXT: Automatically types text after a successful click.
             Supports special commands: {ctrl}a, {del}, {tab}, {enter}
             Uses the clipboard for greater reliability.

✅ CONFIDENCE: Controls accuracy for OCR and image detection.
               0.7 = 70% (more permissive, may have false positives)
               0.9 = 90% (stricter, fewer false positives)
               0.95 = 95% (very strict, may miss valid elements)

✅ DELAY: Customizable pauses between actions in seconds.
          Useful for waiting for interfaces to load.
          delay=0.5 = half a second, delay=2 = two seconds

✅ SHOW_OVERLAY: Controls displaying the red marker before clicks.
                 show_overlay=True  = shows the marker (default, useful for debugging)
                 show_overlay=False = no marker (faster, for production)
                 show_overlay=None  = uses the bot's global configuration

✅ MOUSE_BUTTON: Full support for different click types.
                 • "left" - Simple left click (default)
                 • "right" - Right click (context menu)
                 • "double" or "double left" - Double left click (open/run)
                 • "move_to" - Just moves the mouse without clicking (hover)

                 Usage examples:
                 bot.click_image('file.png', mouse_button="double")  # Open file
                 bot.click_text('Menu', mouse_button="right")       # Context menu
                 bot.click_image('hover_btn.png', mouse_button="move_to")  # Hover only
                 bot.click_relative_image('anchor.png', 'target.png', mouse_button="left")

✅ REGION: Defines a specific screen area to search.
           region=(x, y, width, height)
           x, y = coordinates of the top-left corner
           width, height = width and height of the area
           Improves performance and avoids false positives.

✅ MAX_ATTEMPTS: Controls how many attempts to make before giving up.
                 max_attempts=1 = tries only once
                 max_attempts=3 = tries up to 3 times (default)
                 max_attempts=5 = tries up to 5 times (more persistent)

🎯 USAGE TIPS:
   • Use region whenever possible for better performance
   • confidence between 0.8-0.9 is ideal for most cases
   • specific=False searches the whole screen and allows scale variations
   • specific=True searches only in the defined region (faster)
   • backtrack=True is recommended for complex automations
   • filter_type='letters' improves OCR when you are searching only for text
   • an appropriate delay avoids issues with slow interfaces

🚨 TROUBLESHOOTING:
   • Element not found: Lower confidence or increase region
   • Inaccurate OCR: Use preprocessing_enabled=True in the configuration
   • Click in the wrong place: Check the region coordinates
   • Backtrack not working: Make sure backtrack=True on all methods

═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import time

from .core.capabilities import CapabilitiesMixin
from .core.image_map import ImageMap
from .core.image_processing import ImageProcessor, preprocess_image_for_ocr
from .core.keyboard_commands import KeyboardCommander  # NEW FEATURE
from .core.mouse_extra import drag, move_random, scroll, triple_click
from .core.ocr_engine import OCREngine, OCRResult, find_text_with_multiple_preprocessing
from .core.overlay import VisualOverlay, show_overlay
from .core.process import find_process, is_process_running, kill_process, launch
from .core.relative_image import RelativeImageDetector  # NEW FEATURE
from .core.screen import capture_screen, get_display_size, save_screenshot

# Import the main classes
from .core.task_executor import TaskExecutor, TaskResult
from .core.window import close_window, focus_window, maximize_window, minimize_window
from .exceptions import (
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
from .utils.clipboard import copy as copy_to_clipboard
from .utils.clipboard import get_clipboard, paste
from .utils.config import BotVisionConfig, get_default_config
from .utils.files import wait_for_file, wait_for_file_stable
from .utils.text_filters import clean_text, limpar_texto, matches_filter

# Library version
__version__ = "0.1.0"
__author__ = "Matheus Pereira"
__email__ = "matheuszwilkdev@gmail.com"
__license__ = "MIT"

# Default logging configuration
logger = logging.getLogger(__name__)


class VisusBot(CapabilitiesMixin):
    """
    Main class of Visus Desktop.

    Provides a high-level interface for GUI automation with advanced OCR.

    Examples:
        Basic usage:
        >>> bot = VisusBot()
        >>> bot.execute_tasks(tasks)

        With custom configuration:
        >>> config = {"confidence_threshold": 80.0}
        >>> bot = VisusBot(config=config)
        >>> bot.execute_tasks(tasks)
    """

    def __init__(self, config=None):
        """
        Initialize Visus Desktop.

        Args:
            config (dict or BotVisionConfig, optional): Custom settings
        """
        if isinstance(config, dict):
            self.config = BotVisionConfig(config)
        elif isinstance(config, BotVisionConfig):
            self.config = config
        else:
            self.config = get_default_config()

        self.executor = TaskExecutor(self.config)
        self.ocr_engine = OCREngine(self.config)
        self.image_processor = ImageProcessor()

        # Overlay settings - accessible via properties
        self._overlay_enabled = self.config.get("overlay_enabled", True)
        self._show_overlay = self.config.get("show_overlay", True)

        # Backtrack system for individual methods
        self.individual_task_history = []  # History of executed methods
        self.backtrack_enabled_globally = False  # Whether it is in backtrack mode
        self.current_task_index = -1  # Index of the current task
        self.max_backtrack_attempts = 2  # Maximum backtrack attempts per task
        self.task_session_active = False  # Whether it is in an individual task session

    def _add_to_task_history(self, method_name, args, kwargs):
        """Add a method to the individual task history."""
        task_info = {
            "method": method_name,
            "args": args,
            "kwargs": kwargs,
            "index": len(self.individual_task_history),
            "success": None,
            "backtrack_attempts": 0,
            "timestamp": time.time(),
        }
        self.individual_task_history.append(task_info)
        self.current_task_index = len(self.individual_task_history) - 1
        return self.current_task_index

    def start_task_session(self):
        """Start an individual task session for backtracking."""
        self.task_session_active = True
        self.individual_task_history = []
        self.current_task_index = -1
        logger.info(
            "🚀 Individual task session started - backtrack enabled between methods"
        )

    def end_task_session(self):
        """End an individual task session."""
        self.task_session_active = False
        successful_tasks = sum(
            1 for task in self.individual_task_history if task.get("success", False)
        )
        total_tasks = len(self.individual_task_history)
        logger.info(
            f"🏁 Session ended: {successful_tasks}/{total_tasks} successful tasks"
        )
        return successful_tasks, total_tasks

    # Overlay control properties
    @property
    def overlay_enabled(self):
        """Control whether the overlay system is active."""
        return self._overlay_enabled

    @overlay_enabled.setter
    def overlay_enabled(self, value):
        """Set whether the overlay system is active."""
        self._overlay_enabled = bool(value)
        # Also update the configuration
        self.config.config["overlay_enabled"] = self._overlay_enabled

    @property
    def show_overlay(self):
        """Control whether the visual overlay is displayed before clicks."""
        return self._show_overlay

    @show_overlay.setter
    def show_overlay(self, value):
        """Set whether the visual overlay is displayed before clicks."""
        self._show_overlay = bool(value)
        # Also update the configuration
        self.config.config["show_overlay"] = self._show_overlay

    def configure_overlay(self, enabled=None, color=None, duration=None, width=None):
        """
        Conveniently configure the overlay parameters.

        Args:
            enabled (bool, optional): Whether the overlay is enabled
            color (str, optional): Overlay color - options: 'red', 'blue', 'green', 'yellow',
                                   'purple', 'orange', 'cyan', 'magenta', 'white', 'black'
            duration (int, optional): Duration in milliseconds (500-5000 recommended)
            width (int, optional): Overlay line width (1-10 recommended)

        Examples:
            >>> bot = VisusBot()
            >>> bot.configure_overlay(enabled=True, color="blue", duration=2000)
            >>> bot.configure_overlay(color="green", width=6)

        Raises:
            ValueError: If an invalid color is provided
        """
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

        if enabled is not None:
            self.overlay_enabled = enabled
            self.show_overlay = enabled

        if color is not None:
            if color.lower() not in [c.lower() for c in valid_colors]:
                raise ValueError(
                    f"Invalid color '{color}'. Available colors: {', '.join(valid_colors)}"
                )
            self.config.config["overlay_color"] = color.lower()

        if duration is not None:
            if not isinstance(duration, (int, float)) or duration <= 0:
                raise ValueError(
                    f"Duration must be a positive number, received: {duration}"
                )
            if duration > 10000:
                logger.warning(
                    f"Duration too high ({duration}ms). Consider using less than 5000ms."
                )
            self.config.config["overlay_duration"] = int(duration)

        if width is not None:
            if not isinstance(width, (int, float)) or width <= 0:
                raise ValueError(f"Width must be a positive number, received: {width}")
            if width > 15:
                logger.warning(
                    f"Width too high ({width}). Consider using less than 10."
                )
            self.config.config["overlay_width"] = int(width)

    def get_overlay_config(self):
        """
        Return the current overlay configuration.

        Returns:
            dict: Overlay settings
        """
        return {
            "enabled": self.overlay_enabled,
            "show_overlay": self.show_overlay,
            "color": self.config.config.get("overlay_color", "red"),
            "duration": self.config.config.get("overlay_duration", 1000),
            "width": self.config.config.get("overlay_width", 4),
        }

    @staticmethod
    def get_available_overlay_colors():
        """
        Return the list of available overlay colors.

        Returns:
            list: List of available colors

        Examples:
            >>> colors = VisusBot.get_available_overlay_colors()
            >>> print("Available colors:", colors)
        """
        return [
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

    def test_overlay_colors(self, duration=1500):
        """
        Test all available overlay colors.

        Args:
            duration (int): Duration of each color in milliseconds

        Examples:
            >>> bot = VisusBot()
            >>> bot.test_overlay_colors()  # Shows each color for 1.5 seconds
        """
        from .core.overlay import VisualOverlay

        colors = self.get_available_overlay_colors()
        test_region = (400, 300, 200, 100)  # Center of the screen

        print("🎨 Testing overlay colors...")
        print("📍 Look at the center of the screen!")

        for i, color in enumerate(colors, 1):
            print(f"   {i}. Color: {color.upper()}")
            overlay = VisualOverlay(color=color, width=6, duration=duration)
            overlay.show(test_region, blocking=True)

        print("✅ Color test complete!")

    def _execute_with_individual_backtrack(
        self, method_name, method_func, *args, **kwargs
    ):
        """
        Execute an individual method with backtrack capability.

        Args:
            method_name (str): Name of the method ('click_image', 'click_text', etc.)
            method_func (callable): The method function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            bool: Result of the execution
        """
        backtrack = kwargs.get("backtrack", False)

        # If backtrack is not enabled or there is no active session, execute normally
        if not backtrack or not self.task_session_active:
            if backtrack and not self.task_session_active:
                # Auto-start a session if backtrack=True but no session is active
                self.start_task_session()

            # Remove backtrack from kwargs to avoid infinite recursion
            execution_kwargs = kwargs.copy()
            execution_kwargs.pop("backtrack", None)
            return method_func(*args, **execution_kwargs)

        # Add to the history
        task_index = self._add_to_task_history(method_name, args, kwargs)

        logger.info(
            f"🎯 Running {method_name} (task {task_index + 1}) with backtrack enabled"
        )

        # Remove backtrack from kwargs to avoid infinite recursion
        execution_kwargs = kwargs.copy()
        execution_kwargs.pop("backtrack", None)

        # Try to execute the method
        success = method_func(*args, **execution_kwargs)

        # Update the result in the history
        self.individual_task_history[task_index]["success"] = success

        if success:
            logger.info(
                f"✓ {method_name} (task {task_index + 1}) executed successfully!"
            )
            return True
        else:
            # Failed - check whether a backtrack is possible
            if task_index > 0:  # There are previous tasks
                current_task = self.individual_task_history[task_index]

                if current_task["backtrack_attempts"] < self.max_backtrack_attempts:
                    current_task["backtrack_attempts"] += 1

                    # Execute the previous task
                    prev_task = self.individual_task_history[task_index - 1]
                    logger.info(
                        f"🔄 BACKTRACK: {method_name} (task {task_index + 1}) failed. "
                        f"Re-running the previous task ({prev_task['method']}) and trying again..."
                    )

                    # Re-run the previous task
                    prev_method_name = prev_task["method"]
                    prev_method_func = getattr(self, f"_{prev_method_name}_internal")
                    prev_kwargs = prev_task["kwargs"].copy()
                    prev_kwargs.pop(
                        "backtrack", None
                    )  # Remove backtrack to avoid recursion

                    prev_success = prev_method_func(*prev_task["args"], **prev_kwargs)
                    self.individual_task_history[task_index - 1]["success"] = (
                        prev_success
                    )

                    if prev_success:
                        logger.info(
                            f"✓ Previous task ({prev_task['method']}) re-run successfully"
                        )

                        # Wait a bit and try the current task again
                        time.sleep(0.5)
                        logger.info(
                            f"🔄 Retrying {method_name} (task {task_index + 1}) after backtrack..."
                        )

                        retry_success = method_func(*args, **execution_kwargs)
                        self.individual_task_history[task_index]["success"] = (
                            retry_success
                        )

                        if retry_success:
                            logger.info(
                                f"✓ {method_name} (task {task_index + 1}) succeeded after backtrack!"
                            )
                            return True
                        else:
                            logger.warning(
                                f"✗ {method_name} (task {task_index + 1}) still failed after backtrack"
                            )
                    else:
                        logger.warning(
                            f"✗ Previous task ({prev_task['method']}) also failed on re-run"
                        )
                else:
                    logger.warning(
                        f"✗ {method_name} (task {task_index + 1}) failed after {self.max_backtrack_attempts} backtrack attempts"
                    )
            else:
                logger.warning(
                    f"✗ {method_name} (task {task_index + 1}) failed but it is the first task (no backtrack possible)"
                )

            return False

    def execute_tasks(self, tasks):
        """
        Execute a list of tasks sequentially.

        Args:
            tasks (list): List of dictionaries with task settings

        Returns:
            list: List of TaskResult objects with the result of each task

        Examples:
            >>> # Basic tasks
            >>> tasks = [
            ...     {'text': 'Login', 'region': (100, 100, 500, 300)},
            ...     {'image': 'button.png', 'delay': 2}
            ... ]
            >>>
            >>> # Advanced tasks with ALL the new features:
            >>> advanced_tasks = [
            ...     # 1. OCR text search
            ...     {
            ...         'text': 'Usuário',
            ...         'region': (100, 100, 500, 300),
            ...         'char_type': 'letters',
            ...         'confidence': 0.8,
            ...         'occurrence': 1,
            ...         'backtrack': True,
            ...         'delay': 1,
            ...         'sendtext': 'admin{tab}password{enter}'
            ...     },
            ...     # 2. Relative image search (NEW!)
            ...     {
            ...         'type': 'relative_image',
            ...         'anchor_image': 'warning_icon.png',
            ...         'target_image': 'ok_button.png',
            ...         'max_distance': 200,
            ...         'confidence': 0.9,
            ...         'target_region': (0, 0, 800, 600),
            ...         'specific': True,
            ...         'backtrack': True,
            ...         'delay': 1
            ...     },
            ...     # 3. Click on specific coordinates (NEW!)
            ...     {
            ...         'type': 'click',
            ...         'x': 100,
            ...         'y': 200,
            ...         'mouse_button': 'right',
            ...         'delay': 0.5,
            ...         'backtrack': False
            ...     },
            ...     # 4. Text typing (NEW!)
            ...     {
            ...         'type': 'type_text',
            ...         'text': 'Hello World!',
            ...         'interval': 0.05,
            ...         'delay': 1
            ...     },
            ...     # 5. Keyboard command (NEW!)
            ...     {
            ...         'type': 'keyboard_command',
            ...         'command': 'Ctrl+S',
            ...         'delay': 1
            ...     }
            ... ]
            >>>
            >>> results = bot.execute_tasks(advanced_tasks)
        """
        return self.executor.execute_tasks(tasks)

    def find_text(
        self,
        text,
        region=None,
        filter_type="both",
        confidence_threshold=75.0,
        occurrence=1,
        max_attempts=3,
        backtrack=False,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """
        Find text on screen using advanced OCR with all features.

        Args:
            text (str): Text to find
            region (tuple, optional): (x, y, width, height) of the search region
            filter_type (str): Filter type ("numbers", "letters", "both") - equivalent to char_type
            confidence_threshold (float): Minimum confidence threshold
            occurrence (int): Which occurrence to look for (1 = first, 2 = second, etc.)
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to try multiple times with adjustments
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            tuple: Coordinates (x, y, width, height) where the text was found, or None

        Examples:
            >>> location = bot.find_text("Confirmar", region=(0, 0, 800, 600), backtrack=True)
            >>> if location:
            ...     print(f"Text found at: {location}")
        """
        import time

        # If there are wait parameters, build a task and use the executor with wait
        if wait_until_found or wait_until_disappears:
            temp_task = {
                "text": text,
                "region": region,
                "char_type": filter_type,
                "confidence_threshold": confidence_threshold,
                "occurrence": occurrence,
                "wait_until_found": wait_until_found,
                "wait_until_disappears": wait_until_disappears,
                "wait_timeout": wait_timeout,
            }

            # Use the executor's wait-aware method
            if wait_until_found:
                return self.executor._find_text_with_wait(temp_task, 0)
            elif wait_until_disappears:
                return self.executor._find_text_with_wait(temp_task, 0)

        # Original behavior without wait
        attempts = 0
        while attempts < max_attempts:
            if region is None:
                # If no region was specified, capture the whole screen
                import pyautogui

                screen = pyautogui.screenshot()
                region = (0, 0, screen.width, screen.height)
                region_img = screen
            else:
                region_img = self.executor._capture_region(region)

            found_boxes, confidence_scores, _ = self.ocr_engine.find_text(
                region_img, text, filter_type, confidence_threshold
            )

            if found_boxes and len(found_boxes) >= occurrence:
                # Return the specified occurrence (occurrence-1 since the list is 0-indexed)
                target_index = occurrence - 1
                if target_index < len(found_boxes):
                    best_box_relative = found_boxes[target_index]

                    # Convert to absolute coordinates if needed
                    if region != (0, 0, region_img.width, region_img.height):
                        return (
                            region[0] + best_box_relative[0],
                            region[1] + best_box_relative[1],
                            best_box_relative[2],
                            best_box_relative[3],
                        )
                    else:
                        return best_box_relative

            # If nothing was found and backtrack is enabled, try again
            if backtrack and attempts < max_attempts - 1:
                attempts += 1
                logger.info(f"Attempt {attempts}/{max_attempts} to find '{text}'")

                # Adjust parameters for the next attempt
                confidence_threshold = max(60.0, confidence_threshold - 5.0)
                time.sleep(0.5)
            else:
                break

        return None

    def click_text(
        self,
        text,
        region=None,
        filter_type="both",
        delay=0,
        mouse_button="left",
        occurrence=1,
        backtrack=False,
        max_attempts=3,
        sendtext=None,
        confidence_threshold=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """
        Find and click on text with advanced features.

        Args:
            text (str): Text to click on
            region (tuple, optional): Search region (x, y, width, height)
            filter_type (str): Filter type ("numbers", "letters", "both")
            delay (float): Delay after the click in seconds
            mouse_button (str): Mouse click type:
                • "left" - Simple left click (default)
                • "right" - Right click
                • "double" or "double left" - Double left click
                • "move_to" - Just moves the mouse without clicking
            occurrence (int): Which occurrence to click (1=first)
            backtrack (bool): Whether to use real backtracking between individual methods
            max_attempts (int): Maximum number of attempts
            sendtext (str, optional): Text to type after the click
            confidence_threshold (float, optional): Custom confidence threshold
            show_overlay (bool, optional): Whether to show the red overlay before the click
                                         If None, uses the global configuration
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            bool: True if found and clicked, False otherwise
        """
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay

        # If backtrack is True, use the individual backtrack system
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_text",
                self._click_text_internal,
                text,
                region,
                filter_type,
                delay,
                mouse_button,
                occurrence,
                max_attempts,
                sendtext,
                confidence_threshold,
                show_overlay,
                wait_until_found,
                wait_until_disappears,
                wait_timeout,
                backtrack=backtrack,
            )

        # Original behavior without backtrack
        return self._click_text_internal(
            text,
            region,
            filter_type,
            delay,
            mouse_button,
            occurrence,
            max_attempts,
            sendtext,
            confidence_threshold,
            show_overlay,
            wait_until_found,
            wait_until_disappears,
            wait_timeout,
        )

    def _click_text_internal(
        self,
        text,
        region=None,
        filter_type="both",
        delay=0,
        mouse_button="left",
        occurrence=1,
        max_attempts=3,
        sendtext=None,
        confidence_threshold=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """Internal version of click_text without backtrack (for use by the backtrack system)."""
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay
        attempts = 0
        while attempts < max_attempts:
            attempts += 1

            try:
                if attempts > 1:
                    logger.info(
                        f"Attempt {attempts}/{max_attempts} to click on '{text}'"
                    )

                # Use the custom threshold if provided, otherwise use the one from the configuration
                threshold = confidence_threshold or self.config.confidence_threshold

                location = self.find_text(
                    text,
                    region,
                    filter_type,
                    threshold,
                    occurrence,
                    max_attempts=1,
                    backtrack=False,
                    wait_until_found=wait_until_found,
                    wait_until_disappears=wait_until_disappears,
                    wait_timeout=wait_timeout,
                )

                if location:
                    # Build a temporary task to use the executor
                    temp_task = {
                        "mouse_button": mouse_button,
                        "delay": delay,
                        "sendtext": sendtext,
                        "show_overlay": show_overlay,
                    }

                    try:
                        self.executor._perform_action(temp_task, location)
                        return True
                    except Exception as e:
                        logger.error(f"Error clicking on text: {e}")
                        if attempts >= max_attempts:
                            return False
                        time.sleep(0.5)
                else:
                    logger.warning(f"Text '{text}' not found on attempt {attempts}")
                    if attempts < max_attempts:
                        time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error on attempt {attempts} for '{text}': {e}")
                if attempts >= max_attempts:
                    return False
                time.sleep(0.5)

        return False

    def _click_image_internal(
        self,
        image_path,
        region=None,
        confidence=0.9,
        delay=0,
        mouse_button="left",
        max_attempts=3,
        specific=True,
        sendtext=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """Internal version of click_image without backtrack (for use by the backtrack system)."""
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay

        # For click_image, wait_until_disappears must wait AFTER the click, not before
        # So we pass only wait_until_found to find_image
        location = self.find_image(
            image_path,
            region,
            confidence,
            max_attempts,
            False,
            specific,
            wait_until_found,
            False,
            wait_timeout,
        )  # backtrack=False for find_image

        if location:
            # Build a temporary task to use the executor
            temp_task = {
                "image": image_path,
                "region": region,
                "confidence": confidence,
                "specific": specific,
                "mouse_button": mouse_button,
                "delay": delay,
                "sendtext": sendtext,
                "show_overlay": show_overlay,
                "wait_until_disappears": wait_until_disappears,
                "wait_timeout": wait_timeout,
            }

            try:
                self.executor._perform_action(temp_task, location)
                return True
            except Exception as e:
                logger.error(f"Error clicking on image: {e}")
                return False

        return False

    def extract_text_from_region(
        self,
        region=None,
        filter_type="both",
        confidence_threshold=50.0,
        return_full_data=False,
        max_attempts=3,
        backtrack=False,
    ):
        """
        Extract all text found in a specific region of the screen.

        Args:
            region (tuple, optional): (x, y, width, height) of the region to extract text from.
                                    If None, extracts from the whole screen
            filter_type (str): Filter type for the text:
                • "numbers" - Numbers only
                • "letters" - Letters only
                • "both" - Numbers and letters (default)
            confidence_threshold (float): Minimum confidence threshold (0-100)
            return_full_data (bool): If True, returns full data with coordinates and confidence
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to try multiple times with adjustments

        Returns:
            If return_full_data=False:
                list: List of strings with all the text found
            If return_full_data=True:
                list: List of dictionaries with:
                    - 'text': Text found
                    - 'confidence': Confidence level (0-100)
                    - 'box': Coordinates (x, y, width, height)
                    - 'absolute_box': Absolute coordinates on screen

        Examples:
            Simple extraction:
            >>> texts = bot.extract_text_from_region(region=(100, 100, 400, 300))
            >>> print("Texts found:", texts)

            Extraction with full data:
            >>> data = bot.extract_text_from_region(
            ...     region=(100, 100, 400, 300),
            ...     return_full_data=True,
            ...     confidence_threshold=70.0
            ... )
            >>> for item in data:
            ...     print(f"'{item['text']}' - Confidence: {item['confidence']:.1f}% - Position: {item['absolute_box']}")

            Numbers only:
            >>> numbers = bot.extract_text_from_region(
            ...     region=(50, 50, 200, 100),
            ...     filter_type="numbers"
            ... )
        """
        import time

        attempts = 0
        while attempts < max_attempts:
            try:
                if region is None:
                    # If no region was specified, capture the whole screen
                    import pyautogui

                    screen = pyautogui.screenshot()
                    region = (0, 0, screen.width, screen.height)
                    region_img = screen
                else:
                    region_img = self.executor._capture_region(region)

                # Use the OCR engine's extract_all_text method
                ocr_results = self.ocr_engine.extract_all_text(region_img, filter_type)

                # Filter by confidence
                filtered_results = [
                    result
                    for result in ocr_results
                    if result.confidence >= confidence_threshold
                ]

                if not filtered_results and backtrack and attempts < max_attempts - 1:
                    # If nothing was found and backtrack is enabled, adjust parameters
                    attempts += 1
                    logger.info(
                        f"Attempt {attempts}/{max_attempts} for text extraction"
                    )
                    confidence_threshold = max(30.0, confidence_threshold - 10.0)
                    time.sleep(0.5)
                    continue

                if return_full_data:
                    # Return full data with absolute coordinates
                    full_data = []
                    for result in filtered_results:
                        absolute_box = (
                            (
                                region[0] + result.box[0],
                                region[1] + result.box[1],
                                result.box[2],
                                result.box[3],
                            )
                            if region != (0, 0, region_img.width, region_img.height)
                            else result.box
                        )

                        full_data.append(
                            {
                                "text": result.text,
                                "confidence": result.confidence,
                                "box": result.box,  # Coordinates relative to the region
                                "absolute_box": absolute_box,  # Absolute coordinates on screen
                            }
                        )

                    return full_data
                else:
                    # Return only the texts
                    return [result.text for result in filtered_results]

            except Exception as e:
                logger.error(f"Error on attempt {attempts} for text extraction: {e}")
                if backtrack and attempts < max_attempts - 1:
                    attempts += 1
                    time.sleep(0.5)
                else:
                    break

        # If it got here, it failed
        return [] if not return_full_data else []

    def get_last_extracted_text(self):
        """
        Get the last extracted text when used in task lists.

        Returns:
            list: Last text extraction result, or None if no extraction has been done

        Examples:
            >>> tasks = [
            ...     {
            ...         'type': 'extract_text',
            ...         'region': (100, 100, 400, 300),
            ...         'filter_type': 'both'
            ...     }
            ... ]
            >>> results = bot.execute_tasks(tasks)
            >>> extracted_texts = bot.get_last_extracted_text()
            >>> print("Texts found:", extracted_texts)
        """
        return getattr(self.executor, "last_extracted_text", None)

    def find_image(
        self,
        image_path,
        region=None,
        confidence=0.9,
        max_attempts=3,
        backtrack=False,
        specific=True,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
        scales=None,
    ):
        """
        Find an image on screen with all the advanced features.

        Args:
            image_path (str): Path to the image
            region (tuple, optional): Search region
            confidence (float): Confidence level
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to try multiple times with adjustments
            specific (bool): If True, searches in the region; if False, searches the whole screen + scale variations
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)
            scales (list, optional): List of scales to try (e.g.: [1.0, 0.95, 1.05])

        Returns:
            tuple: Coordinates of the image or None
        """
        import time

        image_path = self.image_map.resolve(image_path)

        if scales is None:
            scales = [1.0, 0.95, 1.05] if not specific else [1.0]

        # If there are wait parameters, build a task and use the executor with wait
        if wait_until_found or wait_until_disappears:
            temp_task = {
                "image": image_path,
                "region": region,
                "confidence": confidence,
                "specific": specific,
                "wait_until_found": wait_until_found,
                "wait_until_disappears": wait_until_disappears,
                "wait_timeout": wait_timeout,
            }

            # Use the executor's wait-aware method
            return self.executor._find_image_with_wait(temp_task, 0)

        # Original behavior without wait
        attempts = 0
        while attempts < max_attempts:
            try:
                # Try with different scales if not specific
                for scale in scales:
                    try:
                        if scale != 1.0 and not specific:
                            # Resize the reference image
                            import os

                            from PIL import Image

                            ref_img = Image.open(image_path)
                            new_width = int(ref_img.width * scale)
                            new_height = int(ref_img.height * scale)
                            scaled_img = ref_img.resize((new_width, new_height))

                            # Save temporarily
                            temp_path = f"temp_scaled_{scale}_{attempts}.png"
                            scaled_img.save(temp_path)

                            # NEW LOGIC: specific controls where to search
                            if specific and region:
                                # If specific AND there is a region, search in the region
                                location = self.executor._locate_image_with_retry(
                                    temp_path, region, confidence
                                )
                            else:
                                # If not specific OR no region, search the whole screen
                                location = self.executor._locate_image_with_retry(
                                    temp_path, None, confidence
                                )

                            # Remove the temporary file
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        else:
                            # NEW LOGIC: specific controls where to search
                            if specific and region:
                                # If specific AND there is a region, search in the region
                                logger.info(
                                    f"Searching for image in region {region} (specific=True)"
                                )
                                location = self.executor._locate_image_with_retry(
                                    image_path, region, confidence
                                )
                            else:
                                # If not specific OR no region, search the whole screen
                                logger.info(
                                    "Searching for image across the whole screen (specific=False)"
                                )
                                location = self.executor._locate_image_with_retry(
                                    image_path, None, confidence
                                )

                        if location:
                            return location

                    except Exception as e:
                        logger.debug(f"Error searching for image at scale {scale}: {e}")
                        continue
                # If nothing was found and backtrack is enabled, adjust parameters
                if backtrack and attempts < max_attempts - 1:
                    attempts += 1
                    logger.info(f"Attempt {attempts}/{max_attempts} to find the image")

                    # Gradually lower the confidence
                    confidence = max(0.7, confidence - 0.05)
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                logger.error(f"Error searching for image: {e}")
                if not backtrack:
                    break

        return None

    def click_image(
        self,
        image_path,
        region=None,
        confidence=0.9,
        delay=0,
        mouse_button="left",
        max_attempts=3,
        backtrack=False,
        specific=True,
        sendtext=None,
        show_overlay=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """
        Find and click on an image with all the advanced features.

        Args:
            image_path (str): Path to the image
            region (tuple, optional): Search region (x, y, width, height)
            confidence (float): Confidence level (0.0-1.0)
            delay (float): Delay after the click in seconds
            mouse_button (str): Mouse click type:
                • "left" - Simple left click (default)
                • "right" - Right click
                • "double" or "double left" - Double left click
                • "move_to" - Just moves the mouse without clicking
            max_attempts (int): Maximum number of attempts if backtrack=True
            backtrack (bool): Whether to use real backtracking between individual methods
            specific (bool): If True, exact search; if False, allows variations
            sendtext (str, optional): Text to type after the click
            show_overlay (bool, optional): Whether to show the red overlay before the click
                                         If None, uses the global configuration
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            bool: True if found and clicked, False otherwise
        """
        # Use the global configuration if not specified
        if show_overlay is None:
            show_overlay = self.config.show_overlay

        image_path = self.image_map.resolve(image_path)

        # If backtrack is True, use the individual backtrack system
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_image",
                self._click_image_internal,
                image_path,
                region,
                confidence,
                delay,
                mouse_button,
                max_attempts,
                specific,
                sendtext,
                show_overlay,
                wait_until_found,
                wait_until_disappears,
                wait_timeout,
                backtrack=backtrack,
            )

        # Original behavior without backtrack
        return self._click_image_internal(
            image_path,
            region,
            confidence,
            delay,
            mouse_button,
            max_attempts,
            specific,
            sendtext,
            show_overlay,
            wait_until_found,
            wait_until_disappears,
            wait_timeout,
        )

    def click_at(self, location, mouse_button="left", delay=0, show_overlay=None):
        """
        Click on specific screen coordinates.

        Args:
            location (tuple): (x, y, width, height) of the location
            mouse_button (str): Mouse button ("left", "right", "double", "move_to")
            delay (float): Delay after the click
            show_overlay (bool, optional): Whether to show the red overlay before the click
                                         If None, uses the global configuration

        Returns:
            bool: True if clicked successfully

        Examples:
            >>> bot.click_at((100, 200, 50, 30), mouse_button='left', delay=1)
        """
        try:
            # Use the global configuration if not specified
            if show_overlay is None:
                show_overlay = self.config.show_overlay

            # Build a temporary task to use the executor
            temp_task = {
                "mouse_button": mouse_button,
                "delay": delay,
                "show_overlay": show_overlay,
            }

            self.executor._perform_action(temp_task, location)
            return True

        except Exception as e:
            logger.error(f"Error clicking on coordinates {location}: {e}")
            return False

    def find_relative_image(
        self,
        anchor_image,
        target_image,
        max_distance=200,
        confidence=0.9,
        target_region=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """
        Find a target image near an anchor image.

        Args:
            anchor_image (str): Path to the anchor image (unique on screen)
            target_image (str): Path to the target image (there may be multiple)
            max_distance (int): Maximum distance in pixels from the anchor to the target
            confidence (float): Confidence level for detection (0.0-1.0)
            target_region (tuple, optional): Specific region to search for the target (x, y, width, height)
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            tuple: Location of the target image closest to the anchor, or None

        Examples:
            >>> location = bot.find_relative_image('anchor.png', 'target.png', max_distance=150)
            >>> if location:
            ...     print(f"Target found near the anchor: {location}")
        """
        # If there are wait parameters, build a task and use the executor with wait
        if wait_until_found or wait_until_disappears:
            # Build a search function for the wait manager
            def search_relative():
                try:
                    return self.executor.relative_detector.locate_relative_image(
                        anchor_image,
                        target_image,
                        confidence,
                        max_distance,
                        target_region,
                    )
                except Exception:
                    return None

            if wait_until_found:
                return self.executor.wait_manager.wait_until_found(
                    search_relative,
                    timeout=wait_timeout or self.config.get("wait_timeout", 30),
                    description=f"relative image '{target_image}' near '{anchor_image}'",
                )
            elif wait_until_disappears:
                # First find the image
                result = search_relative()
                if not result:
                    return None

                # Then wait for it to disappear
                disappeared = self.executor.wait_manager.wait_until_disappears(
                    search_relative,
                    timeout=wait_timeout or self.config.get("wait_timeout", 30),
                    description=f"relative image '{target_image}' near '{anchor_image}'",
                )
                return result if disappeared else None

        # Original behavior without wait
        try:
            return self.executor.relative_detector.locate_relative_image(
                anchor_image, target_image, confidence, max_distance, target_region
            )
        except Exception as e:
            logger.error(f"Error during relative image search: {e}")
            return None

    def click_relative_image(
        self,
        anchor_image,
        target_image,
        max_distance=200,
        confidence=0.9,
        target_region=None,
        delay=0,
        mouse_button="left",
        backtrack=False,
        max_attempts=3,
        sendtext=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """
        Click on a target image near an anchor image.

        Args:
            anchor_image (str): Path to the anchor image
            target_image (str): Path to the target image
            max_distance (int): Maximum distance in pixels
            confidence (float): Confidence level (0.0-1.0)
            target_region (tuple, optional): Region to search for the target (x, y, width, height)
            delay (float): Delay after the click in seconds
            mouse_button (str): Mouse click type:
                • "left" - Simple left click (default)
                • "right" - Right click
                • "double" or "double left" - Double left click
                • "move_to" - Just moves the mouse without clicking
            backtrack (bool): Whether to use backtracking on failure
            max_attempts (int): Maximum number of attempts
            sendtext (str, optional): Text to type after the click
            wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
            wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
            wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

        Returns:
            bool: True if found and clicked, False otherwise

        Examples:
            >>> # Simple left click (default)
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  max_distance=150, mouse_button="left")

            >>> # Right click
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  mouse_button="right", backtrack=True)

            >>> # Double left click
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  mouse_button="double", delay=1.0)

            >>> # Just move the mouse to the position (without clicking)
            >>> success = bot.click_relative_image('anchor.png', 'target.png',
            ...                                  mouse_button="move_to", delay=0.5)

            >>> # Click and type text afterwards
            >>> success = bot.click_relative_image('anchor.png', 'input.png',
            ...                                  sendtext="Hello World", delay=1.0)
        """
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_relative_image",
                self._click_relative_image_internal,
                anchor_image,
                target_image,
                max_distance,
                confidence,
                target_region,
                delay,
                mouse_button,
                max_attempts,
                sendtext,
                wait_until_found,
                wait_until_disappears,
                wait_timeout,
                backtrack=backtrack,
            )

        return self._click_relative_image_internal(
            anchor_image,
            target_image,
            max_distance,
            confidence,
            target_region,
            delay,
            mouse_button,
            max_attempts,
            sendtext,
            wait_until_found,
            wait_until_disappears,
            wait_timeout,
        )

    def _click_relative_image_internal(
        self,
        anchor_image,
        target_image,
        max_distance,
        confidence,
        target_region,
        delay,
        mouse_button,
        max_attempts,
        sendtext=None,
        wait_until_found=False,
        wait_until_disappears=False,
        wait_timeout=None,
    ):
        """Internal implementation of the relative image click."""
        for attempt in range(max_attempts):
            # For click_relative_image, wait_until_disappears must wait AFTER the click, not before
            # So we pass only wait_until_found to find_relative_image
            location = self.find_relative_image(
                anchor_image,
                target_image,
                max_distance,
                confidence,
                target_region,
                wait_until_found,
                False,
                wait_timeout,
            )  # wait_until_disappears=False
            if location:
                temp_task = {
                    "mouse_button": mouse_button,
                    "delay": delay,
                    "sendtext": sendtext,
                    "wait_until_disappears": wait_until_disappears,
                    "wait_timeout": wait_timeout,
                    "image": target_image,  # So wait_until_disappears knows which image to wait for
                    "_wait_after_click": wait_until_disappears,
                    "_wait_timeout": wait_timeout,
                    "_image_path": target_image,
                }
                self.executor._perform_action(temp_task, location)
                return True

            if attempt < max_attempts - 1:
                time.sleep(0.5)

        return False

    def click_coordinates(self, x, y, delay=0, mouse_button="left", backtrack=False):
        """
        Click on specific screen coordinates.

        Args:
            x (int): X coordinate
            y (int): Y coordinate
            delay (float): Delay after the click
            mouse_button (str): Mouse button ("left", "right", "double", "move_to")
            backtrack (bool): Whether to use backtracking

        Returns:
            bool: True if clicked successfully

        Examples:
            >>> success = bot.click_coordinates(100, 200, delay=1, backtrack=True)
        """
        if backtrack:
            return self._execute_with_individual_backtrack(
                "click_coordinates",
                self._click_coordinates_internal,
                x,
                y,
                delay,
                mouse_button,
                backtrack=backtrack,
            )

        return self._click_coordinates_internal(x, y, delay, mouse_button)

    def _click_coordinates_internal(self, x, y, delay, mouse_button):
        """Internal implementation of the coordinate click."""
        try:
            location = (x, y, 1, 1)  # Create a small region
            temp_task = {"mouse_button": mouse_button, "delay": delay}
            self.executor._perform_action(temp_task, location)
            return True
        except Exception as e:
            logger.error(f"Error clicking on coordinates ({x}, {y}): {e}")
            return False

    def type_text(self, text, interval=0.05, delay=0, backtrack=False):
        """
        Type text with an interval between characters.

        Args:
            text (str): Text to type
            interval (float): Interval between characters in seconds
            delay (float): Delay after typing
            backtrack (bool): Whether to use backtracking

        Returns:
            bool: True if typed successfully

        Examples:
            >>> success = bot.type_text('Hello World!', interval=0.05, backtrack=True)
            >>> success = bot.type_text('{ctrl}a{del}New text', backtrack=True)
        """
        if backtrack:
            return self._execute_with_individual_backtrack(
                "type_text",
                self._type_text_internal,
                text,
                interval,
                delay,
                backtrack=backtrack,
            )

        return self._type_text_internal(text, interval, delay)

    def _type_text_internal(self, text, interval, delay):
        """Internal implementation of text typing."""
        try:
            # Check whether there are special commands
            if any(
                cmd in text.lower() for cmd in ["{ctrl}", "{del}", "{tab}", "{enter}"]
            ):
                self.executor.keyboard_commander.process_sendtext_command(text)
            else:
                self.executor.keyboard_commander.type_text(text, interval)

            if delay > 0:
                time.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"Error typing text '{text}': {e}")
            return False

    def keyboard_command(self, command, delay=0, backtrack=False):
        """
        Run a keyboard command.

        Args:
            command (str): Name of the command to run
            delay (float): Delay after the command
            backtrack (bool): Whether to use backtracking

        Returns:
            bool: True if the command ran successfully

        Examples:
            >>> success = bot.keyboard_command('Ctrl+S', delay=1, backtrack=True)
            >>> success = bot.keyboard_command('F7', backtrack=True)  # Oracle Forms
        """
        if backtrack:
            return self._execute_with_individual_backtrack(
                "keyboard_command",
                self._keyboard_command_internal,
                command,
                delay,
                backtrack=backtrack,
            )

        return self._keyboard_command_internal(command, delay)

    def _keyboard_command_internal(self, command, delay):
        """Internal implementation of the keyboard command."""
        try:
            success = self.executor.keyboard_commander.execute_command(command)
            if delay > 0:
                time.sleep(delay)
            return success
        except Exception as e:
            logger.error(f"Error running command '{command}': {e}")
            return False

    def get_available_keyboard_commands(self):
        """
        Return the list of available keyboard commands.

        Returns:
            list: List of all available commands

        Examples:
            >>> commands = bot.get_available_keyboard_commands()
            >>> print(f"Available commands: {len(commands)}")
            >>> for cmd in commands[:10]:  # Show the first 10
            ...     print(f"  - {cmd}")
        """
        return self.executor.keyboard_commander.get_available_commands()

    def _process_sendtext(self, sendtext):
        """
        Process special commands in sendtext and type the text.

        Args:
            sendtext (str): Text with special commands such as {ctrl}a, {del}, etc.
        """
        import time

        import pyautogui
        import pyperclip

        text_to_write = sendtext
        commands_processed = True

        while commands_processed:
            commands_processed = False
            lower_text = text_to_write.lower()

            if lower_text.startswith("{ctrl}a"):
                pyautogui.hotkey("ctrl", "a")
                text_to_write = text_to_write[7:]  # Remove '{ctrl}a'
                commands_processed = True
                time.sleep(0.1)

            elif lower_text.startswith("{del}"):
                pyautogui.press("delete")
                text_to_write = text_to_write[5:]  # Remove '{del}'
                commands_processed = True
                time.sleep(0.1)

            elif lower_text.startswith("{tab}"):
                pyautogui.press("tab")
                text_to_write = text_to_write[5:]  # Remove '{tab}'
                commands_processed = True
                time.sleep(0.1)

            elif lower_text.startswith("{enter}"):
                pyautogui.press("enter")
                text_to_write = text_to_write[7:]  # Remove '{enter}'
                commands_processed = True
                time.sleep(0.1)

        # Type the remaining text using the clipboard for greater reliability
        if text_to_write:
            try:
                pyperclip.copy(text_to_write)
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                # Fallback to direct typing
                pyautogui.write(text_to_write)
            time.sleep(0.1)

    def execute_with_backtrack_between_tasks(self, tasks_list):
        """
        Execute multiple individual tasks with real backtracking between them.

        When a task fails, it goes back to the previous one, runs it,
        and then returns to try the failed one again.

        Args:
            tasks_list (list): List of dictionaries with individual task settings
                              Each item must have: {'type': 'text'|'image', 'params': {...}}

        Returns:
            list: List of boolean results
        """
        if not tasks_list:
            return []

        results = []
        i = 0
        backtrack_stack = []
        task_failures = {}

        logger.info(
            f"🚀 Starting execution with backtracking across {len(tasks_list)} individual tasks"
        )

        while i < len(tasks_list):
            task_config = tasks_list[i]
            task_type = task_config.get("type")
            params = task_config.get("params", {})
            backtrack_enabled = params.get("backtrack", True)

            logger.info(
                f"📋 Running task {i + 1}/{len(tasks_list)} - Type: {task_type}"
            )

            success = False

            try:
                if task_type == "text":
                    # Remove backtrack from params to avoid recursion
                    text_params = params.copy()
                    text_params.pop("backtrack", None)
                    success = self.click_text(**text_params)

                elif task_type == "image":
                    # Remove backtrack from params to avoid recursion
                    image_params = params.copy()
                    image_params.pop("backtrack", None)
                    success = self.click_image(**image_params)

                else:
                    logger.error(f"Unknown task type: {task_type}")
                    success = False

            except Exception as e:
                logger.error(f"Error running task {i + 1}: {e}")
                success = False

            # Adjust the results list
            while len(results) <= i:
                results.append(False)
            results[i] = success

            if success:
                logger.info(f"✓ Task {i + 1}/{len(tasks_list)} executed successfully!")

                # Check whether there are pending backtracks on the stack
                if backtrack_stack:
                    # Pop the item from the stack and go back to the original task that failed
                    original_failed_task = backtrack_stack.pop()
                    logger.info(
                        f"🔄 Returning to task {original_failed_task + 1} that originally failed after backtrack"
                    )
                    i = original_failed_task
                    # Reset the failure attempts for the original task
                    if i in task_failures:
                        task_failures[i] = 0
                else:
                    # Normal behavior: advance to the next task
                    i += 1

            else:
                # Task failed, check backtracking
                if backtrack_enabled and i > 0:
                    # Manage backtracking
                    task_failures.setdefault(i, 0)
                    task_failures[i] += 1

                    if task_failures[i] <= 2:  # Limit backtrack attempts
                        # Add the current task to the backtrack stack (to return later)
                        if i not in backtrack_stack:  # Avoid duplicates
                            backtrack_stack.append(i)
                            logger.info(
                                f"📌 Task {i + 1} added to the backtrack stack for later re-execution"
                            )

                        prev_task_type = tasks_list[i - 1].get("type", "unknown")
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} ({task_type}) failed. "
                            f"BACKTRACKING to task {i}/{len(tasks_list)} ({prev_task_type})"
                        )
                        i -= 1  # Go back to the previous task (THIS IS THE KEY LINE!)
                    else:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} failed "
                            f"after multiple backtracking attempts. Advancing."
                        )
                        # Remove from the stack if it is there
                        if i in backtrack_stack:
                            backtrack_stack.remove(i)
                        i += 1
                else:
                    # No backtrack or first task
                    if backtrack_enabled:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} failed "
                            f"but it is the first task. Advancing."
                        )
                    else:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks_list)} failed "
                            f"and has 'backtrack': False. Advancing."
                        )
                    i += 1

        successful_tasks = sum(1 for r in results if r)
        logger.info(
            f"🏁 Execution finished: {successful_tasks}/{len(results)} successful tasks"
        )

        return results


# Backward-compatibility alias (previous branding: bot-vision-suite / import bot_vision)
BotVision = VisusBot


# NEW CONVENIENCE FUNCTIONS WITH INDIVIDUAL BACKTRACK


def start_individual_session(config=None):
    """
    Start an individual task session with backtracking.

    Args:
        config (dict, optional): Custom configuration

    Returns:
        VisusBot: Instance configured for individual backtracking
    """
    bot = VisusBot(config)
    bot.start_task_session()
    return bot


def run_individual_tasks_with_backtrack(task_functions, config=None):
    """
    Run a list of individual task functions with automatic backtracking.

    Args:
        task_functions (list): List of tuples (function, args, kwargs)
        config (dict, optional): Custom configuration

    Returns:
        tuple: (successes, total, bot_instance)

    Examples:
        >>> tasks = [
        ...     (lambda bot: bot.click_image('btn.png', backtrack=True), (), {}),
        ...     (lambda bot: bot.click_text('Save', backtrack=True), (), {}),
        ... ]
        >>> success, total, bot = run_individual_tasks_with_backtrack(tasks)
    """
    bot = VisusBot(config)
    bot.start_task_session()

    results = []
    for i, (func, args, kwargs) in enumerate(task_functions):
        try:
            result = func(bot, *args, **kwargs)
            results.append(result)
            logger.info(f"Task {i + 1}: {'✓ Success' if result else '✗ Failed'}")
        except Exception as e:
            logger.error(f"Error in task {i + 1}: {e}")
            results.append(False)

    successful, total = bot.end_task_session()
    return successful, total, bot


# Main function compatible with legacy code
def execute_tasks(tasks, config=None):
    """
    Main function to run a list of tasks.

    Supports both simple lists and lists of lists (multiple sets).
    This is the function that users migrated from the original code will use.

    Args:
        tasks (list): List of automation tasks or list of lists
        config (dict, optional): Custom configuration

    Returns:
        list: List of TaskResult or list of lists of TaskResult

    Examples:
        Simple list:
        >>> tasks = [{'text': 'Login', 'region': (100, 100, 500, 300)}]
        >>> results = execute_tasks(tasks)

        Multiple lists:
        >>> task_sets = [
        ...     [{'text': 'Login', 'region': (100, 100, 500, 300)}],
        ...     [{'text': 'Save', 'region': (200, 200, 600, 400)}]
        ... ]
        >>> results = execute_tasks(task_sets)
    """
    if not isinstance(tasks, list):
        logger.error(f"Tasks must be a list. Received type: {type(tasks)}")
        return []

    if not tasks:
        logger.info("Empty task list.")
        return []

    # Check whether it is a list of lists
    if isinstance(tasks[0], list):
        # Multiple task sets
        logger.info(
            f"Detected multiple task sets ({len(tasks)} sets). Running sequentially."
        )

        all_results = []
        for i, task_list in enumerate(tasks):
            if isinstance(task_list, list):
                logger.info(
                    f"--- Starting task set {i + 1}/{len(tasks)} ({len(task_list)} tasks) ---"
                )
                bot = VisusBot(config)
                results = bot.execute_tasks(task_list)
                all_results.append(results)
                logger.info(f"--- Finished task set {i + 1}/{len(tasks)} ---")
            else:
                logger.warning(
                    f"Item {i} in the main list is not a list of tasks. Skipping."
                )
                all_results.append([])

        return all_results
    else:
        # Simple list of tasks
        bot = VisusBot(config)
        return bot.execute_tasks(tasks)


# Additional function for full compatibility with the original click_images
def click_images(tasks, default_confidence=0.9, default_margin=50):
    """
    Function for full compatibility with legacy code.

    This function replicates exactly the behavior of the click_images function
    from the original bot_vision.py, including support for lists of lists.

    Args:
        tasks: List of tasks or list of lists of tasks
        default_confidence (float): Default confidence for image detection
        default_margin (int): Default margin (kept for compatibility)

    Returns:
        list: List of results
    """
    # Build a configuration with compatible default values
    config = {
        "default_confidence": default_confidence,
        "default_margin": default_margin,
        "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        "tessdata_path": r"C:\Program Files\Tesseract-OCR\tessdata",
    }

    return execute_tasks(tasks, config)


# Standalone functions for 100% compatibility with the original code
def locate_image_with_retry(
    image_path: str, region=None, confidence=0.9, max_attempts=3, scales=None
):
    """
    Standalone function that replicates exactly the original function from bot_vision.py.
    Tries to locate an image with different scales and confidence levels.
    """
    executor = TaskExecutor()
    return executor._locate_image_with_retry(
        image_path, region, confidence, max_attempts, scales
    )


# Standalone convenience functions - NEW FEATURES
def find_relative_image(
    anchor_image,
    target_image,
    max_distance=200,
    confidence=0.9,
    target_region=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Standalone function to find a relative image.

    Args:
        anchor_image (str): Path to the anchor image
        target_image (str): Path to the target image
        max_distance (int): Maximum distance in pixels
        confidence (float): Confidence level
        target_region (tuple, optional): Region to search for the target
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        tuple: Location of the image or None

    Examples:
        >>> location = find_relative_image('anchor.png', 'target.png')
    """
    bot = VisusBot()
    return bot.find_relative_image(
        anchor_image,
        target_image,
        max_distance,
        confidence,
        target_region,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
    )


def click_relative_image(
    anchor_image,
    target_image,
    max_distance=200,
    confidence=0.9,
    target_region=None,
    delay=0,
    mouse_button="left",
    backtrack=False,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Standalone function to click on a relative image.

    Args:
        anchor_image (str): Path to the anchor image
        target_image (str): Path to the target image
        max_distance (int): Maximum distance in pixels
        confidence (float): Confidence level (0.0-1.0)
        target_region (tuple, optional): Region to search for the target (x, y, width, height)
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        backtrack (bool): Whether to use backtracking on failure

    Returns:
        bool: True if clicked successfully, False otherwise

    Examples:
        >>> # Simple left click
        >>> success = click_relative_image('anchor.png', 'target.png')

        >>> # Right click
        >>> success = click_relative_image('anchor.png', 'target.png',
        ...                              mouse_button="right", backtrack=True)

        >>> # Double left click
        >>> success = click_relative_image('anchor.png', 'target.png',
        ...                              mouse_button="double", delay=1.0)

        >>> # Just move the mouse to the position (without clicking)
        >>> success = click_relative_image('anchor.png', 'target.png',
        ...                              mouse_button="move_to", delay=0.5)

        Additional args v1.3.0+:
            wait_until_found (bool): Waits for the image to appear automatically
            wait_until_disappears (bool): Waits for the image to disappear
            wait_timeout (int, optional): Specific timeout (overrides the global one)
    """
    bot = VisusBot()
    return bot.click_relative_image(
        anchor_image,
        target_image,
        max_distance,
        confidence,
        target_region,
        delay,
        mouse_button,
        backtrack,
        3,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
    )


def click_coordinates(x, y, delay=0, mouse_button="left", backtrack=False):
    """
    Standalone function to click on specific coordinates.

    Args:
        x (int): X coordinate
        y (int): Y coordinate
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        backtrack (bool): Whether to use backtracking on failure

    Returns:
        bool: True if clicked successfully, False otherwise

    Examples:
        >>> # Simple click
        >>> success = click_coordinates(100, 200, delay=1)

        >>> # Right click
        >>> success = click_coordinates(100, 200, mouse_button="right", backtrack=True)

        >>> # Just move the mouse to the position (without clicking)
        >>> success = click_coordinates(100, 200, mouse_button="move_to", delay=0.5)
    """
    bot = VisusBot()
    return bot.click_coordinates(x, y, delay, mouse_button, backtrack)


def type_text_standalone(text, interval=0.05, delay=0, backtrack=False):
    """
    Standalone function to type text.

    Args:
        text (str): Text to type
        interval (float): Interval between characters
        delay (float): Delay after typing
        backtrack (bool): Whether to use backtracking

    Returns:
        bool: True if typed successfully

    Examples:
        >>> success = type_text_standalone('Hello World!', backtrack=True)
        >>> success = type_text_standalone('{ctrl}a{del}New text', backtrack=True)
    """
    bot = VisusBot()
    return bot.type_text(text, interval, delay, backtrack)


def keyboard_command_standalone(command, delay=0, backtrack=False):
    """
    Standalone function to run a keyboard command.

    Args:
        command (str): Command to run
        delay (float): Delay after the command
        backtrack (bool): Whether to use backtracking

    Returns:
        bool: True if it ran successfully

    Examples:
        >>> success = keyboard_command_standalone('Ctrl+S', delay=1, backtrack=True)
        >>> success = keyboard_command_standalone('F7', backtrack=True)
    """
    bot = VisusBot()
    return bot.keyboard_command(command, delay, backtrack)


def get_available_keyboard_commands():
    """
    Standalone function to get the available keyboard commands.

    Returns:
        list: List of available commands

    Examples:
        >>> commands = get_available_keyboard_commands()
        >>> print(f"Total commands: {len(commands)}")
    """
    bot = VisusBot()
    return bot.get_available_keyboard_commands()


def extract_text_from_region_standalone(
    region=None,
    filter_type="both",
    confidence_threshold=50.0,
    return_full_data=False,
    max_attempts=3,
    backtrack=False,
    config=None,
):
    """
    Standalone function to extract text from a specific region of the screen.

    Args:
        region (tuple, optional): (x, y, width, height) of the region to extract text from.
                                If None, extracts from the whole screen
        filter_type (str): Filter type ("numbers", "letters", "both")
        confidence_threshold (float): Minimum confidence threshold (0-100)
        return_full_data (bool): If True, returns full data with coordinates
        max_attempts (int): Maximum number of attempts if backtrack=True
        backtrack (bool): Whether to try multiple times with adjustments
        config (dict or BotVisionConfig, optional): Custom configuration

    Returns:
        If return_full_data=False:
            list: List of strings with all the text found
        If return_full_data=True:
            list: List of dictionaries with full data

    Examples:
        Simple extraction:
        >>> texts = extract_text_from_region_standalone(region=(100, 100, 400, 300))
        >>> print("Texts found:", texts)

        Extraction with full data:
        >>> data = extract_text_from_region_standalone(
        ...     region=(100, 100, 400, 300),
        ...     return_full_data=True,
        ...     confidence_threshold=70.0,
        ...     backtrack=True
        ... )
        >>> for item in data:
        ...     print(f"'{item['text']}' - Confidence: {item['confidence']:.1f}%")

        Numbers only:
        >>> numbers = extract_text_from_region_standalone(
        ...     region=(50, 50, 200, 100),
        ...     filter_type="numbers"
        ... )
    """
    bot = VisusBot(config=config)
    return bot.extract_text_from_region(
        region=region,
        filter_type=filter_type,
        confidence_threshold=confidence_threshold,
        return_full_data=return_full_data,
        max_attempts=max_attempts,
        backtrack=backtrack,
    )


# Function for full compatibility - task execution with multiple-list support
def run_automation(tasks, default_confidence=0.9, default_margin=50):
    """
    Function that replicates the exact behavior of the if __name__ == '__main__' block of the original bot_vision.py.
    Supports both a simple list and a list of lists (multiple task sets).

    Args:
        tasks: List of tasks or list of lists of tasks (as in the original)
        default_confidence (float): Default confidence
        default_margin (int): Default margin
    """
    import logging

    # Check whether tasks is a list and not empty
    if isinstance(tasks, list) and tasks:
        # Check whether the first element is also a list (indicating a list of lists)
        if isinstance(tasks[0], list):
            logging.info(
                f"Detected multiple task lists ({len(tasks)} lists). Executing sequentially."
            )
            # Iterate through each task list
            for i, task_list in enumerate(tasks):
                if isinstance(task_list, list):
                    logging.info(
                        f"--- Starting task list {i + 1}/{len(tasks)} ({len(task_list)} tasks) ---"
                    )
                    click_images(
                        task_list, default_confidence, default_margin
                    )  # Pass the individual list to the function
                    logging.info(f"--- Finished task list {i + 1}/{len(tasks)} ---")
                else:
                    logging.warning(
                        f"Item {i} in the main list is not a list of tasks. Skipping."
                    )
        else:
            # Assume it is a single flat list of tasks
            logging.info("Detected a single task list. Executing.")
            click_images(tasks, default_confidence, default_margin)
    elif isinstance(tasks, list) and not tasks:
        logging.info("The imported 'tasks' list is empty. Nothing to execute.")
    else:
        logging.error(
            f"The imported 'tasks' is not a list. Type: {type(tasks)}. Cannot execute."
        )


# Initial library setup
def _setup_library():
    """Initial library setup."""
    try:
        # Configure logging if it is not already configured
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
            )

        # Try to configure the library with the default configuration
        get_default_config()
        logger.debug(f"visus.desktop v{__version__} initialized")

    except Exception as e:
        logger.warning(f"Warning during library initialization: {e}")


# Run the initial setup
_setup_library()


# Standalone convenience functions (create a temporary VisusBot instance)
def find_text(
    text,
    region=None,
    filter_type="both",
    confidence_threshold=75.0,
    occurrence=1,
    max_attempts=3,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Search for text on screen using a temporary VisusBot instance.

    Args:
        text (str): Text to find
        region (tuple, optional): Search region (x, y, width, height)
        filter_type (str): Filter type ("letters", "numbers", "both")
        confidence_threshold (float): OCR confidence threshold
        occurrence (int): Which occurrence to look for (1=first)
        max_attempts (int): Maximum number of attempts
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        tuple: Found coordinates or None
    """
    bot = VisusBot(config)
    return bot.find_text(
        text,
        region,
        filter_type,
        confidence_threshold,
        occurrence,
        max_attempts,
        wait_until_found=wait_until_found,
        wait_until_disappears=wait_until_disappears,
        wait_timeout=wait_timeout,
    )


def click_text(
    text,
    region=None,
    filter_type="both",
    delay=0,
    mouse_button="left",
    occurrence=1,
    max_attempts=3,
    sendtext=None,
    confidence_threshold=None,
    show_overlay=True,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Click on text using a temporary VisusBot instance.

    Args:
        text (str): Text to click on
        region (tuple, optional): Search region (x, y, width, height)
        filter_type (str): Filter type ("letters", "numbers", "both")
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        occurrence (int): Which occurrence to click (1=first)
        max_attempts (int): Maximum number of attempts
        sendtext (str, optional): Text to type after the click
        confidence_threshold (float, optional): Custom confidence threshold
        show_overlay (bool): Whether to show the red overlay before the click
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the text to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the text to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        bool: True if found and clicked, False otherwise
    """
    bot = VisusBot(config)
    return bot.click_text(
        text,
        region,
        filter_type,
        delay,
        mouse_button,
        occurrence,
        False,
        max_attempts,
        sendtext,
        confidence_threshold,
        show_overlay,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
    )


def find_image(
    image_path,
    region=None,
    confidence=0.9,
    max_attempts=3,
    specific=True,
    scales=None,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Search for an image on screen using a temporary VisusBot instance.

    Args:
        image_path (str): Path to the image
        region (tuple, optional): Search region
        confidence (float): Confidence level
        max_attempts (int): Maximum number of attempts
        specific (bool): If True, searches in the region; if False, searches the whole screen + variations
        scales (list, optional): List of scales to try
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        tuple: Coordinates of the image or None
    """
    bot = VisusBot(config)
    return bot.find_image(
        image_path,
        region,
        confidence,
        max_attempts,
        False,
        specific,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
        scales,
    )


def click_image(
    image_path,
    region=None,
    confidence=0.9,
    delay=0,
    mouse_button="left",
    max_attempts=3,
    specific=True,
    sendtext=None,
    show_overlay=True,
    config=None,
    wait_until_found=False,
    wait_until_disappears=False,
    wait_timeout=None,
):
    """
    Click on an image using a temporary VisusBot instance.

    Args:
        image_path (str): Path to the image
        region (tuple, optional): Search region (x, y, width, height)
        confidence (float): Confidence level (0.0-1.0)
        delay (float): Delay after the click in seconds
        mouse_button (str): Mouse click type:
            • "left" - Simple left click (default)
            • "right" - Right click
            • "double" or "double left" - Double left click
            • "move_to" - Just moves the mouse without clicking
        max_attempts (int): Maximum number of attempts
        specific (bool): If True, searches in the region; if False, searches the whole screen + variations
        sendtext (str, optional): Text to type after the click
        show_overlay (bool): Whether to show the red overlay before the click
        config (dict, optional): Custom configuration
        wait_until_found (bool): 🆕 v1.3.0+ - Waits for the image to appear automatically
        wait_until_disappears (bool): 🆕 v1.3.0+ - Waits for the image to disappear
        wait_timeout (int, optional): 🆕 v1.3.0+ - Specific timeout (overrides the global one)

    Returns:
        bool: True if found and clicked, False otherwise
    """
    bot = VisusBot(config)
    return bot.click_image(
        image_path,
        region,
        confidence,
        delay,
        mouse_button,
        max_attempts,
        False,
        specific,
        sendtext,
        show_overlay,
        wait_until_found,
        wait_until_disappears,
        wait_timeout,
    )


def click_at(location, mouse_button="left", delay=0, show_overlay=True, config=None):
    """
    Click on specific coordinates using a temporary VisusBot instance.

    Args:
        location (tuple): (x, y, width, height) of the location
        mouse_button (str): Mouse button ("left", "right", "double", "move_to")
        delay (float): Delay after the click
        show_overlay (bool): Whether to show the red overlay before the click
        config (dict, optional): Custom configuration

    Returns:
        bool: True if clicked successfully
    """
    bot = VisusBot(config)
    return bot.click_at(location, mouse_button, delay, show_overlay)


def type_text(text, config=None):
    """
    Type text using a temporary VisusBot instance.

    Args:
        text (str): Text to type (supports special commands)
        config (dict, optional): Custom configuration

    Returns:
        bool: True if typed successfully
    """
    bot = VisusBot(config)
    return bot.type_text(text)


# PUBLIC EXPORTS
__all__ = [
    # Main class
    "VisusBot",
    "BotVision",  # backward-compatibility alias
    # Task execution functions
    "execute_tasks",
    "click_images",  # Full compatibility with legacy code
    "run_automation",  # Compatibility with if __name__ == '__main__'
    # Basic convenience functions
    "find_text",
    "click_text",
    "find_image",
    "click_image",
    "click_at",
    "type_text",
    # NEW FEATURES - Convenience functions for relative images
    "find_relative_image",
    "click_relative_image",
    # NEW FEATURES - Convenience functions for coordinates
    "click_coordinates",
    # NEW FEATURES - Convenience functions for the keyboard
    "type_text_standalone",
    "keyboard_command_standalone",
    "get_available_keyboard_commands",
    # NEW FEATURE - Text extraction
    "extract_text_from_region_standalone",
    # Individual backtrack functions
    "start_individual_session",
    "run_individual_tasks_with_backtrack",
    # Core classes (for advanced use)
    "TaskExecutor",
    "TaskResult",
    "OCREngine",
    "OCRResult",
    "ImageProcessor",
    "VisualOverlay",
    "RelativeImageDetector",  # NEW
    "KeyboardCommander",  # NEW
    # Utilities
    "BotVisionConfig",
    "get_default_config",
    "clean_text",
    "limpar_texto",
    "matches_filter",
    # Standalone processing functions (compatibility)
    "preprocess_image_for_ocr",
    "find_text_with_multiple_preprocessing",
    "show_overlay",
    "locate_image_with_retry",
    # Files / clipboard / screen / process / window / image map / mouse (BotCity parity)
    "wait_for_file",
    "wait_for_file_stable",
    "copy_to_clipboard",
    "paste",
    "get_clipboard",
    "capture_screen",
    "save_screenshot",
    "get_display_size",
    "launch",
    "find_process",
    "is_process_running",
    "kill_process",
    "focus_window",
    "maximize_window",
    "minimize_window",
    "close_window",
    "scroll",
    "drag",
    "triple_click",
    "move_random",
    "ImageMap",
    # Exceptions
    "BotVisionError",
    "ImageNotFoundError",
    "TextNotFoundError",
    "TaskExecutionError",
    "ImageProcessingError",
    "OCRProcessingError",
    "TesseractNotFoundError",
    "InvalidRegionError",
    "ConfigurationError",
    # Library information
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]

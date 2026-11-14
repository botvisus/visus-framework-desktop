"""
Visus Desktop - Keyboard Commands

This module implements a complete list of keyboard commands
for automation, including system-specific and general commands.
"""

import logging
import time
from typing import Callable, Dict

import pyautogui

from ..exceptions import TaskExecutionError
from .human_typing import fix_pyautogui_keys

# setas, Home, End, PgUp/PgDn e Delete com a marca de tecla estendida: sem ela, com o
# NumLock ligado, o Windows solta o Shift (Shift+Right andava em vez de selecionar)
fix_pyautogui_keys()

# every key name pyautogui can press -- the chord parser accepts all of them
_PYAUTOGUI_KEYS = frozenset(k.lower() for k in pyautogui.KEYBOARD_KEYS)
# what people (and AI agents) call a key -> pyautogui's name
_KEY_ALIASES = {
    "control": "ctrl",
    "cmd": "win",
    "super": "win",
    "windows": "win",
    "meta": "win",
    "option": "alt",
    "return": "enter",
    "escape": "esc",
    "del": "delete",
    "bksp": "backspace",
    "spacebar": "space",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
    "prtsc": "printscreen",
    "prtscr": "printscreen",
    "prntscrn": "printscreen",
    "menu": "apps",
    "contextmenu": "apps",
    "break": "pause",
    "ins": "insert",
    "plus": "+",
    "minus": "-",
    "hyphen": "-",
    "comma": ",",
    "period": ".",
    "dot": ".",
    "slash": "/",
    "backslash": "\\",
    "semicolon": ";",
    "colon": ":",
    "quote": "'",
    "apostrophe": "'",
    "backquote": "`",
    "backtick": "`",
    "grave": "`",
    "equals": "=",
    "equal": "=",
    "tilde": "~",
    "openbracket": "[",
    "closebracket": "]",
    "volup": "volumeup",
    "voldown": "volumedown",
    "mute": "volumemute",
}

logger = logging.getLogger(__name__)


class KeyboardCommander:
    """
    Keyboard command executor.

    Provides a unified interface to execute different types
    of keyboard commands, including special keys and combinations.
    """

    def __init__(self):
        """Initializes the keyboard commander."""
        self._setup_command_mapping()

    def _setup_command_mapping(self) -> None:
        """Sets up the mapping of commands to pyautogui functions."""
        self.command_mapping: Dict[str, Callable] = {
            # System-specific commands (Oracle Forms, etc.)
            "F7": lambda: pyautogui.press("f7"),  # Clear Block
            "F5": lambda: pyautogui.press("f5"),  # Clear Field
            "F8": lambda: pyautogui.press("f8"),  # Clear Form
            "F6": lambda: pyautogui.press("f6"),  # Clear Record
            "Ctrl+S": lambda: pyautogui.hotkey("ctrl", "s"),  # Commit
            "F12": lambda: pyautogui.press("f12"),  # Count Query
            "Ctrl+Up": lambda: pyautogui.hotkey("ctrl", "up"),  # Delete Record
            "Shift+Ctrl+E": lambda: pyautogui.hotkey(
                "shift", "ctrl", "e"
            ),  # Display Error
            "Down": lambda: pyautogui.press("down"),  # Down
            "Shift+F5": lambda: pyautogui.hotkey("shift", "f5"),  # Duplicate Field
            "Shift+F6": lambda: pyautogui.hotkey("shift", "f6"),  # Duplicate Record
            "Ctrl+E": lambda: pyautogui.hotkey("ctrl", "e"),  # Edit
            "Ctrl+F11": lambda: pyautogui.hotkey("ctrl", "f11"),  # Enter Query
            "F4": lambda: pyautogui.press("f4"),  # Exit
            "Shift+Ctrl+F10": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f10"
            ),  # Function 0
            "Shift+Ctrl+F1": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f1"
            ),  # Function 1
            "Shift+Ctrl+F2": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f2"
            ),  # Function 2
            "Shift+Ctrl+F3": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f3"
            ),  # Function 3
            "Shift+Ctrl+F4": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f4"
            ),  # Function 4
            "Shift+Ctrl+F5": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f5"
            ),  # Function 5
            "Shift+Ctrl+F6": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f6"
            ),  # Function 6
            "Shift+Ctrl+F7": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f7"
            ),  # Function 7
            "Ctrl+H": lambda: pyautogui.hotkey("ctrl", "h"),  # Help
            "Ctrl+Down": lambda: pyautogui.hotkey("ctrl", "down"),  # Insert Record
            "Ctrl+L": lambda: pyautogui.hotkey("ctrl", "l"),  # List of Values
            "F2": lambda: pyautogui.press("f2"),  # List Tab Pages
            "Shift+PageDown": lambda: pyautogui.hotkey(
                "shift", "pagedown"
            ),  # Next Block
            "Tab": lambda: pyautogui.press("tab"),  # Next Field
            "Shift+F7": lambda: pyautogui.hotkey("shift", "f7"),  # Next Primary Key
            "Shift+F8": lambda: pyautogui.hotkey("shift", "f8"),  # Next Set of Records
            "Shift+PageUp": lambda: pyautogui.hotkey(
                "shift", "pageup"
            ),  # Previous Block
            "Shift+Tab": lambda: pyautogui.hotkey("shift", "tab"),  # Previous Field
            "Up": lambda: pyautogui.press("up"),  # Previous Record
            "Ctrl+P": lambda: pyautogui.hotkey("ctrl", "p"),  # Print
            "Shift+Ctrl+F9": lambda: pyautogui.hotkey(
                "shift", "ctrl", "f9"
            ),  # Prompt/Value LOV
            "Return": lambda: pyautogui.press("enter"),  # Return
            "PageDown": lambda: pyautogui.press("pagedown"),  # Scroll Down
            "PageUp": lambda: pyautogui.press("pageup"),  # Scroll Up
            "Ctrl+K": lambda: pyautogui.hotkey("ctrl", "k"),  # Show Keys
            "Ctrl+U": lambda: pyautogui.hotkey("ctrl", "u"),  # Update Record
            # General editing commands
            "Ctrl+C": lambda: pyautogui.hotkey("ctrl", "c"),  # Copy
            "Ctrl+V": lambda: pyautogui.hotkey("ctrl", "v"),  # Paste
            "Ctrl+X": lambda: pyautogui.hotkey("ctrl", "x"),  # Cut
            "Ctrl+A": lambda: pyautogui.hotkey("ctrl", "a"),  # Select All
            "Ctrl+Z": lambda: pyautogui.hotkey("ctrl", "z"),  # Undo
            "Ctrl+Y": lambda: pyautogui.hotkey("ctrl", "y"),  # Redo
            "Ctrl+F": lambda: pyautogui.hotkey("ctrl", "f"),  # Find
            "Ctrl+N": lambda: pyautogui.hotkey("ctrl", "n"),  # New
            "Ctrl+O": lambda: pyautogui.hotkey("ctrl", "o"),  # Open
            # Navigation keys
            "Enter": lambda: pyautogui.press("enter"),
            "Escape": lambda: pyautogui.press("escape"),
            "Space": lambda: pyautogui.press("space"),
            "Delete": lambda: pyautogui.press("delete"),
            "Backspace": lambda: pyautogui.press("backspace"),
            "Home": lambda: pyautogui.press("home"),
            "End": lambda: pyautogui.press("end"),
            "Page Up": lambda: pyautogui.press("pageup"),
            "Page Down": lambda: pyautogui.press("pagedown"),
            "Arrow Up": lambda: pyautogui.press("up"),
            "Arrow Down": lambda: pyautogui.press("down"),
            "Arrow Left": lambda: pyautogui.press("left"),
            "Arrow Right": lambda: pyautogui.press("right"),
            # Function keys
            "F1": lambda: pyautogui.press("f1"),
            "F3": lambda: pyautogui.press("f3"),
            "F9": lambda: pyautogui.press("f9"),
            "F10": lambda: pyautogui.press("f10"),
            "F11": lambda: pyautogui.press("f11"),
            # System commands
            "Alt+Tab": lambda: pyautogui.hotkey("alt", "tab"),  # Switch windows
            "Alt+F4": lambda: pyautogui.hotkey("alt", "f4"),  # Close window
            "Windows+D": lambda: pyautogui.hotkey("win", "d"),  # Show desktop
            "Windows+L": lambda: pyautogui.hotkey("win", "l"),  # Lock screen
            "Windows+R": lambda: pyautogui.hotkey("win", "r"),  # Run dialog
            # Additional navigation commands
            "Ctrl+Home": lambda: pyautogui.hotkey("ctrl", "home"),  # Start of document
            "Ctrl+End": lambda: pyautogui.hotkey("ctrl", "end"),  # End of document
            "Shift+Home": lambda: pyautogui.hotkey(
                "shift", "home"
            ),  # Select to start of line
            "Shift+End": lambda: pyautogui.hotkey(
                "shift", "end"
            ),  # Select to end of line
            "Ctrl+Left": lambda: pyautogui.hotkey("ctrl", "left"),  # Word left
            "Ctrl+Right": lambda: pyautogui.hotkey("ctrl", "right"),  # Word right
            "Shift+Ctrl+Left": lambda: pyautogui.hotkey(
                "shift", "ctrl", "left"
            ),  # Select word left
            "Shift+Ctrl+Right": lambda: pyautogui.hotkey(
                "shift", "ctrl", "right"
            ),  # Select word right
            # Formatting commands
            "Ctrl+B": lambda: pyautogui.hotkey("ctrl", "b"),  # Bold
            "Ctrl+I": lambda: pyautogui.hotkey("ctrl", "i"),  # Italic
            # Browser-specific commands
            "Ctrl+T": lambda: pyautogui.hotkey("ctrl", "t"),  # New tab
            "Ctrl+W": lambda: pyautogui.hotkey("ctrl", "w"),  # Close tab
            "Ctrl+R": lambda: pyautogui.hotkey("ctrl", "r"),  # Refresh
            "Ctrl+Shift+T": lambda: pyautogui.hotkey(
                "ctrl", "shift", "t"
            ),  # Reopen closed tab
            "Ctrl+D": lambda: pyautogui.hotkey("ctrl", "d"),  # Bookmark
            "Ctrl+J": lambda: pyautogui.hotkey("ctrl", "j"),  # Downloads
            "Ctrl+Shift+N": lambda: pyautogui.hotkey(
                "ctrl", "shift", "n"
            ),  # New incognito window
            # Volume and media commands
            "Volume Up": lambda: pyautogui.press("volumeup"),
            "Volume Down": lambda: pyautogui.press("volumedown"),
            "Volume Mute": lambda: pyautogui.press("volumemute"),
            "Play/Pause": lambda: pyautogui.press("playpause"),
            "Next Track": lambda: pyautogui.press("nexttrack"),
            "Previous Track": lambda: pyautogui.press("prevtrack"),
            # Screen capture commands
            "Print Screen": lambda: pyautogui.press("printscreen"),
            "Alt+Print Screen": lambda: pyautogui.hotkey("alt", "printscreen"),
            "Windows+Shift+S": lambda: pyautogui.hotkey(
                "win", "shift", "s"
            ),  # Snipping tool
        }

    def execute_command(self, command: str) -> bool:
        """
        Executes a keyboard command.

        Args:
            command (str): Name of the command to be executed

        Returns:
            bool: True if the command was executed successfully, False otherwise

        Raises:
            TaskExecutionError: If there is an error executing the command
        """
        try:
            if command in self.command_mapping:
                logger.info(f"Executing keyboard command: '{command}'")
                self.command_mapping[command]()
                logger.info(f"Command '{command}' executed successfully")
                return True
            steps = [step.strip() for step in command.split(",")]
            if len(steps) > 1 and all(steps):
                # one after another, like a person: Office's key tips "Alt, H, O, I"
                # (Home > Format > AutoFit Column Width) in a single call
                for n, step in enumerate(steps):
                    if n:
                        time.sleep(0.15)
                    if not self.execute_command(step):
                        return False
                return True
            # Fall back to a generic chord parser so ANY modifier combo works
            # (e.g. "Ctrl+Shift+S", "Ctrl+Alt+Del") without a hardcoded entry.
            keys = self._parse_chord(command)
            if keys:
                import pyautogui

                logger.info(f"Executing keyboard chord: '{command}' -> {keys}")
                pyautogui.hotkey(*keys)
                return True
            logger.warning(f"Command '{command}' not recognized")
            return False
        except Exception as e:
            error_msg = f"Error executing command '{command}': {e}"
            logger.error(error_msg)
            raise TaskExecutionError(error_msg) from e

    @staticmethod
    def _parse_chord(command: str):
        """Parse ANY key or chord into pyautogui key names, or return None.

        Free, not a list: every key pyautogui knows (Enter, Esc, F1-F24, PageDown,
        PrintScreen, CapsLock, Apps, Num0-Num9, VolumeUp, PlayPause...), any single
        character (``a``, ``7``, ``;``, ``/``, ``ç``) and any combination joined with
        ``+`` -- ``Ctrl+Shift+S``, ``Ctrl+;``, ``Ctrl++``, ``Win+Shift+S``, ``Alt``
        alone. Case-insensitive; spaces inside a name are ignored ("Page Down").
        Aliases: Control, Cmd/Super/Windows/Meta (Win), Option (Alt), Plus, Minus,
        Comma, Period, Slash, Semicolon, Equals... Returns the ordered key list for
        ``pyautogui.hotkey(*keys)`` or ``None`` when a part is not a key.
        """
        if not command or not isinstance(command, str):
            return None
        text = command.strip()
        if len(text) == 1:
            return [text.lower()] if text.isprintable() else None
        # "Ctrl++" / "Ctrl+Shift++": the last key IS the plus sign
        trailing_plus = text.endswith("+")
        if trailing_plus:
            text = text[:-1]
        parts = [p.strip() for p in text.split("+")]
        if trailing_plus:
            # "Ctrl+" split is ["Ctrl", ""]: that empty last part is the plus key
            if parts[-1]:
                parts.append("+")
            else:
                parts[-1] = "+"
        keys = []
        for part in parts:
            key = KeyboardCommander._key_name(part)
            if key is None:
                return None
            keys.append(key)
        return keys or None

    @staticmethod
    def _key_name(part: str):
        """One key's pyautogui name, or None when it isn't a key."""
        if len(part) == 1:
            return part.lower() if part.isprintable() and not part.isspace() else None
        low = part.lower().replace(" ", "").replace("_", "")
        if not low:
            return None
        low = _KEY_ALIASES.get(low, low)
        if len(low) == 1 or low in _PYAUTOGUI_KEYS:
            return low
        return None

    def get_available_commands(self) -> list:
        """
        Returns the list of available commands.

        Returns:
            list: List with all available commands
        """
        return list(self.command_mapping.keys())

    def type_text(self, text: str, interval: float = 0.05) -> None:
        """
        Types text with an interval between characters.

        Args:
            text (str): Text to be typed
            interval (float): Interval between characters in seconds

        Raises:
            TaskExecutionError: If there is an error while typing
        """
        try:
            from .human_typing import type_literally

            logger.info(f"Typing text: '{text}'")
            type_literally(
                text, interval
            )  # certo em qualquer teclado (o typewrite errava o "/" no ABNT2)
            logger.info("Text typed successfully")
        except Exception as e:
            error_msg = f"Error typing text '{text}': {e}"
            logger.error(error_msg)
            raise TaskExecutionError(error_msg) from e

    _TOKEN_RE = None  # compiled lazily in type_with_tokens

    def type_with_tokens(self, text: str, interval: float = 0.05) -> None:
        """Type ``text``, expanding key tokens ANYWHERE, robust against drops.

        Tokens (case-insensitive, recognized at any position): ``{enter}``,
        ``{tab}``, ``{esc}`` / ``{escape}``, ``{backspace}``, ``{del}`` /
        ``{delete}``, and ``{ctrl}a``. Literal text between tokens is entered
        via the clipboard (paste) so no characters are dropped under load; if
        the clipboard is unavailable it falls back to ``typewrite``.
        """
        import re
        import time

        if KeyboardCommander._TOKEN_RE is None:
            KeyboardCommander._TOKEN_RE = re.compile(
                r"(\{ctrl\}a|\{enter\}|\{tab\}|\{esc(?:ape)?\}|\{backspace\}|"
                r"\{del(?:ete)?\})",
                re.IGNORECASE,
            )
        presses = {
            "{enter}": ("press", "enter"),
            "{tab}": ("press", "tab"),
            "{esc}": ("press", "esc"),
            "{escape}": ("press", "esc"),
            "{backspace}": ("press", "backspace"),
            "{del}": ("press", "delete"),
            "{delete}": ("press", "delete"),
            "{ctrl}a": ("hotkey", ("ctrl", "a")),
        }
        for part in KeyboardCommander._TOKEN_RE.split(text):
            if not part:
                continue
            action = presses.get(part.lower())
            if action is None:
                self._type_literal(part, interval)
                continue
            kind, arg = action
            if kind == "press":
                pyautogui.press(arg)
            else:
                pyautogui.hotkey(*arg)
            time.sleep(0.03)

    def _type_literal(self, text: str, interval: float = 0.05) -> None:
        """Enter literal ``text`` via clipboard paste; fall back to typewrite."""
        import time

        from ..utils.clipboard import copy as _copy

        try:
            _copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.05)
        except Exception as exc:  # clipboard unavailable -> reliable-ish typing
            logger.debug("Clipboard paste failed (%s); typing instead", exc)
            from .human_typing import type_literally

            type_literally(text, max(interval, 0.02))

    def process_sendtext_command(self, full_text_command: str) -> None:
        """
        Processes special commands in sendtext.

        Args:
            full_text_command (str): Full command with text and special commands

        Raises:
            TaskExecutionError: If there is an error during processing
        """
        import time

        import pyperclip

        try:
            logger.info(f"Processing sendtext: '{full_text_command}'")

            # Process special commands at the beginning of the string
            text_to_write = full_text_command
            commands_processed = True

            while commands_processed:
                commands_processed = False
                # Normalize to lowercase to make matching easier
                lower_text = text_to_write.lower()

                if lower_text.startswith("{ctrl}a"):
                    logger.info("Executing command: CTRL+A (Select All)")
                    pyautogui.hotkey("ctrl", "a")
                    text_to_write = text_to_write[len("{ctrl}a") :]
                    commands_processed = True
                    time.sleep(0.1)
                elif lower_text.startswith("{del}"):
                    logger.info("Executing command: DEL (Delete)")
                    pyautogui.press("delete")
                    text_to_write = text_to_write[len("{del}") :]
                    commands_processed = True
                    time.sleep(0.1)
                elif lower_text.startswith("{tab}"):
                    logger.info("Executing command: TAB")
                    pyautogui.press("tab")
                    text_to_write = text_to_write[len("{tab}") :]
                    commands_processed = True
                    time.sleep(0.1)
                elif lower_text.startswith("{enter}"):
                    logger.info("Executing command: ENTER")
                    pyautogui.press("enter")
                    text_to_write = text_to_write[len("{enter}") :]
                    commands_processed = True
                    time.sleep(0.1)
                elif lower_text.startswith("{backspace}"):
                    logger.info("Executing command: BACKSPACE")
                    pyautogui.press("backspace")
                    text_to_write = text_to_write[len("{backspace}") :]
                    commands_processed = True
                    time.sleep(0.1)
                elif lower_text.startswith("{escape}"):
                    logger.info("Executing command: ESCAPE")
                    pyautogui.press("escape")
                    text_to_write = text_to_write[len("{escape}") :]
                    commands_processed = True
                    time.sleep(0.1)

            # Type the remaining text using the clipboard for better compatibility
            if text_to_write:
                logger.info(f"Pasting remaining text: '{text_to_write}'")
                pyperclip.copy(text_to_write)
                pyautogui.hotkey("ctrl", "v")

            time.sleep(0.5)  # Small pause after processing sendtext

        except Exception as e:
            error_msg = f"Error processing sendtext '{full_text_command}': {e}"
            logger.error(error_msg)
            raise TaskExecutionError(error_msg) from e

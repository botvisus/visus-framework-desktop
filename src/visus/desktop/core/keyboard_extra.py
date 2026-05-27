"""Visus Desktop - Named keyboard helpers.

A mixin that mirrors BotCity's rich, named keyboard API (``enter``, ``tab``,
``control_c``, ``key_f1`` .. ``key_f12``, etc.) without duplicating the existing
keyboard system. Each named shortcut is a thin one-liner that delegates to
``self.keyboard_command("<Command>")`` -- the single source of truth being the
command map owned by
:class:`visus.desktop.core.keyboard_commands.KeyboardCommander`. This keeps the
method names reading like intentions while ensuring there is exactly one place
that knows how a command maps to real keystrokes.

The mixin assumes the host class provides a ``keyboard_command`` method.
:class:`visus.desktop.VisusBot` does, so mixing this into the bot is enough.

A small set of methods remain *low-level primitives* that talk to ``pyautogui``
directly: :meth:`type_key`, :meth:`key_combo`, :meth:`hold_shift`,
:meth:`release_shift`, :meth:`hold_ctrl` and :meth:`release_ctrl`. These are not
present in the ``KeyboardCommander`` map (holding/releasing a modifier across
several presses, or pressing/combining arbitrary keys, is not a fixed named
command), so they are not duplication. They import ``pyautogui`` lazily, which
keeps the module importable in headless environments (for example CI runners)
where ``pyautogui`` cannot initialize a display.

Example:
    >>> from visus.desktop.core.keyboard_extra import KeyboardMixin
    >>>
    >>> class Bot(KeyboardMixin):
    ...     def keyboard_command(self, command, delay=0, backtrack=False):
    ...         ...  # provided by VisusBot in real usage
    >>>
    >>> bot = Bot()
    >>> bot.enter()              # -> self.keyboard_command("Enter")
    >>> bot.control_c()          # -> self.keyboard_command("Ctrl+C")
    >>> bot.key_f5()             # -> self.keyboard_command("F5")
    >>> bot.type_key("h")        # primitive: pyautogui.press("h")
    >>> bot.hold_shift()         # primitive: pyautogui.keyDown("shift")
    >>> bot.release_shift()      # primitive: pyautogui.keyUp("shift")
"""

from __future__ import annotations

from typing import Any


class KeyboardMixin:
    """Mixin providing a rich, named keyboard API.

    Mix this into any class that exposes a ``keyboard_command`` method (such as
    :class:`visus.desktop.VisusBot`) to gain expressive, self-documenting
    keyboard methods such as :meth:`enter`, :meth:`tab`, :meth:`control_c` and
    :meth:`key_f5`.

    Design:

    * **Named shortcuts** (everything except the primitives below) delegate to
      ``self.keyboard_command("<Command>")``. The ``KeyboardCommander`` command
      map is the single source of truth for how each command is performed, so
      these methods never duplicate that logic -- they only translate a friendly
      method name into the canonical command string.
    * **Primitives** (:meth:`type_key`, :meth:`key_combo`, :meth:`hold_shift`,
      :meth:`release_shift`, :meth:`hold_ctrl`, :meth:`release_ctrl`) call
      ``pyautogui`` directly. They are *not* part of the command map, so they
      are not duplication; ``pyautogui`` is imported lazily inside each one.

    Example:
        >>> bot.control_a()   # select all -> self.keyboard_command("Ctrl+A")
        >>> bot.control_c()   # copy       -> self.keyboard_command("Ctrl+C")
        >>> bot.tab()         # next field -> self.keyboard_command("Tab")
    """

    # ``keyboard_command`` is supplied by the host class (for example VisusBot).
    # Declaring its shape here keeps type checkers and readers honest about the
    # contract this mixin depends on.
    def keyboard_command(
        self, command: str, delay: float = 0, backtrack: bool = False
    ) -> bool:  # pragma: no cover - provided by the host class
        """Run a named keyboard command (provided by the host class)."""
        raise NotImplementedError(
            "KeyboardMixin requires the host class to provide keyboard_command()"
        )

    # ------------------------------------------------------------------
    # Generic primitives (talk to pyautogui directly; not in the command map)
    # ------------------------------------------------------------------
    def type_key(self, key: str) -> None:
        """Press a single key by its ``pyautogui`` name.

        Low-level primitive (not a named command). Pressing an arbitrary key is
        not part of the ``KeyboardCommander`` map, so this calls ``pyautogui``
        directly.

        Args:
            key: The ``pyautogui`` key name to press (for example ``"a"``,
                ``"enter"`` or ``"f5"``).
        """
        import pyautogui

        pyautogui.press(key)

    def key_combo(self, *keys: str) -> None:
        """Press several keys together as a hotkey combination.

        Low-level primitive (not a named command). Combining arbitrary keys is
        not part of the ``KeyboardCommander`` map, so this calls ``pyautogui``
        directly. The keys are pressed down in order and released in reverse
        order, the standard way to express shortcuts such as ``Ctrl+Alt+Del``.

        Args:
            *keys: The ``pyautogui`` key names to combine (for example
                ``"ctrl", "alt", "del"``).
        """
        import pyautogui

        pyautogui.hotkey(*keys)

    # ------------------------------------------------------------------
    # Navigation and editing (delegate to keyboard_command)
    # ------------------------------------------------------------------
    def enter(self) -> Any:
        """Press the Enter/Return key."""
        return self.keyboard_command("Enter")

    def tab(self) -> Any:
        """Press the Tab key (move to the next field)."""
        return self.keyboard_command("Tab")

    def shift_tab(self) -> Any:
        """Press Shift+Tab (move to the previous field)."""
        return self.keyboard_command("Shift+Tab")

    def esc(self) -> Any:
        """Press the Escape key."""
        return self.keyboard_command("Escape")

    def space(self) -> Any:
        """Press the Spacebar."""
        return self.keyboard_command("Space")

    def backspace(self) -> Any:
        """Press the Backspace key (delete the character to the left)."""
        return self.keyboard_command("Backspace")

    def delete(self) -> Any:
        """Press the Delete key (delete the character to the right)."""
        return self.keyboard_command("Delete")

    def key_up(self) -> Any:
        """Press the Up arrow key."""
        return self.keyboard_command("Arrow Up")

    def key_down(self) -> Any:
        """Press the Down arrow key."""
        return self.keyboard_command("Arrow Down")

    def key_left(self) -> Any:
        """Press the Left arrow key."""
        return self.keyboard_command("Arrow Left")

    def key_right(self) -> Any:
        """Press the Right arrow key."""
        return self.keyboard_command("Arrow Right")

    def page_up(self) -> Any:
        """Press the Page Up key."""
        return self.keyboard_command("Page Up")

    def page_down(self) -> Any:
        """Press the Page Down key."""
        return self.keyboard_command("Page Down")

    def home(self) -> Any:
        """Press the Home key."""
        return self.keyboard_command("Home")

    def end(self) -> Any:
        """Press the End key."""
        return self.keyboard_command("End")

    # ------------------------------------------------------------------
    # Function keys (F1 - F12) (delegate to keyboard_command)
    # ------------------------------------------------------------------
    def key_f1(self) -> Any:
        """Press the F1 key."""
        return self.keyboard_command("F1")

    def key_f2(self) -> Any:
        """Press the F2 key."""
        return self.keyboard_command("F2")

    def key_f3(self) -> Any:
        """Press the F3 key."""
        return self.keyboard_command("F3")

    def key_f4(self) -> Any:
        """Press the F4 key."""
        return self.keyboard_command("F4")

    def key_f5(self) -> Any:
        """Press the F5 key."""
        return self.keyboard_command("F5")

    def key_f6(self) -> Any:
        """Press the F6 key."""
        return self.keyboard_command("F6")

    def key_f7(self) -> Any:
        """Press the F7 key."""
        return self.keyboard_command("F7")

    def key_f8(self) -> Any:
        """Press the F8 key."""
        return self.keyboard_command("F8")

    def key_f9(self) -> Any:
        """Press the F9 key."""
        return self.keyboard_command("F9")

    def key_f10(self) -> Any:
        """Press the F10 key."""
        return self.keyboard_command("F10")

    def key_f11(self) -> Any:
        """Press the F11 key."""
        return self.keyboard_command("F11")

    def key_f12(self) -> Any:
        """Press the F12 key."""
        return self.keyboard_command("F12")

    # ------------------------------------------------------------------
    # Shortcuts (hotkeys) (delegate to keyboard_command)
    # ------------------------------------------------------------------
    def control_c(self) -> Any:
        """Press Ctrl+C (copy)."""
        return self.keyboard_command("Ctrl+C")

    def control_v(self) -> Any:
        """Press Ctrl+V (paste)."""
        return self.keyboard_command("Ctrl+V")

    def control_x(self) -> Any:
        """Press Ctrl+X (cut)."""
        return self.keyboard_command("Ctrl+X")

    def control_a(self) -> Any:
        """Press Ctrl+A (select all)."""
        return self.keyboard_command("Ctrl+A")

    def control_s(self) -> Any:
        """Press Ctrl+S (save)."""
        return self.keyboard_command("Ctrl+S")

    def control_z(self) -> Any:
        """Press Ctrl+Z (undo)."""
        return self.keyboard_command("Ctrl+Z")

    def control_y(self) -> Any:
        """Press Ctrl+Y (redo)."""
        return self.keyboard_command("Ctrl+Y")

    def control_f(self) -> Any:
        """Press Ctrl+F (find)."""
        return self.keyboard_command("Ctrl+F")

    def control_p(self) -> Any:
        """Press Ctrl+P (print)."""
        return self.keyboard_command("Ctrl+P")

    def alt_tab(self) -> Any:
        """Press Alt+Tab (switch windows)."""
        return self.keyboard_command("Alt+Tab")

    def alt_f4(self) -> Any:
        """Press Alt+F4 (close the active window)."""
        return self.keyboard_command("Alt+F4")

    # ------------------------------------------------------------------
    # Modifier hold / release (primitives; talk to pyautogui directly)
    # ------------------------------------------------------------------
    def hold_shift(self) -> None:
        """Hold the Shift key down (release it later with :meth:`release_shift`).

        Low-level primitive: holding a modifier across presses is not a named
        command, so this calls ``pyautogui`` directly.
        """
        import pyautogui

        pyautogui.keyDown("shift")

    def release_shift(self) -> None:
        """Release the Shift key previously held with :meth:`hold_shift`.

        Low-level primitive that calls ``pyautogui`` directly.
        """
        import pyautogui

        pyautogui.keyUp("shift")

    def hold_ctrl(self) -> None:
        """Hold the Ctrl key down (release it later with :meth:`release_ctrl`).

        Low-level primitive: holding a modifier across presses is not a named
        command, so this calls ``pyautogui`` directly.
        """
        import pyautogui

        pyautogui.keyDown("ctrl")

    def release_ctrl(self) -> None:
        """Release the Ctrl key previously held with :meth:`hold_ctrl`.

        Low-level primitive that calls ``pyautogui`` directly.
        """
        import pyautogui

        pyautogui.keyUp("ctrl")

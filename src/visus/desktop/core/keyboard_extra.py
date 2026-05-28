"""Visus Desktop - Named keyboard helpers.

A mixin that mirrors BotCity's rich, named keyboard API (``enter``, ``tab``,
``control_c``, ``key_f1`` .. ``key_f12``, etc.) without duplicating the existing
keyboard system. Each named shortcut is a thin one-liner that delegates to
``self.keyboard_command("<Command>", delay=delay, backtrack=backtrack)`` -- the
single source of truth being the command map owned by
:class:`visus.desktop.core.keyboard_commands.KeyboardCommander`. This keeps the
method names reading like intentions while ensuring there is exactly one place
that knows how a command maps to real keystrokes.

Every delegating method accepts two optional keyword arguments, ``delay`` and
``backtrack``, which are forwarded verbatim to ``keyboard_command``. This lets
callers tune how the underlying ``KeyboardCommander`` paces each command (for
example, adding a small delay between modifier and key, or backtracking on
failure) without having to drop down to ``keyboard_command`` directly.

The mixin assumes the host class provides a ``keyboard_command`` method.
:class:`visus.desktop.VisusBot` does, so mixing this into the bot is enough.

A small set of methods remain *low-level primitives* that talk to ``pyautogui``
directly: :meth:`type_key`, :meth:`key_combo`, :meth:`hold_shift`,
:meth:`release_shift`, :meth:`hold_ctrl` and :meth:`release_ctrl`. These are not
present in the ``KeyboardCommander`` map (holding/releasing a modifier across
several presses, or pressing/combining arbitrary keys, is not a fixed named
command), so they are not duplication. They import ``pyautogui`` lazily, which
keeps the module importable in headless environments (for example CI runners)
where ``pyautogui`` cannot initialize a display. Because they do not go through
``keyboard_command``, the primitives do NOT accept ``delay`` or ``backtrack``.

Example:
    >>> from visus.desktop.core.keyboard_extra import KeyboardMixin
    >>>
    >>> class Bot(KeyboardMixin):
    ...     def keyboard_command(self, command, delay=0, backtrack=False):
    ...         ...  # provided by VisusBot in real usage
    >>>
    >>> bot = Bot()
    >>> bot.enter()                          # -> keyboard_command("Enter", 0, False)
    >>> bot.control_c(delay=0.2)             # -> keyboard_command("Ctrl+C", 0.2, False)
    >>> bot.key_f5(backtrack=True)           # -> keyboard_command("F5", 0, True)
    >>> bot.type_key("h")                    # primitive: pyautogui.press("h")
    >>> bot.hold_shift()                     # primitive: pyautogui.keyDown("shift")
    >>> bot.release_shift()                  # primitive: pyautogui.keyUp("shift")
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
      ``self.keyboard_command("<Command>", delay=delay, backtrack=backtrack)``.
      The ``KeyboardCommander`` command map is the single source of truth for
      how each command is performed, so these methods never duplicate that
      logic -- they only translate a friendly method name into the canonical
      command string. They all accept ``delay: float = 0`` and
      ``backtrack: bool = False``, forwarded as-is to ``keyboard_command``.
    * **Primitives** (:meth:`type_key`, :meth:`key_combo`, :meth:`hold_shift`,
      :meth:`release_shift`, :meth:`hold_ctrl`, :meth:`release_ctrl`) call
      ``pyautogui`` directly. They are *not* part of the command map, so they
      are not duplication; ``pyautogui`` is imported lazily inside each one.
      They do NOT accept ``delay``/``backtrack`` because they never reach
      ``keyboard_command``.

    Example:
        >>> bot.control_a()                # select all
        >>> bot.control_c(delay=0.1)       # copy with a 0.1s delay
        >>> bot.tab(backtrack=True)        # next field with backtrack on failure
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
    def enter(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Enter/Return key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Enter", delay=delay, backtrack=backtrack)

    def tab(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Tab key (move to the next field).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Tab", delay=delay, backtrack=backtrack)

    def shift_tab(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Shift+Tab (move to the previous field).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Shift+Tab", delay=delay, backtrack=backtrack)

    def esc(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Escape key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Escape", delay=delay, backtrack=backtrack)

    def space(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Spacebar.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Space", delay=delay, backtrack=backtrack)

    def backspace(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Backspace key (delete the character to the left).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Backspace", delay=delay, backtrack=backtrack)

    def delete(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Delete key (delete the character to the right).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Delete", delay=delay, backtrack=backtrack)

    def key_up(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Up arrow key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Arrow Up", delay=delay, backtrack=backtrack)

    def key_down(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Down arrow key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Arrow Down", delay=delay, backtrack=backtrack)

    def key_left(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Left arrow key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Arrow Left", delay=delay, backtrack=backtrack)

    def key_right(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Right arrow key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Arrow Right", delay=delay, backtrack=backtrack)

    def page_up(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Page Up key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Page Up", delay=delay, backtrack=backtrack)

    def page_down(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Page Down key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Page Down", delay=delay, backtrack=backtrack)

    def home(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the Home key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Home", delay=delay, backtrack=backtrack)

    def end(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the End key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("End", delay=delay, backtrack=backtrack)

    # ------------------------------------------------------------------
    # Function keys (F1 - F12) (delegate to keyboard_command)
    # ------------------------------------------------------------------
    def key_f1(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F1 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F1", delay=delay, backtrack=backtrack)

    def key_f2(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F2 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F2", delay=delay, backtrack=backtrack)

    def key_f3(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F3 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F3", delay=delay, backtrack=backtrack)

    def key_f4(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F4 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F4", delay=delay, backtrack=backtrack)

    def key_f5(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F5 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F5", delay=delay, backtrack=backtrack)

    def key_f6(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F6 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F6", delay=delay, backtrack=backtrack)

    def key_f7(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F7 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F7", delay=delay, backtrack=backtrack)

    def key_f8(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F8 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F8", delay=delay, backtrack=backtrack)

    def key_f9(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F9 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F9", delay=delay, backtrack=backtrack)

    def key_f10(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F10 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F10", delay=delay, backtrack=backtrack)

    def key_f11(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F11 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F11", delay=delay, backtrack=backtrack)

    def key_f12(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press the F12 key.

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("F12", delay=delay, backtrack=backtrack)

    # ------------------------------------------------------------------
    # Shortcuts (hotkeys) (delegate to keyboard_command)
    # ------------------------------------------------------------------
    def control_c(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+C (copy).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+C", delay=delay, backtrack=backtrack)

    def control_v(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+V (paste).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+V", delay=delay, backtrack=backtrack)

    def control_x(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+X (cut).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+X", delay=delay, backtrack=backtrack)

    def control_a(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+A (select all).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+A", delay=delay, backtrack=backtrack)

    def control_s(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+S (save).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+S", delay=delay, backtrack=backtrack)

    def control_z(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+Z (undo).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+Z", delay=delay, backtrack=backtrack)

    def control_y(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+Y (redo).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+Y", delay=delay, backtrack=backtrack)

    def control_f(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+F (find).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+F", delay=delay, backtrack=backtrack)

    def control_p(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Ctrl+P (print).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Ctrl+P", delay=delay, backtrack=backtrack)

    def alt_tab(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Alt+Tab (switch windows).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Alt+Tab", delay=delay, backtrack=backtrack)

    def alt_f4(self, delay: float = 0, backtrack: bool = False) -> Any:
        """Press Alt+F4 (close the active window).

        Args:
            delay: Forwarded to ``keyboard_command``.
            backtrack: Forwarded to ``keyboard_command``.
        """
        return self.keyboard_command("Alt+F4", delay=delay, backtrack=backtrack)

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

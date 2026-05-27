"""Visus Desktop - Named keyboard helpers.

A self-contained mixin that mirrors BotCity's rich, named keyboard API
(``enter``, ``tab``, ``control_c``, ``key_f1`` .. ``key_f12``, etc.). Each
method is a thin one-liner that delegates to ``pyautogui.press`` or
``pyautogui.hotkey``, so the names read like intentions rather than raw key
strings.

``pyautogui`` is imported lazily inside every method. This keeps the module
importable in headless environments (for example CI runners) where
``pyautogui`` cannot initialize a display, and ensures importing the mixin
never triggers any GUI side effects.

Example:
    >>> import pyautogui
    >>> from visus.desktop.core.keyboard_extra import KeyboardMixin
    >>>
    >>> class Bot(KeyboardMixin):
    ...     '''A bot that can type and trigger shortcuts.'''
    >>>
    >>> bot = Bot()
    >>> bot.type_key("h")        # pyautogui.press("h")
    >>> bot.enter()              # pyautogui.press("enter")
    >>> bot.control_c()          # pyautogui.hotkey("ctrl", "c")
    >>> bot.key_f5()             # pyautogui.press("f5")
    >>> bot.hold_shift()         # pyautogui.keyDown("shift")
    >>> bot.key_down()           # pyautogui.press("down")
    >>> bot.release_shift()      # pyautogui.keyUp("shift")
"""

from __future__ import annotations


class KeyboardMixin:
    """Mixin providing a rich, named keyboard API on top of ``pyautogui``.

    Mix this into any class to gain expressive, self-documenting keyboard
    methods such as :meth:`enter`, :meth:`tab`, :meth:`control_c` and
    :meth:`key_f5`. Methods either *press* a single key or fire a *hotkey*
    combination; the modifier helpers (:meth:`hold_shift`, :meth:`hold_ctrl`
    and their ``release_*`` counterparts) let you build custom combinations by
    holding a modifier across several presses.

    All methods import ``pyautogui`` lazily, so importing this mixin has no GUI
    side effects and works in headless environments.

    Example:
        >>> class Bot(KeyboardMixin):
        ...     pass
        >>> bot = Bot()
        >>> bot.control_a()   # select all -> pyautogui.hotkey("ctrl", "a")
        >>> bot.control_c()   # copy       -> pyautogui.hotkey("ctrl", "c")
        >>> bot.tab()         # next field -> pyautogui.press("tab")
    """

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def type_key(self, key: str) -> None:
        """Press a single key by its ``pyautogui`` name.

        Args:
            key: The ``pyautogui`` key name to press (for example ``"a"``,
                ``"enter"`` or ``"f5"``).
        """
        import pyautogui

        pyautogui.press(key)

    def key_combo(self, *keys: str) -> None:
        """Press several keys together as a hotkey combination.

        The keys are pressed down in order and released in reverse order, which
        is the standard way to express shortcuts such as ``Ctrl+Alt+Del``.

        Args:
            *keys: The ``pyautogui`` key names to combine (for example
                ``"ctrl", "alt", "del"``).
        """
        import pyautogui

        pyautogui.hotkey(*keys)

    # ------------------------------------------------------------------
    # Navigation and editing
    # ------------------------------------------------------------------
    def enter(self) -> None:
        """Press the Enter/Return key."""
        import pyautogui

        pyautogui.press("enter")

    def tab(self) -> None:
        """Press the Tab key (move to the next field)."""
        import pyautogui

        pyautogui.press("tab")

    def shift_tab(self) -> None:
        """Press Shift+Tab (move to the previous field)."""
        import pyautogui

        pyautogui.hotkey("shift", "tab")

    def esc(self) -> None:
        """Press the Escape key."""
        import pyautogui

        pyautogui.press("esc")

    def space(self) -> None:
        """Press the Spacebar."""
        import pyautogui

        pyautogui.press("space")

    def backspace(self) -> None:
        """Press the Backspace key (delete the character to the left)."""
        import pyautogui

        pyautogui.press("backspace")

    def delete(self) -> None:
        """Press the Delete key (delete the character to the right)."""
        import pyautogui

        pyautogui.press("delete")

    def key_up(self) -> None:
        """Press the Up arrow key."""
        import pyautogui

        pyautogui.press("up")

    def key_down(self) -> None:
        """Press the Down arrow key."""
        import pyautogui

        pyautogui.press("down")

    def key_left(self) -> None:
        """Press the Left arrow key."""
        import pyautogui

        pyautogui.press("left")

    def key_right(self) -> None:
        """Press the Right arrow key."""
        import pyautogui

        pyautogui.press("right")

    def page_up(self) -> None:
        """Press the Page Up key."""
        import pyautogui

        pyautogui.press("pageup")

    def page_down(self) -> None:
        """Press the Page Down key."""
        import pyautogui

        pyautogui.press("pagedown")

    def home(self) -> None:
        """Press the Home key."""
        import pyautogui

        pyautogui.press("home")

    def end(self) -> None:
        """Press the End key."""
        import pyautogui

        pyautogui.press("end")

    # ------------------------------------------------------------------
    # Function keys (F1 - F12)
    # ------------------------------------------------------------------
    def key_f1(self) -> None:
        """Press the F1 key."""
        import pyautogui

        pyautogui.press("f1")

    def key_f2(self) -> None:
        """Press the F2 key."""
        import pyautogui

        pyautogui.press("f2")

    def key_f3(self) -> None:
        """Press the F3 key."""
        import pyautogui

        pyautogui.press("f3")

    def key_f4(self) -> None:
        """Press the F4 key."""
        import pyautogui

        pyautogui.press("f4")

    def key_f5(self) -> None:
        """Press the F5 key."""
        import pyautogui

        pyautogui.press("f5")

    def key_f6(self) -> None:
        """Press the F6 key."""
        import pyautogui

        pyautogui.press("f6")

    def key_f7(self) -> None:
        """Press the F7 key."""
        import pyautogui

        pyautogui.press("f7")

    def key_f8(self) -> None:
        """Press the F8 key."""
        import pyautogui

        pyautogui.press("f8")

    def key_f9(self) -> None:
        """Press the F9 key."""
        import pyautogui

        pyautogui.press("f9")

    def key_f10(self) -> None:
        """Press the F10 key."""
        import pyautogui

        pyautogui.press("f10")

    def key_f11(self) -> None:
        """Press the F11 key."""
        import pyautogui

        pyautogui.press("f11")

    def key_f12(self) -> None:
        """Press the F12 key."""
        import pyautogui

        pyautogui.press("f12")

    # ------------------------------------------------------------------
    # Shortcuts (hotkeys)
    # ------------------------------------------------------------------
    def control_c(self) -> None:
        """Press Ctrl+C (copy)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "c")

    def control_v(self) -> None:
        """Press Ctrl+V (paste)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "v")

    def control_x(self) -> None:
        """Press Ctrl+X (cut)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "x")

    def control_a(self) -> None:
        """Press Ctrl+A (select all)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "a")

    def control_s(self) -> None:
        """Press Ctrl+S (save)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "s")

    def control_z(self) -> None:
        """Press Ctrl+Z (undo)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "z")

    def control_y(self) -> None:
        """Press Ctrl+Y (redo)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "y")

    def control_f(self) -> None:
        """Press Ctrl+F (find)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "f")

    def control_p(self) -> None:
        """Press Ctrl+P (print)."""
        import pyautogui

        pyautogui.hotkey("ctrl", "p")

    def alt_tab(self) -> None:
        """Press Alt+Tab (switch windows)."""
        import pyautogui

        pyautogui.hotkey("alt", "tab")

    def alt_f4(self) -> None:
        """Press Alt+F4 (close the active window)."""
        import pyautogui

        pyautogui.hotkey("alt", "f4")

    # ------------------------------------------------------------------
    # Modifier hold / release
    # ------------------------------------------------------------------
    def hold_shift(self) -> None:
        """Hold the Shift key down (release it later with :meth:`release_shift`)."""
        import pyautogui

        pyautogui.keyDown("shift")

    def release_shift(self) -> None:
        """Release the Shift key previously held with :meth:`hold_shift`."""
        import pyautogui

        pyautogui.keyUp("shift")

    def hold_ctrl(self) -> None:
        """Hold the Ctrl key down (release it later with :meth:`release_ctrl`)."""
        import pyautogui

        pyautogui.keyDown("ctrl")

    def release_ctrl(self) -> None:
        """Release the Ctrl key previously held with :meth:`hold_ctrl`."""
        import pyautogui

        pyautogui.keyUp("ctrl")

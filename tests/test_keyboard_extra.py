"""Tests for ``visus.desktop.core.keyboard_extra``.

The named shortcut methods delegate to
``self.keyboard_command("<Command>", delay=..., backtrack=...)`` (the single
source of truth being :class:`KeyboardCommander`'s command map), so they are
tested against a fake host that records the ``(command, delay, backtrack)``
tuples it receives. The low-level primitives talk to ``pyautogui`` directly, so
they are tested by monkeypatching the relevant ``pyautogui`` entry points -- no
real keystrokes are ever sent to the host system.
"""

from __future__ import annotations

import pyautogui
import pytest

from visus.desktop.core.keyboard_commands import KeyboardCommander
from visus.desktop.core.keyboard_extra import KeyboardMixin


class _Bot(KeyboardMixin):
    """Minimal host recording the commands its named methods delegate."""

    def __init__(self) -> None:
        # Each entry is a ``(command, delay, backtrack)`` tuple, capturing the
        # full call shape the delegating methods must forward.
        self.commands: list[tuple[str, float, bool]] = []

    def keyboard_command(
        self, command: str, delay: float = 0, backtrack: bool = False
    ) -> bool:
        self.commands.append((command, delay, backtrack))
        return True


# Maps each delegating method name -> the exact command string it must record.
# This is the contract: calling the method delegates to keyboard_command(<str>).
_DELEGATING_COMMANDS: dict[str, str] = {
    # Navigation and editing
    "enter": "Enter",
    "tab": "Tab",
    "shift_tab": "Shift+Tab",
    "esc": "Escape",
    "space": "Space",
    "backspace": "Backspace",
    "delete": "Delete",
    "key_up": "Arrow Up",
    "key_down": "Arrow Down",
    "key_left": "Arrow Left",
    "key_right": "Arrow Right",
    "page_up": "Page Up",
    "page_down": "Page Down",
    "home": "Home",
    "end": "End",
    # Function keys F1..F12
    "key_f1": "F1",
    "key_f2": "F2",
    "key_f3": "F3",
    "key_f4": "F4",
    "key_f5": "F5",
    "key_f6": "F6",
    "key_f7": "F7",
    "key_f8": "F8",
    "key_f9": "F9",
    "key_f10": "F10",
    "key_f11": "F11",
    "key_f12": "F12",
    # Shortcuts (hotkeys)
    "control_c": "Ctrl+C",
    "control_v": "Ctrl+V",
    "control_x": "Ctrl+X",
    "control_a": "Ctrl+A",
    "control_s": "Ctrl+S",
    "control_z": "Ctrl+Z",
    "control_y": "Ctrl+Y",
    "control_f": "Ctrl+F",
    "control_p": "Ctrl+P",
    "alt_tab": "Alt+Tab",
    "alt_f4": "Alt+F4",
}

# Public method names that are NOT delegating shortcuts: the contract method the
# host supplies, plus the low-level primitives that talk to pyautogui directly.
_NON_DELEGATING = {
    "keyboard_command",
    "type_key",
    "key_combo",
    "hold_shift",
    "release_shift",
    "hold_ctrl",
    "release_ctrl",
}


# ----------------------------------------------------------------------
# Delegating named shortcuts
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "method_name, expected_command",
    list(_DELEGATING_COMMANDS.items()),
    ids=list(_DELEGATING_COMMANDS),
)
def test_named_method_delegates_with_defaults(
    method_name: str, expected_command: str
) -> None:
    """Each named method records ``(<command>, 0, False)`` when called with no args."""
    bot = _Bot()

    getattr(bot, method_name)()

    assert bot.commands == [(expected_command, 0, False)]


@pytest.mark.parametrize(
    "method_name, expected_command",
    list(_DELEGATING_COMMANDS.items()),
    ids=list(_DELEGATING_COMMANDS),
)
def test_named_method_forwards_delay_and_backtrack(
    method_name: str, expected_command: str
) -> None:
    """Each named method forwards ``delay`` and ``backtrack`` to ``keyboard_command``."""
    bot = _Bot()

    getattr(bot, method_name)(delay=0.5, backtrack=True)

    assert bot.commands == [(expected_command, 0.5, True)]


def test_every_delegating_method_is_covered() -> None:
    """Guard: every public delegating method appears in the table above.

    If a new named shortcut is added to the mixin it must also be added to
    ``_DELEGATING_COMMANDS``; otherwise this test fails. Non-delegating public
    members (the ``keyboard_command`` contract method and the primitives) are
    explicitly excluded.
    """
    public_methods = {
        name
        for name in dir(KeyboardMixin)
        if not name.startswith("_") and callable(getattr(KeyboardMixin, name))
    }
    delegating = public_methods - _NON_DELEGATING

    assert delegating == set(_DELEGATING_COMMANDS)


# ----------------------------------------------------------------------
# Low-level primitives (talk to pyautogui directly)
# ----------------------------------------------------------------------
@pytest.fixture
def recorder(monkeypatch):
    """Patch ``pyautogui`` key functions and record their calls.

    Returns a dict with ``press``, ``hotkey``, ``keyDown`` and ``keyUp`` keys,
    each holding the list of positional-argument tuples captured.
    """
    calls: dict[str, list] = {
        "press": [],
        "hotkey": [],
        "keyDown": [],
        "keyUp": [],
    }
    monkeypatch.setattr(pyautogui, "press", lambda *a, **k: calls["press"].append(a))
    monkeypatch.setattr(pyautogui, "hotkey", lambda *a, **k: calls["hotkey"].append(a))
    monkeypatch.setattr(
        pyautogui, "keyDown", lambda *a, **k: calls["keyDown"].append(a)
    )
    monkeypatch.setattr(pyautogui, "keyUp", lambda *a, **k: calls["keyUp"].append(a))
    return calls


def test_type_key_presses_via_pyautogui(recorder):
    """``type_key`` forwards the key name to ``pyautogui.press``."""
    bot = _Bot()
    bot.type_key("a")
    assert recorder["press"] == [("a",)]
    assert recorder["hotkey"] == []
    assert bot.commands == []  # did not touch keyboard_command


def test_key_combo_hotkeys_via_pyautogui(recorder):
    """``key_combo`` forwards every key to ``pyautogui.hotkey``."""
    bot = _Bot()
    bot.key_combo("ctrl", "alt", "del")
    assert recorder["hotkey"] == [("ctrl", "alt", "del")]
    assert recorder["press"] == []
    assert bot.commands == []


def test_hold_shift_keydown_via_pyautogui(recorder):
    """``hold_shift`` holds Shift down via ``pyautogui.keyDown``."""
    bot = _Bot()
    bot.hold_shift()
    assert recorder["keyDown"] == [("shift",)]
    assert recorder["keyUp"] == []
    assert bot.commands == []


def test_release_shift_keyup_via_pyautogui(recorder):
    """``release_shift`` releases Shift via ``pyautogui.keyUp``."""
    bot = _Bot()
    bot.release_shift()
    assert recorder["keyUp"] == [("shift",)]
    assert recorder["keyDown"] == []
    assert bot.commands == []


def test_hold_ctrl_keydown_via_pyautogui(recorder):
    """``hold_ctrl`` holds Ctrl down via ``pyautogui.keyDown``."""
    bot = _Bot()
    bot.hold_ctrl()
    assert recorder["keyDown"] == [("ctrl",)]
    assert recorder["keyUp"] == []
    assert bot.commands == []


def test_release_ctrl_keyup_via_pyautogui(recorder):
    """``release_ctrl`` releases Ctrl via ``pyautogui.keyUp``."""
    bot = _Bot()
    bot.release_ctrl()
    assert recorder["keyUp"] == [("ctrl",)]
    assert recorder["keyDown"] == []
    assert bot.commands == []


def test_primitives_do_not_touch_keyboard_command(recorder):
    """A sequence of primitives never delegates to ``keyboard_command``."""
    bot = _Bot()
    bot.type_key("x")
    bot.hold_ctrl()
    bot.release_ctrl()
    assert bot.commands == []
    total = sum(len(v) for v in recorder.values())
    assert total == 3


# ----------------------------------------------------------------------
# Integration: delegation can't silently break against the real command map
# ----------------------------------------------------------------------
def test_all_delegated_commands_exist_in_commander_map() -> None:
    """Every command string the named methods use is a real, available command.

    This pins the mixin's delegation to the actual ``KeyboardCommander`` map, so
    a rename or removal there (or a typo in the mixin) is caught immediately.
    """
    available = set(KeyboardCommander().get_available_commands())
    used = set(_DELEGATING_COMMANDS.values())
    missing = used - available
    assert missing == set(), f"Commands missing from KeyboardCommander map: {missing}"

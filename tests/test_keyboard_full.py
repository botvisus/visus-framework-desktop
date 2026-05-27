"""Exhaustive delegation tests for ``visus.desktop.core.keyboard_extra``.

Every :class:`KeyboardMixin` method is exercised through a parametrized table
that maps the method name to the expected ``pyautogui`` call (function name and
positional arguments). All four ``pyautogui`` entry points used by the mixin
(``press``, ``hotkey``, ``keyDown``, ``keyUp``) are monkeypatched so that no real
keystrokes are ever sent to the host system.
"""

from __future__ import annotations

# Fully warm up cv2 before pyautogui/pyscreeze (and pytest-cov's import hooks)
# touch it. This venv ships a cv2 build whose lazy ``cv2.typing`` module
# references ``cv2.gapi.wip.draw.Text`` during a partial import; under coverage
# the import ordering can otherwise hit that half-initialized state and raise
# AttributeError. Importing it eagerly here resolves it once, cleanly.
try:  # pragma: no cover - environment shim, not part of the tested code
    import cv2  # noqa: F401
    import cv2.typing  # noqa: F401
except Exception:  # pragma: no cover - cv2 is optional at import time
    pass

import pyautogui
import pytest

from visus.desktop.core.capabilities import CapabilitiesMixin
from visus.desktop.core.keyboard_extra import KeyboardMixin


class _Bot(CapabilitiesMixin, KeyboardMixin):
    """Minimal host combining both mixins (no Tesseract/VisusBot needed)."""


@pytest.fixture
def recorder(monkeypatch):
    """Patch the ``pyautogui`` key functions and record their calls.

    Returns a mapping with ``press``, ``hotkey``, ``keyDown`` and ``keyUp``
    keys, each holding the list of positional-argument tuples captured for that
    function.
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


# Each entry: (method_name, args_for_method, expected_pyautogui_func, expected_args)
_CASES = [
    # --- Navigation and editing: single-key presses ---
    ("enter", (), "press", ("enter",)),
    ("esc", (), "press", ("esc",)),
    ("space", (), "press", ("space",)),
    ("backspace", (), "press", ("backspace",)),
    ("delete", (), "press", ("delete",)),
    ("tab", (), "press", ("tab",)),
    ("key_up", (), "press", ("up",)),
    ("key_down", (), "press", ("down",)),
    ("key_left", (), "press", ("left",)),
    ("key_right", (), "press", ("right",)),
    ("page_up", (), "press", ("pageup",)),
    ("page_down", (), "press", ("pagedown",)),
    ("home", (), "press", ("home",)),
    ("end", (), "press", ("end",)),
    # --- Function keys F1..F12 ---
    ("key_f1", (), "press", ("f1",)),
    ("key_f2", (), "press", ("f2",)),
    ("key_f3", (), "press", ("f3",)),
    ("key_f4", (), "press", ("f4",)),
    ("key_f5", (), "press", ("f5",)),
    ("key_f6", (), "press", ("f6",)),
    ("key_f7", (), "press", ("f7",)),
    ("key_f8", (), "press", ("f8",)),
    ("key_f9", (), "press", ("f9",)),
    ("key_f10", (), "press", ("f10",)),
    ("key_f11", (), "press", ("f11",)),
    ("key_f12", (), "press", ("f12",)),
    # --- Hotkey shortcuts ---
    ("control_c", (), "hotkey", ("ctrl", "c")),
    ("control_v", (), "hotkey", ("ctrl", "v")),
    ("control_x", (), "hotkey", ("ctrl", "x")),
    ("control_a", (), "hotkey", ("ctrl", "a")),
    ("control_s", (), "hotkey", ("ctrl", "s")),
    ("control_z", (), "hotkey", ("ctrl", "z")),
    ("control_y", (), "hotkey", ("ctrl", "y")),
    ("control_f", (), "hotkey", ("ctrl", "f")),
    ("control_p", (), "hotkey", ("ctrl", "p")),
    ("shift_tab", (), "hotkey", ("shift", "tab")),
    ("alt_tab", (), "hotkey", ("alt", "tab")),
    ("alt_f4", (), "hotkey", ("alt", "f4")),
    # --- Modifier hold / release ---
    ("hold_shift", (), "keyDown", ("shift",)),
    ("release_shift", (), "keyUp", ("shift",)),
    ("hold_ctrl", (), "keyDown", ("ctrl",)),
    ("release_ctrl", (), "keyUp", ("ctrl",)),
    # --- Generic helpers ---
    ("type_key", ("q",), "press", ("q",)),
    ("key_combo", ("ctrl", "alt", "del"), "hotkey", ("ctrl", "alt", "del")),
]


@pytest.mark.parametrize(
    "method_name, method_args, expected_func, expected_args",
    _CASES,
    ids=[c[0] for c in _CASES],
)
def test_keyboard_method_delegation(
    recorder, method_name, method_args, expected_func, expected_args
):
    """Each mixin method triggers exactly one matching ``pyautogui`` call."""
    bot = _Bot()

    getattr(bot, method_name)(*method_args)

    # The expected pyautogui function was called once with the expected args.
    assert recorder[expected_func] == [expected_args]

    # No other pyautogui function was triggered.
    for func_name, recorded in recorder.items():
        if func_name != expected_func:
            assert recorded == [], (
                f"{method_name} unexpectedly called pyautogui.{func_name}"
            )


def test_every_public_method_is_covered():
    """Guard: every public KeyboardMixin method appears in the case table.

    This keeps the parametrized table honest -- if a new keyboard method is
    added to the mixin it must also be added here, otherwise this test fails.
    """
    covered = {case[0] for case in _CASES}
    public_methods = {
        name
        for name in dir(KeyboardMixin)
        if not name.startswith("_") and callable(getattr(KeyboardMixin, name))
    }
    assert public_methods == covered

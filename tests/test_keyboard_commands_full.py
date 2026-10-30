"""Full coverage for ``visus.desktop.core.keyboard_commands``.

Targets the missing line ranges 194-206 (execute_command branches),
228-235 (type_text), 247-311 (process_sendtext_command branches).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from visus.desktop.core.keyboard_commands import KeyboardCommander
from visus.desktop.exceptions import TaskExecutionError


@pytest.fixture
def commander():
    return KeyboardCommander()


class TestExecuteCommand:
    def test_known_command_invokes_mapping(self, commander):
        called = {"n": 0}
        commander.command_mapping["TestCmd"] = lambda: called.update(n=1)
        assert commander.execute_command("TestCmd") is True
        assert called["n"] == 1

    def test_unknown_command_returns_false(self, commander):
        assert commander.execute_command("NotARealCommand") is False

    def test_generic_chord_not_in_mapping_dispatches_hotkey(self, commander):
        # "Ctrl+Shift+S" isn't a hardcoded entry; the generic parser handles
        # it so scripts never need pyautogui directly.
        assert "Ctrl+Shift+S" not in commander.command_mapping
        with patch("pyautogui.hotkey") as hotkey:
            assert commander.execute_command("Ctrl+Shift+S") is True
        hotkey.assert_called_once_with("ctrl", "shift", "s")

    def test_chord_parser_normalizes_aliases_and_named_keys(self, commander):
        with patch("pyautogui.hotkey") as hotkey:
            assert commander.execute_command("Win+R") is True
            assert commander.execute_command("Control+Alt+Del") is True
        hotkey.assert_any_call("win", "r")
        hotkey.assert_any_call("ctrl", "alt", "delete")

    def test_invalid_chord_still_returns_false(self, commander):
        assert commander.execute_command("Ctrl+Banana") is False

    def test_a_key_alone_even_a_modifier(self, commander):
        """Alt alone opens Office's key tips; a lone letter answers them."""
        with patch("pyautogui.hotkey") as hotkey:
            assert commander.execute_command("Alt") is True
            assert commander.execute_command("H") is True
        assert [c.args for c in hotkey.call_args_list] == [("alt",), ("h",)]

    def test_sequence_presses_one_after_another(self, commander):
        with patch("pyautogui.hotkey") as hotkey,                 patch("visus.desktop.core.keyboard_commands.time.sleep"):
            assert commander.execute_command("Alt, H, O, I") is True
        assert [c.args for c in hotkey.call_args_list] == [
            ("alt",), ("h",), ("o",), ("i",)
        ]

    @pytest.mark.parametrize(
        ("command", "keys"),
        [
            ("Ctrl+;", ("ctrl", ";")),
            ("Ctrl++", ("ctrl", "+")),
            ("Ctrl+Shift++", ("ctrl", "shift", "+")),
            ("Win+Shift+S", ("win", "shift", "s")),
            ("PrintScreen", ("printscreen",)),
            ("page up", ("pageup",)),
            ("Num5", ("num5",)),
            ("VolumeUp", ("volumeup",)),
            ("Control+Option+Escape", ("ctrl", "alt", "esc")),
            ("Ctrl+Comma", ("ctrl", ",")),
            ("ç", ("ç",)),
        ],
    )
    def test_any_key_or_chord_no_fixed_list(self, commander, command, keys):
        """Not a list: every pyautogui key name, any character, any combination."""
        assert command not in commander.command_mapping
        with patch("pyautogui.hotkey") as hotkey:
            assert commander.execute_command(command) is True
        hotkey.assert_called_once_with(*keys)

    def test_sequence_stops_at_an_unknown_step(self, commander):
        with patch("pyautogui.hotkey") as hotkey,                 patch("visus.desktop.core.keyboard_commands.time.sleep"):
            assert commander.execute_command("Alt, Banana, I") is False
        assert [c.args for c in hotkey.call_args_list] == [("alt",)]

    def test_exception_inside_mapping_raises_task_execution_error(self, commander):
        def explodes():
            raise RuntimeError("boom")

        commander.command_mapping["Boom"] = explodes
        with pytest.raises(TaskExecutionError, match="Error executing command 'Boom'"):
            commander.execute_command("Boom")


class TestGetAvailableCommands:
    def test_returns_list_of_keys(self, commander):
        cmds = commander.get_available_commands()
        assert isinstance(cmds, list)
        assert len(cmds) > 0


class TestTypeText:
    def test_calls_pyautogui_typewrite(self, commander):
        with patch(
            "visus.desktop.core.keyboard_commands.pyautogui.typewrite"
        ) as tw:
            commander.type_text("hello", interval=0.1)
        tw.assert_called_once_with("hello", interval=0.1)

    def test_typewrite_failure_raises_task_execution_error(self, commander):
        with patch(
            "visus.desktop.core.keyboard_commands.pyautogui.typewrite",
            side_effect=RuntimeError("device gone"),
        ):
            with pytest.raises(TaskExecutionError, match="Error typing text"):
                commander.type_text("hello")


class TestProcessSendtextCommand:
    """Each {special} prefix dispatches to the matching pyautogui call."""

    def _run(self, commander, text):
        with patch("pyautogui.hotkey") as hotkey, patch(
            "pyautogui.press"
        ) as press, patch("pyperclip.copy") as copy, patch(
            "time.sleep"
        ):
            commander.process_sendtext_command(text)
        return hotkey, press, copy

    def test_ctrl_a_dispatches_hotkey(self, commander):
        hotkey, _, _ = self._run(commander, "{ctrl}a")
        hotkey.assert_any_call("ctrl", "a")

    def test_del_presses_delete(self, commander):
        _, press, _ = self._run(commander, "{del}")
        press.assert_any_call("delete")

    def test_tab_presses_tab(self, commander):
        _, press, _ = self._run(commander, "{tab}")
        press.assert_any_call("tab")

    def test_enter_presses_enter(self, commander):
        _, press, _ = self._run(commander, "{enter}")
        press.assert_any_call("enter")

    def test_backspace_presses_backspace(self, commander):
        _, press, _ = self._run(commander, "{backspace}")
        press.assert_any_call("backspace")

    def test_escape_presses_escape(self, commander):
        _, press, _ = self._run(commander, "{escape}")
        press.assert_any_call("escape")

    def test_multiple_commands_processed_sequentially(self, commander):
        _, press, _ = self._run(commander, "{tab}{enter}")
        keys = [c.args[0] for c in press.call_args_list]
        assert "tab" in keys
        assert "enter" in keys

    def test_remaining_text_uses_clipboard_paste(self, commander):
        hotkey, _, copy = self._run(commander, "{ctrl}atext-to-paste")
        copy.assert_called_once_with("text-to-paste")
        # ctrl+v paste after copy.
        ctrl_v_calls = [
            call for call in hotkey.call_args_list if call.args == ("ctrl", "v")
        ]
        assert ctrl_v_calls

    def test_plain_text_only_uses_clipboard(self, commander):
        hotkey, _, copy = self._run(commander, "just-some-text")
        copy.assert_called_once_with("just-some-text")
        ctrl_v_calls = [
            call for call in hotkey.call_args_list if call.args == ("ctrl", "v")
        ]
        assert ctrl_v_calls

    def test_processing_failure_raises_task_execution_error(self, commander):
        with patch("pyautogui.press", side_effect=RuntimeError("noop")), patch(
            "time.sleep"
        ):
            with pytest.raises(TaskExecutionError, match="Error processing sendtext"):
                commander.process_sendtext_command("{tab}rest")

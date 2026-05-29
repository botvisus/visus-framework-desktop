"""Final coverage push.

One file per module section, hitting the remaining gaps in
session, locate, virtual_mouse, capabilities, task_executor, and the
biggest blocks of __init__.py (VisusBot wrappers).
"""

from __future__ import annotations

import zipfile
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.core import locate as _locate
from visus.desktop.core import session as _session
from visus.desktop.core.task_executor import TaskExecutor

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed",
)


# ===========================================================================
# session.py -- _write_zip ValueError branch + extract_screenshots
# ===========================================================================


class TestSessionWriteZip:
    def test_replay_missing_events_returns_empty(self, tmp_path):
        zp = tmp_path / "empty.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("readme.txt", "no events here")
        assert _session.Session.replay(zp) == []

    def test_write_zip_skips_invalid_json_line(self, tmp_path):
        zp = tmp_path / "rec.zip"
        _session._write_zip(zp, ["not-json", '{"a": 1}'])
        with zipfile.ZipFile(zp) as zf:
            names = zf.namelist()
        # Only the events file present; the bogus line did not crash.
        assert "events.jsonl" in names

    def test_extract_screenshots_writes_pngs(self, tmp_path):
        zp = tmp_path / "rec.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("events.jsonl", "")
            zf.writestr("screenshots/a.png", b"\x89PNG\r\n\x1a\nA")
            zf.writestr("screenshots/b.png", b"\x89PNG\r\n\x1a\nB")
            zf.writestr("readme.txt", "ignore")
        dest = tmp_path / "out"
        written = _session.extract_screenshots(zp, dest)
        assert len(written) == 2
        assert (dest / "a.png").exists()
        assert (dest / "b.png").exists()


# ===========================================================================
# locate.py -- find_all / find_multiple branches + helper edge cases
# ===========================================================================


class TestLocateHelpers:
    def test_box_to_tuple_from_namedtuple_like(self):
        box = MagicMock(left=1, top=2, width=3, height=4)
        assert _locate._box_to_tuple(box) == (1, 2, 3, 4)

    def test_box_to_tuple_from_iterable_fallback(self):
        assert _locate._box_to_tuple((10, 20, 30, 40)) == (10, 20, 30, 40)

    def test_is_not_found_exception_returns_false_when_pyautogui_lacks_attr(self):
        class FakePy:
            pass

        assert _locate._is_not_found_exception(FakePy(), RuntimeError("x")) is False

    def test_is_opencv_confidence_error_for_not_implemented(self):
        assert (
            _locate._is_opencv_confidence_error(
                NotImplementedError("OpenCV missing")
            )
            is True
        )

    def test_is_opencv_confidence_error_for_value_error_message(self):
        assert (
            _locate._is_opencv_confidence_error(ValueError("OpenCV required"))
            is True
        )

    def test_is_opencv_confidence_error_false_otherwise(self):
        assert _locate._is_opencv_confidence_error(KeyError("x")) is False


class TestFindAll:
    def test_returns_list_of_matches(self):
        matches = [MagicMock(left=0, top=0, width=10, height=10)]
        with patch("pyautogui.locateAllOnScreen", return_value=iter(matches)):
            out = _locate.find_all("a.png", confidence=0.9)
        assert len(out) == 1
        assert out[0] == (0, 0, 10, 10)

    def test_returns_empty_on_not_found_exception(self):
        import pyautogui

        not_found = getattr(pyautogui, "ImageNotFoundException", Exception)
        with patch(
            "pyautogui.locateAllOnScreen", side_effect=not_found("missing")
        ):
            assert _locate.find_all("a.png") == []

    def test_returns_empty_on_generic_failure(self):
        with patch("pyautogui.locateAllOnScreen", side_effect=RuntimeError("io")):
            assert _locate.find_all("a.png") == []


class TestFindMultiple:
    def test_dict_input_returns_dict(self):
        with patch.object(
            _locate, "_locate_one", return_value=(1, 2, 3, 4)
        ):
            out = _locate.find_multiple({"a": "a.png", "b": "b.png"})
        assert out == {"a": (1, 2, 3, 4), "b": (1, 2, 3, 4)}

    def test_iterable_input_returns_dict_keyed_by_path(self):
        with patch.object(_locate, "_locate_one", return_value=(0, 0, 1, 1)):
            out = _locate.find_multiple(["a.png", "b.png"])
        # find_multiple normalises any iterable into a {path: box} dict.
        assert out == {"a.png": (0, 0, 1, 1), "b.png": (0, 0, 1, 1)}


# ===========================================================================
# virtual_mouse.py -- platform / availability / fallback branches
# ===========================================================================


class TestVirtualMouseAvailability:
    def test_windows_path_with_win32_imports(self):
        from visus.desktop.core.virtual_mouse import VirtualMouse

        with patch.object(VirtualMouse, "_check_virtual_mouse_availability", return_value=True):
            vm = VirtualMouse(config=MagicMock(get=lambda k, d=None: d))
        assert vm.virtual_available is True

    def test_warns_when_use_virtual_mouse_but_unavailable(self, caplog):
        from visus.desktop.core.virtual_mouse import VirtualMouse

        cfg = MagicMock()
        cfg.get = MagicMock(
            side_effect=lambda k, d=None: True if k == "use_virtual_mouse" else d
        )
        with patch.object(
            VirtualMouse, "_check_virtual_mouse_availability", return_value=False
        ):
            VirtualMouse(config=cfg)
        # Two warnings expected: "not available" and "fallback".
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert warnings, "expected at least one warning when virtual mouse unavailable"


class TestVirtualMouseLinuxPath:
    def test_linux_returns_false(self):
        from visus.desktop.core.virtual_mouse import VirtualMouse

        vm = VirtualMouse.__new__(VirtualMouse)
        vm.system = "linux"
        assert vm._check_virtual_mouse_availability() is False

    def test_darwin_returns_false(self):
        from visus.desktop.core.virtual_mouse import VirtualMouse

        vm = VirtualMouse.__new__(VirtualMouse)
        vm.system = "darwin"
        assert vm._check_virtual_mouse_availability() is False

    def test_unknown_os_returns_false(self):
        from visus.desktop.core.virtual_mouse import VirtualMouse

        vm = VirtualMouse.__new__(VirtualMouse)
        vm.system = "haiku"
        assert vm._check_virtual_mouse_availability() is False


class TestVirtualMouseWindowsImportError:
    def test_returns_false_when_win32_missing(self):
        from visus.desktop.core.virtual_mouse import VirtualMouse

        vm = VirtualMouse.__new__(VirtualMouse)
        vm.system = "windows"
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name in ("win32api", "win32con", "win32gui"):
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            assert vm._check_virtual_mouse_availability() is False


# ===========================================================================
# capabilities.py -- the delegations
# ===========================================================================


@requires_tesseract
class TestCapabilitiesDelegations:
    """Pull each delegation through with patched module-level functions."""

    @pytest.fixture
    def bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_scroll_delegates(self, bot):
        with patch("visus.desktop.core.mouse_extra.scroll") as scr:
            bot.scroll(5)
        scr.assert_called_once()

    def test_drag_delegates(self, bot):
        with patch("visus.desktop.core.mouse_extra.drag") as d:
            bot.drag(0, 0, 100, 100)
        d.assert_called_once()

    def test_triple_click_delegates(self, bot):
        with patch("visus.desktop.core.mouse_extra.triple_click") as tc:
            bot.triple_click(10, 20)
        tc.assert_called_once()

    def test_move_random_delegates(self, bot):
        with patch("visus.desktop.core.mouse_extra.move_random") as mr:
            bot.move_random(10, 20)
        mr.assert_called_once()

    def test_mouse_down_delegates(self, bot):
        with patch("visus.desktop.core.mouse_extra.mouse_down") as md:
            bot.mouse_down(10, 20)
        md.assert_called_once()

    def test_mouse_up_delegates(self, bot):
        with patch("visus.desktop.core.mouse_extra.mouse_up") as mu:
            bot.mouse_up(10, 20)
        mu.assert_called_once()

    def test_launch_delegates(self, bot):
        with patch("visus.desktop.core.process.launch") as lp:
            bot.launch("notepad.exe")
        lp.assert_called_once()

    def test_find_process_delegates(self, bot):
        with patch(
            "visus.desktop.core.process.find_process", return_value=None
        ) as fp:
            bot.find_process("chrome")
        fp.assert_called_once()

    def test_is_process_running_delegates(self, bot):
        with patch(
            "visus.desktop.core.process.is_process_running", return_value=True
        ):
            assert bot.is_process_running("x") is True

    def test_kill_process_delegates(self, bot):
        with patch(
            "visus.desktop.core.process.kill_process", return_value=True
        ):
            assert bot.kill_process(999) is True

    def test_take_screenshot_delegates(self, bot):
        with patch(
            "visus.desktop.core.screen.capture_screen",
            return_value=Image.new("RGB", (4, 4)),
        ):
            img = bot.take_screenshot()
        assert img.size == (4, 4)

    def test_save_screenshot_delegates(self, bot, tmp_path):
        with patch(
            "visus.desktop.core.screen.save_screenshot", return_value=str(tmp_path / "x.png")
        ) as ss:
            bot.save_screenshot(str(tmp_path / "x.png"))
        ss.assert_called_once()

    def test_get_display_size_delegates(self, bot):
        with patch(
            "visus.desktop.core.screen.get_display_size",
            return_value=(1920, 1080),
        ):
            assert bot.get_display_size() == (1920, 1080)

    def test_copy_delegates(self, bot):
        with patch("visus.desktop.utils.clipboard.copy") as cp:
            bot.copy("hi")
        cp.assert_called_once_with("hi")

    def test_paste_delegates(self, bot):
        with patch("visus.desktop.utils.clipboard.paste") as pst:
            bot.paste()
        pst.assert_called_once()

    def test_get_clipboard_delegates(self, bot):
        with patch(
            "visus.desktop.utils.clipboard.get_clipboard", return_value="hi"
        ):
            assert bot.get_clipboard() == "hi"

    def test_wait_for_file_delegates(self, bot):
        with patch(
            "visus.desktop.utils.files.wait_for_file", return_value=True
        ):
            assert bot.wait_for_file("p") is True

    def test_wait_for_file_stable_delegates(self, bot):
        with patch(
            "visus.desktop.utils.files.wait_for_file_stable", return_value=True
        ):
            assert bot.wait_for_file_stable("p") is True

    def test_browse_delegates(self, bot):
        with patch("webbrowser.open") as wb:
            bot.browse("https://example.com")
        wb.assert_called_once_with("https://example.com")

    def test_window_helpers_delegate(self, bot):
        with patch(
            "visus.desktop.core.window.focus_window", return_value=True
        ), patch(
            "visus.desktop.core.window.maximize_window", return_value=True
        ), patch(
            "visus.desktop.core.window.minimize_window", return_value=True
        ), patch(
            "visus.desktop.core.window.close_window", return_value=True
        ):
            assert bot.focus_window("x") is True
            assert bot.maximize_window("x") is True
            assert bot.minimize_window("x") is True
            assert bot.close_window("x") is True


# ===========================================================================
# task_executor.py -- _execute_single_task branches + perform_action helpers
# ===========================================================================


@requires_tesseract
class TestExecuteSingleTaskTypeDispatch:
    @pytest.fixture
    def executor(self):
        return TaskExecutor()

    def test_unknown_task_creates_failure_result(self, executor):
        result = executor._execute_single_task({}, 0, 1)
        assert result.success is False
        assert "valid type" in (result.error or "")

    def test_type_text_task_returns_skip(self, executor):
        with patch.object(
            executor.keyboard_commander, "type_with_tokens"
        ):
            result = executor._execute_single_task(
                {"type": "type_text", "text": "x", "interval": 0.01}, 0, 1
            )
        assert result.success is True
        assert result.location == "skip"

    def test_keyboard_command_task_succeeds(self, executor):
        with patch.object(
            executor.keyboard_commander, "execute_command", return_value=True
        ):
            result = executor._execute_single_task(
                {"type": "keyboard_command", "command": "Tab"}, 0, 1
            )
        assert result.success is True

    def test_keyboard_command_failure_returns_failure(self, executor):
        with patch.object(
            executor.keyboard_commander,
            "execute_command",
            side_effect=RuntimeError("io"),
        ):
            result = executor._execute_single_task(
                {"type": "keyboard_command", "command": "Tab"}, 0, 1
            )
        assert result.success is False

    def test_click_coordinate_task(self, executor):
        fake_center = MagicMock(x=10, y=20)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            executor.virtual_mouse, "click", return_value=True
        ):
            result = executor._execute_single_task(
                {"type": "click", "x": 10, "y": 20}, 0, 1
            )
        assert result.success is True


@requires_tesseract
class TestPerformActionHelpers:
    @pytest.fixture
    def executor(self):
        ex = TaskExecutor()
        # Wire a noop overlay so _perform_action does not block.
        ex.config.set("show_overlay", False)
        return ex

    def test_perform_action_clicks_at_center(self, executor):
        fake_center = MagicMock(x=50, y=60)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            executor.virtual_mouse, "click", return_value=True
        ) as click:
            executor._perform_action(
                {"mouse_button": "left"}, (10, 20, 80, 80)
            )
        click.assert_called()

    def test_perform_action_with_sendtext_invokes_process(self, executor):
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            executor.virtual_mouse, "click", return_value=True
        ), patch.object(executor, "_process_sendtext") as sendtext:
            executor._perform_action(
                {"sendtext": "hello", "delay": 0}, (0, 0, 10, 10)
            )
        sendtext.assert_called_once_with("hello")


# ===========================================================================
# __init__.py VisusBot wrappers
# ===========================================================================


@requires_tesseract
class TestVisusBotWrappers:
    @pytest.fixture
    def bot(self):
        return vd.VisusBot({"show_overlay": False})

    def test_session_helpers(self, bot):
        # start / end_task_session manage the bot's session counter.
        bot.start_task_session()
        succ, total = bot.end_task_session()
        assert succ == 0 and total == 0

    def test_overlay_enabled_property_setter(self, bot):
        bot.overlay_enabled = False
        assert bot.overlay_enabled is False
        bot.overlay_enabled = True
        assert bot.overlay_enabled is True

    def test_show_overlay_property_setter(self, bot):
        bot.show_overlay = False
        assert bot.show_overlay is False
        bot.show_overlay = True
        assert bot.show_overlay is True

    def test_configure_overlay_writes_each_field(self, bot):
        bot.configure_overlay(
            enabled=True, color="blue", duration=500, width=2
        )
        cfg = bot.get_overlay_config()
        assert cfg["color"] == "blue"
        assert cfg["duration"] == 500
        assert cfg["width"] == 2

    def test_get_available_overlay_colors_lists_known(self, bot):
        colors = bot.get_available_overlay_colors()
        assert "red" in colors and "blue" in colors

    def test_get_available_keyboard_commands(self, bot):
        cmds = bot.get_available_keyboard_commands()
        assert isinstance(cmds, list) and cmds

    def test_click_at_returns_bool(self, bot):
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            assert bot.click_at((10, 20, 30, 30)) is True

    def test_type_text_standalone(self, bot):
        with patch.object(
            bot.executor.keyboard_commander, "type_text"
        ) as tt:
            bot.type_text("hello", interval=0.01)
        tt.assert_called_once()

    def test_keyboard_command_standalone(self, bot):
        with patch.object(
            bot.executor.keyboard_commander, "execute_command", return_value=True
        ) as kc:
            assert bot.keyboard_command("Tab") is True
        kc.assert_called_once_with("Tab")

    def test_click_coordinates_standalone(self, bot):
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch.object(
            bot.executor.virtual_mouse, "click", return_value=True
        ):
            assert bot.click_coordinates(10, 20) is True


@requires_tesseract
class TestModuleStandaloneFunctions:
    """Module-level convenience helpers that wrap a fresh bot per call."""

    def test_find_text_standalone(self):
        with patch(
            "visus.desktop.VisusBot.find_text",
            return_value=(1, 2, 3, 4),
        ):
            out = vd.find_text(
                "Login", region=(0, 0, 10, 10), config={"show_overlay": False}
            )
        assert out == (1, 2, 3, 4)

    def test_click_text_standalone(self):
        with patch(
            "visus.desktop.VisusBot.click_text", return_value=True
        ):
            assert vd.click_text(
                "Login",
                region=(0, 0, 10, 10),
                config={"show_overlay": False},
            )

    def test_find_image_standalone(self):
        with patch(
            "visus.desktop.VisusBot.find_image",
            return_value=(0, 0, 1, 1),
        ):
            out = vd.find_image(
                "a.png", config={"show_overlay": False}
            )
        assert out == (0, 0, 1, 1)

    def test_click_image_standalone(self):
        with patch(
            "visus.desktop.VisusBot.click_image", return_value=True
        ):
            assert vd.click_image(
                "a.png", config={"show_overlay": False}
            )

    def test_click_at_standalone(self):
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch(
            "visus.desktop.VisusBot.click_at", return_value=True
        ):
            assert vd.click_at(
                (10, 20, 30, 30), config={"show_overlay": False}
            )

    def test_type_text_module_level(self):
        with patch("visus.desktop.VisusBot.type_text", return_value=True):
            assert vd.type_text("hello", config={"show_overlay": False})

    def test_click_coordinates_standalone(self):
        fake_center = MagicMock(x=1, y=1)
        with patch("pyautogui.center", return_value=fake_center), patch(
            "visus.desktop.VisusBot.click_coordinates", return_value=True
        ):
            assert vd.click_coordinates(
                10, 20
            )

    def test_type_text_standalone_module(self):
        with patch(
            "visus.desktop.VisusBot.type_text", return_value=True
        ):
            assert vd.type_text_standalone(
                "hello"
            )

    def test_keyboard_command_standalone_module(self):
        with patch(
            "visus.desktop.VisusBot.keyboard_command", return_value=True
        ):
            assert vd.keyboard_command_standalone("Tab")

    def test_get_available_keyboard_commands_module(self):
        out = vd.get_available_keyboard_commands()
        assert isinstance(out, list)

    def test_extract_text_from_region_standalone_module(self):
        with patch(
            "visus.desktop.VisusBot.extract_text_from_region",
            return_value=["x"],
        ):
            out = vd.extract_text_from_region_standalone(
                region=(0, 0, 10, 10)
            )
        assert out == ["x"]

    def test_find_relative_image_module(self):
        with patch(
            "visus.desktop.VisusBot.find_relative_image",
            return_value=(1, 2, 3, 4),
        ):
            out = vd.find_relative_image(
                anchor_image="a.png", target_image="t.png"
            )
        assert out == (1, 2, 3, 4)

    def test_click_relative_image_module(self):
        with patch(
            "visus.desktop.VisusBot.click_relative_image", return_value=True
        ):
            assert vd.click_relative_image(
                anchor_image="a.png", target_image="t.png"
            )

    def test_run_automation_wraps_execute_tasks(self):
        with patch("visus.desktop.execute_tasks", return_value=[]) as ex:
            vd.run_automation([{"type": "click", "x": 1, "y": 1}])
        ex.assert_called_once()

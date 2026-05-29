"""Heavy coverage for ``visus.desktop.core.overlay``.

Targets the missing line ranges 64-175 (_fix_tkinter_environment),
198-291 (_create_overlay_alternative Windows ctypes path),
323-453 (_create_overlay_tkinter), 463-539 (multiple overlays),
579-600 (module-level show_overlay convenience functions).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from visus.desktop.core.overlay import (
    VisualOverlay,
    show_multiple_overlays,
    show_overlay,
    show_overlay_blocking,
)


def _make_overlay(tkinter_available=True):
    with patch.object(
        VisualOverlay, "_check_tkinter_availability", return_value=tkinter_available
    ):
        return VisualOverlay()


class TestFixTkinterEnvironment:
    def test_returns_true_when_tcl_path_works(self, tmp_path):
        overlay = _make_overlay(tkinter_available=False)
        fake_tcl = tmp_path / "tcl8.6"
        fake_tcl.mkdir()
        with patch("glob.glob", return_value=[str(fake_tcl)]), patch(
            "os.path.exists", return_value=True
        ), patch.object(
            overlay, "_check_tkinter_availability", return_value=True
        ):
            assert overlay._fix_tkinter_environment() is True

    def test_returns_false_when_no_tcl_paths_found(self):
        overlay = _make_overlay(tkinter_available=False)
        with patch("glob.glob", return_value=[]), patch.object(
            overlay, "_check_tkinter_availability", return_value=False
        ), patch("tkinter.Tk", side_effect=RuntimeError("no display")):
            assert overlay._fix_tkinter_environment() is False

    def test_alternative_tkinter_works_branch(self):
        """Outer try fails; inner ``import tkinter`` succeeds -> True."""
        overlay = _make_overlay(tkinter_available=False)
        with patch("glob.glob", side_effect=RuntimeError("kaboom")):
            with patch("tkinter.Tk") as fake_tk:
                fake_tk.return_value = MagicMock()
                assert overlay._fix_tkinter_environment() is True

    def test_alternative_tkinter_fails_branch(self):
        overlay = _make_overlay(tkinter_available=False)
        with patch("glob.glob", side_effect=RuntimeError("kaboom")):
            with patch("tkinter.Tk", side_effect=RuntimeError("still bad")):
                assert overlay._fix_tkinter_environment() is False


class TestCreateOverlayAlternative:
    """Windows-only ctypes-based overlay drawer."""

    def test_happy_path_draws_rectangle_and_releases_dc(self):
        overlay = _make_overlay()
        fake_user32 = MagicMock()
        fake_user32.GetDC.return_value = 42
        fake_gdi32 = MagicMock()
        fake_gdi32.CreatePen.return_value = 100
        fake_gdi32.SelectObject.return_value = 50

        fake_ctypes = MagicMock()
        fake_ctypes.windll.user32 = fake_user32
        fake_ctypes.windll.gdi32 = fake_gdi32
        fake_ctypes.c_int = lambda v: v

        with patch.dict("sys.modules", {"ctypes": fake_ctypes}), patch("time.sleep"):
            overlay._create_overlay_alternative((10, 20, 30, 40))
        fake_user32.ReleaseDC.assert_called_once_with(0, 42)
        fake_gdi32.DeleteObject.assert_called_once_with(100)

    def test_failure_falls_back_to_log_only(self):
        overlay = _make_overlay()
        fake_ctypes = MagicMock()
        fake_ctypes.windll.user32.GetDC.return_value = 0  # zero = "failure"
        fake_ctypes.windll.gdi32 = MagicMock()
        with patch.dict("sys.modules", {"ctypes": fake_ctypes}):
            # Should not raise -- the exception is caught and a log line
            # describing the region is emitted.
            overlay._create_overlay_alternative((1, 2, 3, 4))


class TestCreateOverlayTkinter:
    def _patched_tk(self):
        """Build a Tk() mock that exercises the overlay's API surface."""
        root = MagicMock()
        root.winfo_screenwidth = MagicMock(return_value=1920)
        root.winfo_screenheight = MagicMock(return_value=1080)
        return root

    def test_returns_true_on_success(self):
        overlay = _make_overlay()
        root = self._patched_tk()
        with patch(
            "visus.desktop.core.overlay.tk.Tk", return_value=root
        ), patch(
            "visus.desktop.core.overlay.tk.Canvas", return_value=MagicMock()
        ):
            assert overlay._create_overlay_tkinter((1, 2, 3, 4)) is True

    def test_returns_false_on_tk_failure(self):
        overlay = _make_overlay()
        with patch(
            "visus.desktop.core.overlay.tk.Tk", side_effect=RuntimeError("no display")
        ):
            assert overlay._create_overlay_tkinter((1, 2, 3, 4)) is False

    def test_alpha_attribute_failure_is_non_fatal(self):
        """When -alpha is unavailable, the overlay still tries to render."""
        overlay = _make_overlay()
        root = self._patched_tk()
        # Each call to attributes raises for the alpha tweak then is ok.
        attempts = {"n": 0}

        def attributes(*args, **kwargs):
            attempts["n"] += 1
            if args and args[0] == "-alpha":
                raise RuntimeError("no alpha")

        root.attributes.side_effect = attributes
        with patch(
            "visus.desktop.core.overlay.tk.Tk", return_value=root
        ), patch(
            "visus.desktop.core.overlay.tk.Canvas", return_value=MagicMock()
        ):
            assert overlay._create_overlay_tkinter((1, 2, 3, 4)) is True


class TestShowMultiple:
    def test_non_blocking_starts_a_daemon_thread(self):
        overlay = _make_overlay()
        with patch.object(
            overlay, "_create_multiple_overlays"
        ), patch("threading.Thread") as Thread:
            overlay.show_multiple([(0, 0, 1, 1)])
        Thread.assert_called_once()
        # The .start() must have been issued on the constructed thread.
        Thread.return_value.start.assert_called_once()

    def test_blocking_calls_directly(self):
        overlay = _make_overlay()
        with patch.object(overlay, "_create_multiple_overlays") as create:
            overlay.show_multiple([(0, 0, 1, 1)], blocking=True)
        create.assert_called_once()


class TestCreateMultipleOverlaysTkinter:
    def test_success(self):
        overlay = _make_overlay()
        root = MagicMock()
        root.winfo_screenwidth = MagicMock(return_value=1920)
        root.winfo_screenheight = MagicMock(return_value=1080)
        with patch(
            "visus.desktop.core.overlay.tk.Tk", return_value=root
        ), patch(
            "visus.desktop.core.overlay.tk.Canvas", return_value=MagicMock()
        ):
            assert (
                overlay._create_multiple_overlays_tkinter([(0, 0, 1, 1)])
                is True
            )

    def test_failure(self):
        overlay = _make_overlay()
        with patch(
            "visus.desktop.core.overlay.tk.Tk", side_effect=RuntimeError("no display")
        ):
            assert (
                overlay._create_multiple_overlays_tkinter([(0, 0, 1, 1)])
                is False
            )


class TestShow:
    def test_blocking_calls_directly(self):
        overlay = _make_overlay()
        with patch.object(overlay, "_create_overlay_with_fallback") as cof:
            overlay.show((1, 2, 3, 4), blocking=True)
        cof.assert_called_once_with((1, 2, 3, 4))

    def test_non_blocking_starts_thread(self):
        overlay = _make_overlay()
        with patch.object(
            overlay, "_create_overlay_with_fallback"
        ), patch("threading.Thread") as Thread:
            overlay.show((1, 2, 3, 4))
        Thread.return_value.start.assert_called_once()


class TestCreateOverlayWithFallback:
    def test_tkinter_branch_success(self):
        overlay = _make_overlay()
        with patch.object(
            overlay, "_create_overlay_tkinter", return_value=True
        ) as tk_branch, patch.object(
            overlay, "_create_overlay_alternative"
        ) as alt:
            overlay._create_overlay_with_fallback((0, 0, 1, 1))
        tk_branch.assert_called_once()
        alt.assert_not_called()

    def test_falls_through_to_alternative_on_windows(self):
        overlay = _make_overlay(tkinter_available=False)
        with patch.object(
            overlay, "_create_overlay_tkinter", return_value=False
        ), patch.object(
            overlay, "_fix_tkinter_environment", return_value=False
        ), patch.object(
            overlay, "_create_overlay_alternative"
        ) as alt, patch("os.name", "nt"):
            overlay._create_overlay_with_fallback((0, 0, 1, 1))
        alt.assert_called_once()


class TestModuleLevelHelpers:
    def test_show_overlay_module_function(self):
        with patch.object(VisualOverlay, "show") as show:
            show_overlay((0, 0, 10, 10), duration=100, color="red", width=2)
        show.assert_called_once()

    def test_show_overlay_blocking_module_function(self):
        with patch.object(VisualOverlay, "show") as show:
            show_overlay_blocking((0, 0, 10, 10), duration=100)
        show.assert_called_once()
        assert show.call_args.kwargs.get("blocking") is True

    def test_show_multiple_overlays_module_function(self):
        with patch.object(VisualOverlay, "show_multiple") as sm:
            show_multiple_overlays([(0, 0, 1, 1)], duration=100)
        sm.assert_called_once()

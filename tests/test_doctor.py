"""Tests for the ``visus doctor`` health-check CLI (Phase 1, R4).

The module ``visus.desktop.doctor`` provides individual check functions
and a ``run_checks`` entry point that prints ``[OK]``/``[FAIL]`` lines
and returns an exit code: ``0`` when every check passed, ``1`` when any
required check failed.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from visus.desktop import doctor


class TestCheckFunctions:
    """Individual check functions return ``(ok: bool, detail: str)``."""

    def test_check_tesseract_ok_when_detection_succeeds(self):
        with patch.object(doctor, "_detect_tesseract", return_value="/path/tesseract"):
            ok, detail = doctor.check_tesseract()
        assert ok is True
        assert "/path/tesseract" in detail

    def test_check_tesseract_fail_when_detection_returns_none(self):
        with patch.object(doctor, "_detect_tesseract", return_value=None):
            ok, detail = doctor.check_tesseract()
        assert ok is False
        assert "tesseract" in detail.lower()

    def test_check_python_dependencies_ok_when_all_present(self):
        ok, detail = doctor.check_python_dependencies()
        # Test environment installs all required deps.
        assert ok is True
        assert "all" in detail.lower() or "ok" in detail.lower()

    def test_check_python_dependencies_fail_when_one_missing(self):
        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "pyperclip":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            ok, detail = doctor.check_python_dependencies()
        assert ok is False
        assert "pyperclip" in detail

    def test_check_display_ok_when_size_returns_pair(self):
        with patch.object(doctor, "_get_display_size", return_value=(1920, 1080)):
            ok, detail = doctor.check_display()
        assert ok is True
        assert "1920" in detail

    def test_check_display_fail_when_size_call_raises(self):
        with patch.object(
            doctor,
            "_get_display_size",
            side_effect=RuntimeError("no display"),
        ):
            ok, detail = doctor.check_display()
        assert ok is False
        assert "display" in detail.lower()

    # off Windows check_pywinauto() is a deliberate no-op (the test below covers it)
    @pytest.mark.skipif(sys.platform != "win32", reason="pywinauto só existe no Windows")
    def test_check_pywinauto_ok_when_import_succeeds(self):
        # Avoid touching the real pywinauto stack so the test is portable.
        fake_module = type(sys)("pywinauto")
        fake_module.__version__ = "0.6.8"
        with patch.dict(sys.modules, {"pywinauto": fake_module}):
            ok, detail = doctor.check_pywinauto()
        assert ok is True
        assert "0.6.8" in detail

    def test_check_pywinauto_skipped_on_non_windows(self):
        with patch.object(doctor.platform, "system", return_value="Linux"):
            ok, detail = doctor.check_pywinauto()
        # On non-Windows it's a no-op success (skipped, not a hard failure).
        assert ok is True
        assert "skip" in detail.lower() or "not applicable" in detail.lower()


class TestRunChecks:
    """``run_checks`` aggregates per-check results into an exit code."""

    def test_run_checks_returns_zero_when_all_pass(self, capsys):
        passing_checks = [
            ("Always OK", lambda: (True, "fine")),
            ("Also OK", lambda: (True, "great")),
        ]
        exit_code = doctor.run_checks(checks=passing_checks)
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "[OK]" in out
        assert "Always OK" in out

    def test_run_checks_returns_nonzero_when_any_fails(self, capsys):
        mixed = [
            ("OK item", lambda: (True, "ok")),
            ("FAIL item", lambda: (False, "broken")),
        ]
        exit_code = doctor.run_checks(checks=mixed)
        out = capsys.readouterr().out
        assert exit_code != 0
        assert "[FAIL]" in out
        assert "FAIL item" in out
        assert "broken" in out

    def test_run_checks_catches_check_exceptions(self, capsys):
        """A check that raises is reported as a failure, not propagated."""

        def explodes():
            raise RuntimeError("boom inside the check")

        exit_code = doctor.run_checks(checks=[("Exploder", explodes)])
        out = capsys.readouterr().out
        assert exit_code != 0
        assert "[FAIL]" in out
        assert "boom inside the check" in out

    def test_module_runnable_via_main(self, capsys):
        """``doctor.main`` is the entry point used by ``python -m``."""
        with patch.object(
            doctor,
            "DEFAULT_CHECKS",
            [("Pretend", lambda: (True, "ok"))],
        ):
            exit_code = doctor.main([])
        out = capsys.readouterr().out
        assert exit_code == 0
        assert "Pretend" in out


class TestCliEntryPoint:
    """``python -m visus.desktop.doctor`` runs ``doctor.main``."""

    def test_module_has_main_callable(self):
        assert callable(doctor.main)


class TestActiveBackendCheck:
    """``check_active_ocr_backend`` reports which backend is configured."""

    def test_default_backend_uses_rapidocr_check(self):
        # Default config is now rapidocr -> the active-backend check routes to
        # the rapidocr sub-check and reports backend=rapidocr.
        ok, detail = doctor.check_active_ocr_backend()
        assert "rapidocr" in detail.lower()

    def test_explicit_tesseract_backend_uses_tesseract_check(self):
        from visus.desktop.utils import config as _config

        with patch.object(
            _config.BotVisionConfig, "_load_default_config",
            return_value={"ocr_backend": "tesseract"},
        ), patch.object(doctor, "check_tesseract", return_value=(True, "ok")):
            ok, detail = doctor.check_active_ocr_backend()
        assert ok is True
        assert "tesseract" in detail.lower()

    def test_rapidocr_backend_check_passes_when_importable(self):
        import sys
        from unittest.mock import MagicMock

        fake_rapid = MagicMock()
        fake_rapid.__version__ = "2.0.0"
        fake_onnx = MagicMock()
        fake_onnx.__version__ = "1.16.0"
        from visus.desktop.utils import config as _config

        with patch.dict(
            sys.modules, {"rapidocr": fake_rapid, "onnxruntime": fake_onnx}
        ), patch.object(
            _config.BotVisionConfig,
            "_load_default_config",
            return_value={"ocr_backend": "rapidocr"},
        ):
            ok, detail = doctor.check_active_ocr_backend()
        assert ok is True
        assert "rapidocr" in detail.lower()

    def test_rapidocr_backend_check_fails_when_not_installed(self):
        from visus.desktop.utils import config as _config

        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "rapidocr":
                raise ImportError(name)
            return original_import(name, *args, **kwargs)

        with patch.object(
            _config.BotVisionConfig,
            "_load_default_config",
            return_value={"ocr_backend": "rapidocr"},
        ), patch("builtins.__import__", side_effect=fake_import):
            ok, detail = doctor.check_active_ocr_backend()
        assert ok is False
        assert "rapidocr" in detail.lower()


class TestTesseractPathHelper:
    """``get_tesseract_candidate_paths`` is the canonical source of paths."""

    def test_helper_returns_a_non_empty_list_for_current_os(self):
        from visus.desktop.utils.config import get_tesseract_candidate_paths

        assert get_tesseract_candidate_paths()

    def test_helper_deduplicates_repeated_paths(self):
        """Order is preserved; duplicates are dropped."""
        from visus.desktop.utils.config import get_tesseract_candidate_paths

        paths = get_tesseract_candidate_paths()
        assert len(paths) == len(set(paths))

    def test_doctor_and_config_share_the_same_paths(self):
        """The doctor's check uses the same canonical helper as the config."""
        from visus.desktop.utils.config import (
            BotVisionConfig,
            get_tesseract_candidate_paths,
        )

        canonical = get_tesseract_candidate_paths()
        config_paths = BotVisionConfig.__dict__["_get_tesseract_paths"](
            BotVisionConfig.__new__(BotVisionConfig)
        )
        assert config_paths == canonical

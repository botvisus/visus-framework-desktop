"""Run the doctor against the real environment.

The unit suite patches the check functions individually; this test
runs them in earnest against the actual machine. On CI the
expectations are: Python deps OK, display OK (via xvfb on Linux),
Tesseract OK if installed system-wide.
"""

from __future__ import annotations

from visus.desktop import doctor


class TestRealDoctor:
    def test_run_checks_returns_an_int(self):
        rc = doctor.run_checks()
        assert isinstance(rc, int)

    def test_python_dependencies_pass_in_dev_env(self):
        ok, detail = doctor.check_python_dependencies()
        assert ok is True, detail

    def test_display_check_passes_under_a_real_or_virtual_display(self):
        ok, detail = doctor.check_display()
        assert ok is True, detail

    def test_active_backend_check_returns_payload(self):
        ok, detail = doctor.check_active_ocr_backend()
        # OK only when Tesseract is on the machine OR rapidocr is wired;
        # but in either case the detail string is informative.
        assert isinstance(detail, str)
        assert detail

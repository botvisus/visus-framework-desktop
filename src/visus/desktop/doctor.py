"""Health-check CLI for visus-desktop (Phase 1, R4).

Run with::

    python -m visus.desktop.doctor

Prints ``[OK]`` / ``[FAIL]`` per check and exits 0 when every required
check passes, non-zero otherwise. Useful as a first-time-user diagnostic
and in CI to catch missing system deps early.

The check functions are deliberately small and individually importable
so users can call any subset programmatically.
"""

from __future__ import annotations

import logging
import platform
import shutil
import sys
from typing import Callable

logger = logging.getLogger(__name__)

CheckResult = tuple[bool, str]
Check = tuple[str, Callable[[], CheckResult]]

_REQUIRED_PYTHON_MODULES = [
    "pyautogui",
    "pytesseract",
    "cv2",
    "PIL",
    "numpy",
    "pyperclip",
    "mss",
    "psutil",
]


def _detect_tesseract() -> str | None:
    """Return the resolved Tesseract binary path, or ``None`` if not found.

    Cheap existence-only check (no subprocess), so the doctor stays fast.
    Reuses the canonical candidate list from
    ``visus.desktop.utils.config.get_tesseract_candidate_paths`` to stay
    in sync with the runtime detector.
    """
    from .utils.config import get_tesseract_candidate_paths

    found = shutil.which("tesseract")
    if found:
        return found
    import os

    for candidate in get_tesseract_candidate_paths():
        if os.path.exists(candidate):
            return candidate
    return None


def _get_display_size() -> tuple[int, int]:
    """Return the display size via the screen helper (raises if unavailable)."""
    from .core.screen import get_display_size

    return get_display_size()


def check_tesseract() -> CheckResult:
    """Verify Tesseract OCR is on PATH or in a known install location."""
    path = _detect_tesseract()
    if path:
        return True, f"Tesseract found at: {path}"
    return False, (
        "Tesseract not found. Install: "
        "https://github.com/UB-Mannheim/tesseract/wiki (Windows) | "
        "apt-get install tesseract-ocr (Linux) | brew install tesseract (macOS)"
    )


def check_python_dependencies() -> CheckResult:
    """Verify every required Python module can be imported."""
    missing: list[str] = []
    for name in _REQUIRED_PYTHON_MODULES:
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if missing:
        return False, f"Missing Python modules: {', '.join(missing)}"
    return True, f"All required Python modules present ({len(_REQUIRED_PYTHON_MODULES)})"


def check_display() -> CheckResult:
    """Verify a display is available by querying its size."""
    try:
        width, height = _get_display_size()
    except Exception as exc:
        return False, f"No usable display: {exc}"
    return True, f"Display available ({width}x{height})"


def check_pywinauto() -> CheckResult:
    """Verify pywinauto imports on Windows; a no-op success elsewhere."""
    if platform.system().lower() != "windows":
        return True, "pywinauto check skipped (not applicable to this OS)"
    try:
        import pywinauto  # type: ignore[import-not-found]
    except ImportError as exc:
        return False, (
            f"pywinauto not installed ({exc}). "
            "Install the native extra: pip install 'visus-desktop[native]'"
        )
    version = getattr(pywinauto, "__version__", "unknown")
    return True, f"pywinauto importable (version {version})"


DEFAULT_CHECKS: list[Check] = [
    ("Tesseract OCR", check_tesseract),
    ("Python dependencies", check_python_dependencies),
    ("Display", check_display),
    ("pywinauto (native automation)", check_pywinauto),
]


def run_checks(checks: list[Check] | None = None) -> int:
    """Execute each check and print a ``[OK]``/``[FAIL]`` line per item.

    Returns the process exit code: ``0`` if all checks passed, ``1`` if
    any check failed (including a check that raised an exception, which
    is reported as a failure rather than crashing the diagnostic).
    """
    selected = checks if checks is not None else DEFAULT_CHECKS
    failures = 0
    for name, fn in selected:
        try:
            ok, detail = fn()
        except Exception as exc:  # never crash the doctor itself
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        marker = "[OK]" if ok else "[FAIL]"
        print(f"{marker} {name}: {detail}")
        if not ok:
            failures += 1
    if failures:
        print(f"\n{failures} check(s) failed.")
        return 1
    print("\nAll checks passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m visus.desktop.doctor``."""
    return run_checks()


if __name__ == "__main__":  # pragma: no cover - exercised via ``python -m``
    sys.exit(main(sys.argv[1:]))

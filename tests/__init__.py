# Tests for the visus.desktop package.
import os
import shutil

# Paths where Tesseract may live; mirrors the detection logic in
# visus.desktop.utils.config.BotVisionConfig.
_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
]


def tesseract_available():
    """Return True if Tesseract OCR can be found on this machine."""
    if shutil.which("tesseract") is not None:
        return True
    return any(os.path.exists(p) for p in _TESSERACT_PATHS)

# Installation

Visus Desktop (`visus-desktop`) is a Python library for desktop GUI automation with OCR and image detection. This guide covers installing the package, setting up the required **Tesseract OCR** engine, verifying the install, and the optional extras.

## Requirements

- **Python 3.8 or newer**
- **Tesseract OCR** installed on the system (required — see [Installing Tesseract OCR](#installing-tesseract-ocr))

The following Python packages are installed automatically as dependencies:

- `PyAutoGUI`
- `pytesseract`
- `opencv-python`
- `Pillow`
- `numpy`
- `pyperclip`
- `pywin32` (Windows only)

## Installing the package

```bash
pip install visus-desktop
```

Using a virtual environment is recommended:

```bash
# Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

pip install visus-desktop
```

The import root is the PEP 420 namespace package `visus.desktop`:

```python
from visus.desktop import VisusBot
```

## Installing Tesseract OCR

Visus Desktop reads on-screen text by calling the Tesseract binary, so Tesseract must be installed on the host system. Installing the Python package does **not** install Tesseract.

### Windows

1. Download the installer from the UB-Mannheim build: <https://github.com/UB-Mannheim/tesseract/wiki>
2. Install to the default location: `C:\Program Files\Tesseract-OCR\`
3. (Recommended) Add `C:\Program Files\Tesseract-OCR\` to your system `PATH`.

Visus Desktop automatically detects Tesseract at the default install paths (including `C:\Program Files\Tesseract-OCR\tesseract.exe` and the `(x86)` variant) or anywhere on the `PATH`.

### Linux (Debian / Ubuntu)

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

Visus Desktop looks for the binary in common locations such as `/usr/bin/tesseract` and `/usr/local/bin/tesseract`, as well as on the `PATH`.

### macOS

```bash
brew install tesseract
```

Common Homebrew locations (`/usr/local/bin/tesseract`, `/opt/homebrew/bin/tesseract`) and the `PATH` are detected automatically.

### Pointing Visus Desktop at a custom Tesseract location

If Tesseract is installed somewhere non-standard and is not on the `PATH`, set `tesseract_path` (and optionally `tesseract_data_path`) in the configuration:

```python
from visus.desktop import VisusBot

bot = VisusBot(config={
    "tesseract_path": r"C:\Tools\Tesseract-OCR\tesseract.exe",
    "tesseract_data_path": r"C:\Tools\Tesseract-OCR\tessdata",
})
```

If Tesseract cannot be found, creating a `VisusBot` (or a `BotVisionConfig`) raises `TesseractNotFoundError`.

## Verifying the install

First confirm Tesseract is reachable from your shell:

```bash
tesseract --version
```

Then confirm Visus Desktop imports and initializes (this also validates that Tesseract and all dependencies are present):

```python
import visus.desktop as vd

print(vd.__version__)        # 0.1.0

from visus.desktop import VisusBot
bot = VisusBot()             # raises TesseractNotFoundError if Tesseract is missing
print("Visus Desktop is ready.")
```

## Optional extras

Extra dependency groups can be installed for additional, optional capabilities:

```bash
# Extra automation helpers: keyboard, MouseInfo, pandas
pip install "visus-desktop[automation]"

# AI integration: openai
pip install "visus-desktop[ai]"

# Web automation helper: webdriver-manager
pip install "visus-desktop[web]"
```

Extras can be combined:

```bash
pip install "visus-desktop[automation,ai]"
```

## Development install

To work on the library from a checkout, install in editable mode with the dev dependency group:

```bash
pip install -e .
```

The dev tooling (pytest, pytest-cov, ruff, mypy, pre-commit) is declared as a PEP 735 dependency group named `dev`.

## Troubleshooting

- **`TesseractNotFoundError`** — Tesseract is not installed or not detected. Install it (see above), add it to the `PATH`, or set `tesseract_path` in the configuration.
- **`ConfigurationError: Required modules not found`** — a core Python dependency is missing. Reinstall the package: `pip install --force-reinstall visus-desktop`.
- **Text not recognized / poor OCR accuracy** — restrict the search to a `region`, lower the `confidence_threshold`, or use `filter_type` to constrain the expected characters.

## Next steps

- [API Reference](api_reference.md)
- [Documentation index](README.md)

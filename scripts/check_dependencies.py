#!/usr/bin/env python3
"""
Dependency check script for Visus Desktop.

This script checks whether all required dependencies are installed
with the correct versions.
"""

import sys
import importlib
import pkg_resources

# Required dependencies with specific versions
REQUIRED_PACKAGES = {
    "PyAutoGUI": "0.9.54",
    "numpy": "1.26.4",
    "opencv-python": "4.9.0.80",
    "pytesseract": None,  # No specific version
    "pyperclip": None,    # >= 1.8.2
    "Pillow": None,       # >= 10.0.0
}

# Optional dependencies (the real install extras)
OPTIONAL_PACKAGES = {
    "pywinauto": None,  # [native] — native/accessibility automation (Windows)
    "mcp": None,        # [mcp]    — the visus-mcp server
    "rapidocr": None,   # [rapidocr] — ONNX OCR backend
}

def check_package(package_name, expected_version=None):
    """
    Check whether a package is installed and optionally its version.

    Args:
        package_name (str): Package name
        expected_version (str, optional): Expected version

    Returns:
        tuple: (is_installed, current_version, version_match)
    """
    try:
        # Try to import the package
        if package_name == "opencv-python":
            import cv2
            installed_version = cv2.__version__
        elif package_name == "PyAutoGUI":
            import pyautogui
            installed_version = pyautogui.__version__
        elif package_name == "Pillow":
            import PIL
            installed_version = PIL.__version__
        else:
            module = importlib.import_module(package_name.lower().replace("-", "_"))
            installed_version = getattr(module, '__version__', 'unknown')

        # Check version if specified
        if expected_version:
            version_match = installed_version == expected_version
        else:
            version_match = True

        return True, installed_version, version_match

    except ImportError:
        return False, None, False
    except Exception as e:
        return False, str(e), False

def main():
    """Main check function."""
    print("=" * 60)
    print("VISUS DESKTOP - DEPENDENCY CHECK")
    print("=" * 60)

    all_good = True

    # Check required dependencies
    print("\nREQUIRED DEPENDENCIES:")
    print("-" * 40)

    for package, expected_version in REQUIRED_PACKAGES.items():
        is_installed, current_version, version_match = check_package(package, expected_version)

        if is_installed:
            if expected_version and version_match:
                status = "OK"
                print(f"{package:15} | {current_version:10} | {status}")
            elif expected_version and not version_match:
                status = f"Incorrect version (expected: {expected_version})"
                print(f"{package:15} | {current_version:10} | {status}")
                all_good = False
            else:
                status = "OK"
                print(f"{package:15} | {current_version:10} | {status}")
        else:
            status = "NOT INSTALLED"
            print(f"{package:15} | {'N/A':10} | {status}")
            all_good = False

    # Check optional dependencies
    print("\nOPTIONAL DEPENDENCIES:")
    print("-" * 40)

    for package, expected_version in OPTIONAL_PACKAGES.items():
        is_installed, current_version, version_match = check_package(package, expected_version)

        if is_installed:
            if expected_version and version_match:
                status = "OK"
            elif expected_version and not version_match:
                status = f"Incorrect version (expected: {expected_version})"
            else:
                status = "OK"
            print(f"{package:15} | {current_version:10} | {status}")
        else:
            status = "Optional - not installed"
            print(f"{package:15} | {'N/A':10} | {status}")

    # Check whether Visus Desktop can be imported
    print("\nVISUS DESKTOP:")
    print("-" * 40)

    try:
        from visus.desktop import BotVision, execute_tasks, click_images
        print("visus.desktop    | Imported   | OK")

        # Test basic initialization
        bot = BotVision()
        print("BotVision()      | Instance   | OK")

    except ImportError as e:
        print(f"visus.desktop    | Error      | ERROR: {e}")
        all_good = False
    except Exception as e:
        print(f"visus.desktop    | Error      | ERROR: {e}")
        all_good = False

    # Final result
    print("\n" + "=" * 60)
    if all_good:
        print("ALL REQUIRED DEPENDENCIES ARE OK!")
        print("Visus Desktop is ready to use.")
    else:
        print("SOME REQUIRED DEPENDENCIES ARE MISSING OR INCORRECT!")
        print("\nTo install the correct dependencies, run:")
        print("pip install PyAutoGUI==0.9.54 numpy==1.26.4 opencv-python==4.9.0.80")
        print("pip install pytesseract pyperclip Pillow")

    print("=" * 60)

    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())

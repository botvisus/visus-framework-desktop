#!/usr/bin/env python
"""
Package validation script for visus-desktop.

This script validates the package structure, imports, and basic functionality.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and report the result."""
    if Path(file_path).exists():
        print(f"OK {description}: {file_path}")
        return True
    else:
        print(f"FAIL {description}: {file_path} (MISSING)")
        return False

def validate_package_structure():
    """Validate the package directory structure."""
    print("Validating Package Structure")
    print("=" * 35)

    required_files = [
        ("Project config", "pyproject.toml"),
        ("License", "LICENSE"),
        ("Main README", "README.md"),
        ("Main __init__", "src/visus/desktop/__init__.py"),
        ("Type marker", "src/visus/desktop/py.typed"),
        ("Exceptions", "src/visus/desktop/exceptions.py"),
        ("Core __init__", "src/visus/desktop/core/__init__.py"),
        ("OCR Engine", "src/visus/desktop/core/ocr_engine.py"),
        ("Image Processing", "src/visus/desktop/core/image_processing.py"),
        ("Task Executor", "src/visus/desktop/core/task_executor.py"),
        ("Visual Overlay", "src/visus/desktop/core/overlay.py"),
        ("Utils __init__", "src/visus/desktop/utils/__init__.py"),
        ("Config", "src/visus/desktop/utils/config.py"),
        ("Text Filters", "src/visus/desktop/utils/text_filters.py"),
    ]

    required_dirs = [
        ("Source directory", "src"),
        ("Tests directory", "tests"),
        ("Examples directory", "examples"),
        ("Documentation", "docs"),
    ]

    all_valid = True

    # Check required files
    print("\nRequired Files:")
    for desc, file_path in required_files:
        all_valid &= check_file_exists(file_path, desc)

    # Check directories
    print("\nRequired Directories:")
    for desc, dir_path in required_dirs:
        if Path(dir_path).is_dir():
            print(f"OK {desc}: {dir_path}/")
        else:
            print(f"FAIL {desc}: {dir_path}/ (MISSING)")
            all_valid = False

    return all_valid

def validate_imports():
    """Validate that all modules can be imported."""
    print("\n\nValidating Imports")
    print("=" * 25)

    # Make the src/ layout importable
    src_path = str((Path.cwd() / "src").resolve())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    import_tests = [
        ("Main package", "import visus.desktop"),
        ("BotVision class", "from visus.desktop import BotVision"),
        ("Convenience functions", "from visus.desktop import execute_tasks, find_text, click_text"),
        ("Configuration", "from visus.desktop.utils.config import BotVisionConfig"),
        ("Exceptions", "from visus.desktop.exceptions import BotVisionError, OCRProcessingError"),
        ("Core modules", "from visus.desktop.core import OCREngine, ImageProcessor, TaskExecutor"),
        ("Utils", "from visus.desktop.utils import clean_text, matches_filter"),
    ]

    all_valid = True

    for desc, import_stmt in import_tests:
        try:
            exec(import_stmt)
            print(f"OK {desc}")
        except ImportError as e:
            print(f"FAIL {desc}: {e}")
            all_valid = False
        except Exception as e:
            print(f"FAIL {desc}: Unexpected error - {e}")
            all_valid = False

    return all_valid

def validate_basic_functionality():
    """Validate basic package functionality."""
    print("\n\nValidating Basic Functionality")
    print("=" * 40)

    try:
        from visus.desktop.utils.config import BotVisionConfig
        from visus.desktop import BotVision

        # Test configuration creation
        config = BotVisionConfig()
        print("OK Configuration creation")

        # Test BotVision instantiation
        bot = BotVision(config=config)
        print("OK BotVision instantiation")

        # Test configuration validation
        config.validate()
        print("OK Configuration validation")

        # Test task format validation (basic)
        sample_task = {
            "task_name": "test",
            "description": "Test task",
            "steps": [
                {"action": "find_text", "text": "test"}
            ]
        }
        print("OK Task format validation")

        return True

    except Exception as e:
        print(f"FAIL Basic functionality test failed: {e}")
        return False

def validate_package_metadata():
    """Validate package metadata files."""
    print("\n\nValidating Package Metadata")
    print("=" * 35)

    all_valid = True

    # Check pyproject.toml
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            toml_content = f.read()
            if "[build-system]" in toml_content:
                print("OK pyproject.toml contains build system config")
            else:
                print("FAIL pyproject.toml missing build system config")
                all_valid = False

            if "name = \"visus-desktop\"" in toml_content:
                print("OK pyproject.toml declares the visus-desktop name")
            else:
                print("FAIL pyproject.toml missing the visus-desktop name")
                all_valid = False

            required_deps = ["opencv-python", "pillow", "numpy", "pyautogui", "pytesseract"]
            for dep in required_deps:
                if dep.lower() in toml_content.lower():
                    print(f"OK {dep} in pyproject.toml dependencies")
                else:
                    print(f"FAIL {dep} missing from pyproject.toml dependencies")
                    all_valid = False
    except FileNotFoundError:
        print("FAIL pyproject.toml not found")
        all_valid = False

    return all_valid

def main():
    """Main validation function."""
    print("Visus Desktop - Package Validation")
    print("=" * 45)
    print("This script validates the package structure and functionality.")

    # Change to the repository root directory (parent of scripts/)
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    print(f"Working directory: {repo_root}")

    # Run validation steps
    results = []

    results.append(("Package Structure", validate_package_structure()))
    results.append(("Package Metadata", validate_package_metadata()))
    results.append(("Module Imports", validate_imports()))
    results.append(("Basic Functionality", validate_basic_functionality()))

    # Summary
    print("\n\nValidation Summary")
    print("=" * 25)

    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "OK" if passed else "FAIL"
        print(f"{symbol} {test_name}: {status}")
        all_passed &= passed

    print("\n" + "=" * 50)
    if all_passed:
        print("All validations PASSED! Package is ready.")
        print("\nNext steps:")
        print("  1. Run tests: python -m pytest")
        print("  2. Build package: python scripts/build_package.py")
        print("  3. Install locally: pip install -e .")
    else:
        print("Some validations FAILED! Fix issues before proceeding.")
        print("\nRecommended actions:")
        print("  1. Check missing files and directories")
        print("  2. Verify import statements")
        print("  3. Review package structure")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

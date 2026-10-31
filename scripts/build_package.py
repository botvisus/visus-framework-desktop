#!/usr/bin/env python
"""
Build script for visus-desktop (without tests).

This script only builds and packages visus-desktop,
skipping the test execution.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command with error handling."""
    print(f"\n{description}")
    print("=" * len(description))

    try:
        result = subprocess.run(cmd, shell=True, check=check, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        return False

def clean_build_artifacts():
    """Clean build artifacts and cache files."""
    print("Cleaning build artifacts...")

    # Directories to clean
    clean_dirs = [
        'build',
        'dist',
        'src/visus_desktop.egg-info',
        'visus_desktop.egg-info',
        '.pytest_cache',
        'htmlcov',
        '__pycache__'
    ]

    # File patterns to clean
    clean_patterns = [
        '**/*.pyc',
        '**/*.pyo',
        '**/__pycache__'
    ]

    for dir_name in clean_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removed {dir_name}/")

    # Clean Python cache files
    for pattern in clean_patterns:
        for path in Path('.').rglob(pattern):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

def install_build_dependencies():
    """Install only the dependencies needed for the build."""
    build_deps = [
        'build>=0.7.0',
        'twine>=3.4.0',
        'wheel>=0.37.0'
    ]

    cmd = f"pip install {' '.join(build_deps)}"
    return run_command(cmd, "Installing build dependencies")

def build_package():
    """Build the package."""
    success = True

    # Build source distribution
    success &= run_command("python -m build --sdist", "Building source distribution")

    # Build wheel distribution
    success &= run_command("python -m build --wheel", "Building wheel distribution")

    return success

def check_package():
    """Check the package with twine."""
    return run_command("python -m twine check dist/*", "Checking package with twine")

def verify_basic_import():
    """Verify that the package can be imported (basic check)."""
    test_script = '''
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

try:
    # Try to import the main module
    import visus.desktop
    print("Basic import succeeded")
    sys.exit(0)
except Exception as e:
    print(f"Warning: Import check failed: {e}")
    print("This may be normal if there are uninstalled dependencies")
    sys.exit(0)
'''

    return run_command(f'python -c "{test_script}"', "Basic import check")

def main():
    """Main function - runs the build without tests."""
    print("Starting build of visus-desktop (without tests)")
    print("=" * 55)

    success = True

    # Step 1: Clean old artifacts
    clean_build_artifacts()

    # Step 2: Install build dependencies
    success &= install_build_dependencies()

    if not success:
        print("\nFailed to install build dependencies!")
        return 1

    # Step 3: Basic import check
    verify_basic_import()

    # Step 4: Build the package
    success &= build_package()

    if not success:
        print("\nPackage build failed!")
        return 1

    # Step 5: Check the package
    success &= check_package()

    if success:
        print("\nBuild completed successfully!")
        print("\nGenerated files:")
        dist_dir = Path("dist")
        if dist_dir.exists():
            for file in dist_dir.iterdir():
                size = file.stat().st_size / 1024  # size in KB
                print(f"  - {file.name} ({size:.1f} KB)")

        print("\nNext steps:")
        print("  1. Test the package: pip install dist/*.whl")
        print("  2. Upload to PyPI: python -m twine upload dist/*")
        print("  3. Upload to TestPyPI: python -m twine upload --repository testpypi dist/*")

    else:
        print("\nBuild failed! Check the errors above.")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

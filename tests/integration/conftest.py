"""Integration-suite scaffolding.

The suite lives under ``tests/integration/`` and touches real OS state
(display, clipboard, mouse, processes). Three design rules:

1. **Default invisible.** A plain ``pytest`` invocation does NOT collect
   anything in this directory -- the project's unit suite stays
   skip-free. The ``pytest_ignore_collect`` hook (root conftest)
   enforces that.
2. **Opt-in via ``--integration``.** Pass the flag to actually collect
   the tests:

       pytest tests/integration --integration -v

3. **Real-input tests need a SECOND gate.**  Tests marked
   ``@pytest.mark.real_input`` send actual keystrokes / mouse clicks /
   window-close events to whatever window is focused. Running those on
   a real interactive desktop is dangerous -- they will type into and
   close YOUR windows. They are skipped unless the
   ``VISUS_INTEGRATION_REAL_INPUT=1`` environment variable is set,
   which only CI (Xvfb / a throwaway runner) does. ``--integration``
   alone is NOT enough.

   On Linux without a desktop session, wrap with xvfb so a virtual
   display is available:

       VISUS_INTEGRATION_REAL_INPUT=1 xvfb-run -a \
           pytest tests/integration --integration -v

   CI runs them via ``.github/workflows/integration.yml`` with Xvfb on
   Linux and a dedicated Windows runner.

Every test in this directory inherits the ``@pytest.mark.integration``
marker automatically (via ``pytest_collection_modifyitems``).
``@pytest.mark.windows_only`` / ``@pytest.mark.linux_only`` apply at
collection time and skip outside the matching OS.
"""

from __future__ import annotations

import os
import sys

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-tag + apply OS / real-input skips when the suite is active."""
    if not config.getoption("--integration", default=False):
        return  # nothing collected from this directory anyway
    skip_windows_only = pytest.mark.skip(reason="windows-only integration test")
    skip_linux_only = pytest.mark.skip(reason="linux-only integration test")
    real_input_allowed = os.environ.get("VISUS_INTEGRATION_REAL_INPUT") == "1"
    skip_real_input = pytest.mark.skip(
        reason=(
            "real-input test: sends keystrokes / mouse / window-close to the "
            "focused window. Set VISUS_INTEGRATION_REAL_INPUT=1 (CI / throwaway "
            "machine only) to enable."
        )
    )
    for item in items:
        if "tests/integration" not in item.nodeid.replace("\\", "/"):
            continue
        item.add_marker(pytest.mark.integration)
        if "windows_only" in item.keywords and sys.platform != "win32":
            item.add_marker(skip_windows_only)
        if (
            "linux_only" in item.keywords
            and not sys.platform.startswith("linux")
        ):
            item.add_marker(skip_linux_only)
        if "real_input" in item.keywords and not real_input_allowed:
            item.add_marker(skip_real_input)

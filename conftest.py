"""Root conftest -- runs BEFORE pytest-cov instruments any module.

The lazy cv2.typing module references attributes on cv2.gapi.wip.draw
that are populated at C-extension import time. When pytest-cov starts
instrumenting modules, the order can leave cv2 partially initialized
(NumPy reload, deferred submodule binding). Importing the full chain
here -- in the project-root conftest -- guarantees the resolution
happens before coverage tracing touches any visus.desktop code.

The same shim still exists in ``tests/conftest.py`` for direct
``python -m pytest tests/...`` invocations from an editor; this root
shim covers the ``pytest --cov`` invocation path.
"""

try:  # pragma: no cover - environment shim, not part of the tested code
    import cv2  # noqa: F401
    import cv2.gapi  # noqa: F401
    import cv2.gapi.wip  # noqa: F401
    import cv2.gapi.wip.draw  # noqa: F401
    import cv2.typing  # noqa: F401
except Exception:  # pragma: no cover - cv2 is optional at import time
    pass


def pytest_addoption(parser):
    """Register the integration-suite opt-in flag at the root level.

    The flag must be discoverable even when no test under
    ``tests/integration/`` is being collected, so it lives here in the
    project-root conftest instead of inside the integration package.
    """
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that touch the real display / OS state.",
    )


def pytest_ignore_collect(collection_path, config):
    """Hide every node under ``tests/integration/`` unless --integration is set.

    Lives in the root conftest so the rule fires for every collection
    attempt, including the case where pytest does not descend into
    ``tests/integration/`` and so never loads the conftest there.
    """
    if config.getoption("--integration", default=False):
        return None  # collect everything
    parts = collection_path.parts
    return "integration" in parts and "tests" in parts

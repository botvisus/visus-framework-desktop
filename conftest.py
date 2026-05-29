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

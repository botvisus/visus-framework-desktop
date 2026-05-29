"""Native RPA -- operate desktop apps through the accessibility tree.

This is the "no-pixel" automation layer: it clicks, types into, reads and
waits for controls by **selector** (title / control_type / automation_id)
via pywinauto's UIA backend, instead of locating by image or OCR. When the
app is accessible (Win32 / WPF / WinUI / .NET) this is the most robust
automation possible -- immune to theme, DPI, resolution, language and
window position.

Every public function:

* targets a window by ``window`` (title substring) or ``pid`` (or the
  foreground window when neither is given);
* resolves the control with a **directed** ``child_window(...)`` query
  (UIA FindFirst -- fast, not a full ``descendants()`` walk);
* runs inside a worker thread bounded by ``timeout`` so a slow UIA
  provider can never hang the caller;
* supports ``retries`` + ``delay`` -- the native analogue of backtrack:
  re-attempt a flaky lookup/action before giving up.

Apps that are NOT accessible (Java Swing without the Access Bridge, some
Electron builds) expose little or nothing here -- use OCR / image
(``capture_element``) for those.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

_TIMEOUT_SENTINEL = object()


def _run_with_timeout(fn, timeout: float):
    """Run ``fn()`` in a daemon thread; return its result or sentinel on timeout.

    UIA calls can block indefinitely; bounding them in a thread keeps the
    tool responsive. Returns ``_TIMEOUT_SENTINEL`` when the worker is still
    alive after ``timeout`` seconds.
    """
    box: dict = {"value": _TIMEOUT_SENTINEL}

    def _work():
        try:
            box["value"] = fn()
        except Exception as exc:  # native faults are non-fatal
            logger.debug("native_rpa worker error: %s", exc)
            box["value"] = None

    worker = threading.Thread(target=_work, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        logger.debug("native_rpa call exceeded %.1fs; giving up", timeout)
        return _TIMEOUT_SENTINEL
    return box["value"]


def _selector_kwargs(title, control_type, auto_id, found_index) -> dict:
    """Build the ``child_window`` kwargs from the selector arguments."""
    kwargs: dict = {}
    if title is not None:
        kwargs["title"] = title
    if control_type is not None:
        kwargs["control_type"] = control_type
    if auto_id is not None:
        kwargs["auto_id"] = auto_id
    if found_index is not None:
        kwargs["found_index"] = found_index
    return kwargs


def _connect_top(window, pid, connect_timeout: float):
    """Connect to the target app (UIA) and return its top window, or None."""
    import pywinauto  # noqa: F401
    from pywinauto import Application

    app = Application(backend="uia")
    if pid is not None:
        app.connect(process=pid, timeout=connect_timeout)
    elif window is not None:
        app.connect(title_re=f".*{window}.*", timeout=connect_timeout)
    else:
        from .locators import get_foreground_window

        fw = get_foreground_window()
        if not fw:
            return None
        app.connect(process=fw["pid"], timeout=connect_timeout)
    return app.top_window()


def _rect_to_box(ctrl):
    try:
        r = ctrl.rectangle()
        return {
            "x": int(r.left),
            "y": int(r.top),
            "width": int(r.right - r.left),
            "height": int(r.bottom - r.top),
        }
    except Exception:
        return None


def _with_retries(action, retries: int, delay: float):
    """Run ``action()`` up to ``retries + 1`` times until it is truthy."""
    attempts = max(0, retries) + 1
    last = None
    for i in range(attempts):
        last = action()
        if last:
            return last
        if i < attempts - 1 and delay > 0:
            time.sleep(delay)
    return last


def _ensure_pywinauto() -> bool:
    try:
        import pywinauto  # noqa: F401

        return True
    except ImportError:
        logger.debug("pywinauto not installed; native_rpa unavailable")
        return False


# ---------------------------------------------------------------------------
# Tree introspection
# ---------------------------------------------------------------------------


def native_dump_tree(
    window=None,
    pid=None,
    *,
    max_depth: int = 3,
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
) -> list[dict]:
    """Return the control tree of the target window as a flat list.

    Each entry is ``{depth, control_type, title, auto_id, rect}``. Walks
    ``children()`` recursively up to ``max_depth`` (NOT the full
    ``descendants()`` -- that is slow and floods on leaf nodes), so the
    agent gets the structural map fast and can decide what to act on.
    Returns ``[]`` when pywinauto is missing or the walk times out.
    """
    if not _ensure_pywinauto():
        return []

    def _job():
        top = _connect_top(window, pid, connect_timeout)
        if top is None:
            return []
        nodes: list[dict] = []

        def _walk(element, depth):
            if depth > max_depth:
                return
            try:
                children = element.children()
            except Exception:
                return
            for child in children:
                try:
                    info = child.element_info
                    nodes.append(
                        {
                            "depth": depth,
                            "control_type": getattr(info, "control_type", "") or "",
                            "title": (info.name or ""),
                            "auto_id": getattr(info, "automation_id", "") or "",
                            "rect": _rect_to_box(child),
                        }
                    )
                except Exception:
                    continue
                _walk(child, depth + 1)

        _walk(top, 1)
        return nodes

    result = _run_with_timeout(_job, timeout)
    return [] if result is _TIMEOUT_SENTINEL or result is None else result


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def native_click(
    window=None,
    pid=None,
    *,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    button: str = "left",
    double: bool = False,
    method: str = "auto",
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
    retries: int = 0,
    delay: float = 0.3,
) -> bool:
    """Click a control located by selector -- no coordinates, no image.

    ``method``: ``"invoke"`` uses the UIA InvokePattern (no mouse movement,
    most robust); ``"click"`` uses ``click_input`` (real mouse on the
    control center); ``"auto"`` (default) tries invoke then falls back to
    click_input. ``retries`` + ``delay`` re-attempt a flaky control.
    Returns True on success.
    """
    if not _ensure_pywinauto():
        return False

    def _attempt():
        def _job():
            top = _connect_top(window, pid, connect_timeout)
            if top is None:
                return False
            ctrl = top.child_window(
                **_selector_kwargs(title, control_type, auto_id, found_index)
            )
            if not ctrl.exists(timeout=timeout):
                return False
            if double:
                ctrl.double_click_input()
                return True
            if method in ("invoke", "auto"):
                try:
                    ctrl.invoke()
                    return True
                except Exception:
                    if method == "invoke":
                        return False
            ctrl.click_input(button=button)
            return True

        return _run_with_timeout(_job, timeout + connect_timeout) is True

    return bool(_with_retries(_attempt, retries, delay))


def native_set_text(
    window=None,
    pid=None,
    *,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    text: str = "",
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
    retries: int = 0,
    delay: float = 0.3,
) -> bool:
    """Set the text of an editable control located by selector.

    Uses ``set_edit_text`` (UIA value pattern) with a ``type_keys``
    fallback. Returns True on success.
    """
    if not _ensure_pywinauto():
        return False

    def _attempt():
        def _job():
            top = _connect_top(window, pid, connect_timeout)
            if top is None:
                return False
            ctrl = top.child_window(
                **_selector_kwargs(title, control_type, auto_id, found_index)
            )
            if not ctrl.exists(timeout=timeout):
                return False
            try:
                ctrl.set_edit_text(text)
                return True
            except Exception:
                try:
                    ctrl.set_focus()
                    ctrl.type_keys(text, with_spaces=True)
                    return True
                except Exception:
                    return False

        return _run_with_timeout(_job, timeout + connect_timeout) is True

    return bool(_with_retries(_attempt, retries, delay))


def native_get_text(
    window=None,
    pid=None,
    *,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
) -> str | None:
    """Read a control's text/value. Returns the string or ``None``."""
    if not _ensure_pywinauto():
        return None

    def _job():
        top = _connect_top(window, pid, connect_timeout)
        if top is None:
            return None
        ctrl = top.child_window(
            **_selector_kwargs(title, control_type, auto_id, found_index)
        )
        if not ctrl.exists(timeout=timeout):
            return None
        try:
            return ctrl.window_text()
        except Exception:
            try:
                return ctrl.get_value()
            except Exception:
                return None

    result = _run_with_timeout(_job, timeout + connect_timeout)
    return None if result is _TIMEOUT_SENTINEL else result


def native_get_state(
    window=None,
    pid=None,
    *,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
) -> dict | None:
    """Return a control's state snapshot, or ``None`` if not found.

    ``{exists, visible, enabled, checked, value, control_type, rect}``.
    ``checked`` reflects the UIA toggle state for checkboxes/toggles
    (``None`` for controls without one).
    """
    if not _ensure_pywinauto():
        return None

    def _job():
        top = _connect_top(window, pid, connect_timeout)
        if top is None:
            return None
        ctrl = top.child_window(
            **_selector_kwargs(title, control_type, auto_id, found_index)
        )
        if not ctrl.exists(timeout=timeout):
            return {"exists": False}

        def _safe(fn, default=None):
            try:
                return fn()
            except Exception:
                return default

        checked = None
        toggle = _safe(lambda: ctrl.get_toggle_state())
        if toggle is not None:
            checked = bool(toggle)
        return {
            "exists": True,
            "visible": bool(_safe(ctrl.is_visible, False)),
            "enabled": bool(_safe(ctrl.is_enabled, False)),
            "checked": checked,
            "value": _safe(ctrl.window_text),
            "control_type": _safe(
                lambda: getattr(ctrl.element_info, "control_type", "") or ""
            ),
            "rect": _rect_to_box(ctrl),
        }

    result = _run_with_timeout(_job, timeout + connect_timeout)
    return None if result is _TIMEOUT_SENTINEL else result


def native_wait(
    window=None,
    pid=None,
    *,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    state: str = "exists",
    timeout: float = 10.0,
    connect_timeout: float = 2.0,
    poll_interval: float = 0.3,
) -> bool:
    """Wait until a control reaches ``state`` (or ``timeout`` elapses).

    ``state``: ``"exists"`` | ``"visible"`` | ``"enabled"`` | ``"ready"``
    (ready = exists + visible + enabled). Returns True when satisfied.
    """
    if not _ensure_pywinauto():
        return False

    wanted = {
        "exists": "exists",
        "visible": "visible",
        "enabled": "enabled",
        "ready": "exists visible enabled ready",
    }.get(state, "exists")

    def _job():
        top = _connect_top(window, pid, connect_timeout)
        if top is None:
            return False
        ctrl = top.child_window(
            **_selector_kwargs(title, control_type, auto_id, found_index)
        )
        try:
            ctrl.wait(wanted, timeout=timeout, retry_interval=poll_interval)
            return True
        except Exception:
            return False

    result = _run_with_timeout(_job, timeout + connect_timeout)
    return result is True

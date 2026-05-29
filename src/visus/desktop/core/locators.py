"""Precise element locators beyond OCR (Windows).

Three strategies, used in this precedence by :func:`locate_layered`:

  1. **Win32 menu** (``locate_win32_menu``) -- for classic native menu bars
     (e.g. legacy Notepad's "Arquivo / Editar / ..."). Reads the exact menu
     item rectangle straight from the OS via ``GetMenu`` /
     ``GetMenuItemRect``; instant and pixel-exact. Returns ``None`` for apps
     without a classic Win32 menu (modern WinUI, Electron, **Java Swing**).
  2. **OCR** (the bot's ``find_text``) -- pixel-based, works on ANYTHING that
     renders text (native, Electron, Java Swing/AWT, remote desktop). The
     universal fallback.
  3. **UIA directed** (``locate_uia_directed``) -- connects to the target
     process and does a *targeted* ``child_window`` (UIA FindFirst) instead
     of enumerating the whole tree, so it is fast. Works on accessible apps;
     usually blind to Java Swing unless the Java Access Bridge is enabled.

``get_window`` resolves a window by title (win32 enumeration, no focus
required) so callers can scope a capture to the right window even when it
is behind another.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# MF_BYPOSITION: address a menu item by its index rather than command id.
_MF_BYPOSITION = 0x400


# ---------------------------------------------------------------------------
# Window targeting
# ---------------------------------------------------------------------------


def find_window_handle(title_substring: str):
    """Return the hwnd of the first visible window whose title matches.

    Case-insensitive substring match. ``None`` if none match or win32 is
    unavailable (non-Windows). Does NOT require the window to be focused.

    Delegates to the single window enumeration in
    :mod:`visus.desktop.core.window` so ``find_window_handle`` / ``get_window``
    and ``list_windows`` can never disagree about what is visible.
    """
    try:
        from .window import _collect_windows

        matches = _collect_windows(title=title_substring)
    except Exception as exc:  # non-Windows or win32 unavailable
        logger.debug("window enumeration failed: %s", exc)
        return None
    return matches[0][0] if matches else None


def _window_dict(hwnd) -> dict | None:
    """Build ``{title, pid, hwnd, x, y, width, height}`` for ``hwnd``."""
    try:
        import win32gui
        import win32process
    except ImportError:
        return None
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        title = win32gui.GetWindowText(hwnd) or ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("window dict failed: %s", exc)
        return None
    return {
        "title": title,
        "pid": int(pid),
        "hwnd": int(hwnd),
        "x": int(left),
        "y": int(top),
        "width": int(right - left),
        "height": int(bottom - top),
    }


def get_window(title_substring: str) -> dict | None:
    """Resolve a window by title to ``{title, pid, hwnd, x, y, width, height}``.

    Returns ``None`` when no visible window matches. No focus required.
    Shares the SAME enumeration as ``list_windows`` (so the two never
    disagree); ``x/y/width/height`` are ``None`` while the window is
    minimized (its on-screen rect is meaningless then).
    """
    try:
        from .window import list_windows

        rows = list_windows(title=title_substring)
    except Exception as exc:  # non-Windows or win32 unavailable
        logger.debug("window enumeration failed: %s", exc)
        return None
    if not rows:
        return None
    win = rows[0]
    rect = win.get("rect") or {}
    return {
        "title": win["title"],
        "pid": win["pid"],
        "hwnd": win["hwnd"],
        "x": rect.get("x"),
        "y": rect.get("y"),
        "width": rect.get("width"),
        "height": rect.get("height"),
    }


def get_foreground_window() -> dict | None:
    """Resolve the currently-active window to the standard window dict.

    Used by ``capture_element`` for ``auto`` / ``native`` modes when the
    caller did not name a specific window -- the active window is the
    natural target.
    """
    try:
        import win32gui
    except ImportError:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
    except Exception:  # pragma: no cover - defensive
        return None
    if not hwnd:
        return None
    return _window_dict(hwnd)


# ---------------------------------------------------------------------------
# Strategy 1: Win32 classic menu
# ---------------------------------------------------------------------------


def _menu_label(hmenu, index: int) -> str:
    """Read a menu item's text via ``user32.GetMenuStringW`` (ctypes).

    pywin32's ``win32gui`` lacks ``GetMenuString`` on some builds, so we
    call the Win32 API directly. The leading '&' accelerator marker is
    stripped.
    """
    import ctypes

    user32 = ctypes.windll.user32
    length = user32.GetMenuStringW(hmenu, index, None, 0, _MF_BYPOSITION)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetMenuStringW(hmenu, index, buf, length + 1, _MF_BYPOSITION)
    return buf.value.replace("&", "")


def _normalize_rect(raw):
    """Coerce pywin32's GetMenuItemRect result into (left, top, right, bottom).

    Depending on the pywin32 build the call returns either ``(l, t, r, b)``
    or ``(flag, (l, t, r, b))``. Handle both.
    """
    if raw is None:
        return None
    if len(raw) == 4 and all(isinstance(v, int) for v in raw):
        return tuple(raw)
    if len(raw) == 2 and isinstance(raw[1], (tuple, list)) and len(raw[1]) == 4:
        return tuple(raw[1])
    return None


def locate_win32_menu(hwnd, query: str) -> tuple | None:
    """Locate a classic Win32 menu item by label; return ``(x, y, w, h)``.

    Returns ``None`` when the window has no classic menu (``GetMenu`` == 0),
    when no item label contains ``query`` (case-insensitive), or on any
    win32 error. The rectangle is in absolute screen coordinates.
    """
    if hwnd is None:
        return None
    try:
        import win32gui
    except ImportError:
        return None
    try:
        hmenu = win32gui.GetMenu(hwnd)
        if not hmenu:
            return None
        count = win32gui.GetMenuItemCount(hmenu)
        needle = (query or "").lower()
        for i in range(count):
            label = _menu_label(hmenu, i).lower()
            if needle and needle in label:
                rect = _normalize_rect(win32gui.GetMenuItemRect(hwnd, hmenu, i))
                if rect is None:
                    return None
                left, top, right, bottom = rect
                return (int(left), int(top), int(right - left), int(bottom - top))
    except Exception as exc:
        logger.debug("win32 menu lookup failed: %s", exc)
        return None
    return None


# ---------------------------------------------------------------------------
# Strategy 3: UIA directed (targeted FindFirst, not full enumeration)
# ---------------------------------------------------------------------------


def locate_uia_directed(
    query: str,
    pid: int | None = None,
    title_substring: str | None = None,
    timeout: float = 4.0,
) -> tuple | None:
    """Locate a control by a *targeted* UIA query; return ``(x, y, w, h)``.

    Connects to the target window (by ``pid`` or ``title_substring``) and
    uses ``child_window(title=..., ...).wrapper_object()`` which maps to
    UIA's native ``FindFirst`` -- fast, unlike enumerating ``descendants()``.
    Runs inside a worker thread bounded by ``timeout`` so a slow provider
    can never hang the caller.
    """
    try:
        import pywinauto  # noqa: F401
    except ImportError:
        return None

    result: dict = {"box": None}

    def _work() -> None:
        try:
            from pywinauto import Application

            app = Application(backend="uia")
            if pid is not None:
                app.connect(process=pid, timeout=1.0)
            elif title_substring is not None:
                app.connect(title_re=f".*{title_substring}.*", timeout=1.0)
            else:
                return
            top = app.top_window()
            # Targeted search by visible name (UIA FindFirst), best-match on
            # the control type that is most likely clickable.
            ctrl = top.child_window(title=query)
            if not ctrl.exists(timeout=timeout):
                # Fall back to a substring/regex title match.
                ctrl = top.child_window(title_re=f".*{query}.*")
                if not ctrl.exists(timeout=timeout):
                    return
            r = ctrl.rectangle()
            result["box"] = (
                int(r.left),
                int(r.top),
                int(r.right - r.left),
                int(r.bottom - r.top),
            )
        except Exception as exc:
            logger.debug("uia directed lookup failed: %s", exc)

    import threading

    worker = threading.Thread(target=_work, daemon=True)
    worker.start()
    worker.join(timeout=timeout + 1.0)
    if worker.is_alive():
        logger.debug("uia directed lookup exceeded timeout; giving up")
        return None
    return result["box"]


# ---------------------------------------------------------------------------
# Layered precedence: Win32 menu -> OCR -> UIA directed
# ---------------------------------------------------------------------------


def locate_layered(
    query: str,
    *,
    bot=None,
    hwnd=None,
    pid: int | None = None,
    title_substring: str | None = None,
    search_region: tuple | None = None,
    confidence_threshold: float = 75.0,
    uia_timeout: float = 4.0,
) -> tuple:
    """Locate ``query`` trying Win32 menu -> OCR -> UIA directed, in order.

    Returns ``(box, method)`` where ``box`` is ``(x, y, w, h)`` or ``None``
    and ``method`` is one of ``"win32" | "text" | "native" | None``.

    The default precedence favours the instant, pixel-exact Win32 menu path
    for native apps, falls back to OCR (which works on anything that renders
    text -- Java Swing, Electron, remote desktop), and finally tries the
    targeted UIA query for accessible controls OCR may have missed.
    """
    # 1. Win32 classic menu (needs a window handle).
    if hwnd is not None:
        box = locate_win32_menu(hwnd, query)
        if box is not None:
            return box, "win32"

    # 2. OCR.
    if bot is not None:
        try:
            box = bot.find_text(
                query,
                region=tuple(search_region) if search_region else None,
                confidence_threshold=confidence_threshold,
            )
        except Exception as exc:
            logger.debug("OCR layer failed: %s", exc)
            box = None
        if box is not None:
            return tuple(int(v) for v in box), "text"

    # 3. UIA directed.
    box = locate_uia_directed(
        query, pid=pid, title_substring=title_substring, timeout=uia_timeout
    )
    if box is not None:
        return box, "native"

    return None, None

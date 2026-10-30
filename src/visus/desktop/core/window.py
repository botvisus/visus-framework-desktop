"""Visus Desktop - Top-level window management.

Cross-platform window helpers. The public surface (``focus_window``,
``maximize_window``, ``minimize_window``, ``close_window``) dispatches
by OS:

  * Windows -> ``pywin32`` (``win32gui`` / ``win32con``).
  * Linux   -> ``xdotool`` + ``wmctrl`` via
    :mod:`visus.desktop.core.window_linux` (Phase 4 / X1).

On unsupported platforms the public helpers raise
:class:`~visus.desktop.exceptions.NotSupportedOnThisOS`.
"""

from __future__ import annotations

import sys

from ..exceptions import NotSupportedOnThisOS


def _require_windows() -> None:
    if sys.platform != "win32":
        raise NotSupportedOnThisOS(
            "Direct win32 API requires Windows."
        )


def find_window(title_substring: str) -> int | None:
    """Find the first visible top-level window matching a title substring.

    Returns the hwnd of the first *visible* window whose title contains
    ``title_substring`` (case-insensitive), or ``None`` if none matched.
    """
    _require_windows()
    import win32gui

    needle = title_substring.lower()
    matches: list[int] = []

    def _callback(hwnd: int, _extra: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd) or ""
        if needle in title.lower():
            matches.append(hwnd)
            return False  # stop enumeration early
        return True

    win32gui.EnumWindows(_callback, None)
    return matches[0] if matches else None


def window_region(title_substring: str) -> tuple[int, int, int, int] | None:
    """``(x, y, w, h)`` of the window whose title contains ``title_substring``:
    what an OCR / image search uses as its region with ``--window`` -- reading
    one window instead of the whole screen is several times faster.

    The visible frame (DWM's extended frame bounds), not ``GetWindowRect``,
    which on Windows 10/11 includes invisible resize borders (-8,-8 on a
    maximized window). ``None`` when no visible window matches or it is
    minimized: OCR and image matching read pixels on screen, so a minimized
    window has nothing to read.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None or win32gui.IsIconic(hwnd):
        return None
    rect = wintypes.RECT()
    dwmwa_extended_frame_bounds = 9
    try:
        hr = ctypes.windll.dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd), dwmwa_extended_frame_bounds,
            ctypes.byref(rect), ctypes.sizeof(rect),
        )
    except (AttributeError, OSError):
        hr = -1
    if hr != 0:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    else:
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
    if right <= left or bottom <= top:
        return None
    return (int(left), int(top), int(right - left), int(bottom - top))


# ---------------------------------------------------------------------------
# Fast window-state primitive (win32 + psutil only -- no UIA, no OCR)
#
# These thin helpers are the ONLY win32-touching surface; `ensure_window` /
# `list_windows` orchestrate them and stay unit-testable by patching them.
# ---------------------------------------------------------------------------


def _enum_visible_windows() -> list:
    """Return ``[(hwnd, title, pid)]`` for every visible top-level window."""
    _require_windows()
    import win32gui
    import win32process

    out: list = []

    def _cb(hwnd: int, _extra: object) -> bool:
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd) or ""
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            out.append((hwnd, title, int(pid)))
        return True

    win32gui.EnumWindows(_cb, None)
    return out


def _window_flags(hwnd) -> dict:
    """Read live state for ``hwnd``: minimized / maximized / foreground / rect."""
    import ctypes

    import win32gui

    # pywin32's win32gui lacks IsZoomed on some builds -- call user32 directly.
    is_zoomed = ctypes.windll.user32.IsZoomed
    return {
        "minimized": bool(win32gui.IsIconic(hwnd)),
        "maximized": bool(is_zoomed(int(hwnd))),
        "foreground": bool(win32gui.GetForegroundWindow() == hwnd),
        "rect": tuple(win32gui.GetWindowRect(hwnd)),
    }


def _restore(hwnd) -> None:
    """Un-minimize ``hwnd`` to its previous (non-minimized) size/position."""
    import win32con
    import win32gui

    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)


def _bring_to_front(hwnd) -> bool:
    """Force ``hwnd`` to the foreground, bypassing the focus-stealing lock.

    Windows refuses ``SetForegroundWindow`` from a process that is not the
    current foreground process (a background MCP server, a spawned script).
    The reliable workaround is to ``AttachThreadInput`` to BOTH the current
    foreground thread and the target window's thread for the duration of the
    call -- then the OS treats us as part of the active input queue and the
    activation succeeds. We always detach again, and fall back to a plain
    Z-order raise if anything errors.
    """
    import ctypes

    import win32con
    import win32gui

    try:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        if int(win32gui.GetForegroundWindow() or 0) == int(hwnd):
            return True

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
        user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        user32.AttachThreadInput.argtypes = [
            ctypes.c_ulong,
            ctypes.c_ulong,
            ctypes.c_int,
        ]
        for fn in (user32.SetForegroundWindow, user32.BringWindowToTop):
            fn.argtypes = [ctypes.c_void_p]

        cur = kernel32.GetCurrentThreadId()
        fg = win32gui.GetForegroundWindow()
        fg_tid = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        tgt_tid = user32.GetWindowThreadProcessId(int(hwnd), None)

        attached = []
        for tid in {fg_tid, tgt_tid}:
            if tid and tid != cur and user32.AttachThreadInput(cur, tid, True):
                attached.append(tid)
        try:
            user32.BringWindowToTop(int(hwnd))
            ok = bool(user32.SetForegroundWindow(int(hwnd)))
        finally:
            for tid in attached:
                user32.AttachThreadInput(cur, tid, False)

        if not ok:
            win32gui.BringWindowToTop(hwnd)
        # Let the activation take effect before callers read GetForegroundWindow
        # (otherwise ensure_window can report a stale foreground=False).
        import time

        time.sleep(0.06)
        return True
    except Exception:  # pragma: no cover - defensive
        try:
            win32gui.BringWindowToTop(hwnd)
        except Exception:
            pass
        return False


def _process_name(pid) -> str:
    """Return the process name for ``pid`` (cheap single lookup), or ''."""
    import psutil

    try:
        return psutil.Process(int(pid)).name() or ""
    except Exception:
        return ""


def _process_running(name: str) -> bool:
    """Full process scan -- True if any process name contains ``name``.

    Only used as a fallback when no matching *window* was found (e.g. an app
    running without a top-level window), so the common path never pays for it.
    """
    import psutil

    needle = (name or "").lower()
    for proc in psutil.process_iter(["name"]):
        try:
            pname = proc.info.get("name") or ""
            if needle and needle in pname.lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False


def _rect_dict(rect) -> dict:
    left, top, right, bottom = rect
    return {
        "x": int(left),
        "y": int(top),
        "width": int(right - left),
        "height": int(bottom - top),
    }


def _state_of(hwnd, title, pid) -> dict:
    flags = _window_flags(hwnd)
    return {
        "hwnd": int(hwnd),
        "title": title,
        "pid": int(pid),
        "minimized": flags["minimized"],
        "maximized": flags["maximized"],
        "foreground": flags["foreground"],
        "rect": None if flags["minimized"] else _rect_dict(flags["rect"]),
    }


def _collect_windows(title=None, process=None) -> list:
    """Filter visible windows by title substring and/or process name.

    Process filtering resolves each candidate window's process name on demand
    (cheap), so it never scans the whole process table.

    Com ``title``, os matches saem ORDENADOS por especificidade — título EXATO
    (case-insensitive) primeiro, depois prefixo, depois substring solta — com a
    ordem de enumeração (Z-order) como desempate (sort estável). Sem isso,
    ``find_window_handle("Calculadora")`` casava a janela do Explorer da pasta
    ``example-calculadora`` (substring incidental em "example-calculadora") no
    lugar da Calculadora real, e todo native_* mirava a janela errada.
    """
    needle_t = (title or "").lower()
    needle_p = (process or "").lower()
    out = []
    for hwnd, wtitle, pid in _enum_visible_windows():
        if title and needle_t not in wtitle.lower():
            continue
        if process and needle_p not in _process_name(pid).lower():
            continue
        out.append((hwnd, wtitle, pid))
    if title:

        def _rank(entry) -> int:
            wl = entry[1].lower()
            if wl == needle_t:
                return 0
            if wl.startswith(needle_t):
                return 1
            return 2

        out.sort(key=_rank)  # estável: preserva o Z-order dentro de cada rank
    return out


def list_windows(title: str | None = None, process: str | None = None) -> list:
    """List visible windows matching ``title`` (substring) and/or ``process``.

    Each entry is ``{hwnd, title, pid, minimized, maximized, foreground, rect}``.
    Fast (pure win32) and read-only -- nothing is focused or moved.
    """
    return [
        _state_of(hwnd, wtitle, pid)
        for hwnd, wtitle, pid in _collect_windows(title=title, process=process)
    ]


def ensure_window(
    title: str | None = None,
    process: str | None = None,
    *,
    show: bool = True,
    foreground: bool = True,
) -> dict:
    """Quickly resolve a window's state and (optionally) bring it to the front.

    Match by ``title`` (substring, case-insensitive), ``process`` (name
    substring, e.g. ``"notepad.exe"``), or both. Matching by process avoids
    title false-positives (e.g. ``"Notepad"`` matching an editor showing a
    file named ``notepad_demo.py``).

    With ``show=True`` a minimized window is restored; with ``foreground=True``
    it is brought to the front. Returns a single dict::

        {found, running, hwnd, pid, title, minimized, maximized,
         foreground, rect, shown, matches}

    ``running`` reflects the process check (``None`` when ``process`` was not
    given). ``rect`` is ``None`` while the window stays minimized. ``shown`` is
    True when this call restored and/or raised the window. ``matches`` is how
    many windows matched (use it to detect ambiguity).

    Pure win32 + psutil -- milliseconds, no UIA/OCR. Raises ``ValueError`` if
    neither ``title`` nor ``process`` is given.
    """
    if not title and not process:
        raise ValueError("ensure_window requires `title` and/or `process`.")

    candidates = _collect_windows(title=title, process=process)
    running = None
    if process is not None:
        running = True if candidates else _process_running(process)

    if not candidates:
        return {
            "found": False,
            "running": running,
            "hwnd": None,
            "pid": None,
            "title": None,
            "minimized": False,
            "maximized": False,
            "foreground": False,
            "rect": None,
            "shown": False,
            "matches": 0,
        }

    hwnd, wtitle, pid = candidates[0]
    initial = _window_flags(hwnd)
    shown = False
    if show:
        if initial["minimized"]:
            _restore(hwnd)
            shown = True
        if foreground and _bring_to_front(hwnd):
            shown = True

    final = _window_flags(hwnd)
    return {
        "found": True,
        "running": running if process is not None else True,
        "hwnd": int(hwnd),
        "pid": int(pid),
        "title": wtitle,
        "minimized": final["minimized"],
        "maximized": final["maximized"],
        "foreground": final["foreground"],
        "rect": None if final["minimized"] else _rect_dict(final["rect"]),
        "shown": shown,
        "matches": len(candidates),
    }


def _dispatch_or_raise(win_impl, linux_fn, *args):
    """Pick the OS backend; raise NotSupportedOnThisOS otherwise."""
    if sys.platform == "win32":
        return win_impl(*args)
    if sys.platform.startswith("linux"):
        return linux_fn(*args)
    raise NotSupportedOnThisOS(
        f"Window management is not implemented on {sys.platform!r}."
    )


def _win_focus(title_substring: str) -> bool:
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.SetForegroundWindow(hwnd)
    return True


def _win_maximize(title_substring: str) -> bool:
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    return True


def _win_minimize(title_substring: str) -> bool:
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return True


def _win_close(title_substring: str) -> bool:
    import win32con
    import win32gui

    hwnd = find_window(title_substring)
    if hwnd is None:
        return False
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    return True


def focus_window(title_substring: str) -> bool:
    """Bring a window matching ``title_substring`` to the foreground."""
    from . import window_linux as _linux

    return _dispatch_or_raise(_win_focus, _linux.focus_window_linux, title_substring)


def maximize_window(title_substring: str) -> bool:
    """Maximize a window matching ``title_substring``."""
    from . import window_linux as _linux

    return _dispatch_or_raise(
        _win_maximize, _linux.maximize_window_linux, title_substring
    )


def minimize_window(title_substring: str) -> bool:
    """Minimize a window matching ``title_substring``."""
    from . import window_linux as _linux

    return _dispatch_or_raise(
        _win_minimize, _linux.minimize_window_linux, title_substring
    )


def close_window(title_substring: str) -> bool:
    """Request that a window matching ``title_substring`` close (posts WM_CLOSE on Win)."""
    from . import window_linux as _linux

    return _dispatch_or_raise(_win_close, _linux.close_window_linux, title_substring)


def foreground_title() -> str:
    """O título da janela em foco agora (onde o teclado vai cair), ou ""."""
    if sys.platform == "win32":
        import win32gui

        return str(win32gui.GetWindowText(win32gui.GetForegroundWindow()) or "")
    import shutil
    import subprocess

    if not shutil.which("xdotool"):
        return ""
    done = subprocess.run(  # noqa: S603,S607
        ["xdotool", "getactivewindow", "getwindowname"], capture_output=True, text=True
    )
    return done.stdout.strip() if done.returncode == 0 else ""


def wait_front_window(title_substring: str, *, timeout: float = 30.0) -> str | None:
    """Espera a janela com ``title_substring`` ficar PRONTA: em foco e com o título
    parado por um instante (3 olhadas, 0,5 s entre elas) -- a tela de carregamento
    ("Opening - Excel") troca de título ou some. Devolve o título, ou None no prazo."""
    import time

    want = title_substring.lower()
    deadline = time.monotonic() + max(0.0, timeout)
    seen, steady = "", 0
    while True:
        found = ensure_window(title=title_substring, show=True, foreground=True)
        front = foreground_title()
        if found.get("found") and want in front.lower():
            steady = steady + 1 if front == seen else 1
            seen = front
            if steady >= 3:
                return front
        else:
            seen, steady = "", 0
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.5)


def front_window(title_substring: str, *, timeout: float = 3.0) -> str | None:
    """Traz para a frente a janela com ``title_substring`` e CONFERE que ela é a janela
    em foco -- como uma pessoa olha antes de digitar. Devolve o título dela, ou None
    quando outra janela continua na frente (aí nada deve ser digitado)."""
    import time

    want = title_substring.lower()
    deadline = time.monotonic() + timeout
    while True:
        try:
            ensure_window(title=title_substring, show=True, foreground=True)
        except Exception:  # noqa: BLE001 -- ainda sem a janela: tenta até o prazo
            pass
        current = foreground_title()
        if want in current.lower():
            return current
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.25)

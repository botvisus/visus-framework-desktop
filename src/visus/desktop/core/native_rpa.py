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


def _selector_kwargs(
    title, control_type, auto_id, found_index, backend="uia", title_re=None
) -> dict:
    """Build the ``child_window`` kwargs from the selector arguments.

    The ``win32`` backend has no UIA ``control_type``/``auto_id`` concept, so
    ``control_type`` is mapped to ``class_name`` (e.g. ``Edit``) and ``auto_id``
    is ignored there. Under ``uia`` the UIA-native keys are used as-is.
    """
    kwargs: dict = {}
    if title is not None:
        kwargs["title"] = title
    elif title_re is not None:
        kwargs["title_re"] = title_re
    if control_type is not None:
        if backend == "win32":
            kwargs["class_name"] = control_type
        else:
            kwargs["control_type"] = control_type
    if auto_id is not None and backend != "win32":
        kwargs["auto_id"] = auto_id
    if found_index is not None:
        kwargs["found_index"] = found_index
    return kwargs


def _connect_top(window, pid, connect_timeout: float, backend="uia"):
    """Connect to the target app and return its top window, or None.

    ``backend`` is ``"uia"`` (default; right for WPF/WinUI/Electron/browsers)
    or ``"win32"`` (fast + reliable for classic Win32 controls like Notepad's
    Edit, where the UIA provider can stall on enumeration).

    ``window=`` resolve o HANDLE por win32 (substring, sem UIA) e prende o UIA
    NAQUELE hwnd — nunca em ``Desktop().window(title_re=...)``. Duas armadilhas
    mortais que essa rota por handle elimina de uma vez (bug real, 2026-07-12):

    1. UWP: a janela pertence ao ``ApplicationFrameHost.exe``, que hospeda
       TODAS as janelas UWP — ``connect(process) + top_window()`` devolve a
       hospedada que estiver por cima NAQUELE instante (a Calculadora só "por
       sorte", em primeiro plano). O handle é a janela-frame CERTA, sempre.
    2. Enumeração: ``Desktop().window(title_re=...)`` faz um ``FindFirst`` na
       RAIZ do desktop, varrendo todos os topos. Se QUALQUER janela do sistema
       tem um provider UIA lento/travado, esse FindFirst BLOQUEIA por tempo
       indefinido (o ``timeout`` do pywinauto só é checado ENTRE tentativas,
       não durante a chamada COM presa) — na worker thread o
       ``_run_with_timeout`` mata por join e devolve False em silêncio; na main
       trava de vez. Amarrar no handle não varre nada: ~50ms, imune ao provider
       podre do vizinho (medido: rota por título trava >8s, por handle resolve
       em ~0.05s — idêntico em STA e MTA).
    """
    import pywinauto  # noqa: F401
    from pywinauto import Application, Desktop

    if window is not None and pid is None:
        from .locators import find_window_handle

        hwnd = find_window_handle(window)
        if not hwnd:
            return None
        spec = Desktop(backend=backend).window(handle=hwnd)
        return spec if spec.exists(timeout=connect_timeout) else None

    app = Application(backend=backend)
    if pid is not None:
        app.connect(process=pid, timeout=connect_timeout)
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
    backend: str = "uia",
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
        top = _connect_top(window, pid, connect_timeout, backend)
        if top is None:
            return []
        return _walk_tree(top, max_depth)

    result = _run_with_timeout(_job, timeout)
    return [] if result is _TIMEOUT_SENTINEL or result is None else result


def _walk_tree(top, max_depth: int, max_nodes: int = 5000) -> list[dict]:
    """Pre-order walk of ``children()`` — the same order pywinauto's
    ``descendants()`` uses, so a ``found_index`` counted here selects the same
    control later. ``max_nodes`` stops a runaway walk on huge trees."""
    nodes: list[dict] = []

    def _walk(element, depth):
        if depth > max_depth or len(nodes) >= max_nodes:
            return
        try:
            children = element.children()
        except Exception:
            return
        for child in children:
            if len(nodes) >= max_nodes:
                return
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


# What an agent can act on. Text, panes, groups and the like are structure: they
# would cost tokens in every snapshot and give nothing to click.
ACTIONABLE_CONTROL_TYPES = frozenset(
    {
        "Button",
        "SplitButton",
        "Edit",
        "Document",
        "CheckBox",
        "RadioButton",
        "ComboBox",
        "MenuItem",
        "ListItem",
        "TabItem",
        "Hyperlink",
        "TreeItem",
        "DataItem",
        "Spinner",
        "Slider",
    }
)


def select_actionable(nodes: list[dict]) -> list[dict]:
    """Number the actionable controls of a walked tree, ready to be acted on by index.

    Each item carries the exact selector that finds it again: title + control_type,
    plus auto_id when it has one, plus ``found_index`` — counted over the SAME
    criteria that selector will use (an empty auto_id is not a criterion), so two
    "Close" buttons become found_index 0 and 1 and never get swapped.
    """
    items: list[dict] = []
    for pos, node in enumerate(nodes):
        ctype = node.get("control_type") or ""
        if ctype not in ACTIONABLE_CONTROL_TYPES:
            continue
        title = node.get("title") or ""
        auto_id = node.get("auto_id") or ""
        found_index = sum(
            1
            for prev in nodes[:pos]
            if (prev.get("control_type") or "") == ctype
            and (prev.get("title") or "") == title
            and (not auto_id or (prev.get("auto_id") or "") == auto_id)
        )
        items.append(
            {
                "index": len(items),
                "control_type": ctype,
                "title": title,
                "auto_id": auto_id,
                "found_index": found_index,
                "rect": node.get("rect"),
            }
        )
    return items


def native_snapshot_nodes(
    window=None,
    pid=None,
    *,
    max_depth: int = 25,
    timeout: float = 10.0,
    connect_timeout: float = 2.0,
    backend: str = "uia",
) -> tuple[str, list[dict]]:
    """``(window title, walked nodes)`` of the target window, deeper than
    ``native_dump_tree`` (actionable controls sit several levels down in modern
    apps). ``(None, [])`` when pywinauto is missing, no window matches, or it
    times out -- so "no such window" never reads as "a window with no controls"."""
    if not _ensure_pywinauto():
        return None, []

    def _job():
        top = _connect_top(window, pid, connect_timeout, backend)
        if top is None:
            return None, []
        try:
            title = top.window_text() or ""
        except Exception:
            title = ""
        return title, _walk_tree(top, max_depth)

    result = _run_with_timeout(_job, timeout)
    return (None, []) if result is _TIMEOUT_SENTINEL or result is None else result


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
    backend: str = "uia",
    title_re=None,
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
            top = _connect_top(window, pid, connect_timeout, backend)
            if top is None:
                return False
            ctrl = top.child_window(
                **_selector_kwargs(title, control_type, auto_id, found_index, backend, title_re)
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
    backend: str = "uia",
) -> bool:
    """Set the text of an editable control located by selector -- like a person.

    Focuses the control, checks its window is the one in front, selects all and
    types the text key by key, then reads it back. Many apps only take what comes
    from the keyboard: the Save As name box SHOWED a name set through the UIA value
    pattern and still saved under the old one. When the window cannot come to the
    front (nothing is typed then), the value pattern is the fallback. Returns True
    when the control ends up holding ``text``.
    """
    if not _ensure_pywinauto():
        return False

    def _attempt():
        def _job():
            top = _connect_top(window, pid, connect_timeout, backend)
            if top is None:
                return False
            ctrl = top.child_window(
                **_selector_kwargs(title, control_type, auto_id, found_index, backend)
            )
            if not ctrl.exists(timeout=timeout):
                return False
            wrapper = ctrl.wrapper_object()
            if _type_into(wrapper, text):
                return True
            try:
                wrapper.set_edit_text(text)
            except Exception:
                return False
            value = _control_value(wrapper)
            return value is None or value == text

        return _run_with_timeout(_job, timeout + connect_timeout) is True

    return bool(_with_retries(_attempt, retries, delay))


def _control_value(wrapper):
    """O texto escrito num campo (UIA ValuePattern), ou None quando não há um."""
    for read in (
        lambda: wrapper.iface_value.CurrentValue,
        lambda: wrapper.get_value(),
    ):
        try:
            value = read()
        except Exception:
            continue
        if value is not None:
            return str(value)
    return None


def _type_into(wrapper, text: str) -> bool:
    """Foca o campo e, com a janela dele na frente, seleciona tudo e digita como uma
    pessoa; confere o resultado. False quando a janela não vem para a frente (aí
    nenhuma tecla sai) ou o campo não ficou com o texto."""
    import sys

    try:
        wrapper.set_focus()
    except Exception:
        return False
    if sys.platform == "win32":
        import win32gui

        # a janela-RAIZ do próprio campo (pela cadeia de pais, não a do dono): um campo
        # do "Salvar como" fica no diálogo, que é a janela em foco -- o
        # top_level_parent() subia até a janela do Excel, dona do diálogo
        element = wrapper
        handle = 0
        for _ in range(30):
            handle = int(
                getattr(getattr(element, "element_info", None), "handle", 0) or 0
            )
            if handle:
                break
            try:
                element = element.parent()
            except Exception:
                return False
            if element is None:
                return False
        if not handle:
            return False
        root = win32gui.GetAncestor(handle, 2)  # GA_ROOT
        if int(win32gui.GetForegroundWindow() or 0) != int(root):
            return False
    import pyautogui

    from visus.desktop.core.human_typing import type_like_a_person

    pyautogui.hotkey("ctrl", "a", _pause=False)
    type_like_a_person(text, 0.01)
    value = _control_value(wrapper)
    return value is None or value == text


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
    backend: str = "uia",
) -> str | None:
    """Read a control's text/value. Returns the string or ``None``."""
    if not _ensure_pywinauto():
        return None

    def _job():
        top = _connect_top(window, pid, connect_timeout, backend)
        if top is None:
            return None
        ctrl = top.child_window(
            **_selector_kwargs(title, control_type, auto_id, found_index, backend)
        )
        if not ctrl.exists(timeout=timeout):
            return None
        # o VALOR de um campo (o que está escrito nele) vem antes do nome: o nome de um
        # Edit é o rótulo ("File name:"), não o texto
        wrapper = ctrl.wrapper_object()
        value = _control_value(wrapper)
        if value:
            return value
        try:
            return wrapper.window_text()
        except Exception:
            return value

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
    backend: str = "uia",
    title_re=None,
) -> dict | None:
    """Return a control's state snapshot, or ``None`` if not found.

    ``{exists, visible, enabled, checked, value, control_type, rect}``.
    ``checked`` reflects the UIA toggle state for checkboxes/toggles
    (``None`` for controls without one).
    """
    if not _ensure_pywinauto():
        return None

    def _job():
        top = _connect_top(window, pid, connect_timeout, backend)
        if top is None:
            return None
        ctrl = top.child_window(
            **_selector_kwargs(
                title, control_type, auto_id, found_index, backend, title_re
            )
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
    backend: str = "uia",
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
        top = _connect_top(window, pid, connect_timeout, backend)
        if top is None:
            return False
        ctrl = top.child_window(
            **_selector_kwargs(title, control_type, auto_id, found_index, backend)
        )
        try:
            ctrl.wait(wanted, timeout=timeout, retry_interval=poll_interval)
            return True
        except Exception as exc:
            # NUNCA silencioso: um wait que falha por infra (COM, conexão,
            # seletor) parecia idêntico a "elemento não apareceu" — logue a
            # causa real para o próximo caçador de fantasmas.
            logger.debug("native_wait(%s) failed: %s", wanted, exc)
            return False

    result = _run_with_timeout(_job, timeout + connect_timeout)
    return result is True

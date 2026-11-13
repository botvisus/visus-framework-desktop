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

Inside :func:`visus.desktop.rpa` (any open task session) ``native_click``,
``native_set_text``, ``native_get_text`` and ``native_wait`` are also steps of
the run report -- with the control highlighted on screen in the bot's overlay
style, boxed on the step screenshot, and a ``False`` / ``None`` result stopping
the run like any failed action. Outside one they behave exactly as described
above.
"""

from __future__ import annotations

import logging
import threading
import time

from .recording import native_target, records_native

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


def _is_window(hwnd) -> bool:
    """A janela ``hwnd`` ainda existe?"""
    try:
        import win32gui

        return bool(win32gui.IsWindow(int(hwnd)))
    except Exception:
        return False


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
        # a AppWindow do use_app traz o handle: vale mesmo que o título seja outro
        # ("Pasta1 - Excel" no lugar do "vendas.xlsx - Excel" da captura); handle
        # morto (a janela fechou) cai para o título, como uma janela por texto
        hwnd = getattr(window, "hwnd", None)
        if not (hwnd and _is_window(hwnd)):
            from .locators import find_window_handle

            hwnd = find_window_handle(str(window))
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


def _on_target(ctrl, *, highlight: bool = True) -> None:
    """Hand the control about to be acted on to an open recording (``rpa()``):
    it is highlighted on screen and boxed on the step screenshot. No-op outside."""
    box = _rect_to_box(ctrl)
    if box:
        native_target(
            (box["x"], box["y"], box["width"], box["height"]), highlight=highlight
        )


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


@records_native("native_click")
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
    at=None,
) -> bool:
    """Click a control located by selector -- no coordinates, no image.

    ``method``: ``"invoke"`` uses the UIA InvokePattern (no mouse movement,
    most robust); ``"click"`` uses ``click_input`` (real mouse on the
    control center); ``"auto"`` (default) tries invoke then falls back to
    click_input. ``retries`` + ``delay`` re-attempt a flaky control.
    ``at=(x, y)``: click THAT point inside the control (offset in pixels from its
    top-left corner) with the real mouse -- where it matters on a surface, like
    Paint's canvas (fill, pick a color, place a point).
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
            _on_target(ctrl)
            if at is not None:  # um ponto da superfície: o mouse de verdade, ali
                rect = ctrl.rectangle()
                point, _ = _drag_points((rect.left, rect.top), at, at)
                if button == "left":
                    _activate_if_needed(rect, point)
                _mouse_click(point, button, 2 if double else 1)
                _mouse_on(rect)
                return True
            if double:
                ctrl.double_click_input()
                _mouse_on(ctrl.rectangle())
                return True
            if method in ("invoke", "auto"):
                try:
                    ctrl.invoke()
                    return True
                except Exception:
                    if method == "invoke":
                        return False
            ctrl.click_input(button=button)
            _mouse_on(ctrl.rectangle())
            return True

        return _run_with_timeout(_job, timeout + connect_timeout) is True

    return bool(_with_retries(_attempt, retries, delay))


def _drag_points(origin, start, end):
    """Os pontos de tela do arrasto: ``start``/``end`` são deslocamentos (px) a partir
    do canto superior esquerdo do controle."""
    left, top = int(origin[0]), int(origin[1])
    return (
        (left + int(start[0]), top + int(start[1])),
        (left + int(end[0]), top + int(end[1])),
    )


# O controle em que o MOUSE de verdade agiu por último (o retângulo dele). Uma superfície
# WinUI 3 -- a tela de desenho do Paint do Windows 11 -- gasta o 1º aperto que chega
# depois de o mouse agir em outro controle (a faixa de ferramentas): ele só a ativa.
# Medido: Paint novo, clique na Oval, arrasto na tela = 0 px de tinta; com um clique de
# ativação no ponto de início antes = a elipse. Arrastos seguidos no mesmo controle
# não precisam (e não ganham) o clique extra.
_last_mouse_target = {"rect": None}


def _rect_key(rect):
    return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))


def _mouse_on(rect) -> None:
    """O mouse de verdade agiu neste controle."""
    _last_mouse_target["rect"] = _rect_key(rect)


def _activate_if_needed(rect, point) -> None:
    """Antes de apertar numa superfície: se o mouse agiu por último em OUTRO controle,
    um clique no próprio ponto de início ativa a superfície (o aperto que ela gasta)."""
    if _last_mouse_target["rect"] != _rect_key(rect):
        _mouse_click(point, "left", 1)
        time.sleep(0.3)
    _mouse_on(rect)


def _mouse_click(point, button: str, clicks: int) -> None:
    import pyautogui

    pyautogui.click(point[0], point[1], clicks=clicks, interval=0.08, button=button)


def _mouse_drag(src, dst, button: str, duration: float) -> None:
    """Aperta em ``src``, arrasta até ``dst`` em ``duration`` s e solta -- com os
    movimentos no meio, como uma pessoa (o Paint desenha seguindo o mouse)."""
    import pyautogui

    pyautogui.moveTo(src[0], src[1])
    pyautogui.dragTo(dst[0], dst[1], duration=duration, button=button)


@records_native("native_drag")
def native_drag(
    window=None,
    pid=None,
    *,
    start,
    end,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    button: str = "left",
    duration: float = 0.4,
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
    retries: int = 0,
    delay: float = 0.3,
    backend: str = "uia",
    title_re=None,
) -> bool:
    """Drag INSIDE a control located by selector -- draw a shape on Paint's canvas,
    move a slider, select a range. ``start`` / ``end`` are ``(x, y)`` offsets in
    pixels from the control's top-left corner, so the drag follows the control
    wherever the window is. Real mouse: press at ``start``, move to ``end`` over
    ``duration`` seconds, release. Returns True on success."""
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
            _on_target(ctrl)
            rect = ctrl.rectangle()
            src, dst = _drag_points((rect.left, rect.top), start, end)
            if button == "left":
                _activate_if_needed(rect, src)
            _mouse_drag(src, dst, button, duration)
            _mouse_on(rect)
            return True

        return _run_with_timeout(_job, timeout + connect_timeout + duration) is True

    return bool(_with_retries(_attempt, retries, delay))


def _wheel(point, amount: int) -> None:
    from .mouse_extra import scroll

    scroll(int(amount), int(point[0]), int(point[1]))


@records_native("native_scroll")
def native_scroll(
    window=None,
    pid=None,
    *,
    amount: int,
    at=None,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
    retries: int = 0,
    delay: float = 0.3,
    backend: str = "uia",
    title_re=None,
) -> bool:
    """Turn the mouse wheel over a control located by selector -- ``amount`` notches,
    positive up / negative down -- at ``at=(x, y)`` inside it (offset from its
    top-left corner) or its center: a list, a document, a canvas. Returns True."""
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
            _on_target(ctrl)
            rect = ctrl.rectangle()
            if at is None:
                point = ((rect.left + rect.right) // 2, (rect.top + rect.bottom) // 2)
            else:
                point, _ = _drag_points((rect.left, rect.top), at, at)
            _wheel(point, amount)
            _mouse_on(rect)
            return True

        return _run_with_timeout(_job, timeout + connect_timeout) is True

    return bool(_with_retries(_attempt, retries, delay))


@records_native("native_set_text")
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
    secret: bool = False,
) -> bool:
    """Set the text of an editable control located by selector -- like a person.

    Focuses the control, checks its window is the one in front, selects all and
    types the text key by key, then reads it back. Many apps only take what comes
    from the keyboard: the Save As name box SHOWED a name set through the UIA value
    pattern and still saved under the old one. When the window cannot come to the
    front (nothing is typed then), the value pattern is the fallback. Returns True
    when the control ends up holding ``text``.

    ``secret=True`` (a password): typed the same, shown as ``••••••`` in the run
    report.
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
            _on_target(ctrl)
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


@records_native("native_get_text")
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
        _on_target(ctrl)
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


@records_native("native_wait")
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
            # boxed on the step screenshot; no on-screen highlight for a wait
            _on_target(ctrl, highlight=False)
            return True
        except Exception as exc:
            # NUNCA silencioso: um wait que falha por infra (COM, conexão,
            # seletor) parecia idêntico a "elemento não apareceu" — logue a
            # causa real para o próximo caçador de fantasmas.
            logger.debug("native_wait(%s) failed: %s", wanted, exc)
            return False

    result = _run_with_timeout(_job, timeout + connect_timeout)
    return result is True

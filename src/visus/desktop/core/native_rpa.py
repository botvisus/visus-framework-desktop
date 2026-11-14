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

from .outcome import ActionOutcome
from .recording import native_target, records_native

logger = logging.getLogger(__name__)

_TIMEOUT_SENTINEL = object()


class NativeAppUnresponsive(Exception):
    """A janela alvo não está atendendo mensagens (o programa travou)."""


def _run_capturing(fn, timeout: float):
    """Como ``_run_with_timeout``, mas devolve ``(valor, exceção, estourou_o_tempo)``
    para quem precisa dizer POR QUE falhou (o ``ActionOutcome``)."""
    box: dict = {"value": None, "error": None}

    def _work():
        try:
            box["value"] = fn()
        except Exception as exc:  # o chamador classifica
            box["error"] = exc

    worker = threading.Thread(target=_work, daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        return None, None, True
    return box["value"], box["error"], False


def _ensure_pumping(hwnd) -> None:
    from .win_health import window_is_pumping

    if hwnd and not window_is_pumping(int(hwnd)):
        raise NativeAppUnresponsive(
            "the program is not responding (its window does not answer) -- wait for it, then retry"
        )


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
        # app travado: ElementFromHandle (WM_GETOBJECT) bloquearia sem prazo -- pergunte antes
        _ensure_pumping(hwnd)
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
        if fw.get("hwnd"):
            _ensure_pumping(fw["hwnd"])
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
    except ImportError:
        logger.debug("pywinauto not installed; native_rpa unavailable")
        return False
    try:
        from .uia_batch import harden_client

        harden_client()  # toda chamada UIA com prazo (o pywinauto cria o cliente sem)
    except Exception as exc:  # pragma: no cover - defensivo
        logger.debug("UIA client hardening skipped: %s", exc)
    return True


class NodeList(list):
    """Os nós de um walk, dizendo se a leitura ficou incompleta: ``unreadable`` ramos que
    deram erro ao ler, ``truncated`` quando o limite de nós cortou."""

    unreadable: int = 0
    truncated: bool = False

    @property
    def partial(self) -> bool:
        return bool(self.unreadable or self.truncated)


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


# Tipos que só viram item do snapshot quando ANUNCIAM uma ação (um Custom/Group
# clicável do WPF ou do Chromium sumia da lista fixa de tipos).
_CANDIDATE_CONTROL_TYPES = frozenset({"Custom", "Group", "Pane", "Image"})
# Ações que fazem um nó merecer número: rolar sozinho não conta (o Chromium anuncia
# rolagem em quase todo nó).
_PRIMARY_ACTIONS = frozenset({"invoke", "toggle", "expand", "select", "value"})
_WRAPPER_TYPES = frozenset({"Group", "Custom", "Pane"})
_CHROMIUM_CLASS = "Chrome_WidgetWin_1"
_MAX_RAW_DEPTH = 50


def _is_web_wrapper(node: dict) -> bool:
    """Um grupo anônimo do Chromium (sem nome, sem id, sem ação): o Chromium empilha
    dezenas deles sobre o conteúdo, e contando-os o snapshot não chegava aos botões.
    Medido no agent-desktop (A16-8): 54 de 81 grupos de uma janela Electron são assim."""
    return (
        node.get("control_type") in _WRAPPER_TYPES
        and not node.get("title")
        and not node.get("auto_id")
        and not (set(node.get("actions") or ()) & _PRIMARY_ACTIONS)
    )


def _with_extras(control_type: str) -> bool:
    return control_type in ACTIONABLE_CONTROL_TYPES or control_type in _CANDIDATE_CONTROL_TYPES


def _walk_tree(top, max_depth: int, max_nodes: int = 5000) -> NodeList:
    """Pre-order walk of ``children()`` — the same order pywinauto's
    ``descendants()`` uses, so a ``found_index`` counted here selects the same
    control later. ``max_nodes`` stops a runaway walk on huge trees.

    Each actionable-looking node also carries its states and announced actions. Under a
    Chromium/Electron window an anonymous wrapper group does not count as a level of
    ``max_depth`` (its raw nesting is still capped), so web content is reachable at the
    usual depth.

    UIA: read in batch (``uia_batch.walk`` -- one cross-process round trip per node, every
    property cached); a branch that failed to read counts in ``unreadable`` instead of
    vanishing. Win32 backend (or no cache support): the per-property walk."""
    try:
        chromium = (getattr(top.element_info, "class_name", "") or "") == _CHROMIUM_CLASS
    except Exception:
        chromium = False

    def skip(node):
        return chromium and _is_web_wrapper(node)

    import ctypes

    element = getattr(getattr(top, "element_info", None), "element", None)
    # só um ponteiro COM de verdade (IUIAutomationElement) vai pelo lote
    if isinstance(element, ctypes._Pointer) and hasattr(element, "FindAllBuildCache"):
        try:
            from .uia_batch import walk

            read = walk(
                element, max_depth=max_depth, max_nodes=max_nodes,
                max_raw_depth=_MAX_RAW_DEPTH, with_extras=_with_extras, skip_level=skip,
            )
            nodes = NodeList(read.nodes)
            nodes.unreadable, nodes.truncated = read.unreadable, read.truncated
            return nodes
        except Exception as exc:
            logger.debug("batch walk failed, falling back: %s", exc)
    return _walk_tree_slow(top, max_depth, max_nodes, skip)


def _walk_tree_slow(top, max_depth: int, max_nodes: int, skip) -> NodeList:
    from .native_patterns import read_node_extras

    nodes = NodeList()

    def _walk(element, depth, raw_depth):
        if depth > max_depth or raw_depth > _MAX_RAW_DEPTH:
            return
        if len(nodes) >= max_nodes:
            nodes.truncated = True
            return
        try:
            children = element.children()
        except Exception:
            nodes.unreadable += 1
            return
        for child in children:
            if len(nodes) >= max_nodes:
                nodes.truncated = True
                return
            try:
                info = child.element_info
                node = {
                    "depth": depth,
                    "control_type": getattr(info, "control_type", "") or "",
                    "title": (info.name or ""),
                    "auto_id": getattr(info, "automation_id", "") or "",
                    "rect": _rect_to_box(child),
                }
                if _with_extras(node["control_type"]):
                    node.update(read_node_extras(info))
                nodes.append(node)
            except Exception:
                nodes.unreadable += 1
                continue
            _walk(child, depth + (0 if skip(node) else 1), raw_depth + 1)

    _walk(top, 1, 1)
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
    import bisect

    from .native_patterns import states_of

    by_name: dict = {}
    by_id: dict = {}
    for pos, node in enumerate(nodes):
        key = (node.get("control_type") or "", node.get("title") or "")
        by_name.setdefault(key, []).append(pos)
        by_id.setdefault(key + (node.get("auto_id") or "",), []).append(pos)

    items: list[dict] = []
    for pos, node in enumerate(nodes):
        if not is_actionable(node):
            continue
        ctype = node.get("control_type") or ""
        title = node.get("title") or ""
        auto_id = node.get("auto_id") or ""
        # o critério do seletor guardado: tipo + nome (+ auto_id quando houver)
        same = by_id[(ctype, title, auto_id)] if auto_id else by_name[(ctype, title)]
        item = {
            "index": len(items),
            "control_type": ctype,
            "title": title,
            "auto_id": auto_id,
            "found_index": bisect.bisect_left(same, pos),
            # quantos controles casam este seletor AGORA: na hora de agir, um número
            # diferente quer dizer que a janela mudou e o found_index aponta outro controle
            "match_count": len(same),
            "rect": node.get("rect"),
        }
        # identidade estável além do seletor (nunca valor nem posição): a conferência
        # antes de agir recusa um controle trocado por outro de mesmo nome
        for key in ("class_name", "help"):
            if node.get(key):
                item[key] = node[key]
        states = states_of(node)
        if states:
            item["states"] = states
        if node.get("actions"):
            item["actions"] = list(node["actions"])
        items.append(item)
    return items


def is_actionable(node: dict) -> bool:
    """Um tipo acionável, ou qualquer nó que anuncie uma ação de verdade."""
    ctype = node.get("control_type") or ""
    return ctype in ACTIONABLE_CONTROL_TYPES or bool(
        set(node.get("actions") or ()) & _PRIMARY_ACTIONS
    )


def _same_selector(node: dict, ctype: str, title: str, auto_id: str) -> bool:
    """O critério do seletor guardado: tipo + nome (+ auto_id quando houver)."""
    return (
        (node.get("control_type") or "") == ctype
        and (node.get("title") or "") == title
        and (not auto_id or (node.get("auto_id") or "") == auto_id)
    )


def verify_snapshot_item(snap: dict, item: dict, *, timeout: float = 10.0) -> str | None:
    """Antes de agir por número: o controle do snapshot ainda é o mesmo?

    Relê a janela e conta quantos controles casam o seletor guardado. Se a contagem
    mudou (apareceu ou sumiu um igual), o ``found_index`` pode apontar OUTRO controle --
    o "segundo Excluir" virou o terceiro -- e a ação é recusada antes de enviar.
    Devolve ``None`` quando confere, ou o motivo. Snapshots antigos sem
    ``match_count`` passam sem conferir.

    Também confere a identidade estável do controle naquele número: a classe e a
    descrição (``HelpText``) -- nunca valor nem posição, que mudam sozinhos.

    Ideia do agent-desktop (Vercel Labs, Apache-2.0): a ref só resolve quando a
    contagem na janela inteira confere e a identidade (papel, id, nome, descrição)
    bate (``refs/resolve_saved_ref.rs``)."""
    expected = item.get("match_count")
    if expected is None:
        return None
    title, nodes = native_snapshot_nodes(
        window=snap.get("window"),
        pid=snap.get("pid"),
        max_depth=snap.get("max_depth") or 25,
        timeout=timeout,
        backend=snap.get("backend") or "uia",
    )
    if title is None:
        return "the window is gone or not responding"
    matches = [
        node
        for node in nodes
        if _same_selector(
            node, item.get("control_type") or "", item.get("title") or "", item.get("auto_id") or ""
        )
    ]
    now = len(matches)
    if now == 0:
        if getattr(nodes, "partial", False):
            return "part of the window could not be read -- snapshot again"
        return "this control is gone from the window"
    if now != expected:
        return (
            f"the window changed since the snapshot ({now} controls like this now, "
            f"{expected} then) -- the number may point to another control"
        )
    target = matches[min(int(item.get("found_index") or 0), now - 1)]
    for key, label in (("class_name", "kind"), ("help", "description")):
        if item.get(key) and (target.get(key) or "") != item[key]:
            return (
                f"the control at this number has another {label} now -- "
                "the window changed since the snapshot"
            )
    return None


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
    Returns True on success. ``retries`` only re-attempts what never reached the app
    (``native_click_ex`` says which): a click that may have landed is never repeated.
    """
    return native_click_ex(
        window, pid, title=title, control_type=control_type, auto_id=auto_id,
        found_index=found_index, button=button, double=double, method=method,
        timeout=timeout, connect_timeout=connect_timeout, retries=retries, delay=delay,
        backend=backend, title_re=title_re, at=at,
    ).ok


def _act_on_control(
    window, pid, selector: dict, *, backend: str, timeout: float, connect_timeout: float, act
) -> ActionOutcome:
    """Acha o controle e roda ``act(ctrl, sent)``; o resultado diz se chegou ao app.

    ``act`` marca ``sent["sent"] = True`` imediatamente antes de enviar algo ao app,
    para que um tempo estourado ou um erro DEPOIS disso vire ``uncertain`` (pode ter
    chegado) e, ANTES disso, ``not_delivered`` (seguro repetir)."""
    if not _ensure_pywinauto():
        return ActionOutcome.not_sent("pywinauto is not installed (pip install visus-desktop[native])")
    sent = {"sent": False}

    def _job():
        try:
            top = _connect_top(window, pid, connect_timeout, backend)
        except NativeAppUnresponsive as exc:
            return ActionOutcome.not_sent(str(exc), kind="app_unresponsive")
        if top is None:
            return ActionOutcome.not_sent("no such window is open", kind="window_not_found")
        ctrl = top.child_window(**selector)
        if not ctrl.exists(timeout=timeout):
            return ActionOutcome.not_sent("control not found in the window", kind="control_not_found")
        _on_target(ctrl)
        return act(ctrl, sent)

    result, error, timed_out = _run_capturing(_job, timeout + connect_timeout)
    if timed_out:
        if sent["sent"]:
            return ActionOutcome.maybe_sent("timed out after the action was sent")
        return ActionOutcome.not_sent(
            f"the window did not answer within {timeout + connect_timeout:g}s", kind="timeout"
        )
    if error is not None:
        logger.debug("native action failed: %s", error)
        if sent["sent"]:
            return ActionOutcome.maybe_sent(f"error after the action was sent: {error}")
        return ActionOutcome.not_sent(str(error) or type(error).__name__)
    return result


def _retrying(run, retries: int, delay: float) -> ActionOutcome:
    """Repete só o que não chegou ao app."""
    outcome = run()
    for _ in range(max(0, retries)):
        if outcome.ok or not outcome.retry_safe:
            break
        if delay > 0:
            time.sleep(delay)
        outcome = run()
    return outcome


def _top_handle(ctrl) -> int:
    """O hwnd da janela-raiz do controle (pela cadeia de pais), ou 0."""
    import sys

    element = ctrl
    for _ in range(30):
        info = getattr(element, "element_info", None)
        handle = int(getattr(info, "handle", 0) or 0)
        if handle:
            if sys.platform == "win32":
                try:
                    import win32gui

                    return int(win32gui.GetAncestor(handle, 2) or handle)  # GA_ROOT
                except Exception:
                    return handle
            return handle
        try:
            element = element.parent()
        except Exception:
            return 0
        if element is None:
            return 0
    return 0


def _physical_check(ctrl, point=None) -> ActionOutcome | None:
    """Antes do mouse de verdade: o Windows vai entregar (UIPI) e o ponto é do controle
    (nenhuma janela de outro programa por cima)? Coberto, traz a janela para a frente uma
    vez e confere de novo. Devolve a recusa (nada enviado) ou None para seguir."""
    from .input_guard import UIPI_REASON, covering_window, uipi_blocks

    try:
        pid = getattr(ctrl.element_info, "process_id", None)
    except Exception:
        pid = None
    if uipi_blocks(pid):
        return ActionOutcome.not_sent(UIPI_REASON, kind="elevated")
    try:
        if point is None:
            r = ctrl.rectangle()
            point = ((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        hwnd = _top_handle(ctrl)
    except Exception:
        return None
    cover = covering_window(hwnd, *point)
    if cover:
        from .window import _bring_to_front

        try:
            _bring_to_front(hwnd)
            time.sleep(0.15)
        except Exception:
            pass
        cover = covering_window(hwnd, *point)
    if cover:
        return ActionOutcome.not_sent(
            f"{cover!r} is over the control -- the mouse would click it instead; close or "
            "move it, or act without the mouse (Invoke / by number)",
            kind="occluded",
        )
    return None


def native_click_ex(
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
) -> ActionOutcome:
    """``native_click`` that says how the click reached the app (``ActionOutcome``).

    ``method="auto"``: UIA ``Invoke`` → ``LegacyIAccessible.DoDefaultAction`` (both
    without the mouse) → the real mouse (``click_input``). ``"invoke"`` stops before
    the mouse; ``"click"`` goes straight to it."""

    def act(ctrl, sent):
        from .input_guard import input_lease

        if at is not None:  # um ponto da superfície: o mouse de verdade, ali
            rect = ctrl.rectangle()
            point, _ = _drag_points((rect.left, rect.top), at, at)
            refusal = _physical_check(ctrl, point)
            if refusal is not None:
                return refusal
            with input_lease():
                sent["sent"] = True
                if button == "left":
                    _activate_if_needed(rect, point)
                _mouse_click(point, button, 2 if double else 1)
            _mouse_on(rect)
            return ActionOutcome.sent("mouse")
        if double:
            refusal = _physical_check(ctrl)
            if refusal is not None:
                return refusal
            with input_lease():
                sent["sent"] = True
                ctrl.double_click_input()
            _mouse_on(ctrl.rectangle())
            return ActionOutcome.sent("mouse double-click")
        if method in ("invoke", "auto"):
            try:
                ctrl.invoke()
                return ActionOutcome.sent("Invoke")
            except Exception:
                pass
            try:
                from .native_patterns import legacy_default_action

                if legacy_default_action(ctrl.wrapper_object()):
                    return ActionOutcome.sent("DoDefaultAction")
            except Exception as exc:
                logger.debug("DoDefaultAction failed: %s", exc)
            if method == "invoke":
                return ActionOutcome.not_sent(
                    "this control has no Invoke or default action -- use method 'click' (mouse)"
                )
        refusal = _physical_check(ctrl)
        if refusal is not None:
            return refusal
        with input_lease():
            sent["sent"] = True
            ctrl.click_input(button=button)
        _mouse_on(ctrl.rectangle())
        return ActionOutcome.sent("mouse click")

    selector = _selector_kwargs(title, control_type, auto_id, found_index, backend, title_re)
    return _retrying(
        lambda: _act_on_control(
            window, pid, selector, backend=backend, timeout=timeout,
            connect_timeout=connect_timeout, act=act,
        ),
        retries,
        delay,
    )


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
    return native_set_text_ex(
        window, pid, title=title, control_type=control_type, auto_id=auto_id,
        found_index=found_index, text=text, timeout=timeout,
        connect_timeout=connect_timeout, retries=retries, delay=delay, backend=backend,
    ).ok


def native_set_text_ex(
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
) -> ActionOutcome:
    """``native_set_text`` that says how the text reached the app (``ActionOutcome``):
    ``verified`` when the field reads back exactly ``text``."""

    def act(ctrl, sent):
        from .input_guard import UIPI_REASON, input_lease, uipi_blocks

        wrapper = ctrl.wrapper_object()
        if uipi_blocks(getattr(getattr(wrapper, "element_info", None), "process_id", None)):
            return ActionOutcome.not_sent(UIPI_REASON, kind="elevated")
        with input_lease():
            sent["sent"] = True  # o foco/as teclas podem chegar mesmo se algo falhar depois
            typed = _type_into(wrapper, text)
        if typed:
            value = _control_value(wrapper)
            return ActionOutcome.sent("keyboard", verified=None if value is None else True)
        try:
            wrapper.set_edit_text(text)
        except Exception as exc:
            return ActionOutcome.maybe_sent(f"the field did not take the text: {exc}")
        value = _control_value(wrapper)
        return ActionOutcome.sent(
            "ValuePattern", verified=None if value is None else value == text
        )

    selector = _selector_kwargs(title, control_type, auto_id, found_index, backend)
    return _retrying(
        lambda: _act_on_control(
            window, pid, selector, backend=backend, timeout=timeout,
            connect_timeout=connect_timeout, act=act,
        ),
        retries,
        delay,
    )


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


# ---------------------------------------------------------------------------
# Semantic actions -- no mouse, no focus, the window may be behind others
# ---------------------------------------------------------------------------


def _pattern_action(window, pid, selector_args: dict, run, *, timeout, connect_timeout, backend):
    selector = _selector_kwargs(
        selector_args.get("title"), selector_args.get("control_type"),
        selector_args.get("auto_id"), selector_args.get("found_index"), backend,
        selector_args.get("title_re"),
    )

    def act(ctrl, sent):
        wrapper = ctrl.wrapper_object()
        sent["sent"] = True  # o padrão do UIA pode agir mesmo se a releitura falhar
        return run(wrapper)

    return _act_on_control(
        window, pid, selector, backend=backend, timeout=timeout,
        connect_timeout=connect_timeout, act=act,
    )


@records_native("native_toggle")
def native_toggle(
    window=None,
    pid=None,
    *,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    checked: bool | None = None,
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
    backend: str = "uia",
    title_re=None,
) -> ActionOutcome:
    """Check (``checked=True``), uncheck (``False``) or flip (``None``) a checkbox,
    toggle button or switch through the UIA Toggle pattern -- no mouse -- reading the
    state back. Already in the asked state: nothing is sent. A tri-state box takes two
    toggles; a toggle that changes nothing is never repeated. Returns an
    ``ActionOutcome`` (truthy on success)."""
    from .native_patterns import set_checked

    return _pattern_action(
        window, pid,
        {"title": title, "control_type": control_type, "auto_id": auto_id,
         "found_index": found_index, "title_re": title_re},
        lambda wrapper: set_checked(wrapper, checked),
        timeout=timeout, connect_timeout=connect_timeout, backend=backend,
    )


@records_native("native_select")
def native_select(
    window=None,
    pid=None,
    *,
    value: str,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    timeout: float = 8.0,
    connect_timeout: float = 2.0,
    backend: str = "uia",
    title_re=None,
) -> ActionOutcome:
    """Pick the option called ``value`` (case-insensitive) in a combo box, list or tab
    strip through the UIA SelectionItem pattern -- no mouse. Expands a collapsed combo,
    scrolls lists that only load items as you scroll, and refuses (nothing sent) when
    two different options share the name. Returns an ``ActionOutcome``."""
    from .native_patterns import select_option

    return _pattern_action(
        window, pid,
        {"title": title, "control_type": control_type, "auto_id": auto_id,
         "found_index": found_index, "title_re": title_re},
        lambda wrapper: select_option(wrapper, value),
        timeout=timeout, connect_timeout=connect_timeout, backend=backend,
    )


@records_native("native_expand")
def native_expand(
    window=None,
    pid=None,
    *,
    expand: bool = True,
    title=None,
    control_type=None,
    auto_id=None,
    found_index=None,
    timeout: float = 5.0,
    connect_timeout: float = 2.0,
    backend: str = "uia",
    title_re=None,
) -> ActionOutcome:
    """Expand (``expand=True``) or collapse a tree node, combo box, menu button or
    group through the UIA ExpandCollapse pattern -- no mouse -- reading the state back.
    Returns an ``ActionOutcome``."""
    from .native_patterns import set_expanded

    return _pattern_action(
        window, pid,
        {"title": title, "control_type": control_type, "auto_id": auto_id,
         "found_index": found_index, "title_re": title_re},
        lambda wrapper: set_expanded(wrapper, expand),
        timeout=timeout, connect_timeout=connect_timeout, backend=backend,
    )


@records_native("native_scroll_into_view")
def native_scroll_into_view(
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
) -> ActionOutcome:
    """Scroll a list/grid until the control is visible, through the UIA ScrollItem
    pattern -- no mouse wheel. Returns an ``ActionOutcome``."""
    from .native_patterns import scroll_into_view

    return _pattern_action(
        window, pid,
        {"title": title, "control_type": control_type, "auto_id": auto_id,
         "found_index": found_index, "title_re": title_re},
        scroll_into_view,
        timeout=timeout, connect_timeout=connect_timeout, backend=backend,
    )

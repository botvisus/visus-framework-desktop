"""O cliente UIA com prazo e a leitura da árvore em lote.

Duas coisas que o pywinauto não faz e que pesam num agente:

* **Prazo em toda chamada.** O pywinauto cria o cliente ``CUIAutomation`` sem prazo: um
  provedor lento prende a chamada COM para sempre, e o nosso ``timeout`` só soltava quem
  esperava -- a thread ficava para trás, presa no Windows. ``harden_client`` troca o
  cliente do pywinauto pelo ``CUIAutomation8`` com ``ConnectionTimeout`` (2 s) e
  ``TransactionTimeout`` (20 s): a própria chamada desiste e devolve erro.
* **Leitura em lote.** Ler um nó custava ~12 idas e voltas ao outro processo (nome, tipo,
  id, retângulo, estados, um por padrão). ``walk`` pede os filhos de cada nó com TODAS
  as propriedades num só ``FindAllBuildCache`` -- uma ida e volta por nó.
* **Leitura incompleta dita.** Um ramo que falhou ao ler (provedor que deu erro no meio)
  sumia calado do snapshot; agora conta em ``unreadable``, e ``truncated`` diz quando o
  limite de nós cortou a leitura.

Ideias do agent-desktop (Vercel Labs, Apache-2.0): ``CUIAutomation8`` com os dois prazos e
o primeiro toque serializado (A14-13: a inicialização do cliente não é reentrante), a
leitura com ``CacheRequest`` e o snapshot que se declara parcial.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

CONNECTION_TIMEOUT_MS = 2000
TRANSACTION_TIMEOUT_MS = 20000

_lock = threading.Lock()
_hardened = False

# nome da ação (como o snapshot mostra) -> propriedade Is*PatternAvailable
PATTERN_FLAGS = {
    "invoke": "UIA_IsInvokePatternAvailablePropertyId",
    "toggle": "UIA_IsTogglePatternAvailablePropertyId",
    "expand": "UIA_IsExpandCollapsePatternAvailablePropertyId",
    "select": "UIA_IsSelectionItemPatternAvailablePropertyId",
    "value": "UIA_IsValuePatternAvailablePropertyId",
    "scroll": "UIA_IsScrollPatternAvailablePropertyId",
}
_BASE_PROPS = (
    "UIA_NamePropertyId",
    "UIA_ControlTypePropertyId",
    "UIA_AutomationIdPropertyId",
    "UIA_ClassNamePropertyId",
    "UIA_BoundingRectanglePropertyId",
    "UIA_IsEnabledPropertyId",
    "UIA_IsOffscreenPropertyId",
    "UIA_IsPasswordPropertyId",
    "UIA_HelpTextPropertyId",
    "UIA_ToggleToggleStatePropertyId",
    "UIA_ExpandCollapseExpandCollapseStatePropertyId",
)


def harden_client() -> bool:
    """Põe o ``CUIAutomation8`` com prazo no lugar do cliente do pywinauto (uma vez por
    processo). True quando o cliente com prazo está em uso."""
    global _hardened
    if _hardened:
        return True
    with _lock:
        if _hardened:
            return True
        try:
            import comtypes
            from pywinauto.uia_defines import IUIA

            iuia = IUIA()
            dll = iuia.UIA_dll
            client = comtypes.CoCreateInstance(
                dll.CUIAutomation8._reg_clsid_,
                interface=dll.IUIAutomation2,
                clsctx=comtypes.CLSCTX_INPROC_SERVER,
            )
            client.ConnectionTimeout = CONNECTION_TIMEOUT_MS
            client.TransactionTimeout = TRANSACTION_TIMEOUT_MS
            # o primeiro toque, ainda com o lock: a inicialização não é reentrante (A14-13)
            root = client.GetRootElement()
            iuia.iuia = client
            iuia.root = root
            iuia.true_condition = client.CreateTrueCondition()
            iuia.get_focused_element = client.GetFocusedElement
            _hardened = True
        except Exception:  # Windows antigo / sem UIA8: segue com o cliente do pywinauto
            return False
    return True


@dataclass
class TreeRead:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    unreadable: int = 0  # ramos cujos filhos não puderam ser lidos
    truncated: bool = False  # o limite de nós cortou a leitura

    @property
    def partial(self) -> bool:
        return self.unreadable > 0 or self.truncated


def _ids(dll) -> dict[str, int]:
    names = (*_BASE_PROPS, *PATTERN_FLAGS.values())
    return {name: getattr(dll, name) for name in names if getattr(dll, name, None) is not None}


def _cache_request(client, ids: dict[str, int]):
    request = client.CreateCacheRequest()
    for pid in ids.values():
        request.AddProperty(pid)
    return request


def _value(element, ids, name):
    pid = ids.get(name)
    return None if pid is None else element.GetCachedPropertyValue(pid)


def node_of(element, ids, control_types, depth: int, *, with_extras) -> dict[str, Any]:
    """Um nó do walk a partir das propriedades em cache (mesmo formato do walk antigo)."""
    ctype = control_types.get(int(_value(element, ids, "UIA_ControlTypePropertyId") or 0), "")
    node: dict[str, Any] = {
        "depth": depth,
        "control_type": ctype,
        "title": str(_value(element, ids, "UIA_NamePropertyId") or ""),
        "auto_id": str(_value(element, ids, "UIA_AutomationIdPropertyId") or ""),
        "rect": _box(_value(element, ids, "UIA_BoundingRectanglePropertyId")),
    }
    if with_extras(ctype):
        actions = [a for a, name in PATTERN_FLAGS.items() if _value(element, ids, name)]
        node.update(
            actions=actions,
            enabled=bool(_value(element, ids, "UIA_IsEnabledPropertyId")),
            offscreen=bool(_value(element, ids, "UIA_IsOffscreenPropertyId")),
            password=bool(_value(element, ids, "UIA_IsPasswordPropertyId")),
            class_name=str(_value(element, ids, "UIA_ClassNamePropertyId") or ""),
            help=str(_value(element, ids, "UIA_HelpTextPropertyId") or ""),
        )
        # estado de padrão só quando o padrão é anunciado: sem ele, o valor é "padrão" (A15-7)
        if "toggle" in actions:
            node["toggle"] = int(_value(element, ids, "UIA_ToggleToggleStatePropertyId") or 0)
        if "expand" in actions:
            node["expand"] = int(
                _value(element, ids, "UIA_ExpandCollapseExpandCollapseStatePropertyId") or 0
            )
    return node


def _box(rect) -> dict[str, int] | None:
    """``(left, top, right, bottom)`` (array de doubles do UIA) -> caixa x/y/w/h."""
    try:
        if rect is None:
            return None
        if hasattr(rect, "left"):
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
            return {"x": int(left), "y": int(top), "width": int(right - left), "height": int(bottom - top)}
        left, top, width, height = (float(v) for v in rect)
        return {"x": int(left), "y": int(top), "width": int(width), "height": int(height)}
    except Exception:
        return None


def walk(
    top_element,
    *,
    max_depth: int,
    max_nodes: int,
    max_raw_depth: int,
    with_extras,
    skip_level,
    iuia=None,
) -> TreeRead:
    """Walk em pré-ordem dos filhos (a ordem do ``descendants()`` do pywinauto, para o
    ``found_index`` contado aqui achar o mesmo controle depois), uma ida e volta por nó.

    ``with_extras(control_type)`` diz se o nó leva estados/ações; ``skip_level(node)``
    diz se o nó não conta como nível de ``max_depth`` (os grupos anônimos do Chromium)."""
    if iuia is None:
        from pywinauto.uia_defines import IUIA

        iuia = IUIA()
    dll = iuia.UIA_dll
    client = iuia.iuia
    ids = _ids(dll)
    request = _cache_request(client, ids)
    condition = client.CreateTrueCondition()
    scope = dll.TreeScope_Children
    control_types = iuia.known_control_type_ids
    read = TreeRead()

    def _walk(element, depth, raw_depth):
        if depth > max_depth or raw_depth > max_raw_depth:
            return
        if len(read.nodes) >= max_nodes:
            read.truncated = True
            return
        try:
            children = element.FindAllBuildCache(scope, condition, request)
            count = children.Length if children is not None else 0
        except Exception:
            read.unreadable += 1
            return
        for i in range(count):
            if len(read.nodes) >= max_nodes:
                read.truncated = True
                return
            try:
                child = children.GetElement(i)
                node = node_of(child, ids, control_types, depth, with_extras=with_extras)
            except Exception:
                read.unreadable += 1
                continue
            read.nodes.append(node)
            _walk(child, depth + (0 if skip_level(node) else 1), raw_depth + 1)

    _walk(top_element, 1, 1)
    return read

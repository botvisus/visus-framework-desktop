"""Ações semânticas do UIA -- sem mouse, sem foco, com a janela atrás de outras.

O clique nativo caía do ``Invoke`` direto para o mouse de verdade (``click_input``), que
tira o mouse e o foco da pessoa; e marcar uma caixa, escolher um item de combo ou
expandir um nó não existiam como ação nativa. Aqui:

* ``legacy_default_action`` -- o ``LegacyIAccessible.DoDefaultAction``, o degrau entre o
  ``Invoke`` e o mouse: funciona em controles que não anunciam ``Invoke`` (WinForms com
  provedor próprio, o Bloco de Notas clássico);
* ``set_checked`` -- ``TogglePattern`` até o estado pedido, relendo (caixa de três
  estados leva dois toques; um toque que não muda nada NÃO é repetido);
* ``set_expanded`` -- ``ExpandCollapsePattern``, relendo;
* ``select_option`` -- ``SelectionItemPattern`` no item com aquele nome dentro do
  combo/lista: expande se preciso, rola para listas que só carregam ao rolar, e dois
  itens com o mesmo nome são recusados (ambíguo) em vez de escolhidos ao acaso;
* ``scroll_into_view`` -- ``ScrollItemPattern``.

Toda ação diz se chegou ao app (``ActionOutcome``). Todo estado de padrão só é lido
quando o padrão é anunciado: sem ele, o UIA devolve valores "padrão" que parecem
reais (``ToggleState`` = indeterminado num texto estático).

Medido no agent-desktop (Vercel Labs, Apache-2.0), ``probes/windows/FINDINGS.md``:
A19-6 (``DoDefaultAction`` funciona num botão sem ``Invoke``), A3-2 (o ``Toggle`` muda o
estado sem disparar Click -- confira relendo o elemento), A15-7 (estado de padrão não
anunciado volta com valor padrão), A19-7 (combo: expandir, procurar, rolar), A2-5 (ids
de propriedade vêm do runtime do UIA, nunca de uma tabela escrita à mão).
"""

from __future__ import annotations

import time
from typing import Any

from .outcome import ActionOutcome

# ToggleState / ExpandCollapseState do UIA
TOGGLE_OFF, TOGGLE_ON, TOGGLE_MIXED = 0, 1, 2
COLLAPSED, EXPANDED, PARTIAL, LEAF = 0, 1, 2, 3
# ScrollAmount do UIA
_NO_AMOUNT, _SMALL_INCREMENT = 2, 4

VERIFY_TIMEOUT = 0.6
POLL = 0.025
MAX_SELECT_NODES = 2048
MAX_REALIZE_SCROLLS = 16

# nome da ação (como o snapshot mostra) -> nome da propriedade Is*PatternAvailable
_PATTERN_FLAGS = {
    "invoke": "UIA_IsInvokePatternAvailablePropertyId",
    "toggle": "UIA_IsTogglePatternAvailablePropertyId",
    "expand": "UIA_IsExpandCollapsePatternAvailablePropertyId",
    "select": "UIA_IsSelectionItemPatternAvailablePropertyId",
    "value": "UIA_IsValuePatternAvailablePropertyId",
    "scroll": "UIA_IsScrollPatternAvailablePropertyId",
}


def _uia():
    from pywinauto.uia_defines import IUIA

    return IUIA().UIA_dll


def _prop(element, name: str):
    """Uma propriedade pelo NOME da constante do UIA (o id vem do runtime)."""
    pid = getattr(_uia(), name, None)
    if pid is None:
        return None
    return element.GetCurrentPropertyValue(pid)


def read_node_extras(element_info) -> dict[str, Any]:
    """Estados e ações de um nó do walk, para o snapshot: ``actions`` (os padrões
    anunciados), ``enabled``, ``offscreen``, ``password``, ``toggle``, ``expand``.
    ``{}`` quando o elemento não é UIA (backend win32) ou a leitura falha."""
    element = getattr(element_info, "element", None)
    if element is None:
        return {}
    try:
        actions = [action for action, name in _PATTERN_FLAGS.items() if _prop(element, name)]
        extras: dict[str, Any] = {
            "actions": actions,
            "enabled": bool(_prop(element, "UIA_IsEnabledPropertyId")),
            "offscreen": bool(_prop(element, "UIA_IsOffscreenPropertyId")),
            "password": bool(_prop(element, "UIA_IsPasswordPropertyId")),
        }
        if "toggle" in actions:
            extras["toggle"] = int(_prop(element, "UIA_ToggleToggleStatePropertyId"))
        if "expand" in actions:
            extras["expand"] = int(_prop(element, "UIA_ExpandCollapseExpandCollapseStatePropertyId"))
        return extras
    except Exception:
        return {}


def states_of(node: dict[str, Any]) -> list[str]:
    """Os estados que o agente precisa ver numa linha do snapshot."""
    states: list[str] = []
    if node.get("enabled") is False:
        states.append("disabled")
    if node.get("offscreen"):
        states.append("offscreen")
    if node.get("password"):
        states.append("password")
    toggle = node.get("toggle")
    if toggle is not None:
        states.append({TOGGLE_ON: "checked", TOGGLE_MIXED: "mixed"}.get(toggle, "unchecked"))
    expand = node.get("expand")
    if expand in (COLLAPSED, EXPANDED, PARTIAL):
        states.append("expanded" if expand in (EXPANDED, PARTIAL) else "collapsed")
    return states


def _iface(wrapper, pattern: str):
    """A interface de um padrão (``Toggle``, ``LegacyIAccessible``...) ou None."""
    try:
        from pywinauto import uia_defines

        return uia_defines.get_elem_interface(wrapper.element_info.element, pattern)
    except Exception:
        return None


def _poll(read, want, timeout: float = VERIFY_TIMEOUT):
    """Relê ``read()`` até devolver ``want`` ou o tempo acabar; devolve a última leitura."""
    end = time.monotonic() + timeout
    value = read()
    while value != want and time.monotonic() < end:
        time.sleep(POLL)
        value = read()
    return value


# --- clique: o degrau entre o Invoke e o mouse ----------------------------------------


def legacy_default_action(wrapper) -> bool:
    """``DoDefaultAction`` quando o controle anuncia uma ação padrão (texto não vazio).
    True = enviado. Um controle sem ação padrão (Edit, Text) não é tocado."""
    legacy = _iface(wrapper, "LegacyIAccessible")
    if legacy is None:
        return False
    default = getattr(legacy, "CurrentDefaultAction", None)
    if not isinstance(default, str) or not default.strip():
        return False
    legacy.DoDefaultAction()
    return True


# --- toggle ----------------------------------------------------------------------------


def toggle_state(wrapper) -> int | None:
    toggle = _iface(wrapper, "Toggle")
    if toggle is None:
        return None
    try:
        return int(toggle.CurrentToggleState)
    except Exception:
        return None


def set_checked(wrapper, want: bool | None) -> ActionOutcome:
    """Marca (True), desmarca (False) ou inverte (None) uma caixa/toggle, relendo."""
    toggle = _iface(wrapper, "Toggle")
    if toggle is None:
        invoke = _iface(wrapper, "Invoke")
        if invoke is None:
            return ActionOutcome.not_sent("this control has no toggle (no Toggle or Invoke pattern)")
        invoke.Invoke()
        return ActionOutcome.sent("Invoke")
    before = toggle_state(wrapper)
    if want is None:
        toggle.Toggle()
        after = _poll(lambda: toggle_state(wrapper), None if before is None else _flip(before))
        return ActionOutcome.sent(
            "Toggle", verified=None if before is None else after != before, state=after
        )
    target = TOGGLE_ON if want else TOGGLE_OFF
    if before == target:
        return ActionOutcome(ok=True, delivery="verified", method="already", details={"state": before})
    for _ in range(2):  # três estados: indeterminado -> marcado leva dois toques
        previous = toggle_state(wrapper)
        toggle.Toggle()
        now = _poll(lambda: toggle_state(wrapper), target)
        if now == target:
            return ActionOutcome.sent("Toggle", verified=True, state=now)
        if now == previous:  # não mudou: tocar de novo poderia voltar ao início
            break
    return ActionOutcome.sent("Toggle", verified=False, state=toggle_state(wrapper))


def _flip(state: int) -> int:
    return TOGGLE_OFF if state == TOGGLE_ON else TOGGLE_ON


# --- expand / collapse -----------------------------------------------------------------


def expand_state(wrapper) -> int | None:
    pattern = _iface(wrapper, "ExpandCollapse")
    if pattern is None:
        return None
    try:
        return int(pattern.CurrentExpandCollapseState)
    except Exception:
        return None


def set_expanded(wrapper, expand: bool) -> ActionOutcome:
    pattern = _iface(wrapper, "ExpandCollapse")
    if pattern is None:
        return ActionOutcome.not_sent("this control does not expand or collapse")
    before = expand_state(wrapper)
    if before == LEAF:
        return ActionOutcome.not_sent("this node has nothing to expand (leaf)")
    if (before == EXPANDED and expand) or (before == COLLAPSED and not expand):
        return ActionOutcome(ok=True, delivery="verified", method="already")
    if expand:
        pattern.Expand()
    else:
        pattern.Collapse()
    target = EXPANDED if expand else COLLAPSED
    after = _poll(lambda: expand_state(wrapper), target)
    return ActionOutcome.sent("ExpandCollapse", verified=after == target)


# --- select ----------------------------------------------------------------------------


def _name(wrapper) -> str:
    try:
        return wrapper.element_info.name or ""
    except Exception:
        return ""


def _runtime_id(wrapper):
    try:
        return tuple(wrapper.element_info.runtime_id or ())
    except Exception:
        return id(wrapper)


def find_option(container, value: str) -> tuple[Any | None, bool]:
    """``(item, ambiguous)``: o item selecionável com o nome ``value`` (sem caixa) dentro
    de ``container``. Dois itens DIFERENTES com o mesmo nome -> ``(None, True)``."""
    wanted = value.strip().casefold()
    found = None
    try:
        candidates = container.descendants()[:MAX_SELECT_NODES]
    except Exception:
        return None, False
    for item in candidates:
        if _name(item).strip().casefold() != wanted:
            continue
        if _iface(item, "SelectionItem") is None:
            continue
        if found is not None and _runtime_id(found) != _runtime_id(item):
            return None, True
        found = found or item
    return found, False


def _scroll_once(container) -> bool:
    """Um passo de rolagem para baixo; False quando não rola mais (fim ou sem padrão)."""
    scroll = _iface(container, "Scroll")
    if scroll is None:
        return False
    try:
        before = scroll.CurrentVerticalScrollPercent
        scroll.Scroll(_NO_AMOUNT, _SMALL_INCREMENT)
        return scroll.CurrentVerticalScrollPercent != before
    except Exception:
        return False


def select_option(container, value: str) -> ActionOutcome:
    """Escolhe o item ``value`` de um combo/lista pelo ``SelectionItemPattern``."""
    expanded_here = False
    item, ambiguous = find_option(container, value)
    if item is None and not ambiguous and expand_state(container) == COLLAPSED:
        set_expanded(container, True)
        expanded_here = True
        item, ambiguous = find_option(container, value)
    scrolls = 0
    while item is None and not ambiguous and scrolls < MAX_REALIZE_SCROLLS and _scroll_once(container):
        scrolls += 1
        item, ambiguous = find_option(container, value)
    if item is None:
        if expanded_here:
            set_expanded(container, False)
        if ambiguous:
            return ActionOutcome.not_sent(
                f"more than one option is called {value!r} -- pick it another way", kind="ambiguous"
            )
        # combo Win32 (a lista é um popup que só existe aberto, e o Expand não a abre sem
        # foco -- medido no Mapa de Caracteres): o ValuePattern gravável escolhe pelo texto
        by_value = _select_by_value(container, value)
        if by_value is not None:
            return by_value
        return ActionOutcome.not_sent(f"no option called {value!r} in this control", kind="not_found")
    _iface(item, "SelectionItem").Select()

    def _selected():
        pattern = _iface(item, "SelectionItem")
        try:
            return bool(pattern.CurrentIsSelected) if pattern is not None else None
        except Exception:
            return None

    return ActionOutcome.sent("SelectionItem", verified=_poll(_selected, True) is True)


def _select_by_value(container, value: str) -> ActionOutcome | None:
    """``SetValue`` num combo de valor gravável, conferindo que ele ficou com ``value``.
    ``None`` quando não há esse caminho (sem ValuePattern, ou só leitura)."""
    pattern = _iface(container, "Value")
    if pattern is None:
        return None
    try:
        if pattern.CurrentIsReadOnly:
            return None
    except Exception:
        return None
    pattern.SetValue(value)

    def _current():
        try:
            return str(pattern.CurrentValue or "").strip().casefold()
        except Exception:
            return None

    after = _poll(_current, value.strip().casefold())
    if after == value.strip().casefold():
        return ActionOutcome.sent("ValuePattern", verified=True)
    # o combo recusou um texto que não está na lista: nada mudou
    return ActionOutcome.not_sent(f"no option called {value!r} in this control", kind="not_found")


# --- scroll into view ------------------------------------------------------------------


def scroll_into_view(wrapper) -> ActionOutcome:
    pattern = _iface(wrapper, "ScrollItem")
    if pattern is None:
        return ActionOutcome.not_sent("this control cannot be scrolled into view (no ScrollItem)")
    pattern.ScrollIntoView()
    offscreen = _poll(lambda: _offscreen(wrapper), False)
    return ActionOutcome.sent("ScrollItem", verified=None if offscreen is None else not offscreen)


def _offscreen(wrapper):
    try:
        return bool(_prop(wrapper.element_info.element, "UIA_IsOffscreenPropertyId"))
    except Exception:
        return None

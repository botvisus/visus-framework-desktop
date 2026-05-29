"""Unified cascading targeting -- the "do whatever works" layer.

``smart_find`` / ``smart_click`` try every targeting technique in a
configurable order and report which one won. The default precedence is::

    native -> image -> ocr -> coordinates

Rationale (most-robust first, most-universal-fallback last):

* **native** -- operate the actual control via UIA (no pixel); immune to
  theme/DPI/resolution/language. Only works on accessible apps.
* **image**  -- template match a PNG you captured once; pixel-based, works
  on anything visible, robust to text changes.
* **ocr**    -- read on-screen text; pixel-based, works on Java Swing,
  Electron, remote desktop.
* **coordinates** -- absolute (x, y); last resort when nothing else fits.

Pass ``order=[...]`` to force a single method (e.g. ``order=["native"]``)
or reorder the cascade. A method is skipped automatically when the input
it needs is absent (no ``image`` -> skip image; no ``query`` -> skip
native/ocr; no ``coordinates`` -> skip coordinates).
"""

from __future__ import annotations

from typing import Any

from .native_rpa import native_click, native_get_state

DEFAULT_ORDER = ("native", "image", "ocr", "coordinates")
_VALID_METHODS = set(DEFAULT_ORDER)


def _resolve_order(order):
    if order is None:
        return list(DEFAULT_ORDER)
    unknown = [m for m in order if m not in _VALID_METHODS]
    if unknown:
        raise ValueError(
            f"unknown targeting method(s): {unknown}; "
            f"valid: {sorted(_VALID_METHODS)}"
        )
    return list(order)


def _coerce(seq):
    return tuple(seq) if seq is not None else None


def _get_bot(bot):
    if bot is not None:
        return bot
    from .. import VisusBot

    return VisusBot()


def smart_find(
    query: str | None = None,
    *,
    image: str | None = None,
    coordinates: list | None = None,
    window: str | None = None,
    pid: int | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    search_region: list | None = None,
    confidence: float = 0.9,
    confidence_threshold: float = 75.0,
    order=None,
    timeout: float = 5.0,
    bot: Any = None,
) -> dict:
    """Locate a target by cascading native -> image -> ocr -> coordinates.

    Returns ``{found, box, method, tried}`` where ``box`` is
    ``{x, y, width, height}`` (or ``None``), ``method`` is the winning
    technique (or ``None``), and ``tried`` lists the methods attempted.
    """
    order = _resolve_order(order)
    bot = _get_bot(bot)
    tried: list = []

    for method in order:
        if method == "native":
            if not (query or control_type or auto_id):
                continue
            tried.append("native")
            state = native_get_state(
                window=window, pid=pid, title=query,
                control_type=control_type, auto_id=auto_id, timeout=timeout,
            )
            if state and state.get("exists") and state.get("rect"):
                return {"found": True, "box": state["rect"], "method": "native",
                        "tried": tried}
        elif method == "image":
            if image is None:
                continue
            tried.append("image")
            box = bot.find_image(
                image, region=_coerce(search_region), confidence=confidence
            )
            if box:
                return {"found": True, "box": _box_dict(box), "method": "image",
                        "tried": tried}
        elif method == "ocr":
            if not query:
                continue
            tried.append("ocr")
            box = bot.find_text(
                query, region=_coerce(search_region),
                confidence_threshold=confidence_threshold,
            )
            if box:
                return {"found": True, "box": _box_dict(box), "method": "ocr",
                        "tried": tried}
        elif method == "coordinates":
            if coordinates is None:
                continue
            tried.append("coordinates")
            x, y = int(coordinates[0]), int(coordinates[1])
            return {"found": True, "box": {"x": x, "y": y, "width": 0, "height": 0},
                    "method": "coordinates", "tried": tried}

    return {"found": False, "box": None, "method": None, "tried": tried}


def smart_click(
    query: str | None = None,
    *,
    image: str | None = None,
    coordinates: list | None = None,
    window: str | None = None,
    pid: int | None = None,
    control_type: str | None = None,
    auto_id: str | None = None,
    search_region: list | None = None,
    button: str = "left",
    confidence: float = 0.9,
    confidence_threshold: float = 75.0,
    order=None,
    timeout: float = 5.0,
    retries: int = 0,
    delay: float = 0.3,
    bot: Any = None,
) -> dict:
    """Click a target by cascading native -> image -> ocr -> coordinates.

    Each layer uses its own native action (native invoke/click, image
    click, OCR click, coordinate click). Returns ``{clicked, method,
    tried}``.
    """
    order = _resolve_order(order)
    bot = _get_bot(bot)
    tried: list = []

    for method in order:
        if method == "native":
            if not (query or control_type or auto_id):
                continue
            tried.append("native")
            if native_click(
                window=window, pid=pid, title=query, control_type=control_type,
                auto_id=auto_id, button=button, timeout=timeout,
                retries=retries, delay=delay,
            ):
                return {"clicked": True, "method": "native", "tried": tried}
        elif method == "image":
            if image is None:
                continue
            tried.append("image")
            if bot.click_image(
                image, region=_coerce(search_region), confidence=confidence,
                mouse_button=button,
            ):
                return {"clicked": True, "method": "image", "tried": tried}
        elif method == "ocr":
            if not query:
                continue
            tried.append("ocr")
            if bot.click_text(
                query, region=_coerce(search_region), mouse_button=button
            ):
                return {"clicked": True, "method": "ocr", "tried": tried}
        elif method == "coordinates":
            if coordinates is None:
                continue
            tried.append("coordinates")
            x, y = int(coordinates[0]), int(coordinates[1])
            if bot.click_at((x, y, 0, 0), mouse_button=button):
                return {"clicked": True, "method": "coordinates", "tried": tried}

    return {"clicked": False, "method": None, "tried": tried}


def _box_dict(box) -> dict:
    x, y, w, h = box
    return {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}

"""Element capture -- locate a UI element, save a reusable template + an
annotated screenshot, and optionally click it.

This is the high-level primitive that lets an agent build a click-by-image
flow without guessing coordinates. It composes the existing locators
(``find_text`` OCR, the native UIA lookup) with ``save_screenshot`` and
``click_at`` -- so it is fully testable and reusable outside the MCP layer.

Typical step-by-step (Notepad "save as"):

    capture_element("arquivo",     text="Arquivo",     click=True)
    capture_element("salvar_como", text="Salvar como", click=True)
    capture_element("btn_salvar",  text="Salvar",      click=True)

Each call:
  1. Locates the element by exactly one of ``text`` / ``native`` / ``region``.
  2. Saves a tight template PNG to ``<elements_dir>/<label>.png`` (reusable
     by ``find_image`` / ``click_image`` later).
  3. Saves an annotated full-screen PNG (rectangle drawn around the located
     box) to ``<elements_dir>/trace/<label>_annotated.png`` so a human can
     see exactly what was located.
  4. Optionally clicks the element's center.
"""

from __future__ import annotations

import os
from typing import Any

from .screen import capture_screen, save_screenshot

_TRACE_SUBDIR = "trace"


def _coerce_region(region):
    if region is None:
        return None
    return tuple(region)


def _annotate(full_image, box, out_path: str):
    """Save ``full_image`` with a rectangle drawn around ``box`` (x, y, w, h).

    When ``box`` is None (element not found) the unmodified screenshot is
    saved so the caller can still see the screen state.
    """
    from PIL import ImageDraw

    annotated = full_image.convert("RGB")
    if box is not None:
        x, y, w, h = box
        draw = ImageDraw.Draw(annotated)
        # Coral outline (matches the project's accent) + a small inset so a
        # 1px-edge element stays visible.
        draw.rectangle([x, y, x + w, y + h], outline=(204, 120, 92), width=3)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    annotated.save(out_path)


def _apply_padding(box, padding: int, screen_w: int, screen_h: int):
    """Expand ``box`` by ``padding`` px each side, clamped to the screen."""
    if padding <= 0:
        return box
    x, y, w, h = box
    nx = max(0, x - padding)
    ny = max(0, y - padding)
    right = min(screen_w, x + w + padding)
    bottom = min(screen_h, y + h + padding)
    return (nx, ny, right - nx, bottom - ny)


def capture_element(
    label: str,
    *,
    text: str | None = None,
    native: str | None = None,
    region: list | None = None,
    search_region: list | None = None,
    auto: str | None = None,
    window: str | None = None,
    click: bool = False,
    mouse_button: str = "left",
    padding: int = 0,
    confidence_threshold: float = 75.0,
    native_timeout: float = 5.0,
    elements_dir: str = "./visus-elements",
    bot: Any = None,
) -> dict:
    """Locate an element, save its template + an annotated screenshot, click.

    Exactly one locator is required:

    * ``auto=`` -- **recommended**. Tries Win32 menu -> OCR -> UIA directed
      in order (see :func:`visus.desktop.core.locators.locate_layered`).
      Win32 is instant + pixel-exact for native menus; OCR works on
      anything that renders text (Java Swing, Electron, remote desktop);
      UIA directed catches accessible controls OCR missed.
    * ``text=`` -- OCR only.
    * ``native=`` -- targeted UIA only (fast ``child_window`` FindFirst).
    * ``region=`` -- an explicit ``(x, y, w, h)``.

    ``window=`` (title substring) scopes Win32/UIA to that window even when
    it is not focused; without it the foreground window is targeted.

    Returns ``{found, label, located_by, box, template_path,
    annotated_path, clicked}``. On a miss ``found`` is False and only the
    annotated full-screen PNG (no rectangle) is written.
    """
    locators = [
        ("auto", auto),
        ("text", text),
        ("native", native),
        ("region", region),
    ]
    provided = [(name, val) for name, val in locators if val is not None]
    if len(provided) != 1:
        raise ValueError(
            "capture_element requires exactly one of: auto=, text=, native=, "
            f"region= (got {len(provided)})"
        )
    mode, value = provided[0]

    if bot is None:
        from .. import VisusBot

        bot = VisusBot()

    # ---- Resolve the target window (for Win32 / UIA strategies) -------
    hwnd = pid = None
    if mode in ("auto", "native"):
        from . import locators as _loc

        win = _loc.get_window(window) if window else _loc.get_foreground_window()
        if win:
            hwnd, pid = win["hwnd"], win["pid"]

    # ---- Locate -------------------------------------------------------
    box = None
    located_by = mode
    if mode == "region":
        box = _coerce_region(value)
    elif mode == "text":
        box = bot.find_text(
            value,
            region=_coerce_region(search_region),
            confidence_threshold=confidence_threshold,
        )
    elif mode == "native":
        from . import locators as _loc

        box = _loc.locate_uia_directed(
            value, pid=pid, title_substring=window, timeout=native_timeout
        )
    elif mode == "auto":
        from . import locators as _loc

        box, method = _loc.locate_layered(
            value,
            bot=bot,
            hwnd=hwnd,
            pid=pid,
            title_substring=window,
            search_region=_coerce_region(search_region),
            confidence_threshold=confidence_threshold,
            uia_timeout=native_timeout,
        )
        located_by = method or "auto"

    # Normalise a located box to a plain (x, y, w, h) int tuple.
    if box is not None:
        box = tuple(int(v) for v in box)

    # ---- Paths --------------------------------------------------------
    template_path = os.path.abspath(os.path.join(elements_dir, f"{label}.png"))
    annotated_path = os.path.abspath(
        os.path.join(elements_dir, _TRACE_SUBDIR, f"{label}_annotated.png")
    )

    full = capture_screen()
    screen_w, screen_h = full.size

    if box is None:
        # Miss: save the annotated (no rectangle) so the user sees the state.
        _annotate(full, None, annotated_path)
        return {
            "found": False,
            "label": label,
            "located_by": located_by,
            "box": None,
            "template_path": None,
            "annotated_path": annotated_path,
            "clicked": False,
        }

    box = _apply_padding(box, padding, screen_w, screen_h)
    x, y, w, h = box

    # ---- Save artifacts ----------------------------------------------
    save_screenshot(template_path, region=(x, y, w, h))
    _annotate(full, box, annotated_path)

    # ---- Optional click ----------------------------------------------
    clicked = False
    if click:
        center_x, center_y = x + w // 2, y + h // 2
        clicked = bool(
            bot.click_at((center_x, center_y, 0, 0), mouse_button=mouse_button)
        )

    return {
        "found": True,
        "label": label,
        "located_by": located_by,
        "box": {"x": x, "y": y, "width": w, "height": h},
        "template_path": template_path,
        "annotated_path": annotated_path,
        "clicked": clicked,
    }

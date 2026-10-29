"""``visus smart`` -- the cascade: native -> image -> OCR -> coordinates."""

from __future__ import annotations

import click

from .._common import (
    build_bot,
    click_human,
    dry_run_option,
    json_option,
    smart_options,
    virtual_option,
    virtual_overrides,
)
from .._output import done


@click.group(help="Smart cascade: native -> image -> OCR -> coordinates.")
def smart():
    pass


@smart.command(help="Find a target using the smart cascade.")
@smart_options
@json_option
def find(
    query, image, coordinates, window, pid, control_type, auto_id,
    search_region, confidence, confidence_threshold, order, timeout, json_mode,
):
    from visus.desktop.core.smart import smart_find

    result = smart_find(
        query, image=image, coordinates=coordinates, window=window, pid=pid,
        control_type=control_type, auto_id=auto_id, search_region=search_region,
        confidence=confidence, confidence_threshold=confidence_threshold,
        order=order, timeout=timeout, bot=build_bot(),
    )
    ok = bool(result.get("found"))
    tried = ", ".join(result.get("tried") or [])
    human = (
        f"found via {result.get('method')} at {result.get('box')}"
        if ok
        else f"not found (tried: {tried})"
    )
    done(result, json_mode=json_mode, ok=ok, human=human)


@smart.command(name="click", help="Click a target using the smart cascade.")
@smart_options
@click.option(
    "--button", default="left", show_default=True,
    type=click.Choice(["left", "right", "middle"]),
)
@click.option("--retries", type=int, default=0, show_default=True)
@click.option("--delay", type=float, default=0.3, show_default=True)
@virtual_option
@dry_run_option
@json_option
def click_cmd(
    query, image, coordinates, window, pid, control_type, auto_id,
    search_region, confidence, confidence_threshold, order, timeout,
    button, retries, delay, virtual, dry_run, json_mode,
):
    from visus.desktop.core.smart import smart_click, smart_find

    if dry_run:
        result = smart_find(
            query, image=image, coordinates=coordinates, window=window, pid=pid,
            control_type=control_type, auto_id=auto_id,
            search_region=search_region, confidence=confidence,
            confidence_threshold=confidence_threshold, order=order, timeout=timeout,
            bot=build_bot(),
        )
        ok = bool(result.get("found"))
        tried = ", ".join(result.get("tried") or [])
        human = (
            f"[dry-run] would click via {result.get('method')} at {result.get('box')}"
            if ok
            else f"[dry-run] target not found (tried: {tried})"
        )
        done(result, json_mode=json_mode, ok=ok, human=human)
        return

    # native clicks through UIA (no mouse at all); --virtual covers the
    # image / OCR / coordinate steps of the cascade
    bot = build_bot(**virtual_overrides(virtual))
    result = smart_click(
        query, image=image, coordinates=coordinates, window=window, pid=pid,
        control_type=control_type, auto_id=auto_id, search_region=search_region,
        button=button, confidence=confidence,
        confidence_threshold=confidence_threshold, order=order, timeout=timeout,
        retries=retries, delay=delay, bot=bot,
    )
    ok = bool(result.get("clicked"))
    tried = ", ".join(result.get("tried") or [])
    human = click_human(bot, ok, f"clicked via {result.get('method')}", f"not clicked (tried: {tried})")
    done(result, json_mode=json_mode, ok=ok, human=human)

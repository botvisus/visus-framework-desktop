"""``visus capture`` -- coordinate-free element capture."""

from __future__ import annotations

import click

from .._common import dry_run_option, json_option, region_cb
from .._output import done, fail


@click.command(
    help="Capture a UI element: locate -> save template + annotated -> optional click."
)
@click.argument("label")
@click.option("--auto", help="Recommended: Win32 menu -> OCR -> UIA directed.")
@click.option("--text", help="Locate by OCR text only.")
@click.option("--native", "native_", help="Locate by directed UIA only.")
@click.option("--region", callback=region_cb, help="Explicit region 'X,Y,W,H'.")
@click.option("--window", help="Scope to a window title (no focus needed).")
@click.option(
    "--search-region", "search_region", callback=region_cb,
    help="Restrict the search to 'X,Y,W,H'.",
)
@click.option("--click", "do_click", is_flag=True, help="Click the located center.")
@click.option("--mouse-button", "mouse_button", default="left", show_default=True)
@click.option("--padding", type=int, default=0, show_default=True)
@click.option(
    "--confidence-threshold", "confidence_threshold", type=float,
    default=75.0, show_default=True,
)
@click.option("--native-timeout", "native_timeout", type=float, default=5.0, show_default=True)
@click.option("--elements-dir", "elements_dir", default="./visus-elements", show_default=True)
@dry_run_option
@json_option
def capture(
    label, auto, text, native_, region, window, search_region, do_click,
    mouse_button, padding, confidence_threshold, native_timeout, elements_dir,
    dry_run, json_mode,
):
    locators = [v for v in (auto, text, native_, region) if v]
    if len(locators) != 1:
        fail(
            "provide exactly one of --auto / --text / --native / --region",
            json_mode=json_mode,
        )
        return

    from visus.desktop.core.elements import capture_element

    effective_click = bool(do_click) and not dry_run
    result = capture_element(
        label=label, auto=auto, text=text, native=native_, region=region,
        window=window, search_region=search_region, click=effective_click,
        mouse_button=mouse_button, padding=padding,
        confidence_threshold=confidence_threshold, native_timeout=native_timeout,
        elements_dir=elements_dir,
    )
    ok = bool(result.get("found"))
    if ok:
        human = (
            f"captured '{label}' via {result.get('located_by')} "
            f"-> {result.get('template_path')}"
        )
        if dry_run and do_click:
            human += " (dry-run: not clicked)"
        elif result.get("clicked"):
            human += " (clicked)"
    else:
        human = f"not found; see {result.get('annotated_path')}"
    done(result, json_mode=json_mode, ok=ok, human=human)

"""``visus screenshot`` -- capture the screen to a PNG on disk."""

from __future__ import annotations

import click

from .._common import json_option, region_cb
from .._output import done


@click.command(
    help="Capture the screen to a PNG on disk (the find_image template format)."
)
@click.argument("path")
@click.option("--region", callback=region_cb, help="Crop region 'X,Y,W,H'.")
@click.option("--monitor", type=int, help="1-based physical monitor index.")
@json_option
def screenshot(path, region, monitor, json_mode):
    from visus.desktop.core.screen import save_screenshot

    result = save_screenshot(
        path, region=tuple(region) if region else None, monitor=monitor
    )
    done(
        result, json_mode=json_mode, ok=True,
        human=f"saved {result.get('path')} ({result.get('width')}x{result.get('height')})",
    )

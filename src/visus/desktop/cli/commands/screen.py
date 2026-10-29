"""``visus screenshot`` / ``visus monitors`` / ``visus display-size``."""

from __future__ import annotations

import base64
import io

import click

from .._common import json_option, region_cb
from .._output import done, fail


@click.command(
    help="Capture the screen to a PNG on disk (the find_image template format)."
)
@click.argument("path", required=False)
@click.option("--region", callback=region_cb, help="Crop region 'X,Y,W,H'.")
@click.option("--monitor", type=int, help="1-based physical monitor index.")
@click.option(
    "--base64", "as_base64", is_flag=True,
    help="Print a base64 PNG to stdout instead of saving (PATH optional).",
)
@click.option(
    "--jpeg", is_flag=True,
    help="With --base64: JPEG instead of PNG (smaller for photo-like content; "
         "flat UI screens compress about as well as PNG).",
)
@click.option(
    "--quality", type=click.IntRange(1, 95), default=70, show_default=True,
    help="JPEG quality, with --jpeg.",
)
@click.option(
    "--max-width", "max_width", type=click.IntRange(min=64), default=None,
    help="With --base64: shrink to at most this width. An AI model pays for an "
         "image by its resolution, not its bytes -- 1280 instead of 1920 costs "
         "far fewer tokens. 'scale' in --json maps image pixels back to the screen.",
)
@json_option
def screenshot(path, region, monitor, as_base64, jpeg, quality, max_width, json_mode):
    region_t = tuple(region) if region else None

    if as_base64:
        from visus.desktop.core.screen import capture_screen

        img = capture_screen(region=region_t, monitor=monitor)
        scale = 1.0
        if max_width and img.width > max_width:
            from PIL import Image

            scale = max_width / img.width
            img = img.resize((max_width, max(1, round(img.height * scale))), Image.LANCZOS)
        buf = io.BytesIO()
        if jpeg:
            img.convert("RGB").save(buf, format="JPEG", quality=quality)
        else:
            img.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        result = {
            "mime_type": "image/jpeg" if jpeg else "image/png",
            "data_base64": encoded,
            "width": img.width,
            "height": img.height,
            # screen pixel = image pixel / scale (1.0 when not shrunk)
            "scale": round(scale, 6),
        }
        done(result, json_mode=json_mode, ok=True, human=encoded)
        return

    if not path:
        fail("PATH is required unless --base64 is given", json_mode=json_mode)
        return

    import os

    from PIL import Image

    from visus.desktop.core.screen import save_screenshot as _save

    # ``save_screenshot`` returns the path string; build the {path,width,height}
    # result here (same shape the MCP tool returns) by reading the saved file.
    written = os.path.abspath(_save(path, region=region_t, monitor=monitor))
    with Image.open(written) as img:
        width, height = img.size
    result = {"path": written, "width": int(width), "height": int(height)}
    done(
        result, json_mode=json_mode, ok=True,
        human=f"saved {result['path']} ({result['width']}x{result['height']})",
    )


@click.command(help="List connected monitors (for the --monitor index).")
@json_option
def monitors(json_mode):
    from visus.desktop.core.screen import get_monitors as _get

    rows = [
        {
            "index": m.index, "x": m.x, "y": m.y,
            "width": m.width, "height": m.height, "is_primary": m.is_primary,
        }
        for m in _get()
    ]
    human = "\n".join(
        f"{r['index']}\t{r['width']}x{r['height']} @ ({r['x']},{r['y']})"
        f"{'  [primary]' if r['is_primary'] else ''}"
        for r in rows
    ) or "(no monitors)"
    done(rows, json_mode=json_mode, ok=True, human=human)


@click.command(name="display-size", help="Print the primary display size.")
@json_option
def display_size(json_mode):
    from visus.desktop.core.screen import get_display_size as _size

    width, height = _size()
    result = {"width": int(width), "height": int(height)}
    done(result, json_mode=json_mode, ok=True, human=f"{width}x{height}")

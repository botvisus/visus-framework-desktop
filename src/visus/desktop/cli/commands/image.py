"""``visus image`` -- template-image find / click / relative-image."""

from __future__ import annotations

import click

from .._common import build_bot, json_option, region_cb
from .._output import done


@click.group(help="Template-image targeting: find / click / relative.")
def image():
    pass


def _box_payload(box):
    x, y, w, h = box
    return {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}


def _robustness_options(f):
    """Wait / retry knobs shared by find / click."""
    f = click.option(
        "--max-attempts", "max_attempts", type=int, default=3, show_default=True,
        help="Retry attempts.",
    )(f)
    f = click.option(
        "--wait-until-found", "wait_until_found", is_flag=True,
        help="Poll until the template appears, then act.",
    )(f)
    f = click.option(
        "--wait-until-disappears", "wait_until_disappears", is_flag=True,
        help="Wait until the template is gone.",
    )(f)
    f = click.option(
        "--wait-timeout", "wait_timeout", type=int, default=None,
        help="Seconds for the wait options (default: config wait_timeout).",
    )(f)
    return f


@image.command(name="find", help="Find a template PNG; print its box (no click).")
@click.argument("image_path")
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@click.option("--confidence", type=float, default=0.9, show_default=True, help="Match confidence 0-1.")
@click.option(
    "--specific/--no-specific", default=True, show_default=True,
    help="--specific: search the region; --no-specific: whole screen + scale variations.",
)
@click.option("--backtrack", is_flag=True, help="Retry with adjustments on a miss.")
@_robustness_options
@json_option
def find(
    image_path, region, confidence, specific, backtrack,
    max_attempts, wait_until_found, wait_until_disappears, wait_timeout, json_mode,
):
    box = build_bot().find_image(
        image_path, region=tuple(region) if region else None, confidence=confidence,
        specific=specific, backtrack=backtrack, max_attempts=max_attempts,
        wait_until_found=wait_until_found, wait_until_disappears=wait_until_disappears,
        wait_timeout=wait_timeout,
    )
    if box is None:
        done(None, json_mode=json_mode, ok=False, human="not on screen")
        return
    payload = _box_payload(box)
    done(payload, json_mode=json_mode, ok=True, human=f"({payload['x']}, {payload['y']})")


@image.command(name="click", help="Find a template PNG and click its center.")
@click.argument("image_path")
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@click.option("--confidence", type=float, default=0.9, show_default=True, help="Match confidence 0-1.")
@click.option(
    "--specific/--no-specific", default=True, show_default=True,
    help="--specific: search the region; --no-specific: whole screen + scale variations.",
)
@click.option(
    "--button", "mouse_button", default="left", show_default=True,
    type=click.Choice(["left", "right", "double", "move_to"]),
)
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after the click (s).")
@click.option("--sendtext", default=None, help="Type this string right after clicking.")
@click.option("--backtrack", is_flag=True, help="Retry earlier step(s) on a miss.")
@_robustness_options
@json_option
def click_cmd(
    image_path, region, confidence, specific, mouse_button, delay, sendtext,
    backtrack, max_attempts, wait_until_found, wait_until_disappears, wait_timeout,
    json_mode,
):
    ok = bool(
        build_bot().click_image(
            image_path, region=tuple(region) if region else None,
            confidence=confidence, specific=specific, mouse_button=mouse_button,
            delay=delay, sendtext=sendtext, backtrack=backtrack,
            max_attempts=max_attempts, wait_until_found=wait_until_found,
            wait_until_disappears=wait_until_disappears, wait_timeout=wait_timeout,
        )
    )
    done(ok, json_mode=json_mode, ok=ok, human=("clicked" if ok else "not on screen"))


@image.command(name="find-all", help="Find EVERY occurrence of a template PNG (no click).")
@click.argument("image_path")
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@click.option("--confidence", type=float, default=0.9, show_default=True, help="Match confidence 0-1.")
@json_option
def find_all_cmd(image_path, region, confidence, json_mode):
    from visus.desktop import find_all as _find_all

    boxes = _find_all(image_path, region=tuple(region) if region else None, confidence=confidence)
    payload = [
        {"occurrence": i, "x": b[0], "y": b[1], "width": b[2], "height": b[3]}
        for i, b in enumerate(boxes, start=1)
    ]
    human = (
        "\n".join(f"#{p['occurrence']} ({p['x']}, {p['y']}) {p['width']}x{p['height']}" for p in payload)
        if payload else "no matches"
    )
    done(payload, json_mode=json_mode, ok=bool(payload), human=human)


@image.command(name="find-multiple", help="Find the first match of SEVERAL template PNGs.")
@click.argument("image_paths", nargs=-1, required=True)
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@click.option("--confidence", type=float, default=0.9, show_default=True, help="Match confidence 0-1.")
@json_option
def find_multiple_cmd(image_paths, region, confidence, json_mode):
    from visus.desktop import find_multiple as _find_multiple

    found = _find_multiple(
        list(image_paths), region=tuple(region) if region else None, confidence=confidence
    )
    payload = {
        path: ({"x": b[0], "y": b[1], "width": b[2], "height": b[3]} if b else None)
        for path, b in found.items()
    }
    human = "\n".join(
        f"{path}: {'(' + str(box['x']) + ',' + str(box['y']) + ')' if box else 'not found'}"
        for path, box in payload.items()
    )
    done(payload, json_mode=json_mode, ok=any(payload.values()), human=human)


@image.command(name="relative", help="Find/click a target template NEAR a unique anchor.")
@click.argument("anchor_image")
@click.argument("target_image")
@click.option("--max-distance", "max_distance", type=int, default=200, show_default=True)
@click.option("--confidence", type=float, default=0.9, show_default=True, help="Match confidence 0-1.")
@click.option(
    "--target-region", "target_region", callback=region_cb,
    help="Scope the target search to 'X,Y,W,H'.",
)
@click.option("--click", "do_click", is_flag=True, help="Click the target (else just locate).")
@click.option(
    "--button", "mouse_button", default="left", show_default=True,
    type=click.Choice(["left", "right", "double", "move_to"]),
)
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after the click (s).")
@click.option("--sendtext", default=None, help="Type this string right after clicking (click only).")
@click.option("--backtrack", is_flag=True, help="Retry earlier step(s) on a miss (click only).")
@click.option(
    "--max-attempts", "max_attempts", type=int, default=3, show_default=True,
    help="Retry attempts (click only).",
)
@click.option(
    "--wait-until-found", "wait_until_found", is_flag=True,
    help="Poll until the pair appears, then act.",
)
@click.option(
    "--wait-until-disappears", "wait_until_disappears", is_flag=True,
    help="Wait until the target is gone.",
)
@click.option(
    "--wait-timeout", "wait_timeout", type=int, default=None,
    help="Seconds for the wait options (default: config wait_timeout).",
)
@json_option
def relative(
    anchor_image, target_image, max_distance, confidence, target_region,
    do_click, mouse_button, delay, sendtext, backtrack, max_attempts,
    wait_until_found, wait_until_disappears, wait_timeout, json_mode,
):
    bot = build_bot()
    tregion = tuple(target_region) if target_region else None
    if do_click:
        ok = bool(
            bot.click_relative_image(
                anchor_image, target_image, max_distance=max_distance,
                confidence=confidence, target_region=tregion,
                mouse_button=mouse_button, delay=delay, sendtext=sendtext,
                backtrack=backtrack, max_attempts=max_attempts,
                wait_until_found=wait_until_found,
                wait_until_disappears=wait_until_disappears, wait_timeout=wait_timeout,
            )
        )
        done(ok, json_mode=json_mode, ok=ok, human=("clicked" if ok else "target not found"))
        return
    box = bot.find_relative_image(
        anchor_image, target_image, max_distance=max_distance,
        confidence=confidence, target_region=tregion,
        wait_until_found=wait_until_found,
        wait_until_disappears=wait_until_disappears, wait_timeout=wait_timeout,
    )
    if box is None:
        done(None, json_mode=json_mode, ok=False, human="target not found")
        return
    payload = _box_payload(box)
    done(payload, json_mode=json_mode, ok=True, human=f"({payload['x']}, {payload['y']})")

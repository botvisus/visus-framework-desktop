"""``visus text`` -- OCR text: find/click a label, list all matches, overlay them."""

from __future__ import annotations

import click

from .._common import json_option, region_cb
from .._output import done


@click.group(help="OCR text: find/click a label, list every match, or overlay them.")
def text():
    pass


def _ocr_option(f):
    """``--ocr tesseract|rapidocr`` shared by the text subcommands."""
    return click.option(
        "--ocr", "ocr_backend", default=None,
        type=click.Choice(["tesseract", "rapidocr"]),
        help="OCR engine: 'tesseract' (needs the binary) or 'rapidocr' "
             "(bundled ONNX models). Default: persisted config, else tesseract.",
    )(f)


def _filter_option(f):
    return click.option(
        "--filter", "filter_type", default="both", show_default=True,
        type=click.Choice(["letters", "numbers", "both"]),
        help="Restrict matched characters.",
    )(f)


def _word_option(f):
    """``--word`` -- box the matched word, not the whole OCR line."""
    return click.option(
        "--word", "word_box", is_flag=True,
        help="Box only the searched word, not the whole OCR text line "
             "(e.g. just 'visus' inside a long URL). RapidOCR uses native "
             "per-word boxes; no-op on Tesseract.",
    )(f)


def _robustness_options(f):
    """Wait / retry knobs shared by the find/click primitives."""
    f = click.option(
        "--max-attempts", "max_attempts", type=int, default=3, show_default=True,
        help="Retry attempts.",
    )(f)
    f = click.option(
        "--backtrack", is_flag=True, help="Retry with adjusted thresholds on a miss.",
    )(f)
    f = click.option(
        "--wait-until-found", "wait_until_found", is_flag=True,
        help="Poll until the target appears, then act.",
    )(f)
    f = click.option(
        "--wait-until-disappears", "wait_until_disappears", is_flag=True,
        help="Wait until the target is gone.",
    )(f)
    f = click.option(
        "--wait-timeout", "wait_timeout", type=int, default=None,
        help="Seconds for the wait options (default: config wait_timeout).",
    )(f)
    return f


def _make_bot(ocr_backend):
    """Build a VisusBot: persisted config + an optional --ocr override."""
    from .._common import build_bot

    return build_bot(ocr_backend=ocr_backend)


@text.command(name="find", help="Find on-screen text via OCR; print its box (no click).")
@click.argument("query")
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@_filter_option
@click.option(
    "--confidence-threshold", "confidence_threshold", type=float, default=75.0,
    show_default=True, help="OCR confidence 0-100.",
)
@click.option("--occurrence", type=int, default=1, show_default=True, help="Nth match (1-based).")
@_word_option
@_robustness_options
@_ocr_option
@json_option
def find(
    query, region, filter_type, confidence_threshold, occurrence, word_box,
    max_attempts, backtrack, wait_until_found, wait_until_disappears, wait_timeout,
    ocr_backend, json_mode,
):
    bot = _make_bot(ocr_backend)
    box = bot.find_text(
        query,
        region=tuple(region) if region else None,
        filter_type=filter_type,
        confidence_threshold=confidence_threshold,
        occurrence=occurrence,
        max_attempts=max_attempts,
        backtrack=backtrack,
        wait_until_found=wait_until_found,
        wait_until_disappears=wait_until_disappears,
        wait_timeout=wait_timeout,
        word_box=word_box,
    )
    if box is None:
        done(None, json_mode=json_mode, ok=False, human=f"'{query}' not found")
        return
    x, y, w, h = box
    payload = {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
    done(payload, json_mode=json_mode, ok=True, human=f"({x}, {y}) {w}x{h}")


@text.command(name="click", help="Find on-screen text via OCR and click its center.")
@click.argument("query")
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@_filter_option
@click.option(
    "--confidence-threshold", "confidence_threshold", type=float, default=75.0,
    show_default=True, help="OCR confidence 0-100.",
)
@click.option("--occurrence", type=int, default=1, show_default=True, help="Nth match (1-based).")
@click.option(
    "--button", "mouse_button", default="left", show_default=True,
    type=click.Choice(["left", "right", "double", "move_to"]),
)
@click.option("--delay", type=float, default=0, show_default=True, help="Pause after the click (s).")
@click.option("--sendtext", default=None, help="Type this string right after clicking.")
@_word_option
@_robustness_options
@_ocr_option
@json_option
def click_cmd(
    query, region, filter_type, confidence_threshold, occurrence,
    mouse_button, delay, sendtext, word_box,
    max_attempts, backtrack, wait_until_found, wait_until_disappears, wait_timeout,
    ocr_backend, json_mode,
):
    bot = _make_bot(ocr_backend)
    ok = bool(
        bot.click_text(
            query,
            region=tuple(region) if region else None,
            filter_type=filter_type,
            confidence_threshold=confidence_threshold,
            occurrence=occurrence,
            mouse_button=mouse_button,
            delay=delay,
            sendtext=sendtext,
            max_attempts=max_attempts,
            backtrack=backtrack,
            wait_until_found=wait_until_found,
            wait_until_disappears=wait_until_disappears,
            wait_timeout=wait_timeout,
            word_box=word_box,
        )
    )
    done(ok, json_mode=json_mode, ok=ok, human=("clicked" if ok else f"'{query}' not found"))


@text.command(
    name="find-all",
    help="List EVERY on-screen occurrence of TEXT and overlay each one, numbered.",
)
@click.argument("query")
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@_filter_option
@click.option(
    "--confidence-threshold", "confidence_threshold", type=float, default=None,
    help="Minimum OCR confidence 0-100 (defaults to the config value).",
)
@click.option(
    "--overlay/--no-overlay", "overlay", default=True, show_default=True,
    help="Also paint a numbered overlay on screen (matching the printed #N).",
)
@click.option("--color", default="red", show_default=True, help="Overlay color.")
@click.option(
    "--duration", type=int, default=3000, show_default=True,
    help="How long each overlay stays on screen (ms).",
)
@click.option("--width", type=int, default=3, show_default=True, help="Outline thickness (px).")
@_word_option
@_ocr_option
@json_option
def find_all(
    query, region, filter_type, confidence_threshold,
    overlay, color, duration, width, word_box, ocr_backend, json_mode,
):
    bot = _make_bot(ocr_backend)
    region_arg = tuple(region) if region else None
    if overlay:
        # Draws the numbered overlay AND returns the same matches we list, so
        # the printed #N lines up with the number painted on screen.
        matches = bot.show_text_occurrences(
            query,
            region=region_arg,
            filter_type=filter_type,
            confidence_threshold=confidence_threshold,
            color=color,
            duration_ms=duration,
            width=width,
            word_box=word_box,
        )
    else:
        matches = bot.find_all_text(
            query,
            region=region_arg,
            filter_type=filter_type,
            confidence_threshold=confidence_threshold,
            word_box=word_box,
        )
    payload = [
        {
            "occurrence": i,
            "x": int(x), "y": int(y), "width": int(w), "height": int(h),
            "confidence": round(float(conf), 2),
        }
        for i, (x, y, w, h, conf) in enumerate(matches, start=1)
    ]
    human = (
        "\n".join(
            f"#{m['occurrence']} ({m['x']}, {m['y']}) {m['width']}x{m['height']} "
            f"conf={m['confidence']}%"
            for m in payload
        )
        if payload
        else f"no occurrences of '{query}' found"
    )
    # The overlays paint in daemon threads; ``done`` exits the process, which
    # kills them instantly regardless of --duration. Hold here FIRST (for the
    # duration + a small teardown margin) so they stay up, THEN report & exit.
    if overlay and payload:
        import time

        time.sleep(duration / 1000.0 + 0.3)
    done(payload, json_mode=json_mode, ok=bool(payload), human=human)


@text.command(name="show", help="Overlay every occurrence of TEXT on screen, numbered.")
@click.argument("query")
@click.option("--region", callback=region_cb, help="Search region 'X,Y,W,H' (else whole screen).")
@_filter_option
@click.option(
    "--confidence-threshold", "confidence_threshold", type=float, default=None,
    help="Minimum OCR confidence 0-100 (defaults to the config value).",
)
@click.option("--color", default="red", show_default=True, help="Overlay color.")
@click.option(
    "--duration", type=int, default=3000, show_default=True,
    help="How long each overlay stays on screen (ms).",
)
@click.option("--width", type=int, default=3, show_default=True, help="Outline thickness (px).")
@_word_option
@_ocr_option
@json_option
def show(
    query, region, filter_type, confidence_threshold, color, duration, width,
    word_box, ocr_backend, json_mode,
):
    bot = _make_bot(ocr_backend)
    matches = bot.show_text_occurrences(
        query,
        region=tuple(region) if region else None,
        filter_type=filter_type,
        confidence_threshold=confidence_threshold,
        color=color,
        duration_ms=duration,
        width=width,
        word_box=word_box,
    )
    payload = [
        {
            "occurrence": i,
            "x": int(x), "y": int(y), "width": int(w), "height": int(h),
            "confidence": round(float(conf), 2),
        }
        for i, (x, y, w, h, conf) in enumerate(matches, start=1)
    ]
    # The overlays paint in daemon threads; if the CLI process exits now they
    # are killed and vanish instantly regardless of --duration. Hold the
    # process for the duration (+ a small teardown margin) so they stay up.
    if payload:
        import time

        time.sleep(duration / 1000.0 + 0.3)
    human = (
        f"overlaid {len(payload)} occurrence(s) of '{query}' for {duration}ms"
        if payload
        else f"no occurrences of '{query}' found"
    )
    done(payload, json_mode=json_mode, ok=bool(payload), human=human)

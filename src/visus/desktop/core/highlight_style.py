"""The look of the highlight — the same box the visus-studio draws.

Brand green ``#2ea043``, a thin rounded border, a translucent fill of the same
color and a soft glow around it, a few pixels clear of the target. One drawing
serves both the on-screen highlight (``overlay_win32``, a per-pixel-alpha
window) and the box on the report screenshots (``TaskExecutor._annotate_location``),
so what the run showed and what the report shows look the same.

Pure PIL: no Win32 here.
"""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFilter, ImageFont

STUDIO_GREEN = (46, 160, 67)  # #2ea043, visus-studio's brand green

# The named overlay colors. "green" is the studio green; pure black is nudged so a
# color-keyed fallback never makes it invisible.
COLORS_RGB = {
    "red": (255, 0, 0),
    "blue": (0, 128, 255),
    "green": STUDIO_GREEN,
    "yellow": (255, 255, 0),
    "purple": (128, 0, 128),
    "orange": (255, 128, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
    "black": (1, 1, 1),
}

PAD = 3  # px clear around the target
RADIUS = 3  # corner radius
FILL_ALPHA = 38  # ~15 %: the target stays readable under the fill
GLOW_ALPHA = 150
GLOW_BLUR = 5  # gaussian radius of the soft glow
GLOW_MARGIN = 10  # room the glow needs around the box
LABEL_SIZE = 18  # numbered overlays: the caption above the box
LABEL_BAND = 26


def color_rgb(name: str | tuple[int, int, int]) -> tuple[int, int, int]:
    """RGB of a named overlay color (unknown names -> the studio green)."""
    if isinstance(name, tuple):
        return name
    return COLORS_RGB.get(str(name).lower(), STUDIO_GREEN)


def _font(size: int):
    for candidate in ("segoeuib.ttf", "seguisb.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(
    w: int,
    h: int,
    color: str | tuple[int, int, int] = "green",
    width: int = 2,
    label: str | None = None,
) -> tuple[Image.Image, int, int]:
    """The highlight for a ``w`` x ``h`` target as an RGBA image.

    Returns ``(image, ox, oy)``: the target's top-left sits at ``(ox, oy)`` inside
    the image (the image also holds the padding, the glow and an optional label).
    """
    rgb = color_rgb(color)
    width = max(1, int(width))
    w, h = max(1, int(w)), max(1, int(h))
    top_extra = LABEL_BAND if label else 0
    margin = GLOW_MARGIN
    ox, oy = margin + PAD, margin + PAD + top_extra
    img_w = w + 2 * (margin + PAD)
    img_h = h + 2 * (margin + PAD) + top_extra
    box = (ox - PAD, oy - PAD, ox + w + PAD - 1, oy + h + PAD - 1)

    glow = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        box, radius=RADIUS, outline=(*rgb, GLOW_ALPHA), width=width + 2
    )
    image = glow.filter(ImageFilter.GaussianBlur(GLOW_BLUR))

    shape = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shape)
    draw.rounded_rectangle(box, radius=RADIUS, fill=(*rgb, FILL_ALPHA))
    draw.rounded_rectangle(box, radius=RADIUS, outline=(*rgb, 255), width=width)
    if label:
        draw.text((box[0] + 2, oy - PAD - LABEL_BAND + 2), str(label),
                  fill=(*rgb, 255), font=_font(LABEL_SIZE))
    image.alpha_composite(shape)
    return image, ox, oy


def annotate(
    screenshot: Image.Image,
    location: tuple[int, int, int, int],
    color: str | tuple[int, int, int] = "green",
    width: int = 2,
) -> None:
    """Draw the highlight on ``screenshot`` (in place) around ``location`` (x, y, w, h)."""
    x, y, w, h = (int(v) for v in location[:4])
    overlay, ox, oy = render(w, h, color, width)
    left, top = x - ox, y - oy
    # the part of the highlight that falls on the screenshot
    crop = (max(0, left), max(0, top),
            min(screenshot.width, left + overlay.width), min(screenshot.height, top + overlay.height))
    if crop[0] >= crop[2] or crop[1] >= crop[3]:
        return
    region = screenshot.crop(crop).convert("RGBA")
    part = overlay.crop((crop[0] - left, crop[1] - top, crop[2] - left, crop[3] - top))
    region.alpha_composite(part)
    screenshot.paste(region.convert(screenshot.mode), crop[:2])

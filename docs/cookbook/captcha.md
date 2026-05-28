# Cookbook — Solve old-style image captchas with OCR

**Problem.** A legacy intranet site shows a 5-character captcha (the
kind that's just black text on a noisy background). You need the bot
to read it and type the answer before it expires.

**Solution.** Capture the captcha image as a region, pre-process to
strip noise, and run OCR with a constrained character set. This recipe
uses Tesseract's `tessedit_char_whitelist` (Tesseract backend only) so
similar-looking glyphs are excluded from the result.

> ⚠️ Modern captchas (reCAPTCHA v3, hCaptcha, Cloudflare Turnstile)
> are not OCR-solvable. Use a real captcha-solving service. This
> recipe targets the older "wavy black text on grey" style.

## Minimal example

```python
import pytesseract
from PIL import ImageOps

from visus.desktop import VisusBot, capture_screen

bot = VisusBot()

# 1. Crop the captcha region from the live screen.
captcha = capture_screen(region=(420, 180, 200, 60))

# 2. Pre-process: convert to greyscale, invert, threshold.
gray = ImageOps.grayscale(captcha)
binary = gray.point(lambda p: 0 if p < 140 else 255)

# 3. OCR with a tight character set.
text = pytesseract.image_to_string(
    binary,
    config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
).strip()

# 4. Type the answer.
bot.execute_tasks([
    {"text": "Captcha", "region": (300, 250, 400, 50)},
    {"type": "type_text", "text": text},
    {"type": "keyboard_command", "command": "Enter"},
])
```

## Why a whitelist matters

Tesseract returns `0` and `O` from the same glyph half the time. By
removing `0` (zero), `O` (capital O), `I` (capital i), `1` (one),
and `l` (lowercase L) from the allowed set, you drop the most common
ambiguous swaps that captchas can never legally produce.

The whitelist is a Tesseract-only feature; switching to the RapidOCR
backend (Phase 3 / E5) loses it. Stay on Tesseract for captchas.

## Pre-processing toolbox

| Captcha trait | Pre-processing |
|---|---|
| Background gradient | `ImageOps.grayscale` + threshold (>140) |
| Sparse dotted noise | `cv2.medianBlur(arr, 3)` before OCR |
| Wavy character spacing | Use `--psm 7` (single line) instead of `--psm 6` |
| Distinctly coloured background | `cv2.inRange` HSV mask to keep only text colours |

## Tested patterns

```python
def solve_captcha(bot, region):
    img = capture_screen(region=region)
    gray = ImageOps.grayscale(img)
    binary = gray.point(lambda p: 0 if p < 140 else 255)
    return pytesseract.image_to_string(
        binary,
        config="--psm 7 -c tessedit_char_whitelist=ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
    ).strip()
```

## See also

* [Cookbook index](README.md)
* [`docs/troubleshooting.md`](../troubleshooting.md#ocr-cannot-find-text-that-is-clearly-on-screen)
  -- general OCR debugging tips.
* [Cookbook -- download wait](download-wait.md)

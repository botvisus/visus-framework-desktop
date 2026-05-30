# Solve a simple image captcha (OCR)

For a **legible, text-based** captcha (distorted letters/digits, not reCAPTCHA),
OCR the captcha region, then type the result into the answer field. Tune the
character filter and try the alternate OCR engine if the first misses.

```python
from visus.desktop import VisusBot, ensure_window, BotVisionConfig

ensure_window(process="myapp.exe")

# RapidOCR is often more robust on noisy/curved captcha glyphs; swap as needed.
bot = VisusBot(config=BotVisionConfig({"ocr_backend": "rapidocr"}))

# 1. OCR the captcha box (use a tight region around just the glyphs).
captcha_region = (520, 300, 180, 60)
words = bot.extract_text_from_region(
    region=captcha_region,
    filter_type="both",          # "letters" / "numbers" / "both"
    return_full_data=True,       # -> [{text, confidence, box, absolute_box}, ...]
)
guess = "".join(w["text"] for w in words).strip()
print("captcha guess:", guess)

# 2. Type it into the answer field and submit.
bot.click_text("Answer", region=(400, 360, 400, 80))   # focus the input
bot.type_text(guess)
bot.click_text("Submit", region=(400, 420, 400, 80))
```

**Notes**

- Keep `captcha_region` tight — surrounding chrome/labels pollute the read.
- If digits-only, set `filter_type="numbers"`; letters-only, `"letters"`.
- Inspect what OCR actually read with `return_full_data=True` and the per-word
  `confidence`; if confidence is low, try the other `ocr_backend`
  (`"tesseract"` ↔ `"rapidocr"`) or pre-zoom the screenshot.
- This only works for OCR-legible captchas. Audio/behavioral/reCAPTCHA challenges
  are out of scope — escalate to the user.

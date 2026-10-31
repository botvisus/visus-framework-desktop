---
name: solve-image-captcha
description: Read an old-style image captcha (wavy black text on a noisy background) via take_screenshot + extract_text_from_region with a constrained Tesseract whitelist, then type the answer into the captcha input field.
when_to_use: Activate ONLY for legacy intranet captchas (image-based, ~5 alphanumeric characters). Do NOT activate for modern captchas (reCAPTCHA v3, hCaptcha, Cloudflare Turnstile) — those require a paid solver service and are out of scope for this skill.
---

# Solve an old-style image captcha

## Pre-flight

* Confirm with the user (or yourself, from `take_screenshot`) that the captcha is the **image-text** kind. A "Verify you are human" checkbox or a coloured-button grid is NOT this — abort and tell the user we can't solve it.
* Make sure the OCR backend is Tesseract (whitelisting is unique to it):

  ```text
  configure(config={"ocr_backend": "tesseract"})
  ```

## Steps

1. `take_screenshot()` — orient.
2. Capture the captcha image as its own region:
   * `take_screenshot(region=[x, y, w, h])` — store the data URL or width/height for sanity.
3. Read it with a constrained alphabet. Captchas avoid ambiguous glyphs (`0`/`O`, `1`/`I`/`l`), so whitelisting only `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` resolves most ambiguous reads.
   * Use `extract_text_from_region(region=[x, y, w, h], filter_type="both", return_full_data=false)`.
   * If the result has spaces or extra characters, trim them.
4. Locate the captcha input field: `find_text(text="Captcha")` or look at the layout from step 1.
5. `click_at(x, y)` on the field, then `type_text(text="<solved>")`.
6. Click the submit button (commonly "Verify", "Continue", "Submit").
7. `wait_for_stable_screen(stable_for=0.6, timeout=10)`.
8. Verify success — `find_text(text="Welcome")` (or whatever appears post-captcha). If `None`, retry **at most twice**, then escalate to the user.

## Retry budget

Captcha systems lock accounts after ~3 wrong attempts. Hard-cap your retries at 2:

```text
for attempt in [1, 2, 3]:
    if solve_and_submit():
        break
    if attempt == 2:
        report failure and stop
```

## What to refuse

* Skip this skill for reCAPTCHA / hCaptcha / Cloudflare. Tell the user the captcha is unsolvable by OCR and recommend a human-in-the-loop or a paid captcha service.
* If the captcha is audio-based, this skill does not apply.

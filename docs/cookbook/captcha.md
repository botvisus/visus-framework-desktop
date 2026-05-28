# Cookbook — Captcha via OCR (stub)

> 🚧 **Stub.** Recipe planned for an upcoming release.

## What this recipe will cover

* Capture a fixed region containing the captcha image:
  ```python
  bot.save_screenshot("captcha.png", region=(420, 180, 200, 60))
  ```
* Pre-process the image (binarize, dilate noise) — the
  `image_processing` module has the helpers; the recipe will pick the
  right pipeline for typical "wavy text" captchas.
* OCR the cleaned image with `find_text` or directly with
  `pytesseract.image_to_string`.
* Type the answer into the field with `type_text`.

## Caveats

* Modern captchas (reCAPTCHA v3, hCaptcha) are **not** OCR-solvable. This
  recipe targets old-style image captchas.
* For unsolvable captchas, the planned [`W4` task type](../research/2026-05-28-improvements-catalog.md#-web-automation-visus-web-planned-sibling)
  will integrate paid solvers (2captcha / anti-captcha) behind a stable
  API.

## See also

* [Cookbook index](README.md)

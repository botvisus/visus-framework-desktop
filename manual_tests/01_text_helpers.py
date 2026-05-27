"""Text helpers demo — clean_text, matches_filter, validators, extractors.

These are pure functions: no screen, mouse, or Tesseract needed.

Run:  python manual_tests/01_text_helpers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from visus.desktop import clean_text, matches_filter
from visus.desktop.utils.text_filters import (
    extract_letters_from_text,
    extract_numbers_from_text,
    validate_text_input,
)


def show(label: str, value: object) -> None:
    print(f"  {label:<52} -> {value!r}")


def main() -> int:
    print("clean_text(text, filter_type)  — filters characters by type")
    show('clean_text("  R$ 1.234,56 total!  ", "numbers")',
         clean_text("  R$ 1.234,56 total!  ", "numbers"))
    show('clean_text("  Order #42 — Ação  ", "letters")',
         clean_text("  Order #42 — Ação  ", "letters"))
    show('clean_text("  user_name 99!  ", "both")',
         clean_text("  user_name 99!  ", "both"))
    show('clean_text("  ...trim me...  ", "trim")',
         clean_text("  ...trim me...  ", "trim"))

    print("\nmatches_filter(word, filter_type)  — note: 'numbers' means an integer 1..31")
    show('matches_filter("15", "numbers")', matches_filter("15", "numbers"))
    show('matches_filter("32", "numbers")', matches_filter("32", "numbers"))
    show('matches_filter("Hello", "letters")', matches_filter("Hello", "letters"))
    show('matches_filter("a1b2", "both")', matches_filter("a1b2", "both"))

    print("\nextractors")
    show('extract_numbers_from_text("Page 5 of 10 — 3 items")',
         extract_numbers_from_text("Page 5 of 10 — 3 items"))
    show('extract_letters_from_text("Item123abc456def")',
         extract_letters_from_text("Item123abc456def"))

    print("\nvalidate_text_input(text, filter_type)  — raises ValueError on empty/invalid")
    show('validate_text_input("  Total: 250  ", "numbers")',
         validate_text_input("  Total: 250  ", "numbers"))
    try:
        validate_text_input("!!!", "letters")
    except ValueError as exc:
        show('validate_text_input("!!!", "letters")  -> raised', f"ValueError: {exc}")

    print("\nDone. [OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

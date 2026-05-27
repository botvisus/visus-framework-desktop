"""Screen OCR demo — reads text from your screen and prints it (read-only).

Examples:
    python manual_tests/03_screen_ocr.py                 # whole screen
    python manual_tests/03_screen_ocr.py 0 0 800 200     # region x y width height
    python manual_tests/03_screen_ocr.py 0 0 800 200 --full   # with confidence + boxes
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from visus.desktop import VisusBot


def parse_region(args: list[str]) -> tuple[int, int, int, int] | None:
    nums = [a for a in args if a.lstrip("-").isdigit()]
    if len(nums) >= 4:
        x, y, w, h = (int(nums[i]) for i in range(4))
        return (x, y, w, h)
    return None


def main() -> int:
    args = sys.argv[1:]
    region = parse_region(args)
    full = "--full" in args

    try:
        bot = VisusBot()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Could not create VisusBot(): {exc}")
        print("       Is Tesseract OCR installed? See the project README.")
        return 1

    where = f"region {region}" if region else "the whole screen"
    print(f"Reading text from {where} ...\n")

    if full:
        data = bot.extract_text_from_region(
            region=region, filter_type="both", return_full_data=True
        )
        if not data:
            print("(no text detected)")
        for item in data:
            print(f"  conf={item['confidence']:>5}  box={item['absolute_box']}  "
                  f"text={item['text']!r}")
        print(f"\nDetected {len(data)} text fragments. [OK]")
    else:
        lines = bot.extract_text_from_region(region=region, filter_type="both")
        if not lines:
            print("(no text detected)")
        for line in lines:
            print(f"  {line!r}")
        print(f"\nDetected {len(lines)} text fragments. [OK]")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

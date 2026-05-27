"""Find on screen — locate text and/or an image and report where it is.

Read-only by default (it only reports coordinates). Pass --click to actually click
the first match.

Examples:
    python manual_tests/04_find_on_screen.py --text "File"
    python manual_tests/04_find_on_screen.py --image button.png --confidence 0.85
    python manual_tests/04_find_on_screen.py --text "Save" --region 0 0 1000 400 --click
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import argparse

from visus.desktop import VisusBot


def main() -> int:
    parser = argparse.ArgumentParser(description="Find text/image on screen.")
    parser.add_argument("--text", help="text to find via OCR")
    parser.add_argument("--image", help="path to a template image to find")
    parser.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "W", "H"),
                        help="restrict the search to a region")
    parser.add_argument("--confidence", type=float, default=0.9,
                        help="image match confidence (0.0-1.0), default 0.9")
    parser.add_argument("--filter", default="both", choices=["letters", "numbers", "both"],
                        help="OCR character filter, default 'both'")
    parser.add_argument("--click", action="store_true",
                        help="click the first match (otherwise just report it)")
    args = parser.parse_args()

    if not args.text and not args.image:
        parser.error("provide --text and/or --image")

    region = tuple(args.region) if args.region else None

    try:
        bot = VisusBot()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Could not create VisusBot(): {exc}")
        return 1

    if args.text:
        print(f"Searching for text {args.text!r} ...")
        loc = bot.find_text(args.text, region=region, filter_type=args.filter)
        if loc:
            print(f"  FOUND at (x, y, w, h) = {loc}")
            if args.click:
                print("  clicking it ...")
                print(f"  click_text -> {bot.click_text(args.text, region=region, filter_type=args.filter)}")
        else:
            print("  not found")

    if args.image:
        print(f"Searching for image {args.image!r} (confidence {args.confidence}) ...")
        loc = bot.find_image(args.image, region=region, confidence=args.confidence)
        if loc:
            print(f"  FOUND at (x, y, w, h) = {loc}")
            if args.click:
                print("  clicking it ...")
                print(f"  click_image -> {bot.click_image(args.image, region=region, confidence=args.confidence)}")
        else:
            print("  not found")

    print("\nDone. [OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

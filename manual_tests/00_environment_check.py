"""Environment check — verifies the install end to end without touching the screen.

Run:  python manual_tests/00_environment_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from source without installing the package: add the project's src/ to sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def main() -> int:
    print("=" * 70)
    print("Visus Desktop — environment check")
    print("=" * 70)

    # 1) Import + version + aliases
    try:
        import visus.desktop as vd
        from visus.desktop import BotVision, VisusBot, clean_text, limpar_texto
    except Exception as exc:  # noqa: BLE001 - report any import failure plainly
        print(f"[FAIL] Could not import visus.desktop: {exc}")
        return 1

    print(f"[OK]   import visus.desktop            -> {vd.__file__}")
    print(f"[OK]   version                         -> {vd.__version__}")
    print(f"[OK]   alias  BotVision is VisusBot    -> {BotVision is VisusBot}")
    print(f"[OK]   alias  limpar_texto is clean_text -> {limpar_texto is clean_text}")

    # 2) Text helpers (pure, no screen)
    assert clean_text("  123abc!  ", "numbers") == "123"
    assert clean_text("  123abc!  ", "letters") == "abc"
    assert clean_text("  123abc!  ", "both") == "123abc"
    print("[OK]   clean_text() filters            -> numbers/letters/both verified")

    # 3) Build a bot (this detects Tesseract and validates dependencies)
    try:
        bot = VisusBot()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Could not create VisusBot(): {exc}")
        print("       Is Tesseract OCR installed? See the project README.")
        return 1
    print("[OK]   VisusBot()                       -> created")

    # 4) Show a few resolved config defaults
    cfg = bot.config
    for key in ("confidence_threshold", "default_mouse_button", "overlay_color",
                "use_virtual_mouse", "wait_timeout"):
        print(f"         config[{key!r}] = {cfg.get(key)!r}")
    print(f"         tesseract_path = {cfg.get('tesseract_path')!r}")

    # 5) Capabilities
    colors = VisusBot.get_available_overlay_colors()
    print(f"[OK]   overlay colors ({len(colors)})            -> {', '.join(colors)}")

    commands = bot.get_available_keyboard_commands()
    print(f"[OK]   keyboard commands ({len(commands)})        -> "
          f"{', '.join(commands[:12])}{' ...' if len(commands) > 12 else ''}")

    print("=" * 70)
    print("All good. The library is installed and working. [OK]")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

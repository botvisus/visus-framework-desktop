# Cookbook — Oracle Forms (stub)

> 🚧 **Stub.** This recipe is being written. The bullet list below
> captures the patterns that will be expanded into the worked example.

## What makes Oracle Forms hard

* Java Web Start / Java applet rendering — not a normal Windows window
  hierarchy, so `pywinauto` cannot inspect it.
* Heavy keyboard-driven workflow (F-keys, Ctrl+F11, Ctrl+S).
* Slow, animation-free screen updates that defeat naive "click, sleep
  500 ms" patterns.

## Planned patterns

1. **OCR-only navigation.** `find_text(...)` against well-chosen
   `region` boxes is the most reliable primitive on the form area.
2. **Keyboard shortcuts via `execute_command`.** `Ctrl+F11`, `Ctrl+Up`,
   `F8` etc. as `keyboard_command` tasks.
3. **`wait_for_stable_screen`** (Phase 2, S1) for "wait until the form
   stops redrawing". Until that lands, polling a known anchor region
   with `find_image` works.
4. **`backtrack=True`** on every task — the form occasionally pops up
   a "Working…" modal that obscures the target.

## See also

* [Cookbook index](README.md)
* [Implementation roadmap](../research/2026-05-28-implementation-plan.md)

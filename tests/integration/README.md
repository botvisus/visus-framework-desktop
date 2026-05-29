# Integration tests

Tests in this directory hit the **real OS state** (display, clipboard,
mouse, processes, native Tk). They are **deselected by default** so a
normal `pytest` invocation stays fast and skip-free.

## ⚠️ Safety: real-input tests

Some tests send **real keystrokes / mouse clicks / window-close events**
to whatever window is focused, or pop a screen-covering overlay. Running
those on your working desktop will type into and close YOUR windows.

They are marked `@pytest.mark.real_input` and are **double-gated**:
`--integration` alone is not enough — you must ALSO set
`VISUS_INTEGRATION_REAL_INPUT=1`. Only do this on a throwaway VM or in
CI (Xvfb / dedicated runner), never on a machine you're actively using.

## Running locally

```bash
# Safe subset: read-only tests (screen capture, clipboard, doctor,
# executor-with-disk-source). The real-input tests SKIP here.
pytest tests/integration --integration -v

# Everything (unit + the safe integration subset)
pytest --integration -v
```

**Do NOT run the line below on your own desktop** — it will drive real
input. Use a disposable VM:

```bash
VISUS_INTEGRATION_REAL_INPUT=1 pytest tests/integration --integration -v
```

On Linux without a desktop session (CI runners, Docker containers,
servers) wrap with Xvfb so a virtual display absorbs the input:

```bash
VISUS_INTEGRATION_REAL_INPUT=1 \
xvfb-run -a --server-args="-screen 0 1920x1080x24" \
    pytest tests/integration --integration -v
```

## CI

`.github/workflows/integration.yml` runs the suite on:

| OS | Display | Trigger |
|---|---|---|
| Ubuntu | Xvfb (headless virtual) | manual + nightly + path-filtered PRs |
| Windows | native | same |
| macOS | not in scope (would need a real Mac runner with a logged-in user) | — |

## Why two suites?

The default unit suite (`tests/`) mocks every real interaction:
`capture_screen` returns a fake PIL frame, `pyautogui.click` is a no-op,
`subprocess.Popen` is intercepted. That keeps it fast (~38 s for 1020
tests) and 100 % deterministic, but it cannot exercise:

* the actual mss / pyautogui screen-capture fallback chain
* real-Tk overlay rendering (the unit suite patches `tk.Tk`)
* clipboard race against another process holding the clipboard
* `wait_for_file_stable` against an actual disk-flush sequence
* the executor's full `execute_tasks` → `_perform_action` chain with
  real time and real failures

The integration suite covers exactly those branches. It is **slower**
(~60 s on a desktop, longer in Xvfb) and **environmentally
dependent**, so it stays opt-in.

## Authoring conventions

* Every test inherits `@pytest.mark.integration` automatically via
  `conftest.py` — you don't need to add it.
* For OS-specific tests, use `pytestmark = pytest.mark.windows_only`
  (or `linux_only`) at module level. The shared conftest skips them on
  the other OS.
* Real-state tests should be **idempotent** — clean up any process /
  file you create. The `clean_notepad` fixture in
  `test_real_notepad_flow.py` is the pattern to copy.
* OS clipboard races on Windows: wrap pyperclip calls in the
  `_retry(...)` helper from `test_real_clipboard.py`.

## What's covered here

| Test file | What it exercises |
|---|---|
| `test_real_screen.py` | mss capture, region crop, monitor enumeration on a real (or Xvfb) display. |
| `test_real_clipboard.py` | pyperclip roundtrip with unicode + retry under Windows clipboard races. |
| `test_real_doctor.py` | `doctor.run_checks()` end-to-end against the actual environment. |
| `test_real_overlay.py` | Tk overlay rendered for ~50 ms (non-blocking + multi-region). |
| `test_real_notepad_flow.py` | Windows-only: launch Notepad, focus by localized title substring, type, terminate the process cleanly. |
| `test_real_executor_chain.py` | `execute_tasks` failure path, JSON event emission, circuit-breaker trip — all without any patching of the executor itself. |

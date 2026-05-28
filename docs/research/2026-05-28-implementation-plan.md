# Implementation plan — visus-desktop improvements

> **Date:** 2026-05-28
> **Companion:** [`2026-05-28-improvements-catalog.md`](2026-05-28-improvements-catalog.md)
> (the **what** + **why**; this doc is the **how** + **when**).
> **Item IDs** (e.g. `O1`, `T1`, `E5`) refer to the catalog.

## Principles

These hold for every item below:

1. **TDD** — write a failing test that captures the intent first, then implement,
   then verify with `pytest` + `ruff`. The existing 537-test suite is the safety net.
2. **Never break the public API** — every new parameter has a default that preserves
   today's behavior. Backward-compat aliases (`BotVision`, `limpar_texto`) stay.
3. **Match the original visus parameter style** — backtrack / wait_until_found /
   wait_until_disappears / wait_timeout / show_overlay / sendtext / delay /
   mouse_button — when the operation makes sense for them.
4. **Cross-platform by default, Windows-only with a clean fallback** — features
   that need pywinauto / win32 raise `NotSupportedOnThisOS` instead of an
   ImportError. Linux backends slot in behind the same interface when added.
5. **Incremental commits, small PRs** — each phase ships independently. Don't
   batch unrelated changes.
6. **Docs grow with the code** — README + `docs/api_reference.md` updated in the
   same commit as the new method.

## Sequencing rationale

Phases are ordered by **value × effort** with hard dependencies first.
Within a phase, items are independent and can ship in any order (or in parallel
via subagents). Each phase ends in a tagged release-candidate-style milestone.

```
PHASE 1  →  PHASE 2  →  PHASE 3  →  PHASE 4  →  PHASE 5  →  PHASE 6
quick      observability  engine       cross-     DX /         web + cloud
wins       + reliability  + hybrid     platform   tooling      + plugins
                                       (Linux)
                                                   ↑
                                                   depends on engine
                                                   for the recorder
```

---

## Phase 1 — Quick wins (≈ 1 week)

Highest ROI in the smallest blast radius. Most items are **S**-effort.

| ID | Item | Effort | Acceptance |
|----|------|--------|------------|
| B1 / TS4 | `conftest.py` warm-up for `cv2.gapi.wip.draw.Text` so `pytest --cov` works | S | `pytest --cov=visus.desktop` runs without the workaround shim. |
| O1 | **Screenshot-on-failure** on `execute_tasks` | S | On a failing task, a PNG named `<run_id>__<task_id>__<timestamp>.png` is saved under `config['artifacts_dir']` (default `./visus-artifacts/`). Path is attached to the `TaskResult`. Tests with a fake screen capture + a failing task verify the file appears. |
| O2 | Structured JSON logging with `run_id` / `task_id` / `duration_ms` | S | New `BotVisionConfig['log_format'] = 'json' \| 'text'`. JSON emits one line per task with fixed schema. Snapshot test of one record. |
| R1 | Generic `@retry(attempts=3, backoff='expo', exceptions=(...))` decorator in `visus.desktop.utils.retry` | S | Decorator + 6 tests covering attempts, backoff calculation, exception allow-list. Documented with the same vibe as `backtrack`. |
| R4 | `visus doctor` CLI subcommand (or `python -m visus.desktop.doctor`) checking Tesseract / display / pywinauto / required deps | S | Prints `[OK]` / `[FAIL]` per check; exits non-zero on failure. CI runs it on each OS. |
| R5 | Graceful shutdown: SIGINT handler in long-running flows releases held buttons and stops the heartbeat thread (when present) | S | A test issues SIGINT mid-run and asserts no held mouse buttons / no live threads at exit. |
| DOC1 | Cookbook scaffolding under `docs/cookbook/` with stubs for: Oracle Forms, download wait, captcha, Excel input, file dialogs | S | One worked recipe per stub (the rest are filled in later phases). |
| DOC2 | Expanded `docs/migration.md` from `bot-vision-suite` | S | Covers the new methods + the dispatch-bug fix + the rebrand. |
| DOC3 | `docs/troubleshooting.md` covering OCR-not-found, DPI wrong, pywinauto-can't-connect, Tcl/Tk broken | S | Each section has symptom + diagnosis + fix. |

**Definition of done for Phase 1:**
- Full suite green, ruff clean, build sane.
- `docs/cookbook/` browseable; `troubleshooting.md` indexed in `docs/README.md`.
- A `CHANGELOG` entry under `[Unreleased]` lists every shipped item.
- Tagged commit on `main` (no PR ceremony needed solo, but each item is one focused commit).

---

## Phase 2 — Observability + reliability deep cuts (≈ 1.5 weeks)

Phase 1 plants the seed (screenshot-on-failure, JSON logs); Phase 2 builds the
loop developers actually trust in production.

| ID | Item | Effort | Acceptance |
|----|------|--------|------------|
| O3 | **Session record/replay** | M | `bot.start_recording('run.zip')` captures screenshots + actions + timings; `Session.replay('run.zip')` reproduces with a mocked screen. Both round-trip in tests. |
| O4 | Per-task metrics (find_time, attempts, success rate) on `TaskResult` | S-M | New fields on `TaskResult`; existing tests updated; one new test for accumulator. |
| O5 | HTML run report (`bot.write_report(path)`) — timeline + screenshots + errors | M | Jinja-rendered single-file HTML; smoke test that opens it and looks for key tags. |
| O6 | Pluggable error sinks (Sentry / Datadog / OpenTelemetry hooks) — `config['on_error']` callable | S | Optional; tested with a fake callback. |
| R2 | Circuit breaker (`config['breaker_threshold']`) for `execute_tasks` | S-M | After N consecutive failures, the executor stops and raises a typed error. Test with a deterministic failing task. |
| R3 | Resume-from-checkpoint for `execute_tasks` (state file under `artifacts_dir`) | M-L | `execute_tasks(tasks, resume=True)` skips already-successful tasks from the last interrupted run. Two integration tests. |
| TS1 | **`pytest-visus` plugin** with `mock_screen`, `fake_ocr`, `record_clicks` fixtures | M | Lives in this repo as `src/visus_pytest/`; users `pip install visus-desktop[test]` and get the fixtures. Documented in cookbook. |
| TS2 | Snapshot/visual regression for OCR regions | M | `assert_screen_matches('snapshots/login.png', region=(...))` API. Stored under `tests/snapshots/`. |
| TS3 | "Test mode": screen is loaded from PNGs on disk | S-M | `config['screen_source'] = 'disk:./fixtures'`; ships with TS1. |
| S1 | `wait_for_stable_screen(region=None, stable_for=0.5, timeout=15)` | S-M | Polls captures, hashes pixels, returns when unchanged for `stable_for`. Tested with synthetic PNG stream. |

**Definition of done for Phase 2:**
- Full suite + new tests green; coverage on `core/task_executor.py` ≥ 60%.
- `pytest-visus` extracted as an installable extra (`visus-desktop[test]`).
- Cookbook has a "Debugging a failed bot" recipe pulling together O1/O3/O5.

---

## Phase 3 — Engine + hybrid targeting (≈ 2 weeks)

The hardest technical phase. Lays the architecture the rest of the roadmap leans on.

| ID | Item | Effort | Acceptance |
|----|------|--------|------------|
| E5 | **Backends interface**: `ScreenSource`, `Matcher`, `InputController` ABCs in `visus.desktop.backends` | M | Existing internals refactored behind these; no public API change. Tests still green. |
| E1 | Own `cv2.matchTemplate` `Matcher` implementation, default for find_image/find_all | M | Replaces `pyautogui.locateOnScreen`. Bench shows ≥ 2× speed on a 1080p haystack. |
| E2 | ORB feature `Matcher` (opt-in via `confidence_strategy='features'`) | M-L | Useful for theme/DPI invariance; documented limitation (slower per call). |
| E3 | Region screenshot cache (TTL `config['screen_cache_ms']=80`) | S-M | Back-to-back find on the same region uses the cached PIL image. Cache invalidation on click/typed input. |
| E4 | Multi-monitor explicit API (`take_screenshot(monitor=2)`, `get_monitors()`) | S-M | Returns a list of `Monitor` dataclasses. `find_image(monitor=2, …)`. |
| T1 | **`hybrid_find(name, …)`** tries native → OCR → image in order | M | Single method; falls back transparently. Each layer is mockable. Documented as the recommended targeting primitive. |
| T2 | `{"type": "hybrid", "name": "..."}` task type | S | Builds on T1; new tests in `test_tasks.py`. |

**Definition of done for Phase 3:**
- Public `bot.find_image`/`click_image` route through the new `Matcher` by default.
- Engine swap is silent to existing users (all 537+ tests still pass).
- A new benchmark file `benchmarks/find_speed.py` shows before/after numbers in the CHANGELOG.
- `hybrid_find` documented in README's "Usage guide" with one example.

---

## Phase 4 — Cross-platform (Linux first) (≈ 1 week)

| ID | Item | Effort | Acceptance |
|----|------|--------|------------|
| X1 | Linux `WindowManager` backend (xdotool / wmctrl) | M | Same `focus_window`/`maximize_window`/… API works on Linux; CI matrix runs the tests under xvfb. |
| X4 | WSL guidance auto-detect; better DPI message on WSL | S | Documented + a runtime hint if WSL is detected without an X server. |
| X2 | Linux native backend (AT-SPI via `pyatspi`/`dogtail`) — opt-in behind `[native-linux]` extra | L | `connect_to_app` returns a wrapper compatible with `find_app_window`/`find_app_element`. Tested against a known GTK app in CI. |

**Definition of done for Phase 4:**
- All previously Windows-only window features work on Linux when system deps are installed.
- `NotSupportedOnThisOS` only fires for genuinely platform-locked things (native on macOS until X3 lands).

## Phase 4.5 — macOS (optional, on demand)
| ID | Item | Effort | Notes |
|----|------|--------|-------|
| X3 | macOS support (Quartz / Accessibility) | L | Only if real demand surfaces (counts of issues / users). |

---

## Phase 5 — DX / tooling (≈ 2–3 weeks)

This is what users see first. Higher marketing leverage.

| ID | Item | Effort | Acceptance |
|----|------|--------|------------|
| D2 | `visus` CLI (`new project`, `run <script>`, `record`, `report`) | M | `pipx install visus-desktop` exposes the binary; `visus --help` covers all subcommands; each subcommand has a smoke test. |
| D4 | Recipe gallery — at least 5 fully worked recipes under `docs/cookbook/` | S | Login form, table scraping, file download wait, captcha, Excel input. Cross-linked from README. |


**Definition of done for Phase 5:**
- A new user can `pipx install visus-desktop && visus new myproj && visus run` in < 5 minutes.
- README opens with the CLI flow.
- The recorder produces tasks that run unchanged.

---

## Phase 6 — Web + cloud + ecosystem (≈ 4+ weeks)

The brand-family completion phase.

| ID | Item | Effort | Acceptance |
|----|------|--------|------------|
| W1 | `visus-web` package (Playwright-first, Selenium adapter) with the same task-list/backtrack/cloud DX | L | Lives in its own repo; depends on `visus-cloud` for orchestration; mirrors `botcity-framework-web` in spirit. |
| W2 | Bezier mouse paths + Gaussian/Poisson timing helpers | S-M | Cross-published in `visus-web` and used by `move_random` on desktop. |
| W3 | Browser profile / cookies / session helpers | S-M | Aligns with the author's `a.py` pattern. |
| W4 | CAPTCHA helper task type with optional 2captcha/anti-captcha plugin | S-M | Off by default; pluggable. |
| C1 | Finish `visus-cloud` SDK (REST + Bearer + SSE + heartbeat) | L | Resume the paused work when the SaaS API stabilizes. |
| C3 | Credential vault (`bot.get_credential(...)`) wired into both desktop and web | S | Part of C1. |
| C4 | Cron / runtime registration | M | Part of C1. |
| P1 | Plugin system (custom task types + backends loaded via entry points) | M | `pip install visus-plugin-foo` registers via `[project.entry-points."visus.task_types"]`. |
| AD3 | Browser fingerprint randomization (only in `visus-web`) | M | Opt-in; behind `[stealth]` extra. |

## Cross-cutting (every phase)

| ID | Concern | Effort | Notes |
|----|---------|--------|-------|
| A1 | Split `__init__.py` / `task_executor.py` (B2/B3) | M | Do during Phase 3 when refactoring for backends anyway. |
| A2 | mypy strict gradual per module | M | One module per phase. |
| A3 | Richer stubs for the public API | S | Whenever a new method ships. |
| A4 | Coverage > 80% on the core modules | M | Continuous; checked in CI. |
| A5 | Optional async API (`async def click_async`) | L | Defer to Phase 6+ unless cloud SDK demands it sooner. |
| DOC5 | Published docs site (MkDocs Material) | M | Stand it up by the end of Phase 2; auto-deploy from `docs/`. |
| AD1, AD2 | Bezier paths + timing jitter | S-M | Land alongside W2 in Phase 6 (or earlier as a helper). |

---

## Practical integrations (slot opportunistically)

These are low-priority on their own but cheap wins when paired with a real
user request. They don't fit a single phase — pull from this pool when bandwidth
allows.

| ID | Item | Effort |
|----|------|--------|
| I1 | PDF reading helper | S-M |
| I2 | Excel/CSV helpers | S |
| I3 | Email (IMAP/SMTP) helpers | S-M |
| I4 | File-dialog handler (Windows "Open File") | S |
| I5 | OS file ops paired with `wait_for_file` | S |

---

## How to run the plan

1. **Pick a phase.** Don't multi-phase. Phase 1 is the natural starting point.
2. **Open a tracking issue / use the TaskCreate tool** with one task per line item.
3. **TDD each item** (skill: `superpowers:test-driven-development`).
4. **One commit per item** with a `<phase>: <id>: <summary>` prefix
   (e.g. `phase1: O1: screenshot-on-failure`).
5. **Update the catalog's "Done" section** as each item lands.
6. **Cut a release** at the end of each phase (`0.2.0`, `0.3.0`, …).

The order above is the **default**, not a contract. Always promote items that
real users (you, beta testers, the first paying customer) ask for — concrete
demand beats roadmap aesthetics.

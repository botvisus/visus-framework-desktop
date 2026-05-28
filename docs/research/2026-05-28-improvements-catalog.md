# Improvements catalog — visus-desktop

> **Date:** 2026-05-28
> **Status:** living document. Synthesizes everything surfaced during the BotCity
> audit, the bugs found by the comprehensive test suite, observations from the
> author's own RPA code (`a.py` / LGE-GERP automation), and the architectural
> notes accumulated through the rebrand+integration work.
>
> This is the **what** and **why**. The phased **how** lives in
> [`2026-05-28-implementation-plan.md`](2026-05-28-implementation-plan.md).

Each item is tagged with **value** (★ low · ★★ medium · ★★★ high) and **effort**
(**S** ≤ 1 day · **M** 2–5 days · **L** > 1 week), plus whether competitors
already have it (so we can frame as **parity** vs **differentiator**).

---

## 🐛 Bugs / technical debt still open
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| B1 | `cv2.gapi.wip.draw.Text` warm-up in `conftest.py` so `pytest --cov` works without manual workaround | ★★ | S | Surfaced by the validation-tests agent; current shim lives in two test files. |
| B2 | Split `src/visus/desktop/__init__.py` (~2500 lines) into focused modules (`finders.py`, `executor_api.py`, `sessions.py`) | ★★ | M | Original spec deferred this; safe to do now with the 537-test safety net. |
| B3 | Split `core/task_executor.py` (~1280 lines) into per-action handlers | ★★ | M | Same rationale as B2. |
| B4 | Audit and remove remaining dead branches surfaced by coverage gaps | ★ | S | Run `coverage` with branch coverage after B1. |

## 🚀 Engine / performance (Lote 3, deferred)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| E1 | Own `cv2.matchTemplate` matcher replacing `pyautogui.locateOnScreen` (pyscreeze) | ★★★ | M | The remaining "slow path" in find_image; mss capture already in place. |
| E2 | Feature-based matching (ORB) for theme/DPI invariance | ★★ | M-L | Differentiator vs BotCity; opt-in fallback when template fails. |
| E3 | Per-region screenshot cache (don't re-capture identical regions within N ms) | ★★ | S-M | Cheap win for back-to-back finds. |
| E4 | Multi-monitor explicit API (`take_screenshot(monitor=N)`, absolute virtual-screen coords) | ★★ | S-M | `mss` supports it; expose. |
| E5 | Pluggable backends architecture: `ScreenSource` / `Matcher` / `InputController` interfaces | ★★★ | L | The "pro engine" architecture — enables E1/E2/E4 and the hybrid targeting (T1). |

## 🎯 Hybrid targeting (the big differentiator)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| T1 | `hybrid_find(name)` — tries native (pywinauto) → OCR → image, in order, transparently | ★★★ | M | Genuine superset of BotCity (which keeps them separate / OCR in a paid plugin). |
| T2 | Hybrid task type in `execute_tasks` (`{"type": "hybrid", "name": "Login"}`) | ★★ | S | Builds on T1 once it exists. |

## 🪟 Cross-platform (Linux/macOS gaps)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| X1 | Linux `WindowManager` backend (xdotool / wmctrl) — focus/maximize/minimize/close | ★★ | M | Removes a `NotSupportedOnThisOS` from the Linux path. |
| X2 | Linux native backend (AT-SPI via `pyatspi`/`dogtail`) | ★★ | L | Heavy but real parity; works mainly for GTK/Qt accessible apps. |
| X3 | macOS support: virtual mouse (Quartz), native (Accessibility API), window mgmt | ★ | L | Lower priority unless we see real macOS demand. |
| X4 | WSL guidance + auto-config (X server, paths) | ★ | S | Document, optionally auto-detect. |

## 🛠️ DX / tooling (high marketing leverage)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| D1 | **Recorder / codegen** ("Visus Studio") — click in UI → generated tasks/code | ★★★ | L | BotCity's killer feature; huge onboarding lever. |
| D2 | `visus` CLI (`new project`, `run`, `record`, `deploy`) | ★★ | M | Foundation for D1 and the cloud SDK. |
| D3 | VS Code extension (snippets, run task, screenshot-region picker) | ★★ | L | After D2. |
| D4 | Example gallery + recipe templates (login form, table scrape, file download…) | ★★ | S | Cheap; great for "first 10 min" experience. |

## 📊 Observability / debugging (a real pain in the author's own `a.py`)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| O1 | **Screenshot-on-failure** automatic: failed tasks save a PNG + context | ★★★ | S | The single highest-ROI quick win. |
| O2 | Structured JSON logging with `run_id` / `task_id` / `duration_ms` | ★★ | S | Plays well with cloud orchestrator. |
| O3 | Session record/replay (capture screenshots+actions; replay as test) | ★★ | M | Foundation for snapshot tests (TS1). |
| O4 | Per-task metrics (`find_time`, attempts, success rate) | ★★ | S-M | Exposed via a results report or to Visus Cloud. |
| O5 | HTML run report (timeline + screenshots + errors) | ★★ | M | Great demo asset. |
| O6 | Pluggable error sinks (Sentry, Datadog, OpenTelemetry hooks) | ★ | S | Optional callbacks. |

## 🔁 Reliability / resilience
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| R1 | Generic `@retry(attempts, backoff)` decorator usable outside backtrack sessions | ★★ | S | Backtrack is task-list scoped; standalone retry has its own niche. |
| R2 | Circuit breaker (pause after N consecutive failures) | ★ | S-M | Optional safety net. |
| R3 | Resume-from-checkpoint for `execute_tasks` (persisted progress) | ★★ | M-L | Long-running RPA killer feature. |
| R4 | Health checks (`visus doctor`): Tesseract OK? display OK? pywinauto OK? | ★★ | S | First-time-user pain reducer. |
| R5 | Graceful shutdown (SIGINT releases held buttons, frees overlay threads) | ★ | S | Quality of life. |

## 🧪 Testing (own dogfooding + user DX)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| TS1 | `pytest-visus` plugin: fixtures `mock_screen`, `fake_ocr`, `record_clicks` | ★★★ | M | Lets *users* test their bots — huge DX. |
| TS2 | Snapshot / visual-regression for OCR/image regions | ★★ | M | Detects UI drift before it breaks production. |
| TS3 | "Test mode": bot reads PNGs from disk instead of capturing real screen | ★★ | S-M | Pairs with O3 (record/replay). |
| TS4 | Permanent fix for the `cv2` `--cov` issue in `conftest.py` (B1) | ★★ | S | Already listed under bugs; cross-referenced here. |

## 🌐 Web automation (`visus-web`, planned sibling)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| W1 | `visus-web` package wrapping Selenium / Playwright with the same task-list + backtrack + cloud DX | ★★★ | L | Mirrors `botcity-framework-web`; part of the brand plan. |
| W2 | Humanized mouse paths (bezier trajectories) — extends `move_random` | ★ | S-M | Mostly for anti-detection in web flows. |
| W3 | Persistent browser profile / cookies / sessions helpers | ★★ | S-M | The author already does this manually in `a.py`. |
| W4 | CAPTCHA helper (OCR-on-image) as a task type, with optional 2captcha/anti-captcha integration | ★★ | S-M | The author already solves captchas via OCR in `a.py`. |

## ☁️ Visus Cloud (scaffold already started, then paused)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| C1 | Finish `visus-cloud` SDK (REST + Bearer + SSE + heartbeat) | ★★★ | L | Paused at user request; resume when SaaS API contract stabilizes. |
| C2 | Web dashboard (out of scope for Python — author's SaaS owns it) | n/a | n/a | TypeScript / IgniterJS side. |
| C3 | Credential vault (`bot.get_credential(...)`) — already designed in the client | ★★ | S | Part of C1. |
| C4 | Cron scheduling / runtime registration | ★★ | M | Part of C1; mirrors Maestro. |

## 🔌 Plugins / ecosystem
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| P1 | Plugin system: users register custom task types / backends | ★★ | M | Enables a community. |
| P2 | Template marketplace (login forms, SAP, Oracle Forms…) | ★ | L | Needs community; later. |

## 📚 Documentation / onboarding
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| DOC1 | **Cookbook / recipes** ("Oracle Forms", "download wait", "captcha", "Excel input") | ★★★ | S | Cheap; reduces support load. |
| DOC2 | Detailed migration guide from `bot-vision-suite` | ★★ | S | README note exists; expand. |
| DOC3 | Troubleshooting guide ("OCR doesn't find X", "DPI wrong", "pywinauto can't connect") | ★★ | S | High-impact, low-cost. |
| DOC4 | Performance tuning guide (region, confidence, scales, cache) | ★ | S | Niche but useful. |
| DOC5 | Published docs site (MkDocs Material or Sphinx) | ★★ | M | Big credibility boost. |

## 🏗️ Architecture / code health
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| A1 | Split `__init__.py` and `task_executor.py` (see B2/B3) | ★★ | M | Cross-referenced. |
| A2 | mypy strict gradual rollout (per-module) | ★★ | M | Currently permissive. |
| A3 | Richer `py.typed` / stubs for public API | ★ | S | IDE autocomplete. |
| A4 | Push core coverage > 80% (currently ~40% total, ~25% in legacy core) | ★★ | M | Continues the 537-test push. |
| A5 | Optional async API (`async def click_async`) — useful for orchestrator-driven bots | ★ | L | Defer; lower demand. |

## 🔐 Anti-detection / "human-like" (web context)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| AD1 | Bezier mouse paths (W2 cross-reference) | ★ | S-M | |
| AD2 | Gaussian/Poisson timing jitter helpers | ★ | S | |
| AD3 | Browser fingerprint randomization (UA, fonts, canvas) | ★ | M | Only relevant in `visus-web`. |

## 📦 Practical integrations (real RPA needs)
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| I1 | PDF reading helper (PyMuPDF/pdfminer) — task type or helper | ★★ | S-M | Common in invoice/document RPA. |
| I2 | Excel/CSV helpers (openpyxl wrapper) | ★★ | S | Most desktop RPA touches spreadsheets. |
| I3 | Email (IMAP/SMTP) — read inbox, download attachments | ★★ | S-M | Very common trigger. |
| I4 | File-dialog handler (Windows "Open File" dialog auto-fill) | ★★ | S | Tedious without it. |
| I5 | OS file ops (download confirm, move, rename) paired with `wait_for_file` | ★ | S | Quality-of-life. |

## ⏰ Advanced synchronization
| # | Item | Value | Effort | Notes |
|---|---|---|---|---|
| S1 | `wait_for_stable_screen()` — wait until the screen stops changing | ★★ | S-M | Classic SPA / Oracle Forms pain. |
| S2 | Event-driven "when X appears, do Y" callback in background | ★★ | M | Pairs well with async API (A5). |
| S3 | Element-diff / self-healing ("the button moved 10px") | ★★ | L | High-end RPA platforms have this. |

---

## How to use this catalog

* Pull from this catalog when planning a new release; **do not** treat it as a queue
  (priorities shift as the user/customer base grows).
* The companion document
  [`2026-05-28-implementation-plan.md`](2026-05-28-implementation-plan.md) maps these
  items into a phased plan with dependencies and acceptance criteria.
* When something is shipped, move it to a "Done" section at the bottom of this file
  (or remove it and reference the changelog).
* When a new pain point comes up (from issues, user reports, web research),
  append it here first — implementation follows the catalog, not the other way around.

## Done (already shipped in this codebase)
For reference, what's already in the library after the recent integration work:

* ✅ src/ layout + namespace package + py.typed
* ✅ Rebrand: `VisusBot` / `clean_text` with backward-compat aliases
* ✅ mss-backed screen capture with pyautogui fallback
* ✅ Native (accessibility) automation via pywinauto (Windows-only, gated with `NotSupportedOnThisOS`)
* ✅ `find_all` / `find_multiple` (full param style)
* ✅ Image map (`register_image` / `get_image` + label resolution in `find_image`/`click_image`)
* ✅ Process management (`launch`/`find_process`/`is_process_running`/`kill_process`)
* ✅ Window management (Windows): `focus_window`/`maximize_window`/`minimize_window`/`close_window`
* ✅ File waits: `wait_for_file` / `wait_for_file_stable`
* ✅ Clipboard helpers (`copy`/`paste`/`get_clipboard`)
* ✅ Screen helpers (`take_screenshot`/`save_screenshot`/`get_display_size`)
* ✅ `browse(url)`
* ✅ Mouse extras: `scroll`/`drag`/`triple_click`/`move_random`/`mouse_down`/`mouse_up`
* ✅ Named keyboard shortcuts (40, delegate to `keyboard_command`)
* ✅ Coordinate helpers (`get_element_coords`/`get_element_coords_centered`)
* ✅ `click_relative(image, x_offset, y_offset, …)` (image + coordinate offset)
* ✅ Full param-style integration on all new methods (backtrack, wait_*, show_overlay, sendtext, delay, mouse_button)
* ✅ Cross-platform core; Windows-only features raise `NotSupportedOnThisOS`
* ✅ CI on Linux with `xvfb` + system deps
* ✅ Bug fixes: virtual-mouse DPI, `type_text` task dispatch, overlay fallback `UnboundLocalError`, duplicate `__all__`, `\\P` SyntaxWarning
* ✅ 537 passing tests, ruff clean

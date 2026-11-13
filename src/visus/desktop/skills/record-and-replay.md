---
name: record-and-replay
description: Record a visus-desktop run as a step-by-step HTML report — every action (clicks, typing, keys, native_* controls, open_app, execute_tasks) with its duration, OK/FAILED + reason, a screenshot and its logs — in a portable zip. Live via the MCP (start_recording / stop_recording) or in a delivered script via rpa().
when_to_use: Activate when the user wants a paper trail of a run — for QA, customer hand-off, or post-mortem of a flaky bot — or when the user explicitly says "record this", "save the run", "give me a report", or asks for a script that produces a report.
---

# Record and replay a run

Two ways to get the same report — pick by who runs the automation:

| Who drives | How | Output |
|---|---|---|
| **You, live, through the MCP** | `start_recording` → your tool calls → `stop_recording(report_path=…)` | the zip + `report.html` you name |
| **A script you hand off** | `with rpa("name", open_report=True) as bot:` | `./visus-runs/<name>-<timestamp>/run.zip` + `report.html` |

## 1. Live, through the MCP

1. `start_recording(path="C:/runs/pedido.zip", name="pedido")` — opens the recording. From here **every action tool you call is a step of the report**: `click_text`, `click_image`, `click_at`, `click_relative_image`, `type_text`, `keyboard_command`, `open_app`, `use_app`, `extract_text_from_region` (the text read shows on the step), `scroll`, `drag`, `triple_click`, `native_click` / `native_set_text` / `native_get_text` / `native_wait` (the control is also highlighted on screen in the overlay style), and each task of `execute_tasks`. Query tools (`find_text`, `find_image`, `native_get_state`, screenshots…) are not steps.
2. Work as usual. The tools keep their normal return values: a failed step is **recorded with its reason and a failure screenshot**, it does not raise — you decide what to do next. Type passwords with `type_text(..., secret=true)` / `native_set_text(..., secret=true)`: they show as `••••••` in the report.
3. `stop_recording(report_path="C:/runs/pedido.html")` — writes the zip and the HTML report, and returns `{saved, zip, report, steps, failures, timeline}`. Read `failures` / `timeline` to tell the person how it went; hand them the report.

```text
start_recording(path="C:/runs/pedido.zip", name="pedido")
open_app(target="calc", wait_window="Calculadora")
native_click(window="Calculadora", auto_id="num8Button")
type_text(text="*7=", window="Calculadora")
native_get_text(window="Calculadora", auto_id="CalculatorResults")
stop_recording(report_path="C:/runs/pedido.html")
# -> {"saved": true, "steps": 4, "failures": 0, "timeline": [["open_app", true], ...], ...}
```

`configure(...)` in the middle keeps recording into the same run. Only one recording at a time (`start_recording` again raises; `stop_recording` with none open returns `{"saved": false}`).

## 2. In a script you deliver — `rpa()`

The same contract as `visus.web`'s `rpa()`: the script holds only the automation.

```python
from visus.desktop import rpa
from visus.desktop.core.native_rpa import native_click

def run() -> None:
    with rpa("pedido", app="calc", window="Calculadora", open_report=True) as bot:
        native_click(window="Calculadora", auto_id="num8Button")
        bot.type_text("*7=", window="Calculadora")

if __name__ == "__main__":
    run()
```

* Every `bot.*` action and every `native_*` action inside the `with` is a step. Anything else (a `smart_click`, your own check) → `with bot.step("label"):`.
* **A failed action stops the run** there: the step is FAILED with the reason and a screenshot, the console summary says why, and the process exits with code `1` (`reraise=True` raises `ActionFailedError` instead; `stop_on_failure=False` keeps the old `True`/`False` returns). An `assert` or unexpected error is added as the last FAILED step. For an "is it on screen?" check use `find_text` / `find_image` / `native_get_state`, which never stop the run.
* The report is written **even when a step fails**. `config={...}` takes the usual `VisusBot` settings — `overlay_color`, `show_overlay` and friends also style the highlight of native clicks.
* Under the RunPilot runner (`RUNPILOT_RUN_TOKEN`) every step streams live to the orchestrator instead and no local files are written.
* From the CLI: `visus new ./pedido` scaffolds this script; `visus run pedido/tasks.py` runs it and propagates the exit code.

## Inspecting a recording programmatically

`replay_session(zip_path="...zip")` returns the steps as JSON-friendly dicts — use it when the user wants the run summarized in chat ("which steps failed"):

```text
events = replay_session(zip_path="C:/runs/pedido.zip")
for e in events:
    if not e["success"]:
        print(e["type"], e["target"], e["error"])
```

Each event carries `type`, `target`, `success`, `duration_ms`, `attempts`, `error`, `output` (text a read step returned), `location`, `screenshot` / `failure_screenshot` and `logs`. `render_report(zip_path, html_path, title=None)` (or `visus report run.zip --html out.html`) renders the HTML again.

## What the report shows

One self-contained HTML file (screenshots embedded as base64, prints as a PDF), in the same "Run report" look as the RunPilot orchestrator: the run name as the headline, a KPI band (steps, OK, failed, retries, success %, duration), an **Errors** section with each failure's reason and screenshot, then the step timeline — "Click text · Login", "Type · Ada", "Click · num8Button in 'Calculadora'" — each with its duration, the screenshot right after it (the target boxed) and its collapsible logs.

## When NOT to record

* Short ad-hoc clicks that don't need a paper trail.
* Many unrelated runs — keep one recording per logical run; runs are not concatenated into one zip.

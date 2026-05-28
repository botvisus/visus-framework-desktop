---
name: record-and-replay
description: Capture every task event from a visus-desktop run into a session zip, then render it as a styled HTML report (cream / coral / dark-navy following DESIGN.md). The zip is portable and bundles failure screenshots inline.
when_to_use: Activate when the user wants a paper trail of a run — for QA, customer hand-off, or post-mortem of a flaky bot — or when the user explicitly says "record this", "save the run", or "give me a report".
---

# Record and replay a run

## Quick flow

1. `start_recording(path="C:\\runs\\<run_name>.zip")` — opens the recording context. The MCP server keeps it active until `stop_recording` is called.
2. Run the automation as normal. Every task event emitted by `execute_tasks` is captured plus any `failure_screenshot` referenced by the event.
3. `stop_recording()` — flushes the zip. From here the file is portable.
4. **Optional but recommended**: `render_report(zip_path="...zip", html_path="...html")` produces a single-file HTML report styled with the Anthropic Claude design system (cream canvas, Copernicus serif, coral CTAs, dark-navy code surfaces). Open the HTML to see a timeline + KPIs + failure screenshots embedded as base64.

## Compact MCP transcript

```text
start_recording(path="C:/runs/login-and-export.zip")
execute_tasks(tasks=[
    {"text": "Login", "region": [200, 100, 600, 400]},
    {"type": "type_text", "text": "alice"},
    {"type": "keyboard_command", "command": "Tab"},
    {"type": "type_text", "text": "<password>"},
    {"text": "Sign in", "region": [200, 100, 600, 500]},
    {"text": "Export", "region": [800, 100, 400, 80]},
])
stop_recording()
render_report(
    zip_path="C:/runs/login-and-export.zip",
    html_path="C:/runs/login-and-export.html",
)
```

## Inspecting a recording programmatically

`replay_session(zip_path="...zip")` returns the list of events as JSON-friendly dicts. Use this when the user wants the run summarized in chat (e.g. "which steps failed"):

```text
events = replay_session(zip_path="C:/runs/run.zip")
for e in events:
    if not e["success"]:
        print(e["task_name"], e["error"])
```

## When NOT to record

* For short ad-hoc clicks that don't need a paper trail. Recording adds zero behaviour but the zip is a small file you'd never use.
* Across many short runs — keep one recording per logical session. Concatenating runs into one zip is not supported.

## Pairing with screenshot-on-failure

If `screenshot_on_failure` is enabled (it's the default), failed tasks already produce PNGs under `artifacts_dir`. Recording **adds these PNGs into the zip** so the recipient does not need access to the original artifacts directory. The HTML report embeds them as base64 data URIs — the report is one file with no external dependencies.

## Design-system note

The HTML report follows `D:\bot_vision\DESIGN.md` (Anthropic Claude marketing-surface tokens). Do not regenerate the report with custom styling — the renderer is opinionated for a reason.

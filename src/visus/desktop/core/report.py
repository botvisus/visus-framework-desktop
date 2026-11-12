"""Single-file HTML run report (Phase 2, O5).

Reads the ``events.jsonl`` from a session zip (see
``visus.desktop.core.session``) and renders a self-contained HTML file
suitable for emailing, attaching to a CI artefact, or pinning in a
bug ticket. Every PNG referenced by ``screenshot`` or ``failure_screenshot``
is embedded as a base64 data URI so the report has no external dependencies.

The look is the orchestrator's (RunPilot) own run report -- the same one
visus.web renders -- so a run reads the same on the desktop and in the web
console: a white sheet on a light-grey floor, the GMES crimson ``#E0205C`` for
the eyebrow, a KPI band with mono numbers, the task timeline as bordered cards
with green OK / red FAILED badges, errors in red tints and the logs in a light
box. Geist when installed, the system sans otherwise. It is always a light
document: a report is printed and shared as a PDF.
"""

from __future__ import annotations

import base64
import json
import os
import zipfile
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Iterable

_EVENTS_FILE = "events.jsonl"
_MANIFEST_FILE = "manifest.json"
_SCREENSHOTS_DIR = "screenshots/"
_DEFAULT_TITLE = "Desktop automation"

_CSS = """
:root {
  --floor: #f5f5f5;
  --paper: #ffffff;
  --soft: #fafafa;
  --line: #e5e5e5;
  --line-soft: #f5f5f5;
  --ink: #171717;
  --text: #262626;
  --body: #404040;
  --sub: #525252;
  --muted: #737373;
  --faint: #a3a3a3;
  --crimson: #E0205C;
  --ok: #047857;
  --ok-strong: #059669;
  --ok-bg: #ecfdf5;
  --ok-line: #a7f3d0;
  --err: #b91c1c;
  --err-strong: #dc2626;
  --err-text: #991b1b;
  --err-soft: #ef4444;
  --err-bg: #fef2f2;
  --err-line: #fecaca;
  --warn: #b45309;
  --warn-bg: #fffbeb;
  --warn-line: #fde68a;
  --sans: Geist, "Segoe UI Variable Text", "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
  --mono: "Geist Mono", "Cascadia Mono", Consolas, ui-monospace, SFMono-Regular, Menlo, monospace;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--floor);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.5;
  padding: 24px 16px;
  -webkit-font-smoothing: antialiased;
}
.sheet {
  max-width: 896px;
  margin: 0 auto;
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 1px 2px rgb(0 0 0 / .05);
  print-color-adjust: exact;
  -webkit-print-color-adjust: exact;
}
header.report { border-bottom: 1px solid var(--line); padding-bottom: 20px; }
.head { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 12px; }
.head > div { min-width: 0; }
.eyebrow {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--crimson);
}
h1 {
  margin: 4px 0 0;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -.01em;
  color: var(--ink);
  overflow-wrap: anywhere;
}
.run-id { margin: 4px 0 0; font-family: var(--mono); font-size: 11px; color: var(--muted); }
.pill {
  flex-shrink: 0;
  border: 1px solid;
  border-radius: 9999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
}
.tone-ok { border-color: var(--ok-line); background: var(--ok-bg); color: var(--ok); }
.tone-failed { border-color: var(--err-line); background: var(--err-bg); color: var(--err); }
.tone-neutral { border-color: var(--line); background: var(--line-soft); color: var(--sub); }
.meta { margin-top: 20px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px 24px; }
.meta > div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
}
.meta .v {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
section.kpis { margin-top: 24px; display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.kpi-card { border: 1px solid var(--line); background: var(--soft); border-radius: 8px; padding: 12px 16px; }
.kpi-card .value {
  font-family: var(--mono);
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
.kpi-card .label { margin-top: 6px; }
.kpi-card.ok .value { color: var(--ok-strong); }
.kpi-card.failed .value { color: var(--err-strong); }
.kpi-card.quiet .value { color: var(--muted); }
section.block { margin-top: 32px; }
.block-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
h2 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--body);
}
h2.errors { color: var(--err); }
.error-card {
  border: 1px solid var(--err-line);
  background: var(--err-bg);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}
.error-card p.message {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.6;
  color: var(--err-text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.error-card .when { margin: 8px 0 0; font-family: var(--mono); font-size: 10px; color: var(--err-soft); }
.run-header { display: flex; align-items: baseline; gap: 8px; margin: 20px 0 8px; flex-wrap: wrap; }
.run-header:first-child { margin-top: 0; }
.run-header h3 { margin: 0; font-family: var(--mono); font-size: 12px; font-weight: 600; color: var(--body); }
.run-header .run-sub { font-size: 11px; color: var(--muted); }
.steps { display: flex; flex-direction: column; gap: 12px; }
article.task { border: 1px solid var(--line); background: var(--paper); border-radius: 8px; padding: 16px; }
.task .row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.task .index { font-family: var(--mono); font-size: 11px; font-weight: 500; color: var(--faint); }
.task .name { font-size: 13px; font-weight: 500; color: var(--ink); overflow-wrap: anywhere; }
.badge-success, .badge-failure, .badge-backtrack {
  border: 1px solid;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}
.badge-success { border-color: var(--ok-line); background: var(--ok-bg); color: var(--ok); }
.badge-failure { border-color: var(--err-line); background: var(--err-bg); color: var(--err); }
.badge-backtrack { border-color: var(--warn-line); background: var(--warn-bg); color: var(--warn); }
.task .duration { margin-left: auto; font-family: var(--mono); font-size: 11px; color: var(--muted); }
.task .action { margin: 4px 0 0; font-family: var(--mono); font-size: 11px; color: var(--muted); overflow-wrap: anywhere; }
.task .action b { font-weight: 400; color: var(--body); }
.task .step-error {
  display: inline-block;
  margin: 8px 0 0;
  border: 1px solid var(--err-line);
  background: var(--err-bg);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 11px;
  line-height: 1.6;
  color: var(--err);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
dl.kv { margin: 8px 0 0; display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; }
dl.kv dt { font-family: var(--mono); font-size: 10.5px; color: var(--muted); }
dl.kv dd { margin: 0; min-width: 0; font-family: var(--mono); font-size: 10.5px; color: var(--body); overflow-wrap: anywhere; }
details.logs { margin-top: 12px; border: 1px solid var(--line); background: var(--soft); border-radius: 8px; overflow: hidden; }
details.logs > summary {
  cursor: pointer;
  padding: 6px 12px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--sub);
}
details.logs > summary::marker { color: var(--crimson); }
.log-output { border-top: 1px solid var(--line); max-height: 360px; overflow-y: auto; }
.log-line { display: flex; gap: 12px; padding: 4px 12px; border-bottom: 1px solid var(--line-soft); }
.log-line:last-child { border-bottom: 0; }
.log-line .lvl {
  flex-shrink: 0;
  min-width: 56px;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--sub);
}
.log-line .msg { min-width: 0; white-space: pre-wrap; overflow-wrap: anywhere; font-family: var(--mono); font-size: 10.5px; color: var(--body); }
.lvl-DEBUG .lvl { color: var(--faint); }
.lvl-WARNING .lvl { color: var(--warn); }
.lvl-ERROR .lvl, .lvl-CRITICAL .lvl { color: var(--err); }
pre.json {
  margin: 0;
  padding: 8px 12px;
  border-top: 1px solid var(--line);
  max-height: 360px;
  overflow: auto;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--body);
  white-space: pre-wrap;
}
figure.shot { margin: 12px 0 0; max-width: 672px; }
figure.shot img { display: block; width: 100%; height: auto; border: 1px solid var(--line); border-radius: 6px; }
figure.shot.failure img { border-color: var(--err-line); }
figure.shot figcaption { margin-top: 4px; font-family: var(--mono); font-size: 10px; color: var(--faint); }
.empty {
  border: 1px dashed var(--line);
  border-radius: 8px;
  padding: 32px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--muted);
}
footer.report { margin-top: 32px; border-top: 1px solid var(--line); padding-top: 16px; font-size: 10px; color: var(--faint); }
@media (max-width: 860px) {
  section.kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  body { padding: 0; }
  .sheet { border-radius: 0; border-left: 0; border-right: 0; padding: 20px 16px; }
  .meta, section.kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media print {
  html, body { background: #fff !important; padding: 0 !important; }
  .sheet { max-width: none; margin: 0; padding: 0; border: 0; box-shadow: none; }
  article.task, .error-card, figure.shot { break-inside: avoid; }
  @page { margin: 12mm; }
}
""".strip()


def write_report(
    zip_path: str | os.PathLike[str],
    html_path: str | os.PathLike[str],
    title: str | None = None,
) -> str:
    """Render a session zip into a single-file HTML report.

    ``title`` is the report's headline; by default the run name recorded in
    the zip (``rpa("name")`` / ``Session.start_recording(..., name=)``), else
    "Desktop automation". Returns the absolute path of the written file.
    """
    events, screenshots = _read_session(Path(zip_path))
    headline = title or _read_manifest(Path(zip_path)).get("name") or _DEFAULT_TITLE
    html = _render_html(events, screenshots, title=str(headline))
    out = Path(html_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return str(out.resolve())


def _read_manifest(zip_path: Path) -> dict[str, Any]:
    """The zip's ``manifest.json`` (``{}`` when absent or unreadable)."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            if _MANIFEST_FILE not in zf.namelist():
                return {}
            data = json.loads(zf.read(_MANIFEST_FILE).decode("utf-8"))
    except (OSError, ValueError, zipfile.BadZipFile):
        return {}
    return data if isinstance(data, dict) else {}


def _read_session(zip_path: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    """Return ``(events, {basename: png_bytes})`` from a session zip."""
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    events: list[dict[str, Any]] = []
    screenshots: dict[str, bytes] = {}
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if _EVENTS_FILE in names:
            raw = zf.read(_EVENTS_FILE).decode("utf-8")
            for line in raw.splitlines():
                if line.strip():
                    events.append(json.loads(line))
        for name in names:
            if name.startswith(_SCREENSHOTS_DIR) and name.lower().endswith(".png"):
                screenshots[os.path.basename(name)] = zf.read(name)
    return events, screenshots


def _kpis(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Compute the headline KPIs displayed in the report's KPI strip."""
    events = list(events)
    total = len(events)
    if total == 0:
        return {
            "total": 0,
            "success_rate_pct": 0,
            "total_duration_ms": 0,
            "failed": 0,
            "attempts": 0,
            "retries": 0,
        }
    succeeded = sum(1 for e in events if e.get("success"))
    total_duration = sum(int(e.get("duration_ms") or 0) for e in events)
    attempts = [int(e.get("attempts") or 0) for e in events]
    return {
        "total": total,
        "success_rate_pct": round(succeeded / total * 100),
        "total_duration_ms": total_duration,
        "failed": total - succeeded,
        "attempts": sum(attempts),
        "retries": sum(max(a - 1, 0) for a in attempts),
    }


def _group_runs(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group events into runs (by ``run_id``), preserving first-seen order."""
    runs: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for e in events:
        rid = str(e.get("run_id") or "n/a")
        run = index.get(rid)
        if run is None:
            run = {"run_id": rid, "events": []}
            index[rid] = run
            runs.append(run)
        run["events"].append(e)
    for run in runs:
        evs = run["events"]
        run["ts"] = evs[0].get("timestamp", "")
        run["ok"] = sum(1 for e in evs if e.get("success"))
        run["total"] = len(evs)
    return runs


# --- formatting (the orchestrator's: 391ms, 2.4s, 1m 3s; en-US instants) ----------


def _duration(ms: float | None) -> str:
    if ms is None or ms < 0:
        return "—"
    if ms < 1000:
        return f"{round(ms)}ms"
    seconds = ms / 1000
    if seconds < 60:
        text = f"{seconds:.1f}"
        return (text[:-2] if text.endswith(".0") else text) + "s"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m {round(seconds % 60)}s"
    return f"{minutes // 60}h {minutes % 60}m"


def _moment(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value)).astimezone()
    except (TypeError, ValueError):
        return None


def _instant(value: Any) -> str:
    """``10/30/2026, 9:06:53 AM`` in the reader's local time (or the raw value)."""
    if not value:
        return "—"
    moment = _moment(value)
    if moment is None:
        return str(value)
    hour = moment.hour % 12 or 12
    half = "AM" if moment.hour < 12 else "PM"
    return (
        f"{moment.month}/{moment.day}/{moment.year}, "
        f"{hour}:{moment.minute:02d}:{moment.second:02d} {half}"
    )


def _short_time(iso_ts: str) -> str:
    """HH:MM:SS of an ISO timestamp in the reader's local time, like the dates
    above it (fallback: the raw string)."""
    moment = _moment(iso_ts)
    return moment.strftime("%H:%M:%S") if moment else iso_ts


def _wall_ms(events: list[dict[str, Any]]) -> float | None:
    """First task's start to the last one's end. A task is stamped when it ends,
    so the first one's own duration is added back."""
    moments = [_moment(e.get("timestamp")) for e in events]
    stamped = [m for m in moments if m is not None]
    if not stamped:
        return None
    first = int(events[0].get("duration_ms") or 0)
    return max(0.0, (max(stamped) - min(stamped)).total_seconds() * 1000 + first)


def _meta(label: str, value: str) -> str:
    return (
        f'<div><span class="label">{escape(label)}</span>'
        f'<span class="v">{escape(value)}</span></div>'
    )


def _kpi(label: str, value: Any, tone: str = "") -> str:
    cls = f"kpi-card {tone}".strip()
    return (
        f'<div class="{cls}"><div class="value">{escape(str(value))}</div>'
        f'<div class="label">{escape(label)}</div></div>'
    )


def _render_html(
    events: list[dict[str, Any]],
    screenshots: dict[str, bytes],
    title: str = _DEFAULT_TITLE,
) -> str:
    kpis = _kpis(events)
    runs = _group_runs(events)
    ordered = [e for run in runs for e in run["events"]]
    numbered = list(enumerate(ordered, start=1))

    if not events:
        status, tone = "No tasks", "tone-neutral"
    elif kpis["failed"]:
        status, tone = "Failed", "tone-failed"
    else:
        status, tone = "Completed", "tone-ok"
    run_ids = ", ".join(run["run_id"] for run in runs) or "—"
    last_task = next(
        (str(e["task_name"]) for e in reversed(ordered) if e.get("task_name")), "—"
    )
    meta = "".join(
        [
            _meta("Run", run_ids),
            _meta("Started", _instant(ordered[0].get("timestamp")) if ordered else "—"),
            _meta(
                "Finished", _instant(ordered[-1].get("timestamp")) if ordered else "—"
            ),
            _meta("Duration", _duration(_wall_ms(ordered)) if ordered else "—"),
            _meta("Attempts", str(kpis["attempts"])),
            _meta("Last task", last_task),
        ]
    )
    kpi_band = "".join(
        [
            _kpi("Tasks", kpis["total"]),
            _kpi("OK", kpis["total"] - kpis["failed"], "ok"),
            _kpi("Failed", kpis["failed"], "failed"),
            _kpi("Retries", kpis["retries"], "quiet"),
            _kpi("Success", f"{kpis['success_rate_pct']}%"),
            _kpi("Duration", _duration(kpis["total_duration_ms"])),
        ]
    )

    failures = [(n, e) for n, e in numbered if not e.get("success")]
    errors_block = ""
    if failures:
        cards = "".join(_render_error(e, screenshots, n) for n, e in failures)
        errors_block = (
            f'<section class="block"><div class="block-head">'
            f'<h2 class="errors">Errors ({len(failures)})</h2></div>{cards}</section>'
        )

    if runs:
        sections = []
        number = 0
        for run in runs:
            failed = run["total"] - run["ok"]
            summary = f"{run['ok']}/{run['total']} ok" + (
                f" · {failed} failed" if failed else ""
            )
            header = ""
            if len(runs) > 1:
                header = (
                    f'<div class="run-header"><h3>Run {escape(run["run_id"])}</h3>'
                    f'<span class="run-sub">{escape(_instant(run["ts"]))} · '
                    f"{summary}</span></div>"
                )
            cards = []
            for event in run["events"]:
                number += 1
                cards.append(_render_task(event, screenshots, number))
            sections.append(header + f'<div class="steps">{"".join(cards)}</div>')
        timeline = "\n".join(sections)
    else:
        timeline = '<p class="empty">No tasks recorded.</p>'

    generated = _instant(datetime.now().astimezone().isoformat())
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)} — Visus Desktop run report</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="sheet">
    <header class="report">
      <div class="head">
        <div>
          <p class="eyebrow">Visus Desktop — Run report</p>
          <h1>{escape(title)}</h1>
          <p class="run-id">{escape(run_ids)}</p>
        </div>
        <span class="pill {tone}">{status}</span>
      </div>
      <div class="meta">{meta}</div>
    </header>

    <section class="kpis" aria-label="Run summary">{kpi_band}</section>

    {errors_block}

    <section class="block">
      <div class="block-head"><h2>Task timeline</h2></div>
      {timeline}
    </section>

    <footer class="report">
      Generated by Visus Desktop on {escape(generated)} · Run {escape(run_ids)} ·
      every task in order, with its duration, attempts and screenshots.
    </footer>
  </div>
</body>
</html>
"""


def _render_error(
    event: dict[str, Any], screenshots: dict[str, bytes], number: int
) -> str:
    message = str(event.get("error") or "failed")
    shot = ""
    if event.get("failure_screenshot"):
        shot = _render_screenshot(
            event["failure_screenshot"], screenshots, kind="failure"
        )
    when = _short_time(str(event.get("timestamp") or ""))
    name = _task_title(event)
    return (
        f'<div class="error-card"><p class="message">{escape(message)}</p>{shot}'
        f'<p class="when">{escape(when)} · task #{number} · {escape(name)}</p></div>'
    )


# What each recorded action type reads as in a step title ("Click text · Login").
_TYPE_TITLES = {
    "text": "Click text",
    "image": "Click image",
    "click": "Click at",
    "relative_image": "Click image near",
    "type_text": "Type",
    "keyboard_command": "Press",
    "extract_text": "Read text",
    "open_app": "Open",
    "scroll": "Scroll",
    "drag": "Drag",
    "triple_click": "Triple-click",
    "hybrid": "Find & click",
    "step": "Step",
    "error": "Run stopped",
}

# Longest step output shown in the report (an extraction can be a whole screen).
_OUTPUT_LIMIT = 600


def _task_title(event: dict[str, Any]) -> str:
    """``"Click text · Login"`` for a known action type, else the task name."""
    ttype = str(event.get("type") or "")
    verb = _TYPE_TITLES.get(ttype)
    label = str(event.get("target") or event.get("task_name") or "")
    if verb:
        return f"{verb} · {label}" if label else verb
    return str(event.get("task_name") or event.get("target") or ttype or "task")


def _render_task(
    event: dict[str, Any], screenshots: dict[str, bytes], number: int
) -> str:
    success = bool(event.get("success"))
    badge = (
        '<span class="badge-success">OK</span>'
        if success
        else '<span class="badge-failure">FAILED</span>'
    )
    ttype = str(event.get("type") or "task")
    name = _task_title(event)
    target = event.get("target")
    action_line = f"<b>{escape(ttype)}</b>" + (
        f" → {escape(str(target))}" if target else ""
    )

    error = event.get("error")
    error_block = f'<p class="step-error">{escape(str(error))}</p>' if error else ""

    rows: list[tuple[str, str]] = [("attempts", str(int(event.get("attempts") or 0)))]
    if event.get("output"):
        output = str(event.get("output"))
        if len(output) > _OUTPUT_LIMIT:
            output = output[:_OUTPUT_LIMIT] + "…"
        rows.append(("output", output))
    if event.get("location") not in (None, "skip"):
        rows.append(("location", str(event.get("location"))))
    if event.get("region"):
        rows.append(("region", str(event.get("region"))))
    if event.get("timestamp"):
        rows.append(("time", _short_time(str(event.get("timestamp")))))
    kv = "".join(f"<dt>{escape(k)}</dt><dd>{escape(v)}</dd>" for k, v in rows)

    shot = ""
    if event.get("screenshot"):
        shot = _render_screenshot(event["screenshot"], screenshots, kind="step")

    return f"""<article class="task">
        <div class="row">
          <span class="index">#{number}</span>
          <span class="name">{escape(name)}</span>
          {badge}
          <span class="duration">{_duration(int(event.get("duration_ms") or 0))}</span>
        </div>
        <p class="action">{action_line}</p>
        {error_block}
        <dl class="kv">{kv}</dl>
        {_render_logs(event.get("logs") or [])}
        {shot}
      </article>"""


def _render_logs(lines: list[str]) -> str:
    """Render the per-task log lines as a collapsible ``<details>`` block.

    Lines come in shaped as ``"[LEVEL] logger.name: message"`` (set by
    :func:`_attach_logs_to_events`): one row each, the level coloured.
    """
    if not lines:
        return ""
    rendered: list[str] = []
    for line in lines:
        level, message = "INFO", line
        if line.startswith("[") and "]" in line:
            level = line[1 : line.index("]")] or "INFO"
            message = line[line.index("]") + 1 :].strip()
        safe_class = "".join(c for c in level if c.isalnum()).upper() or "INFO"
        rendered.append(
            f'<div class="log-line lvl-{safe_class}">'
            f'<span class="lvl">{escape(safe_class)}</span>'
            f'<span class="msg">{escape(message)}</span></div>'
        )
    return (
        f'<details class="logs">'
        f"<summary>Logs · {len(lines)} line(s)</summary>"
        f'<div class="log-output">{"".join(rendered)}</div>'
        "</details>"
    )


def _render_screenshot(
    shot_path: str, screenshots: dict[str, bytes], kind: str = "failure"
) -> str:
    basename = os.path.basename(shot_path)
    data = screenshots.get(basename)
    if data is None:
        return ""
    encoded = base64.b64encode(data).decode("ascii")
    label = "Step result" if kind == "step" else "Failure screenshot"
    return (
        f'<figure class="shot {kind}">'
        f'<img src="data:image/png;base64,{encoded}" alt="{kind} screenshot" '
        f'loading="eager" />'
        f"<figcaption>{label} · {escape(basename)}</figcaption>"
        "</figure>"
    )

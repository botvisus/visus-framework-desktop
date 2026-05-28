"""Single-file HTML run report (Phase 2, O5).

Reads the ``events.jsonl`` from a session zip (see
``visus.desktop.core.session``) and renders a self-contained HTML file
suitable for emailing, attaching to a CI artefact, or pinning in a
bug ticket. Every PNG referenced by ``failure_screenshot`` is embedded
as a base64 data URI so the report has no external dependencies.

The styling follows the design tokens documented in
``D:\\bot_vision\\DESIGN.md`` (Anthropic Claude design system):

  * cream canvas ``#faf9f5``  -- page floor
  * surface card ``#efe9de``  -- feature card backgrounds
  * dark navy ``#181715``     -- code / terminal / footer surfaces
  * coral ``#cc785c``         -- primary CTA / KPI accent
  * ink ``#141413``           -- headlines + body emphasis
  * body ``#3d3d3a``          -- running text
  * muted ``#6c6a64``         -- captions and labels
  * hairline ``#e6dfd8``      -- 1px dividers
  * EB Garamond / Tiempos / Cormorant fallback for serif display
    headlines; Inter / system sans for body; JetBrains Mono for code
"""

from __future__ import annotations

import base64
import json
import os
import zipfile
from html import escape
from pathlib import Path
from typing import Any, Iterable

_EVENTS_FILE = "events.jsonl"
_SCREENSHOTS_DIR = "screenshots/"

_CSS = """
:root {
  --canvas: #faf9f5;
  --surface-card: #efe9de;
  --surface-cream-strong: #e8e0d2;
  --surface-dark: #181715;
  --surface-dark-soft: #1f1e1b;
  --ink: #141413;
  --body: #3d3d3a;
  --muted: #6c6a64;
  --muted-soft: #8e8b82;
  --hairline: #e6dfd8;
  --primary: #cc785c;
  --primary-active: #a9583e;
  --on-primary: #ffffff;
  --on-dark: #faf9f5;
  --on-dark-soft: #a09d96;
  --success: #5db872;
  --error: #c64545;
  --serif: Copernicus, 'Tiempos Headline', 'EB Garamond', 'Cormorant Garamond', Garamond, 'Times New Roman', serif;
  --sans: StyreneB, Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: var(--canvas);
  color: var(--body);
  font-family: var(--sans);
  font-size: 16px;
  line-height: 1.55;
}
main { max-width: 1200px; margin: 0 auto; padding: 0 32px; }
header.hero {
  padding: 96px 32px 48px;
  max-width: 1200px;
  margin: 0 auto;
}
header.hero h1 {
  font-family: var(--serif);
  font-weight: 400;
  font-size: 64px;
  line-height: 1.05;
  letter-spacing: -1.5px;
  color: var(--ink);
  margin: 0 0 16px;
}
header.hero p.lede {
  font-family: var(--sans);
  font-size: 18px;
  color: var(--muted);
  margin: 0;
}
header.hero .run-meta {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}
.badge-pill {
  display: inline-block;
  background: var(--surface-card);
  color: var(--ink);
  font-size: 13px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 9999px;
}
.badge-coral {
  display: inline-block;
  background: var(--primary);
  color: var(--on-primary);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 4px 12px;
  border-radius: 9999px;
}
.badge-success {
  display: inline-block;
  background: var(--surface-card);
  color: var(--success);
  font-size: 13px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 9999px;
}
.badge-failure {
  display: inline-block;
  background: var(--primary);
  color: var(--on-primary);
  font-size: 13px;
  font-weight: 500;
  padding: 4px 12px;
  border-radius: 9999px;
}
section.kpis {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 96px;
}
.kpi-card {
  background: var(--surface-card);
  border-radius: 12px;
  padding: 32px;
}
.kpi-card .label {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 12px;
}
.kpi-card .value {
  font-family: var(--serif);
  font-weight: 400;
  font-size: 36px;
  line-height: 1.15;
  letter-spacing: -0.5px;
  color: var(--ink);
}
section.timeline {
  margin-bottom: 96px;
}
section.timeline h2 {
  font-family: var(--serif);
  font-weight: 400;
  font-size: 36px;
  line-height: 1.15;
  letter-spacing: -0.5px;
  color: var(--ink);
  margin: 0 0 32px;
}
article.task {
  border-top: 1px solid var(--hairline);
  padding: 24px 0;
  display: grid;
  grid-template-columns: 56px 1fr auto;
  gap: 24px;
  align-items: start;
}
article.task:first-of-type { border-top: none; }
article.task .index {
  font-family: var(--serif);
  font-weight: 400;
  font-size: 28px;
  line-height: 1.2;
  letter-spacing: -0.3px;
  color: var(--muted-soft);
}
article.task .body h3 {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 500;
  color: var(--ink);
}
article.task .body .meta {
  font-size: 14px;
  color: var(--muted);
}
article.task .status {
  text-align: right;
  min-width: 140px;
}
article.task pre.error {
  font-family: var(--mono);
  font-size: 14px;
  line-height: 1.6;
  margin-top: 12px;
  padding: 16px 20px;
  background: var(--surface-dark);
  color: var(--on-dark);
  border-radius: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
}
.screenshot-card {
  margin-top: 16px;
  padding: 24px;
  background: var(--surface-dark);
  border-radius: 12px;
}
.screenshot-card .header {
  color: var(--on-dark-soft);
  font-family: var(--mono);
  font-size: 12px;
  margin-bottom: 12px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.screenshot-card img {
  max-width: 100%;
  height: auto;
  display: block;
  border-radius: 8px;
  background: var(--surface-dark-soft);
}
footer.site {
  background: var(--surface-dark);
  color: var(--on-dark-soft);
  padding: 64px 32px;
  font-size: 14px;
}
footer.site .inner {
  max-width: 1200px;
  margin: 0 auto;
}
footer.site .wordmark {
  color: var(--on-dark);
  font-family: var(--serif);
  font-weight: 400;
  font-size: 22px;
  letter-spacing: -0.3px;
  margin-bottom: 12px;
}
@media (max-width: 900px) {
  section.kpis { grid-template-columns: repeat(2, 1fr); }
  header.hero h1 { font-size: 44px; letter-spacing: -1px; }
  article.task { grid-template-columns: 40px 1fr; }
  article.task .status { grid-column: 2; text-align: left; }
}
@media (max-width: 600px) {
  section.kpis { grid-template-columns: 1fr; }
  main, header.hero { padding: 48px 20px; }
}
""".strip()


def write_report(zip_path: str | os.PathLike[str], html_path: str | os.PathLike[str]) -> None:
    """Render a session zip into a single-file HTML report."""
    events, screenshots = _read_session(Path(zip_path))
    html = _render_html(events, screenshots)
    out = Path(html_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")


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
            "total_attempts": 0,
        }
    succeeded = sum(1 for e in events if e.get("success"))
    total_duration = sum(int(e.get("duration_ms") or 0) for e in events)
    total_attempts = sum(int(e.get("attempts") or 0) for e in events)
    return {
        "total": total,
        "success_rate_pct": round(succeeded / total * 100),
        "total_duration_ms": total_duration,
        "total_attempts": total_attempts,
    }


def _render_html(
    events: list[dict[str, Any]], screenshots: dict[str, bytes]
) -> str:
    kpis = _kpis(events)
    run_id = events[0]["run_id"] if events else ""
    last_ts = events[-1]["timestamp"] if events else ""

    task_rows = "\n".join(_render_task(e, screenshots) for e in events)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Visus Desktop -- Run report</title>
  <style>{_CSS}</style>
</head>
<body>
  <header class="hero">
    <h1>Visus Desktop run report</h1>
    <p class="lede">A timeline of every task, with durations, attempts and failure
       screenshots embedded inline.</p>
    <div class="run-meta">
      <span class="badge-pill">run {escape(run_id) or 'n/a'}</span>
      <span class="badge-pill">{escape(last_ts)}</span>
      {('<span class="badge-coral">failures present</span>' if kpis['total'] and kpis['success_rate_pct'] < 100 else '')}
    </div>
  </header>

  <main>
    <section class="kpis" aria-label="Run summary">
      <div class="kpi-card">
        <div class="label">Total tasks</div>
        <div class="value">{kpis['total']}</div>
      </div>
      <div class="kpi-card">
        <div class="label">Success rate</div>
        <div class="value">{kpis['success_rate_pct']}%</div>
      </div>
      <div class="kpi-card">
        <div class="label">Total duration</div>
        <div class="value">{kpis['total_duration_ms']} ms</div>
      </div>
      <div class="kpi-card">
        <div class="label">Total attempts</div>
        <div class="value">{kpis['total_attempts']}</div>
      </div>
    </section>

    <section class="timeline">
      <h2>Timeline</h2>
      {task_rows if task_rows else '<p style="color: var(--muted);">No tasks recorded.</p>'}
    </section>
  </main>

  <footer class="site">
    <div class="inner">
      <div class="wordmark">* Visus Desktop</div>
      <div>Generated from <code>{escape(_EVENTS_FILE)}</code>. Design system: cream canvas + coral CTA + dark navy product surfaces.</div>
    </div>
  </footer>
</body>
</html>
"""


def _render_task(event: dict[str, Any], screenshots: dict[str, bytes]) -> str:
    success = bool(event.get("success"))
    badge = (
        '<span class="badge-success">SUCCESS</span>'
        if success
        else '<span class="badge-failure">FAILED</span>'
    )
    task_id = event.get("task_id", "?")
    name = escape(str(event.get("task_name") or "(unnamed task)"))
    duration = int(event.get("duration_ms") or 0)
    attempts = int(event.get("attempts") or 0)
    error = event.get("error")
    error_block = (
        f'<pre class="error">{escape(str(error))}</pre>' if error else ""
    )
    shot_path = event.get("failure_screenshot")
    shot_block = _render_screenshot(shot_path, screenshots) if shot_path else ""
    return f"""<article class="task">
        <div class="index">#{escape(str(int(task_id) + 1))}</div>
        <div class="body">
          <h3>{name}</h3>
          <div class="meta">{duration} ms &middot; {attempts} attempt(s)</div>
          {error_block}
          {shot_block}
        </div>
        <div class="status">{badge}</div>
      </article>"""


def _render_screenshot(shot_path: str, screenshots: dict[str, bytes]) -> str:
    basename = os.path.basename(shot_path)
    data = screenshots.get(basename)
    if data is None:
        return ""
    encoded = base64.b64encode(data).decode("ascii")
    return (
        '<div class="screenshot-card">'
        f'<div class="header">Failure screenshot &middot; {escape(basename)}</div>'
        f'<img src="data:image/png;base64,{encoded}" alt="failure screenshot" />'
        "</div>"
    )

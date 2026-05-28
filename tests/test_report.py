"""Tests for the HTML run report (Phase 2, O5).

``Session.write_report(zip_path, html_path)`` reads the recorded events
from a session zip and renders a single-file HTML report. The styling
follows ``D:\\bot_vision\\DESIGN.md`` (Anthropic Claude design system —
cream canvas, serif headlines, coral CTAs, dark navy code surfaces).
"""

from __future__ import annotations

import base64
import json
import re
import zipfile
from pathlib import Path

from PIL import Image

from visus.desktop.core.session import Session


def _make_zip(zip_path: Path, events, screenshots: dict | None = None):
    """Build a session zip from in-memory events for the report tests."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("events.jsonl", "\n".join(json.dumps(e) for e in events))
        for name, image in (screenshots or {}).items():
            from io import BytesIO

            buf = BytesIO()
            image.save(buf, "PNG")
            zf.writestr(f"screenshots/{name}", buf.getvalue())


class TestReportSmoke:
    def test_report_is_written_and_contains_html_skeleton(self, tmp_path):
        zip_path = tmp_path / "run.zip"
        html_path = tmp_path / "report.html"
        _make_zip(
            zip_path,
            [
                {
                    "run_id": "abc",
                    "task_id": 0,
                    "task_name": "Login",
                    "success": True,
                    "duration_ms": 120,
                    "attempts": 1,
                    "error": None,
                    "failure_screenshot": None,
                    "timestamp": "2026-05-28T10:00:00+00:00",
                },
            ],
        )
        Session.write_report(zip_path, html_path)
        assert html_path.exists()
        html = html_path.read_text(encoding="utf-8")
        assert "<!doctype html>" in html.lower()
        assert "<html" in html
        assert "</html>" in html
        assert "<title>" in html

    def test_report_renders_each_task(self, tmp_path):
        zip_path = tmp_path / "run.zip"
        html_path = tmp_path / "report.html"
        _make_zip(
            zip_path,
            [
                {
                    "run_id": "r1",
                    "task_id": 0,
                    "task_name": "Open file",
                    "success": True,
                    "duration_ms": 200,
                    "attempts": 1,
                    "error": None,
                    "failure_screenshot": None,
                    "timestamp": "2026-05-28T10:00:00+00:00",
                },
                {
                    "run_id": "r1",
                    "task_id": 1,
                    "task_name": "Submit form",
                    "success": False,
                    "duration_ms": 500,
                    "attempts": 4,
                    "error": "TextNotFoundError: 'Submit' not visible",
                    "failure_screenshot": None,
                    "timestamp": "2026-05-28T10:00:01+00:00",
                },
            ],
        )
        Session.write_report(zip_path, html_path)
        html = html_path.read_text(encoding="utf-8")
        assert "Open file" in html
        assert "Submit form" in html
        assert "TextNotFoundError" in html

    def test_report_embeds_failure_screenshot_as_data_uri(self, tmp_path):
        zip_path = tmp_path / "run.zip"
        html_path = tmp_path / "report.html"
        image = Image.new("RGB", (16, 16), color="red")
        _make_zip(
            zip_path,
            [
                {
                    "run_id": "r",
                    "task_id": 0,
                    "task_name": "Click",
                    "success": False,
                    "duration_ms": 80,
                    "attempts": 1,
                    "error": "ImageNotFoundError",
                    "failure_screenshot": "C:/anywhere/r__0__t.png",
                    "timestamp": "2026-05-28T10:00:00+00:00",
                },
            ],
            screenshots={"r__0__t.png": image},
        )
        Session.write_report(zip_path, html_path)
        html = html_path.read_text(encoding="utf-8")
        # A real <img> tag with a base64 PNG data URI is emitted for the
        # failure screenshot, so the report is portable as a single file.
        assert "data:image/png;base64," in html
        # Sanity: the embedded payload should be a non-trivial size.
        match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', html)
        assert match is not None
        decoded = base64.b64decode(match.group(1))
        # Cheap "is this actually a PNG" check rather than a size threshold:
        # base64 of even the tiniest valid PNG is well over 80 bytes and the
        # header bytes are stable.
        assert decoded.startswith(b"\x89PNG\r\n\x1a\n")

    def test_report_includes_kpi_block(self, tmp_path):
        zip_path = tmp_path / "run.zip"
        html_path = tmp_path / "report.html"
        events = [
            {
                "run_id": "x",
                "task_id": i,
                "task_name": f"t{i}",
                "success": i % 2 == 0,
                "duration_ms": 100,
                "attempts": 1,
                "error": None,
                "failure_screenshot": None,
                "timestamp": "2026-05-28T10:00:00+00:00",
            }
            for i in range(4)
        ]
        _make_zip(zip_path, events)
        Session.write_report(zip_path, html_path)
        html = html_path.read_text(encoding="utf-8")
        # KPI strip should expose the totals so a reader sees them at a glance.
        assert "4" in html  # total
        assert "50" in html  # success rate percent

    def test_report_follows_design_system_anchor_colors(self, tmp_path):
        """The cream canvas, coral accent and dark navy are present in the CSS."""
        zip_path = tmp_path / "run.zip"
        html_path = tmp_path / "report.html"
        _make_zip(
            zip_path,
            [
                {
                    "run_id": "x",
                    "task_id": 0,
                    "task_name": "t",
                    "success": True,
                    "duration_ms": 1,
                    "attempts": 1,
                    "error": None,
                    "failure_screenshot": None,
                    "timestamp": "2026-05-28T10:00:00+00:00",
                },
            ],
        )
        Session.write_report(zip_path, html_path)
        html = html_path.read_text(encoding="utf-8")
        assert "#faf9f5" in html  # cream canvas
        assert "#cc785c" in html  # coral primary
        assert "#181715" in html  # dark navy surface
        assert "#141413" in html  # ink text

    def test_empty_recording_writes_valid_empty_report(self, tmp_path):
        zip_path = tmp_path / "empty.zip"
        html_path = tmp_path / "report.html"
        _make_zip(zip_path, [])
        Session.write_report(zip_path, html_path)
        html = html_path.read_text(encoding="utf-8")
        assert "<html" in html
        # No task rows are emitted but the header / KPIs / footer still render.
        assert "Visus" in html

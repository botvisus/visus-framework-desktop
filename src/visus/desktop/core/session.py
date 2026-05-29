"""Session record/replay (Phase 2, O3).

``Session`` is a context manager that records every structured task
event emitted on the ``visus.desktop.task_events`` logger plus the
failure screenshots referenced by those events. The resulting zip
contains:

  * ``events.jsonl`` -- one JSON object per task, identical to the lines
    emitted by ``config['log_format'] = 'json'``.
  * ``screenshots/<basename>.png`` -- a copy of each
    ``failure_screenshot`` path referenced in an event (so the zip is
    self-contained and the bot can be unplugged from its original
    artifacts directory).

``Session.replay(path)`` reads the zip back into the in-memory event
list, ready to be fed into a report, an assertion, or a future
disk-source-driven replay run.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_EVENTS_LOGGER = "visus.desktop.task_events"
_EVENTS_FILE = "events.jsonl"
_SCREENSHOTS_DIR = "screenshots"


class _MemoryHandler(logging.Handler):
    """Capture each JSON event line into an in-memory list."""

    def __init__(self):
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            self.lines.append(record.getMessage())
        except Exception:  # pragma: no cover - defensive
            pass


class Session:
    """Public entry point for recording / replaying a bot run."""

    @staticmethod
    @contextmanager
    def start_recording(zip_path: str | os.PathLike[str]):
        """Context manager that writes a session zip on exit.

        Usage::

            with Session.start_recording('run.zip'):
                bot.execute_tasks(...)
        """
        handler = _MemoryHandler()
        logger = logging.getLogger(_EVENTS_LOGGER)
        prior_level = logger.level
        if prior_level == logging.NOTSET or prior_level > logging.INFO:
            logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            yield
        finally:
            logger.removeHandler(handler)
            if prior_level != logger.level:
                logger.setLevel(prior_level)
            _write_zip(zip_path, handler.lines)

    @staticmethod
    def replay(zip_path: str | os.PathLike[str]) -> list[dict[str, Any]]:
        """Read the events list back from a session zip.

        Returns an empty list if the recording captured no task events.
        Raises ``FileNotFoundError`` if the zip itself is missing.
        """
        path = Path(zip_path)
        if not path.exists():
            raise FileNotFoundError(path)
        with zipfile.ZipFile(path) as zf:
            if _EVENTS_FILE not in zf.namelist():
                return []
            raw = zf.read(_EVENTS_FILE).decode("utf-8")
        return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _write_zip(zip_path: str | os.PathLike[str], event_lines: list[str]) -> None:
    """Bundle the captured events plus any referenced screenshots."""
    target = Path(zip_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(_EVENTS_FILE, "\n".join(event_lines))
        seen: set[str] = set()
        for line in event_lines:
            try:
                event = json.loads(line)
            except ValueError:
                continue
            # Bundle both per-step screenshots and failure screenshots so the
            # report can show every step, not just the failures.
            for key in ("screenshot", "failure_screenshot"):
                shot = event.get(key)
                if not shot or shot in seen or not os.path.exists(shot):
                    continue
                seen.add(shot)
                entry = f"{_SCREENSHOTS_DIR}/{os.path.basename(shot)}"
                try:
                    zf.write(shot, arcname=entry)
                except Exception:  # pragma: no cover - defensive
                    continue


def _delegate_write_report(zip_path, html_path):
    """Forward to ``report.write_report`` (kept as a function so the
    ``Session`` namespace stays small but still exposes the report API)."""
    from . import report as _report

    return _report.write_report(zip_path, html_path)


# Expose ``Session.write_report(zip, html)`` as a static method without
# circular-import noise at module load.
Session.write_report = staticmethod(_delegate_write_report)


def extract_screenshots(zip_path: str | os.PathLike[str], dest_dir: str | os.PathLike[str]) -> list[str]:
    """Extract the ``screenshots/`` folder from a session zip.

    Convenience helper used by report generation (O5) to materialise the
    embedded PNGs next to an HTML file.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.startswith(f"{_SCREENSHOTS_DIR}/"):
                continue
            target = dest / Path(name).name
            with zf.open(name) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            written.append(str(target))
    return written

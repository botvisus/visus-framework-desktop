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


# Third-party loggers too noisy to be useful in a run report. Records from
# these (and their children) are dropped from the captured log tail:
#   * PIL          -- logs every PNG chunk as it decodes
#   * RapidOCR     -- repeats "Using engine_name / model" lines per inference
#   * onnxruntime  -- RapidOCR's backend, chatty about providers/sessions
#   * pytesseract  -- defensive; the useful OCR narrative is on visus.* anyway
# The automation's own narrative lives under ``visus.*`` and is kept.
_NOISY_LOG_PREFIXES = ("PIL", "RapidOCR", "onnxruntime", "pytesseract")


class _LogTailHandler(logging.Handler):
    """Capture log records (with timestamps) emitted during a recording.

    Sibling of :class:`_MemoryHandler`: the memory one stores task event
    JSON lines, this one stores the surrounding free-form logs so the zip
    writer can associate each task with the lines that happened during its
    window. Attached to the **root** logger, so it captures the full trail
    of a run -- ``visus.*`` plus any other library that logs while
    recording. We drop:

      * the dedicated ``task_events`` logger (its JSON already lives in
        ``events.jsonl``), and
      * known-noisy third-party loggers -- PIL, RapidOCR, onnxruntime,
        pytesseract (see ``_NOISY_LOG_PREFIXES``).
    """

    def __init__(self):
        super().__init__()
        self.records: list[tuple[float, str, str, str]] = []

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        name = record.name
        if name == _EVENTS_LOGGER:
            return
        if any(name == p or name.startswith(p + ".") for p in _NOISY_LOG_PREFIXES):
            return
        try:
            self.records.append((
                record.created,
                record.levelname,
                name,
                record.getMessage(),
            ))
        except Exception:  # pragma: no cover - defensive
            pass


class Session:
    """Public entry point for recording / replaying a bot run."""

    @staticmethod
    @contextmanager
    def start_recording(zip_path: str | os.PathLike[str]):
        """Context manager that writes a session zip on exit.

        Captures two streams simultaneously:

        * structured task events on ``visus.desktop.task_events`` (the
          JSON lines written to ``events.jsonl``);
        * every other ``visus.*`` log record at whatever level the host
          configured via ``BotVisionConfig`` -- bundled per task in the
          ``logs`` array of each event so reports show the step-by-step
          forensics (``DEBUG`` shows the OCR / matcher decision trail;
          ``INFO`` only marks the milestones).

        Usage::

            with Session.start_recording('run.zip'):
                bot.execute_tasks(...)
        """
        event_handler = _MemoryHandler()
        log_handler = _LogTailHandler()

        event_logger = logging.getLogger(_EVENTS_LOGGER)
        prior_event_level = event_logger.level
        if prior_event_level == logging.NOTSET or prior_event_level > logging.INFO:
            event_logger.setLevel(logging.INFO)
        event_logger.addHandler(event_handler)

        # Attach to the ROOT logger so the recording captures the whole
        # trail emitted during the window -- ``visus.*`` plus the OCR
        # backend (``RapidOCR``) and any other library. Don't force a level
        # here: callers set it via ``BotVisionConfig({'log_level': ...})``
        # and we respect that exact choice (noisy PIL records are filtered
        # in the handler).
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)

        try:
            yield
        finally:
            event_logger.removeHandler(event_handler)
            root_logger.removeHandler(log_handler)
            if prior_event_level != event_logger.level:
                event_logger.setLevel(prior_event_level)
            _write_zip(zip_path, event_handler.lines, log_handler.records)

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


def _write_zip(
    zip_path: str | os.PathLike[str],
    event_lines: list[str],
    log_records: list[tuple[float, str, str, str]] | None = None,
) -> None:
    """Bundle captured events (enriched with per-task logs) + screenshots."""
    target = Path(zip_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    enriched_lines = _attach_logs_to_events(event_lines, log_records or [])
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(_EVENTS_FILE, "\n".join(enriched_lines))
        seen: set[str] = set()
        for line in enriched_lines:
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


def _attach_logs_to_events(
    event_lines: list[str],
    log_records: list[tuple[float, str, str, str]],
) -> list[str]:
    """Inject a ``logs`` array into each task event.

    Walks event lines in order and claims all log records whose timestamp
    falls inside ``(previous_event_ts, this_event_ts]`` as belonging to
    the current task. Lines that aren't valid JSON pass through untouched
    so callers using a bare ``events.jsonl`` stay compatible.
    """
    from datetime import datetime

    if not log_records:
        return list(event_lines)
    sorted_logs = sorted(log_records, key=lambda r: r[0])
    enriched: list[str] = []
    last_cutoff = 0.0
    for line in event_lines:
        try:
            event = json.loads(line)
        except ValueError:
            enriched.append(line)
            continue
        ts_iso = event.get("timestamp")
        cutoff = 0.0
        if ts_iso:
            try:
                cutoff = datetime.fromisoformat(
                    ts_iso.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                cutoff = 0.0
        if cutoff:
            # 1ms slack on both ends: ``record.created`` (from ``time.time``)
            # carries more precision than ``datetime.isoformat`` round-trips,
            # so a log emitted microseconds before an event can otherwise
            # fall just past the cutoff once it's been serialised + parsed.
            window_start = last_cutoff - 0.001
            window_end = cutoff + 0.001
            event["logs"] = [
                f"[{lvl}] {name}: {msg}"
                for ts, lvl, name, msg in sorted_logs
                if window_start < ts <= window_end
            ]
            last_cutoff = cutoff
        enriched.append(json.dumps(event))
    return enriched


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

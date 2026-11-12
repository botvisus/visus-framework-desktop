"""Batteries-included RPA session -- bot + recording + report + summary, automatic.

The goal: the developer writes ONLY the automation; visus.desktop handles the
rest -- the same contract as ``visus.web``'s ``rpa()``::

    from visus.desktop import rpa

    with rpa("notepad", app="notepad", window="Bloco de notas", open_report=True) as bot:
        bot.type_text("Olá, mundo")
        bot.keyboard_command("Ctrl+S")

On exit -- whether the block finishes or a step fails -- ``run.zip`` and
``report.html`` are written (to ``./visus-runs/<name>-<timestamp>/`` by default,
or *outdir*), a one-block summary is printed, and a failure ends the script with
exit code 1 (or is re-raised with ``reraise=True``). Every bot action is a step
of the report: what it aimed at, its duration, OK/FAILED with the reason, a
screenshot of the screen right after it (the target boxed) and the logs it
produced. No Session / zip / config / report plumbing in your script.

For finer control (several bots, your own zip path) drop down to
``Session.start_recording`` + ``bot.start_task_session()`` directly.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import webbrowser
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from .core.recording import _clear_action_highlight, mark_recorded, was_recorded
from .exceptions import ActionFailedError, BotVisionError

if TYPE_CHECKING:
    from . import VisusBot
    from .utils.config import BotVisionConfig


def _slug(name: str) -> str:
    """Filesystem-safe label for the run folder."""
    kept = "".join(c if (c.isalnum() or c in "-_") else "-" for c in name).strip("-")
    return kept or "run"


@contextmanager
def rpa(
    name: str = "run",
    *,
    config: dict[str, Any] | BotVisionConfig | None = None,
    app: str | None = None,
    window: str | None = None,
    timeout: float = 30.0,
    outdir: str | os.PathLike | None = None,
    report: bool = True,
    summary: bool = True,
    open_report: bool = False,
    screenshots: bool = True,
    stop_on_failure: bool = True,
    reraise: bool = False,
) -> Iterator[VisusBot]:
    """Run a desktop RPA with the bot, recording, HTML report and summary handled for you.

    Yields a ready-to-drive :class:`~visus.desktop.VisusBot`.

    Args:
        name: label for this run -- the report's headline and the output folder name.
        config: ``VisusBot`` settings (a dict or a ``BotVisionConfig``), as usual.
        app: open this first (``"notepad"``, ``"excel"``, a ``.xlsx``, a URL) --
            recorded as the run's first step.
        window: the window the run works in. With *app*: wait until it is ready
            and in front (*timeout* seconds). Alone: bring it to the front.
            Not found -> the run stops there, like any failed step.
        timeout: how long to wait for *window*, in seconds.
        outdir: where to write run.zip/report.html
            (default ``./visus-runs/<name>-<timestamp>/``).
        report: render report.html on exit (it is written even when a step fails).
        summary: print a one-block run summary on exit.
        open_report: open report.html in the default browser on exit.
        screenshots: a screenshot after EVERY step (the target boxed). Failed steps
            always get one (``config["screenshot_on_failure"]``, on by default).
        stop_on_failure: a failed action (``click_text`` that finds nothing, a
            ``type_text`` with the wrong window in front...) stops the run with
            :class:`~visus.desktop.ActionFailedError` instead of returning
            ``False``. Pass ``False`` to keep the bool returns and decide yourself;
            for an "is it on screen?" check use ``find_text`` / ``find_image``,
            which never stop the run.
        reraise: on a failed step, re-raise the original error (for programmatic
            handling). Default ``False``: the summary already explains the
            failure, so the process just exits with code 1 -- no internal
            traceback dumped to your console.
    """
    from . import VisusBot  # local import: rpa is loaded by the package __init__
    from .core import task_executor as _task_executor
    from .core.report import write_report
    from .core.session import Session
    from .utils.config import BotVisionConfig

    settings: dict[str, Any] = (
        config.to_dict() if isinstance(config, BotVisionConfig) else dict(config or {})
    )
    # The step / failure PNGs land in a scratch folder and travel inside run.zip
    # (the report embeds them), so the run folder holds just run.zip + report.html.
    scratch: str | None = None
    if "artifacts_dir" not in settings:
        scratch = tempfile.mkdtemp(prefix="visus-rpa-")
        settings["artifacts_dir"] = scratch
    settings["screenshot_steps"] = screenshots
    try:
        bot = VisusBot(config=settings)
    except BaseException:
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)
        raise
    bot.stop_on_failure = stop_on_failure

    # Under the RunPilot runner every step streams live to the orchestrator
    # (the SaaS run report IS the report): no local run.zip / report.html.
    orchestrated = bool(os.environ.get("RUNPILOT_RUN_TOKEN")) and (
        _task_executor._run_reporter() is not None
    )

    if orchestrated:
        base: Path | None = None
        zip_path: Path | None = None
        report_path: Path | None = None
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = Path(outdir) if outdir else Path.cwd() / "visus-runs" / f"{_slug(name)}-{stamp}"
        base.mkdir(parents=True, exist_ok=True)
        zip_path = base / "run.zip"
        report_path = base / "report.html"
    do_report = report and report_path is not None

    box: dict[str, Any] = {}
    rpa_error: BaseException | None = None
    try:
        with Session.start_recording(zip_path, name=name) as recording:
            box["rec"] = recording
            bot.start_task_session()
            try:
                _prepare(bot, app=app, window=window, timeout=timeout)
                yield bot
            except BaseException as exc:
                # An assert / unexpected error in the script never passed through
                # a recorded action: add it as the last FAILED step (screenshot
                # included) so the report shows why the run stopped.
                if _counts_as_failure(exc) and not was_recorded(exc):
                    try:
                        bot._record_run_failure(exc)
                    except Exception:  # pragma: no cover - never mask the real error
                        pass
                raise
            finally:
                bot.end_task_session()
                # the last step's box goes now, not after the report is written
                _clear_action_highlight()
    except (BotVisionError, AssertionError) as exc:
        # a failed action (BotVisionError) OR an assert -> present it cleanly
        # (friendly summary + exit 1) instead of dumping an internal traceback.
        rpa_error = exc
    finally:
        recording = box.get("rec")
        active = rpa_error if rpa_error is not None else sys.exc_info()[1]
        if active is not None and not _counts_as_failure(active):
            active = None
        # The PNGs are inside run.zip by now (written when the recording closed).
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)
        written: Path | None = None
        if do_report and recording is not None and recording.written:
            # While unwinding an unexpected exception, render best-effort so a
            # report bug can never mask the real failure.
            try:
                written = Path(write_report(zip_path, report_path, title=name))
            except Exception:
                if active is None:
                    raise
        if summary and recording is not None:
            _print_summary(recording, base, written, error=active)
        if open_report and written is not None:
            try:
                webbrowser.open(written.resolve().as_uri())
            except Exception:
                pass

    # Only reached when no *unexpected* exception is propagating. For a failed
    # step: re-raise it if asked, otherwise exit cleanly with code 1 -- the
    # summary above already explained why, so there is no scary traceback.
    if rpa_error is not None:
        if reraise:
            raise rpa_error
        raise SystemExit(1)


def _counts_as_failure(exc: BaseException) -> bool:
    """A ``sys.exit(0)`` / generator close inside the block is not a failed run."""
    if isinstance(exc, GeneratorExit):
        return False
    if isinstance(exc, SystemExit):
        return exc.code not in (0, None)
    return True


def _prepare(bot: Any, *, app: str | None, window: str | None, timeout: float) -> None:
    """Open *app* / bring *window* to the front -- each a recorded step."""
    if app:
        try:
            bot.open_app(app, wait_window=window, timeout=timeout)
        except OSError as exc:  # no such app / file: already a FAILED step
            failure = ActionFailedError(
                f"Could not open '{app}': {exc}", action="open_app", target=app
            )
            mark_recorded(failure)
            raise failure from exc
        return
    if window:
        from .core.window import front_window

        with bot.step(f"Bring '{window}' to the front"):
            if front_window(window, timeout=timeout) is None:
                raise ActionFailedError(
                    f"Window '{window}' was not found or did not come to the front "
                    f"within {timeout}s",
                    action="window",
                    target=window,
                )


def _print_summary(
    recording: Any,
    base: Path | None,
    report_path: Path | None,
    *,
    error: BaseException | None = None,
) -> None:
    s = recording.summary()
    steps = ", ".join(f"{a}{'' if ok else '(FAILED)'}" for a, ok in s["steps"])
    status = "FAILED" if (error is not None or s["failures"]) else "OK"
    print(f"\n=== visus.desktop RPA [{status}] ===")
    print(f"steps     : {s['total']}")
    print(f"failures  : {s['failures']}")
    print(f"retries   : {s['retries']}")
    if steps:
        print(f"timeline  : {steps}")
    if error is not None:
        text = str(error) or type(error).__name__
        if isinstance(error, KeyboardInterrupt):
            text = "interrupted (Ctrl+C)"
        print("error     : " + "\n            ".join(text.splitlines()))
    if base is not None:
        print(f"folder    : {base}")
    else:
        print("report    : streamed live to RunPilot (SaaS run report)")
    if report_path is not None:
        print(f"report    : {report_path}")

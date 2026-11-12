"""Tests for ``rpa()`` -- the batteries-included run with the HTML report.

``rpa()`` mirrors ``visus.web``'s: it yields a ready bot, records every action
as a report step (duration, OK/FAILED + reason, screenshot, logs), writes
``run.zip`` + ``report.html`` even when a step fails, prints a summary, and
ends a failed run with exit code 1. Nothing physical happens here: the click,
the typing, the keys, the OCR and the screen capture are all faked.
"""

from __future__ import annotations

import json
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from PIL import Image

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.core.session import Session
from visus.desktop.core.task_executor import TaskExecutor

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)

QUIET = {"show_overlay": False}


@pytest.fixture(autouse=True)
def fake_desktop(monkeypatch):
    """Fake every physical effect: clicks, typing, keys, OCR and the screen."""

    def perform(self, task, location):
        self.last_action_location = location

    monkeypatch.setattr(TaskExecutor, "_perform_action", perform)
    monkeypatch.setattr(
        "visus.desktop.core.task_executor.capture_screen",
        lambda *a, **k: Image.new("RGB", (64, 48), "white"),
    )
    monkeypatch.setattr(
        TaskExecutor, "_capture_region", lambda self, region: Image.new("RGB", (8, 8))
    )
    monkeypatch.setattr(
        "visus.desktop.core.human_typing.type_like_a_person", lambda text, interval: None
    )
    monkeypatch.setattr(
        "visus.desktop.core.keyboard_commands.KeyboardCommander.execute_command",
        lambda self, command: True,
    )
    monkeypatch.setattr("webbrowser.open", lambda *a, **k: True)


def _events(run_dir):
    with zipfile.ZipFile(run_dir / "run.zip") as zf:
        raw = zf.read("events.jsonl").decode("utf-8")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def _manifest(run_dir):
    with zipfile.ZipFile(run_dir / "run.zip") as zf:
        return json.loads(zf.read("manifest.json"))


@requires_tesseract
class TestRpaHappyPath:
    def test_every_action_is_a_step_of_the_report(self, tmp_path, capsys):
        out = tmp_path / "run"
        with vd.rpa("cadastro", outdir=out, config=QUIET) as bot:
            assert isinstance(bot, vd.VisusBot)
            bot.click_coordinates(10, 20)
            bot.type_text("Ada")
            bot.keyboard_command("Enter")

        events = _events(out)
        assert [e["type"] for e in events] == ["click", "type_text", "keyboard_command"]
        assert all(e["success"] for e in events)
        assert [e["target"] for e in events] == ["(10, 20)", "Ada", "Enter"]
        # one run, one id
        assert len({e["run_id"] for e in events}) == 1
        assert _manifest(out)["name"] == "cadastro"

        html = (out / "report.html").read_text(encoding="utf-8")
        assert "<h1>cadastro</h1>" in html
        assert "Click at · (10, 20)" in html
        assert "Type · Ada" in html
        assert "Press · Enter" in html
        # a screenshot per step, embedded in the single-file report
        assert html.count("data:image/png;base64,") == 3

        printed = capsys.readouterr().out
        assert "=== visus.desktop RPA [OK] ===" in printed
        assert "steps     : 3" in printed
        assert str(out / "report.html") in printed

    def test_run_folder_holds_only_zip_and_report(self, tmp_path):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET) as bot:
            bot.click_coordinates(1, 1)
        assert sorted(p.name for p in out.iterdir()) == ["report.html", "run.zip"]

    def test_default_folder_is_visus_runs_name_timestamp(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with vd.rpa("meu bot!", config=QUIET, summary=False) as bot:
            bot.click_coordinates(1, 1)
        (run_dir,) = (tmp_path / "visus-runs").iterdir()
        assert run_dir.name.startswith("meu-bot-")
        assert (run_dir / "report.html").exists()

    def test_open_report_opens_the_html(self, tmp_path):
        with patch("webbrowser.open") as opened:
            with vd.rpa(outdir=tmp_path / "r", config=QUIET, open_report=True) as bot:
                bot.click_coordinates(1, 1)
        (url,) = opened.call_args.args
        assert url.startswith("file:") and url.endswith("report.html")

    def test_execute_tasks_joins_the_same_run(self, tmp_path):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET) as bot:
            bot.click_coordinates(1, 1)
            bot.execute_tasks([{"type": "click", "x": 5, "y": 6}])
            bot.click_coordinates(2, 2)
        events = _events(out)
        assert len(events) == 3
        assert len({e["run_id"] for e in events}) == 1

    def test_extracted_text_is_shown_in_the_report(self, tmp_path):
        out = tmp_path / "run"
        ocr = [SimpleNamespace(text="R$ 1.234,56", confidence=93.0)]
        with vd.rpa(outdir=out, config=QUIET) as bot, patch.object(
            bot.ocr_engine, "extract_all_text", return_value=ocr
        ), patch.object(bot.executor.ocr_engine, "extract_all_text", return_value=ocr):
            assert bot.extract_text_from_region(region=(0, 0, 8, 8)) == ["R$ 1.234,56"]
            bot.execute_tasks([{"type": "extract_text", "region": [0, 0, 8, 8]}])
        events = _events(out)
        assert [e["output"] for e in events] == ["R$ 1.234,56", "R$ 1.234,56"]
        html = (out / "report.html").read_text(encoding="utf-8")
        assert "R$ 1.234,56" in html

    def test_secret_text_never_reaches_the_report(self, tmp_path):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET) as bot:
            bot.type_text("hunter2", secret=True)
        raw = (out / "report.html").read_text(encoding="utf-8")
        assert "hunter2" not in raw
        assert "••••••" in raw
        with zipfile.ZipFile(out / "run.zip") as zf:
            assert b"hunter2" not in zf.read("events.jsonl")

    def test_step_records_any_block(self, tmp_path):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET) as bot:
            with bot.step("Login pelo controle nativo"):
                pass
        (event,) = _events(out)
        assert event["type"] == "step" and event["success"] is True
        html = (out / "report.html").read_text(encoding="utf-8")
        assert "Step · Login pelo controle nativo" in html

    def test_screenshots_false_keeps_only_failure_shots(self, tmp_path):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET, screenshots=False) as bot:
            bot.click_coordinates(1, 1)
        (event,) = _events(out)
        assert event["screenshot"] is None


@requires_tesseract
class TestRpaFailures:
    def test_failed_action_stops_the_run_with_exit_1(self, tmp_path, capsys):
        out = tmp_path / "run"
        after = []
        with pytest.raises(SystemExit) as exit_info:
            with vd.rpa("login", outdir=out, config=QUIET) as bot, patch.object(
                bot, "find_text", return_value=None
            ):
                bot.click_coordinates(1, 1)
                bot.click_text("Entrar", region=(0, 0, 50, 50), max_attempts=1)
                after.append("ran")  # never reached: the run stopped
        assert exit_info.value.code == 1
        assert after == []

        events = _events(out)
        assert [e["success"] for e in events] == [True, False]
        assert "Text 'Entrar' was not found in region [0, 0, 50, 50]" in events[1]["error"]
        assert events[1]["failure_screenshot"]

        html = (out / "report.html").read_text(encoding="utf-8")
        assert "Errors (1)" in html
        assert "Click text · Entrar" in html
        printed = capsys.readouterr().out
        assert "[FAILED]" in printed and "Entrar" in printed

    def test_reraise_gives_the_action_error(self, tmp_path):
        with pytest.raises(vd.ActionFailedError) as info:
            with vd.rpa(outdir=tmp_path / "r", config=QUIET, reraise=True) as bot:
                with patch.object(bot, "find_image", return_value=None):
                    bot.click_image("salvar.png", max_attempts=1)
        assert info.value.action == "image"
        assert "salvar.png" in str(info.value)

    def test_stop_on_failure_false_keeps_the_bool_returns(self, tmp_path):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET, stop_on_failure=False) as bot:
            with patch.object(bot, "find_text", return_value=None):
                assert bot.click_text("Popup", max_attempts=1) is False
            bot.click_coordinates(1, 1)  # the run goes on
        assert [e["success"] for e in _events(out)] == [False, True]

    def test_assert_in_the_script_is_recorded_as_the_last_step(self, tmp_path):
        out = tmp_path / "run"
        with pytest.raises(SystemExit):
            with vd.rpa(outdir=out, config=QUIET) as bot:
                bot.click_coordinates(1, 1)
                total = 1
                assert total == 2, "total não confere"
        events = _events(out)
        assert events[-1]["type"] == "error"
        assert events[-1]["success"] is False
        assert "total não confere" in events[-1]["error"]
        assert events[-1]["failure_screenshot"]

    def test_unexpected_error_propagates_but_the_report_is_written(self, tmp_path):
        out = tmp_path / "run"
        with pytest.raises(ZeroDivisionError):
            with vd.rpa(outdir=out, config=QUIET, summary=False) as bot:
                bot.click_coordinates(1, 1)
                1 / 0  # noqa: B018
        html = (out / "report.html").read_text(encoding="utf-8")
        assert "Run stopped · ZeroDivisionError" in html

    def test_sys_exit_zero_is_not_a_failure(self, tmp_path):
        out = tmp_path / "run"
        with pytest.raises(SystemExit) as info:
            with vd.rpa(outdir=out, config=QUIET, summary=False) as bot:
                bot.click_coordinates(1, 1)
                raise SystemExit(0)
        assert info.value.code == 0
        assert [e["type"] for e in _events(out)] == ["click"]

    def test_failed_step_block_is_recorded_once(self, tmp_path):
        out = tmp_path / "run"
        with pytest.raises(SystemExit):
            with vd.rpa(outdir=out, config=QUIET, summary=False) as bot:
                with bot.step("Conferir saldo"):
                    raise vd.BotVisionError("saldo divergente")
        (event,) = _events(out)
        assert event["type"] == "step" and not event["success"]
        assert "saldo divergente" in event["error"]

    def test_app_window_that_never_shows_up_stops_the_run(self, tmp_path):
        out = tmp_path / "run"
        with patch(
            "visus.desktop.core.process.open_app",
            return_value={"target": "notepad", "window": None},
        ):
            with pytest.raises(SystemExit):
                with vd.rpa(
                    outdir=out, config=QUIET, app="notepad", window="Bloco", timeout=1
                ):
                    pytest.fail("the block must not run without its window")
        (event,) = _events(out)
        assert event["type"] == "open_app" and not event["success"]
        assert "'Bloco' did not show up" in event["error"]


class _FakeReporter:
    """Stands in for ``runpilot.Orchestrator``: keeps every streamed step."""

    def __init__(self):
        self.steps = []

    def report_ui_step(self, **kwargs):
        self.steps.append(kwargs)


@requires_tesseract
class TestRpaUnderRunPilot:
    """Under the RunPilot runner every step streams to the orchestrator, fitted to
    its ``POST /sdk/run/step`` schema (name<=500, target<=2000, errorMessage<=5000
    -- a longer field gets the WHOLE step rejected)."""

    @pytest.fixture
    def reporter(self, monkeypatch):
        from visus.desktop.core import task_executor as te

        fake = _FakeReporter()
        monkeypatch.setenv("RUNPILOT_RUN_TOKEN", "rt_test")
        monkeypatch.setattr(te, "_run_reporter_cache", fake)
        return fake

    def test_steps_stream_and_no_local_files(self, tmp_path, reporter, capsys):
        out = tmp_path / "run"
        ocr = [SimpleNamespace(text="42", confidence=90.0)]
        with vd.rpa(outdir=out, config=QUIET) as bot, patch.object(
            bot.ocr_engine, "extract_all_text", return_value=ocr
        ):
            bot.click_coordinates(1, 2)
            bot.extract_text_from_region(region=(0, 0, 8, 8))
        assert [s["action"] for s in reporter.steps] == ["click", "extract_text"]
        assert all(s["status"] == "ok" and s["screenshot_png"] for s in reporter.steps)
        assert reporter.steps[1]["attributes"]["output"] == "42"
        assert not out.exists() or not any(out.iterdir())
        assert "streamed live to RunPilot" in capsys.readouterr().out

    def test_long_fields_are_clipped_to_the_step_schema(self, tmp_path, reporter):
        with pytest.raises(SystemExit):
            with vd.rpa(outdir=tmp_path / "r", config=QUIET, summary=False) as bot:
                bot.type_text("x" * 2600)
                raise AssertionError("y" * 6000)
        typed, error = reporter.steps
        assert len(typed["name"]) <= 500 and len(typed["target"]) <= 2000
        assert error["status"] == "failed" and len(error["error"]) <= 5000
        assert typed["target"].endswith("…")


@requires_tesseract
class TestSessionWithoutJsonLogs:
    """``Session.start_recording`` no longer needs ``log_format='json'``."""

    def test_direct_calls_are_recorded_with_text_logs(self, tmp_path):
        bot = vd.VisusBot(QUIET)
        zip_path = tmp_path / "run.zip"
        with Session.start_recording(zip_path, name="manual") as rec:
            bot.start_task_session()
            bot.click_coordinates(3, 4)
            bot.end_task_session()
        assert rec.summary()["total"] == 1
        assert rec.written
        assert len(Session.replay(zip_path)) == 1

    def test_outside_a_recording_nothing_is_captured(self, tmp_path):
        bot = vd.VisusBot({**QUIET, "artifacts_dir": str(tmp_path / "art")})
        bot.start_task_session()
        with patch.object(bot, "find_text", return_value=None):
            assert bot.click_text("x", max_attempts=1) is False
        bot.end_task_session()
        # no recording, no JSON logs -> no failure screenshot written either
        assert not (tmp_path / "art").exists()

    def test_backtrack_after_a_recorded_call_does_not_crash(self, tmp_path):
        """Recorded direct calls must not land in the backtrack history."""
        bot = vd.VisusBot(QUIET)
        with Session.start_recording(tmp_path / "run.zip"):
            bot.start_task_session()
            bot.click_coordinates(1, 1)  # recorded, not replayable
            with patch.object(bot, "_click_text_internal", return_value=False), patch(
                "time.sleep"
            ):
                assert bot.click_text("Salvar", backtrack=True) is False
            bot.end_task_session()

    def test_the_old_generated_script_still_works(self, tmp_path):
        """The visus.studio script shape (JSON logs + manual session) keeps working
        -- and now its execute_tasks joins the same run as the direct calls."""
        bot = vd.VisusBot({**QUIET, "log_format": "json"})
        zip_path = tmp_path / "run.zip"
        report_path = tmp_path / "report.html"
        ocr = [SimpleNamespace(text="42", confidence=90.0)]
        with Session.start_recording(zip_path):
            bot.start_task_session()
            try:
                bot.click_coordinates(1003, 512, mouse_button="left", delay=0)
                with patch.object(
                    bot.executor.ocr_engine, "extract_all_text", return_value=ocr
                ):
                    bot.execute_tasks(
                        [{"type": "extract_text", "region": [1, 2, 3, 4]}]
                    )
                assert bot.get_last_extracted_text() == ["42"]
            finally:
                bot.end_task_session()
        Session.write_report(zip_path, report_path)
        events = Session.replay(zip_path)
        assert [e["type"] for e in events] == ["click", "extract_text"]
        assert len({e["run_id"] for e in events}) == 1
        assert "Read text · region [1, 2, 3, 4]" in report_path.read_text(
            encoding="utf-8"
        )

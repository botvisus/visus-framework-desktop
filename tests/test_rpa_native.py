"""``native_*`` actions inside ``rpa()``: report steps, highlight, stop on failure.

Inside an open task session (``rpa()`` opens one) ``native_click``,
``native_set_text``, ``native_get_text`` and ``native_wait`` record a step each
-- with the control highlighted in the bot's overlay style and boxed on the
screenshot -- and a ``False`` / ``None`` result stops the run. Outside one they
behave exactly as before. The UIA tree is faked: no pywinauto, no real window.
"""

from __future__ import annotations

import json
import zipfile

import pytest
from PIL import Image

import visus.desktop as vd
from tests import tesseract_available
from visus.desktop.core import native_rpa
from visus.desktop.core.task_executor import TaskExecutor

requires_tesseract = pytest.mark.skipif(
    not tesseract_available(),
    reason="Tesseract OCR not installed (VisusBot requires it at construction)",
)

QUIET = {"show_overlay": True, "overlay_color": "blue"}
BOX = (10, 20, 50, 25)


class _Rect:
    left, top, right, bottom = 10, 20, 60, 45


class _Ctrl:
    """A UIA control spec: found or not, with a rectangle."""

    def __init__(self, found=True):
        self.found = found
        self.invoked = 0

    def exists(self, timeout=0):
        return self.found

    def rectangle(self):
        return _Rect()

    def invoke(self):
        self.invoked += 1

    def wait(self, wanted, timeout=0, retry_interval=0):
        if not self.found:
            raise TimeoutError(f"not {wanted}")

    def wrapper_object(self):
        return object()


@pytest.fixture
def ui(monkeypatch):
    """Fake the accessibility tree and every physical / visual effect."""
    state = {"ctrl": _Ctrl(), "highlights": []}

    class _Top:
        def child_window(self, **kwargs):
            return state["ctrl"]

    monkeypatch.setattr(native_rpa, "_ensure_pywinauto", lambda: True)
    monkeypatch.setattr(native_rpa, "_connect_top", lambda *a, **k: _Top())
    monkeypatch.setattr(native_rpa, "_type_into", lambda wrapper, text: True)
    monkeypatch.setattr(native_rpa, "_control_value", lambda wrapper: "56")
    monkeypatch.setattr(
        TaskExecutor,
        "_highlight",
        lambda self, box: state["highlights"].append((box, self.config.get("overlay_color"))),
    )
    monkeypatch.setattr(
        "visus.desktop.core.task_executor.capture_screen",
        lambda *a, **k: Image.new("RGB", (64, 48), "white"),
    )
    monkeypatch.setattr("webbrowser.open", lambda *a, **k: True)
    return state


def _events(run_dir):
    with zipfile.ZipFile(run_dir / "run.zip") as zf:
        raw = zf.read("events.jsonl").decode("utf-8")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


@requires_tesseract
class TestNativeInsideRpa:
    def test_click_is_a_highlighted_step(self, tmp_path, ui):
        out = tmp_path / "run"
        with vd.rpa("calc", outdir=out, config=QUIET):
            assert native_rpa.native_click(
                window="Calculadora", auto_id="num8Button", control_type="Button"
            )
        (event,) = _events(out)
        assert event["type"] == "native_click" and event["success"] is True
        assert event["target"] == "num8Button in 'Calculadora'"
        assert event["location"] == list(BOX)  # boxed on the screenshot
        assert ui["highlights"] == [(BOX, "blue")]  # in the bot's overlay style
        html = (out / "report.html").read_text(encoding="utf-8")
        assert "Click · num8Button in &#x27;Calculadora&#x27;" in html

    def test_show_overlay_false_keeps_the_screen_clean(self, tmp_path, ui):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config={"show_overlay": False}):
            native_rpa.native_click(window="Calculadora", auto_id="num8Button")
        assert ui["highlights"] == []
        assert _events(out)[0]["location"] == list(BOX)  # still boxed in the report

    def test_missing_control_stops_the_run(self, tmp_path, ui):
        out = tmp_path / "run"
        ui["ctrl"] = _Ctrl(found=False)
        after = []
        with pytest.raises(SystemExit) as info:
            with vd.rpa(outdir=out, config=QUIET, summary=False):
                native_rpa.native_click(window="Calculadora", auto_id="num9Button")
                after.append("ran")
        assert info.value.code == 1 and after == []
        (event,) = _events(out)
        assert event["success"] is False
        assert event["error"] == (
            "num9Button in 'Calculadora' was not found within 5.0s "
            "(or it did not take the click)"
        )
        assert event["failure_screenshot"]

    def test_wait_failure_names_the_state(self, tmp_path, ui):
        ui["ctrl"] = _Ctrl(found=False)
        with pytest.raises(vd.ActionFailedError) as info:
            with vd.rpa(outdir=tmp_path / "r", config=QUIET, reraise=True, summary=False):
                native_rpa.native_wait(
                    window="Calculadora", auto_id="equalButton", state="ready", timeout=2
                )
        assert str(info.value) == "equalButton in 'Calculadora' did not become 'ready' within 2s"
        assert ui["highlights"] == []  # a wait is not highlighted

    def test_get_text_shows_what_it_read(self, tmp_path, ui):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET):
            assert native_rpa.native_get_text(window="Calculadora", auto_id="CalculatorResults") == "56"
        (event,) = _events(out)
        assert event["type"] == "native_get_text" and event["output"] == "56"

    def test_set_text_secret_is_masked(self, tmp_path, ui):
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET):
            native_rpa.native_set_text(
                window="Login", auto_id="password", text="hunter2", secret=True
            )
        (event,) = _events(out)
        assert event["target"] == "password in 'Login' <- '••••••'"
        assert "hunter2" not in (out / "report.html").read_text(encoding="utf-8")

    def test_without_pywinauto_the_reason_is_clear(self, tmp_path, ui, monkeypatch):
        monkeypatch.setattr(native_rpa, "_ensure_pywinauto", lambda: False)
        with pytest.raises(vd.ActionFailedError, match="pywinauto is not installed"):
            with vd.rpa(outdir=tmp_path / "r", config=QUIET, reraise=True, summary=False):
                native_rpa.native_click(window="Calculadora", auto_id="num8Button")

    def test_a_native_step_and_a_bot_step_share_the_run(self, tmp_path, ui, monkeypatch):
        monkeypatch.setattr(
            TaskExecutor, "_perform_action",
            lambda self, task, location: setattr(self, "last_action_location", location),
        )
        out = tmp_path / "run"
        with vd.rpa(outdir=out, config=QUIET) as bot:
            native_rpa.native_click(window="Calculadora", auto_id="num8Button")
            bot.click_coordinates(1, 1)
        events = _events(out)
        assert [e["type"] for e in events] == ["native_click", "click"]
        assert len({e["run_id"] for e in events}) == 1


class TestNativeOutsideRpa:
    """No task session open: the functions behave exactly as before."""

    def test_returns_false_without_raising_or_highlighting(self, ui):
        ui["ctrl"] = _Ctrl(found=False)
        assert native_rpa.native_click(window="Calculadora", auto_id="x") is False
        assert native_rpa.native_get_text(window="Calculadora", auto_id="x") is None
        assert ui["highlights"] == []

    def test_success_is_untouched(self, ui):
        assert native_rpa.native_click(window="Calculadora", auto_id="num8Button") is True
        assert ui["ctrl"].invoked == 1
        assert ui["highlights"] == []

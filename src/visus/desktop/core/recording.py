"""Record every ``VisusBot`` action as one step of the run report.

:func:`records_step` decorates the public action methods (``click_text``,
``click_image``, ``type_text``, ``keyboard_command``, ``open_app``,
``extract_text_from_region``, ``scroll``...). Inside a task session -- which
:func:`visus.desktop.rpa` opens for you -- each call becomes one task event in
the recording: what it aimed at, how long it took, OK/FAILED with the reason,
the per-step (or failure) screenshot and the logs it produced. Outside a
session the wrapper is transparent: the method runs exactly as before.

With ``bot.stop_on_failure`` on (the ``rpa()`` default) a failed action raises
:class:`~visus.desktop.exceptions.ActionFailedError` after it is recorded, so
the run stops at the step that went wrong -- the same contract as visus.web.
"""

from __future__ import annotations

import functools
import inspect
import os
import time
from typing import Any, Callable, Dict, Optional, Tuple

from ..exceptions import ActionFailedError

# Parameters copied from a call into its recorded task, so the report shows the
# context of each step (and ``TaskExecutor._task_target`` can label it).
RECORDED_KWARGS = (
    "text",
    "image",
    "anchor_image",
    "target_image",
    "command",
    "region",
    "target_region",
    "x",
    "y",
    "confidence",
    "confidence_threshold",
    "mouse_button",
    "occurrence",
    "specific",
    "max_distance",
    "filter_type",
    "window",
    "target",
    "wait_window",
    "app",
    "file",
    "query",
    "amount",
    "start_x",
    "start_y",
    "end_x",
    "end_y",
    # native_* selectors
    "pid",
    "title",
    "auto_id",
    "control_type",
    "found_index",
    "state",
    "timeout",
    "start",
    "end",
    "at",
)

# Shown instead of what ``type_text(..., secret=True)`` typed.
MASK = "••••••"

# A check decides a call's outcome from its return value:
# ``check(result, params) -> (ok, error_or_None, output_or_None)``.
Check = Callable[[Any, Dict[str, Any]], Tuple[bool, Optional[str], Optional[str]]]


def records_step(type_field: str, check: Check | None = None):
    """Decorator: record the wrapped bot method as a step while a session is open.

    ``type_field`` is the step type the report shows (``"text"``, ``"image"``,
    ``"type_text"``...). ``check`` turns the return value into the outcome;
    by default a ``bool`` result is the outcome and anything else is a success.
    An exception is always a failed step (recorded, then re-raised).
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # Only the outermost action records: a recorded method that calls
            # another one (``enter()`` -> ``keyboard_command``) is ONE step.
            if not _recording(self):
                return method(self, *args, **kwargs)
            params = _bound_params(method, (self, *args), kwargs)
            params.pop("self", None)
            return _run_recorded(
                self, type_field, check, params, lambda: method(self, *args, **kwargs)
            )

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Native actions (``native_click``, ``native_set_text``...) are free functions,
# not bot methods: they record through the bot of the open task session --
# ``rpa()`` opens one -- and show the same highlight its clicks do.
# ---------------------------------------------------------------------------
_active_bot: Any = None


def set_active_bot(bot: Any) -> None:
    """Make ``bot`` the one native actions record through (``None`` clears)."""
    global _active_bot
    _active_bot = bot


def clear_active_bot(bot: Any) -> None:
    """Clear the active bot, if it is still ``bot`` (another may have taken over)."""
    global _active_bot
    if _active_bot is bot:
        _active_bot = None


def active_bot() -> Any:
    """The bot of the open task session, or ``None``."""
    return _active_bot


def records_native(type_field: str, check: Check | None = None):
    """Decorator for the ``native_*`` functions: inside a task session (``rpa()``)
    each call is a step of the report -- duration, OK/FAILED + reason, a screenshot
    with the control boxed -- and, with ``stop_on_failure``, a ``False`` / ``None``
    result stops the run. With no session open the function runs as before."""

    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            bot = _active_bot
            if bot is None or not _recording(bot):
                return function(*args, **kwargs)
            params = _bound_params(function, args, kwargs, defaults=True)
            return _run_recorded(
                bot, type_field, check or _native_check, params,
                lambda: function(*args, **kwargs),
            )

        return wrapper

    return decorator


def native_target(box: tuple, *, highlight: bool = True) -> None:
    """Called by a ``native_*`` function with the ``(x, y, w, h)`` of the control it
    is about to act on: the active bot boxes it on the step screenshot and, when its
    config has ``show_overlay`` on, highlights it on screen with the bot's
    ``overlay_color`` / ``overlay_width`` / ``overlay_duration``."""
    bot = _active_bot
    if bot is None or not getattr(bot, "task_session_active", False):
        return
    executor = getattr(bot, "executor", None)
    if executor is None:
        return
    executor.last_action_location = box
    if highlight and bot.config.get("show_overlay", True):
        try:
            executor._highlight(box)
        except Exception:  # pragma: no cover - the highlight is only visual
            pass


def _recording(bot: Any) -> bool:
    """A step is recorded only inside a task session and not nested in another."""
    return bool(getattr(bot, "task_session_active", False)) and not getattr(
        bot, "_step_depth", 0
    )


def _run_recorded(bot: Any, type_field: str, check, params: dict[str, Any], call):
    """Run ``call()`` as ONE recorded step of ``bot``'s session."""
    task = build_event_task(type_field, params)
    executor = getattr(bot, "executor", None)
    if executor is not None:
        # A stale box from the previous step must not be drawn on this
        # step's screenshot (a failed find has no box of its own).
        executor.last_action_location = None
    # ...nor left ON SCREEN: the previous step's highlight goes as soon as the bot
    # moves on, so a fast run never stacks boxes in the next steps' screenshots.
    _clear_action_highlight()

    started = time.monotonic()
    bot._step_depth = 1
    try:
        result = call()
    except Exception as exc:
        bot._step_depth = 0
        bot._emit_direct_call_event(
            task, success=False, started_at=started, error=exception_text(exc)
        )
        mark_recorded(exc)
        raise
    finally:
        bot._step_depth = 0

    ok, error, output = (check or _default_check)(result, params)
    if not ok and not error:
        error = describe_failure(task)
    bot._emit_direct_call_event(
        task, success=ok, started_at=started, error=error, output=output
    )
    if not ok and getattr(bot, "stop_on_failure", False):
        failure = ActionFailedError(
            error or f"{type_field} failed",
            action=type_field,
            target=str(task.get("text") or task.get("image") or task.get("auto_id") or ""),
        )
        mark_recorded(failure)
        raise failure
    return result


def _clear_action_highlight() -> None:
    """Close the on-screen highlight of the previous action (best-effort)."""
    try:
        from .overlay_win32 import clear_click_through_overlays

        clear_click_through_overlays()
    except Exception:  # pragma: no cover - the highlight is only visual
        pass


def _default_check(result: Any, params: dict[str, Any]):
    if isinstance(result, bool):
        return result, None, None
    return True, None, None


def _native_check(result: Any, params: dict[str, Any]):
    """``native_*`` report failure with ``False`` (click/set/wait) or ``None`` (get)."""
    if result is False or result is None:
        from . import native_rpa  # lazy: native_rpa imports this module

        if not native_rpa._ensure_pywinauto():
            return (
                False,
                "pywinauto is not installed -- native actions need it: "
                "pip install \"visus-desktop[native]\"",
                None,
            )
        return False, None, None
    if isinstance(result, str):
        return True, None, short_output(result)
    return True, None, None


def _bound_params(function, args, kwargs, *, defaults: bool = False) -> dict[str, Any]:
    """The call's arguments by parameter name (with ``defaults``, unset ones too)."""
    try:
        bound = inspect.signature(function).bind(*args, **kwargs)
    except TypeError:
        return dict(kwargs)
    if defaults:
        bound.apply_defaults()
    return dict(bound.arguments)


def build_event_task(type_field: str, params: dict[str, Any]) -> dict[str, Any]:
    """The task dict a recorded call is reported as (``TaskExecutor`` shape).

    ``click_text("Login")`` -> ``{"type": "text", "text": "Login"}``;
    ``click_at((10, 20, 5, 5))`` -> ``{"type": "click", "x": 10, "y": 20, ...}``.
    A ``secret=True`` call keeps its value out of the report.
    """
    task: dict[str, Any] = {"type": type_field}
    if "image_path" in params:
        task["image"] = params["image_path"]
    location = params.get("location")
    if type_field == "click" and isinstance(location, (tuple, list)) and len(location) >= 2:
        task["x"], task["y"] = location[0], location[1]
        task["region"] = list(location)
    for key in RECORDED_KWARGS:
        if key in params and key not in task:
            task[key] = params[key]
    if params.get("secret"):
        for key in ("text", "command"):
            if key in task:
                task[key] = MASK
    return task


def describe_failure(task: dict[str, Any]) -> str:
    """A 'what went wrong and where' message for an action that returned False."""
    ttype = task.get("type")
    region = task.get("region") or task.get("target_region")
    where = f" in region {list(region)}" if region else " on the screen"
    window = task.get("window")
    if ttype == "text":
        return (
            f"Text '{task.get('text')}' was not found{where} "
            "(or the click on it failed) -- see the step logs"
        )
    if ttype == "image":
        image = os.path.basename(str(task.get("image", "")))
        conf = task.get("confidence", 0.9)
        return (
            f"Image '{image}' was not found{where} at confidence {conf} "
            "(or the click on it failed) -- see the step logs"
        )
    if ttype == "relative_image":
        target = os.path.basename(str(task.get("target_image", "")))
        anchor = os.path.basename(str(task.get("anchor_image", "")))
        return (
            f"Image '{target}' was not found within "
            f"{task.get('max_distance', 200)}px of '{anchor}'"
        )
    if ttype in ("type_text", "keyboard_command") and window:
        return f"Window '{window}' is not the window in front -- nothing was sent"
    if ttype == "type_text":
        return "Typing failed -- see the step logs"
    if ttype == "keyboard_command":
        return f"Keyboard command '{task.get('command')}' failed -- see the step logs"
    if ttype == "click":
        return f"Click at ({task.get('x')}, {task.get('y')}) failed -- see the step logs"
    if str(ttype).startswith("native_"):
        control = native_control_label(task)
        timeout = task.get("timeout")
        within = f" within {timeout}s" if timeout is not None else ""
        if ttype == "native_wait":
            return f"{control} did not become '{task.get('state', 'exists')}'{within}"
        if ttype == "native_click":
            return f"{control} was not found{within} (or it did not take the click)"
        if ttype == "native_set_text":
            return f"{control} was not found{within} (or it did not take the text)"
        return f"{control} was not found{within}"
    return f"{ttype} failed -- see the step logs"


def native_control_label(task: dict[str, Any]) -> str:
    """``"num8Button in 'Calculadora'"`` -- the control a ``native_*`` step aimed at."""
    what = task.get("auto_id") or task.get("title") or task.get("control_type") or "control"
    if task.get("window"):
        return f"{what} in '{task['window']}'"
    if task.get("pid"):
        return f"{what} in pid {task['pid']}"
    return str(what)


def exception_text(exc: BaseException) -> str:
    """``"TypeName: message"`` (just the type name when the message is empty)."""
    message = str(exc).strip()
    name = type(exc).__name__
    return f"{name}: {message}" if message else name


def mark_recorded(exc: BaseException) -> None:
    """Flag ``exc`` as already in the report (``rpa()`` won't add it twice)."""
    try:
        exc._visus_recorded = True  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - exotic exceptions with __slots__
        pass


def was_recorded(exc: BaseException) -> bool:
    """True when ``exc`` came out of a step that is already in the report."""
    return bool(getattr(exc, "_visus_recorded", False))


def short_output(value: Any, limit: int = 2000) -> str | None:
    """A step's result as report text (``None`` when there is nothing to show)."""
    if value is None or value == [] or value == "":
        return None
    if isinstance(value, (list, tuple)):
        parts = [str(v.get("text", v)) if isinstance(v, dict) else str(v) for v in value]
        text = " | ".join(parts)
    else:
        text = str(value)
    return text if len(text) <= limit else text[:limit] + "…"

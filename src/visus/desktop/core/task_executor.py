"""
Visus Desktop - Task Executor

This module manages the execution of automation tasks, including
text/image detection, clicks, typing, and navigation with backtracking.
"""

import json
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image

from ..exceptions import (
    CircuitBreakerTrippedError,
    TaskExecutionError,
    TextNotFoundError,  # noqa: F401  -- kept for back-compat re-export
)
from ..utils.config import BotVisionConfig
from .keyboard_commands import KeyboardCommander
from .ocr_engine import OCREngine
from .overlay import show_overlay
from .overlay_win32 import show_click_through_overlay
from .relative_image import RelativeImageDetector
from .screen import (
    capture_screen,
    invalidate_screen_cache,
    set_screen_cache_ms,
    set_screen_source,
)
from .virtual_mouse import VirtualMouse
from .wait_manager import WaitManager

logger = logging.getLogger(__name__)
# Dedicated logger for structured task events (Phase 1 / O2). Lives on its own
# name so users can attach a JSON sink (file, Loki, OpenTelemetry, …) without
# touching the human-readable ``visus.desktop`` logger.
task_event_logger = logging.getLogger("visus.desktop.task_events")


class TaskResult:
    """Class to store the execution result of a task."""

    def __init__(
        self,
        task_index: int,
        success: bool,
        task_name: str,
        location: Optional[Tuple] = None,
        error: Optional[str] = None,
    ):
        self.task_index = task_index
        self.success = success
        self.task_name = task_name
        self.location = location
        self.error = error
        self.attempts = 0
        # Path to a screenshot saved when the task failed (Phase 1 / O1).
        # Stays ``None`` for successful tasks or when the capture is disabled.
        self.failure_screenshot: Optional[str] = None
        # Wall-clock time the find/locate loop took for this task (Phase 2 / O4).
        # Excludes ``_perform_action`` (the click/typing happens after this
        # result is built). Zero for tasks created outside the executor.
        self.duration_ms: int = 0
        # Per-step screenshot path (config['screenshot_steps']=True). Captured
        # AFTER the action so it shows the result of the step. None otherwise.
        self.step_screenshot: Optional[str] = None


class TaskExecutor:
    """
    Automation task executor with support for OCR, image detection,
    and robust execution with backtracking.
    """

    def __init__(self, config: Optional[BotVisionConfig] = None, hybrid_finder=None):
        """
        Initializes the task executor.

        Args:
            config: Library configuration.
            hybrid_finder: Optional callable ``(name, region=None) -> box``
                used to resolve ``{"type": "hybrid", "name": ...}`` tasks.
                When unset, hybrid tasks fail with a clear error message
                (Phase 3 / T2).
        """
        self.config = config or BotVisionConfig()
        self._hybrid_finder = hybrid_finder
        self.ocr_engine = OCREngine(self.config)
        self.relative_detector = RelativeImageDetector()
        self.keyboard_commander = KeyboardCommander()
        self.virtual_mouse = VirtualMouse(self.config)
        self.wait_manager = WaitManager(self.config)

        # Default settings
        self.default_confidence = 0.9
        self.default_margin = 50
        self.max_attempts = 4

        # Internal state
        self.task_failures = {}
        self.current_task_index = 0
        self.last_extracted_text = None  # Stores the last extracted text
        # ``current_run_id`` is rotated at the start of every ``execute_tasks``
        # call so failure screenshots from concurrent runs don't collide.
        self.current_run_id: Optional[str] = None
        # The last (x, y, w, h) box passed to ``_perform_action``. Lets
        # ``VisusBot._emit_direct_call_event`` annotate the step screenshot
        # for a direct ``click_text`` / ``click_image`` call even though
        # the public method only returns a bool.
        self.last_action_location: Optional[Tuple] = None

        # Test mode (Phase 2 / TS3): config['screen_source'] = 'disk:<path>'
        # makes capture_screen read PNGs from disk instead of grabbing the
        # live display. Applied here so any code path that goes through
        # capture_screen (find_image, screenshot-on-failure, the stable
        # screen helper, …) benefits without per-call plumbing.
        screen_source = self.config.get("screen_source")
        if screen_source:
            set_screen_source(screen_source)

        # Region screenshot cache (Phase 3 / E3). 0 = disabled.
        set_screen_cache_ms(int(self.config.get("screen_cache_ms") or 0))

        self._setup_pyautogui()

    @staticmethod
    def _task_type(task: Dict[str, Any]) -> str:
        """Classify a task by its ``type`` key or inferred text/image key."""
        explicit = task.get("type")
        if explicit:
            return str(explicit)
        if "text" in task:
            return "text"
        if "image" in task:
            return "image"
        return "unknown"

    def _task_target(self, task: Dict[str, Any]) -> str:
        """A short human label of WHAT a task acted on (for logs/reports)."""
        ttype = self._task_type(task)
        if ttype == "type_text":
            return str(task.get("text", ""))
        if ttype == "keyboard_command":
            return str(task.get("command", ""))
        if ttype == "click":
            return f"({task.get('x')}, {task.get('y')})"
        if ttype == "relative_image":
            anchor = os.path.basename(str(task.get("anchor_image", "")))
            target = os.path.basename(str(task.get("target_image", "")))
            return f"{target} near {anchor}"
        if ttype == "image":
            return os.path.basename(str(task.get("image", "")))
        if ttype == "extract_text":
            return f"region {task.get('region')}"
        return str(task.get("text") or task.get("name") or "")

    def _describe_miss(self, task: Dict[str, Any], attempts: int) -> str:
        """Build a detailed 'why it failed' message for a not-found task."""
        ttype = self._task_type(task)
        target = self._task_target(task)
        region = task.get("region") or task.get("target_region")
        where = f" in region {list(region)}" if region else " on the full screen"
        plural = "attempt" if attempts == 1 else "attempts"
        if ttype == "image":
            conf = task.get("confidence", self.default_confidence)
            return (
                f"Image '{target}' not found{where} at confidence {conf} "
                f"after {attempts} {plural}"
            )
        if ttype == "text":
            ctype = task.get("char_type", "both")
            return (
                f"OCR text '{target}' not found{where} (char_type={ctype}) "
                f"after {attempts} {plural}"
            )
        if ttype == "relative_image":
            dist = task.get("max_distance", 200)
            return (
                f"Relative target not found: {target} within {dist}px "
                f"after {attempts} {plural}"
            )
        return f"Target not found: {ttype} '{target}' after {attempts} {plural}"

    def _capture_step_screenshot(
        self, task_index: int, location: Optional[Tuple] = None
    ) -> Optional[str]:
        """Capture a screenshot for ANY step (config['screenshot_steps']).

        Mirrors ``_save_failure_screenshot`` but is taken after a successful
        action so the report can show every step, not just failures. When
        ``location`` is provided and ``config['screenshot_annotate']`` is
        on, the click target is drawn on the PNG so the saved image makes
        sense even after the on-screen overlay has vanished.
        """
        artifacts_dir = self.config.get("artifacts_dir", "./visus-artifacts")
        run_id = self.current_run_id or uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{run_id}__{task_index}__step__{timestamp}.png"
        try:
            os.makedirs(artifacts_dir, exist_ok=True)
            path = os.path.abspath(os.path.join(artifacts_dir, filename))
            image = capture_screen()
            if location and self.config.get("screenshot_annotate", True):
                self._annotate_location(image, location)
            image.save(path)
            return path
        except Exception as exc:  # pragma: no cover - logged for forensics
            logger.warning("Failed to save step screenshot: %s", exc)
            return None

    def _annotate_location(self, image, location) -> None:
        """Draw the click target on ``image`` in-place.

        Uses PIL so we don't have to depend on the on-screen overlay being
        present when the screenshot was captured. Matches the overlay's
        colour / width so step PNGs look consistent with what was shown
        on screen during the run.
        """
        try:
            from PIL import ImageDraw

            x, y, w, h = (int(v) for v in location[:4])
        except (TypeError, ValueError, ImportError):
            return
        color = str(self.config.get("overlay_color", "red"))
        width = max(1, int(self.config.get("overlay_width", 4)))
        draw = ImageDraw.Draw(image)
        draw.rectangle((x, y, x + w, y + h), outline=color, width=width)
        cx = x + w // 2
        cy = y + h // 2
        cross = max(2, min(10, w // 4 or 2, h // 4 or 2))
        draw.line((cx - cross, cy, cx + cross, cy), fill=color, width=width)
        draw.line((cx, cy - cross, cx, cy + cross), fill=color, width=width)

    def _emit_task_event(self, result: "TaskResult", task: Dict[str, Any]) -> None:
        """Emit a structured JSON event for ``result`` when ``log_format='json'``.

        Writes to the dedicated ``visus.desktop.task_events`` logger. The event
        carries enough telemetry to debug a run without the source: the task
        ``type`` / ``target`` / ``region`` searched, the ``location`` acted on,
        ``attempts``, ``duration_ms``, a detailed ``error`` on failure, and the
        per-step / failure ``screenshot`` paths.
        """
        if self.config.get("log_format", "text") != "json":
            return
        region = task.get("region") or task.get("target_region")
        loc = result.location
        if loc == "skip":
            loc = None

        def _ints(seq):
            # Coerce numpy int64 (from cv2 matches) to plain ints so the event
            # is JSON-serializable.
            try:
                return [int(v) for v in seq]
            except (TypeError, ValueError):
                return seq

        event = {
            "run_id": self.current_run_id,
            "task_id": result.task_index,
            "task_name": result.task_name,
            "type": self._task_type(task),
            "target": self._task_target(task),
            "region": _ints(region) if region else None,
            "success": result.success,
            "attempts": result.attempts,
            "duration_ms": result.duration_ms,
            "location": _ints(loc) if isinstance(loc, (list, tuple)) else loc,
            "error": result.error,
            "screenshot": result.step_screenshot,
            "failure_screenshot": result.failure_screenshot,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        task_event_logger.info(json.dumps(event))

    # ------------------------------------------------------------------
    # Checkpoint / resume (Phase 2 / R3)
    # ------------------------------------------------------------------

    def _checkpoint_path(self) -> str:
        artifacts_dir = self.config.get("artifacts_dir", "./visus-artifacts")
        return os.path.abspath(os.path.join(artifacts_dir, "checkpoint.json"))

    @staticmethod
    def _tasks_hash(tasks: List[Dict[str, Any]]) -> str:
        """Stable identifier for a task list, used to invalidate checkpoints."""
        import hashlib

        canonical = json.dumps(tasks, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def _read_checkpoint(self, tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Return the checkpoint dict if it exists and matches ``tasks``."""
        path = self._checkpoint_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return None
        if data.get("tasks_hash") != self._tasks_hash(tasks):
            return None
        return data

    def _write_checkpoint(
        self, tasks: List[Dict[str, Any]], completed_indices: List[int]
    ) -> None:
        path = self._checkpoint_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "tasks_hash": self._tasks_hash(tasks),
            "completed_indices": sorted(set(completed_indices)),
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except OSError as exc:  # pragma: no cover - logged for forensics
            logger.warning("Failed to write checkpoint: %s", exc)

    def _clear_checkpoint(self) -> None:
        path = self._checkpoint_path()
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:  # pragma: no cover
            pass

    def _save_failure_screenshot(
        self, task_index: int, location: Optional[Tuple] = None
    ) -> Optional[str]:
        """Capture the current screen and save it under ``artifacts_dir``.

        Called by ``_execute_single_task`` when a task ends unsuccessfully.
        Returns the absolute path of the PNG, or ``None`` when the feature is
        disabled or capture fails (capture failures are swallowed so they
        never mask the original task failure). When ``location`` is given
        (e.g. a failed click whose target was located but the click itself
        broke), the target is drawn on the saved PNG.
        """
        if not self.config.get("screenshot_on_failure", True):
            return None

        artifacts_dir = self.config.get("artifacts_dir", "./visus-artifacts")
        run_id = self.current_run_id or uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{run_id}__{task_index}__{timestamp}.png"

        try:
            os.makedirs(artifacts_dir, exist_ok=True)
            path = os.path.abspath(os.path.join(artifacts_dir, filename))
            image = capture_screen()
            if location and self.config.get("screenshot_annotate", True):
                self._annotate_location(image, location)
            image.save(path)
            return path
        except Exception as exc:  # pragma: no cover - logged for forensics
            logger.warning("Failed to save failure screenshot: %s", exc)
            return None

    def _setup_pyautogui(self) -> None:
        """Configures PyAutoGUI with the appropriate settings."""
        try:
            import pyautogui

            # Safety and performance settings
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        except ImportError as e:
            raise TaskExecutionError("PyAutoGUI is not installed") from e

    def _release_held_inputs(self) -> None:
        """Defensively release any held mouse buttons (Phase 1 / R5).

        ``pyautogui`` does not track which buttons are pressed, so on a
        user-initiated abort (Ctrl+C) we release ``left``, ``middle`` and
        ``right`` unconditionally. The cost is three syscalls; the benefit
        is no stuck buttons after an interrupted ``drag`` / ``mouse_down``.
        Errors here are swallowed so they never mask the user's original
        ``KeyboardInterrupt``.
        """
        try:
            import pyautogui
        except ImportError:  # pragma: no cover - pyautogui is a hard dep
            return
        for button in ("left", "middle", "right"):
            try:
                pyautogui.mouseUp(button=button)
            except Exception as exc:  # pragma: no cover - logged for forensics
                logger.debug("mouseUp(%s) during cleanup failed: %s", button, exc)

    def execute_tasks(
        self,
        tasks: List[Dict[str, Any]],
        resume: bool = False,
    ) -> List[TaskResult]:
        """
        Executes a list of tasks sequentially.
        Implements backtracking correctly: goes back to the previous task and then returns to the one that failed.

        Args:
            tasks (list): List of dictionaries with task configurations

        Returns:
            list: List of TaskResult with the results of each task

        Raises:
            TaskExecutionError: If there is a critical error during execution
        """
        if not tasks:
            logger.warning("Task list is empty")
            return []

        # Rotate the run identifier so failure artifacts from this invocation
        # are namespaced separately from any previous run.
        self.current_run_id = uuid.uuid4().hex[:8]

        logger.info(f"Starting execution of {len(tasks)} tasks")

        # Resume-from-checkpoint (Phase 2 / R3): when ``resume=True`` and a
        # matching checkpoint exists, pre-fill ``results`` for the already-
        # completed task indices and start from the first incomplete one.
        completed_indices: List[int] = []
        if resume:
            checkpoint = self._read_checkpoint(tasks)
            if checkpoint is not None:
                completed_indices = list(checkpoint.get("completed_indices", []))

        results: List[TaskResult] = []
        for idx in range(len(tasks)):
            if idx in completed_indices:
                placeholder = TaskResult(
                    idx, True, "(resumed - previously completed)"
                )
                placeholder.attempts = 0
                results.append(placeholder)
            else:
                break

        i = len(results)
        backtrack_stack: List[int] = []  # Stack to track backtracks

        try:
            final = self._run_task_loop(
                tasks, results, i, backtrack_stack, completed_indices
            )
        except KeyboardInterrupt:
            logger.info("Interrupted by SIGINT/KeyboardInterrupt; cleaning up")
            self._release_held_inputs()
            raise

        # Clean up the checkpoint only when every task in the list succeeded;
        # otherwise the checkpoint stays so a follow-up ``resume=True`` call
        # can pick up where this one left off.
        if all(r.success for r in final):
            self._clear_checkpoint()
        return final

    def _run_task_loop(
        self,
        tasks: List[Dict[str, Any]],
        results: List["TaskResult"],
        i: int,
        backtrack_stack: List[int],
        completed_indices: Optional[List[int]] = None,
    ) -> List["TaskResult"]:
        """Inner driver for :meth:`execute_tasks` (extracted for cleanup wrap)."""
        breaker_threshold = int(self.config.get("breaker_threshold") or 0)
        consecutive_failures = 0
        completed = set(completed_indices or [])

        while i < len(tasks):
            task = tasks[i]
            task_result = self._execute_single_task(task, i, len(tasks))

            # Add the result only if it is not a re-execution
            if len(results) <= i:
                results.append(task_result)
            else:
                results[i] = task_result  # Update existing result

            if task_result.success:
                logger.info(
                    f"✓ Task {i + 1}/{len(tasks)}: '{task_result.task_name}' completed successfully"
                )
                consecutive_failures = 0
                completed.add(i)
                self._write_checkpoint(tasks, sorted(completed))

                # Check whether there are pending backtracks on the stack
                if backtrack_stack:
                    # Pop the item from the stack and return to the original task that failed
                    original_failed_task = backtrack_stack.pop()
                    logger.info(
                        f"🔄 Returning to task {original_failed_task + 1} which originally failed after backtrack"
                    )
                    i = original_failed_task
                    # Reset the failure attempts for the original task
                    if i in self.task_failures:
                        self.task_failures[i] = 0
                else:
                    # Normal behavior: advance to the next task
                    i += 1

                # If it was not a skip, perform the action
                if task_result.location != "skip":
                    self._perform_action(task, task_result.location)
            else:
                # Task failed, check the circuit breaker before deciding
                # what to do with backtracking / advancement.
                consecutive_failures += 1
                if breaker_threshold > 0 and consecutive_failures >= breaker_threshold:
                    logger.error(
                        "Circuit breaker tripped after %s consecutive failures "
                        "(threshold=%s); aborting execute_tasks.",
                        consecutive_failures,
                        breaker_threshold,
                    )
                    raise CircuitBreakerTrippedError(
                        threshold=breaker_threshold,
                        consecutive_failures=consecutive_failures,
                    )
                backtrack = task.get("backtrack", False)

                if backtrack and i > 0:
                    # Manage backtracking
                    self.task_failures.setdefault(i, 0)
                    self.task_failures[i] += 1

                    if self.task_failures[i] <= 2:  # Limit backtrack attempts
                        # Add the current task to the backtrack stack (to return later)
                        if i not in backtrack_stack:  # Avoid duplicates
                            backtrack_stack.append(i)
                            logger.info(
                                f"📌 Task {i + 1} added to the backtrack stack for later re-execution"
                            )

                        prev_task_name = tasks[i - 1].get(
                            "text", tasks[i - 1].get("image", f"Task {i}")
                        )
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks)}: '{task_result.task_name}' failed. "
                            f"BACKTRACKING to task {i}/{len(tasks)}: '{prev_task_name}'"
                        )
                        i -= 1  # Go back to the previous task
                    else:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks)}: '{task_result.task_name}' failed "
                            f"after multiple backtracking attempts. Advancing."
                        )
                        # Remove from the stack if it is there
                        if i in backtrack_stack:
                            backtrack_stack.remove(i)
                        i += 1
                else:
                    # No backtrack or first task
                    if backtrack:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks)}: '{task_result.task_name}' failed "
                            f"but it is the first task. Advancing."
                        )
                    else:
                        logger.info(
                            f"✗ Task {i + 1}/{len(tasks)}: '{task_result.task_name}' failed "
                            f"and has 'backtrack': False. Advancing."
                        )
                    i += 1

            # Per-step screenshot (success path) + the structured event, both
            # emitted AFTER the action so a step screenshot reflects its result.
            # (Failed tasks already captured a failure_screenshot.)
            if task_result.success and self.config.get("screenshot_steps"):
                task_result.step_screenshot = self._capture_step_screenshot(
                    task_result.task_index,
                    location=task_result.location,
                )
            self._emit_task_event(task_result, task)

        successful_tasks = sum(1 for r in results if r.success)
        logger.info(
            f"Execution complete: {successful_tasks}/{len(results)} tasks successful"
        )

        return results

    def _execute_single_task(
        self, task: Dict[str, Any], task_index: int, total_tasks: int
    ) -> TaskResult:
        """
        Executes a single task.

        Args:
            task (dict): Task configuration
            task_index (int): Task index
            total_tasks (int): Total number of tasks

        Returns:
            TaskResult: Execution result
        """
        self.current_task_index = task_index

        # Task name for logs
        if task.get("type") == "relative_image":
            anchor_name = os.path.basename(task.get("anchor_image", "unknown"))
            target_name = os.path.basename(task.get("target_image", "unknown"))
            task_name = f"Relative: {target_name} near {anchor_name}"
        else:
            task_name = task.get("text", task.get("image", f"Task {task_index + 1}"))

        logger.info(f"Starting task {task_index + 1}/{total_tasks}: {task_name}")

        start_monotonic = time.monotonic()
        location = None
        attempts = 0
        last_error = None

        # Try to execute the task with multiple attempts
        while attempts < self.max_attempts and location is None:
            try:
                # Explicit action types take precedence over the text/image
                # heuristics, so e.g. a {"type": "type_text", "text": ...} task
                # is typed rather than being intercepted by the OCR branch.
                task_type = task.get("type")
                if task_type == "type_text":
                    location = self._execute_type_text(task, attempts)
                elif task_type == "keyboard_command":
                    location = self._execute_keyboard_command(task, attempts)
                elif task_type == "click":
                    location = self._find_coordinate_location(task, attempts)
                elif task_type == "relative_image":
                    location = self._find_relative_image_location(task, attempts)
                elif task_type == "extract_text":
                    location = self._execute_extract_text(task, attempts)
                elif task_type == "hybrid":
                    location = self._execute_hybrid(task, attempts)
                elif "text" in task:
                    # Check whether it has wait parameters
                    if task.get("wait_until_found") or task.get(
                        "wait_until_disappears"
                    ):
                        location = self._find_text_with_wait(task, attempts)
                    else:
                        location = self._find_text_location(task, attempts)
                elif "image" in task:
                    # Check whether it has wait parameters
                    if task.get("wait_until_found") or task.get(
                        "wait_until_disappears"
                    ):
                        location = self._find_image_with_wait(task, attempts)
                    else:
                        location = self._find_image_location(task, attempts)
                else:
                    last_error = (
                        "Task without a 'text', 'image' key or a valid type defined"
                    )
                    logger.warning(last_error)
                    break

            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Error in task {task_index + 1}, attempt {attempts + 1}: {e}"
                )

            # If not found, wait before the next attempt
            if not location:
                time.sleep(max(0.5, attempts * 0.5))

            attempts += 1

        # Create result
        if location:
            result = TaskResult(task_index, True, task_name, location)
        else:
            # Synthesize a detailed "why" when the find loop ended without a
            # specific exception (e.g. a plain not-found), so failures always
            # explain WHERE and WHY, not just "failed".
            if not last_error:
                last_error = self._describe_miss(task, attempts)
            result = TaskResult(task_index, False, task_name, error=last_error)
            result.failure_screenshot = self._save_failure_screenshot(task_index)

        result.attempts = attempts
        result.duration_ms = int((time.monotonic() - start_monotonic) * 1000)
        # NOTE: the structured event is emitted by the run loop AFTER the
        # action runs (so a per-step screenshot reflects the step's result).
        if not result.success:
            self._invoke_error_sink(result)
        return result

    def _invoke_error_sink(self, result: "TaskResult") -> None:
        """Call ``config['on_error']`` for a failed task (Phase 2 / O6).

        Errors raised by the sink itself are swallowed and logged so a
        buggy adapter (Sentry SDK, custom callback) never masks the
        original task failure.
        """
        sink = self.config.get("on_error")
        if sink is None:
            return
        try:
            sink(result)
        except Exception as exc:  # pragma: no cover - logged for forensics
            logger.warning("on_error hook raised %s: %s", type(exc).__name__, exc)

    def _find_text_location(
        self, task: Dict[str, Any], attempt: int
    ) -> Optional[Union[str, Tuple]]:
        """
        Finds the location of text using OCR.

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            tuple or str: Coordinates of the location or "skip"
        """
        target_text = task.get("text")
        filter_type = task.get("char_type", "both").lower()
        region = task.get("region")
        early_confidence_threshold = task.get("early_confidence", 75.0)

        # No region -> match the direct ``bot.find_text`` / ``bot.click_text``
        # behavior and fall back to the whole screen, instead of refusing
        # the task. Uses ``capture_screen`` (mss-backed, with the screen
        # cache) so this is faster than ``pyautogui.screenshot``.
        if not region:
            screen = capture_screen()
            region = (0, 0, screen.width, screen.height)
            region_img = screen
        else:
            region_img = self._capture_region(region)

        logger.debug(
            f"Searching for text '{target_text}' in region {region} "
            f"with filter '{filter_type}' (attempt {attempt + 1} of {self.max_attempts})"
        )

        logger.info(f"Area captured for OCR: {region[2]}x{region[3]} pixels")

        # Use the OCR engine to find text
        found_boxes, confidence_scores, early_match = self.ocr_engine.find_text(
            region_img, target_text, filter_type, early_confidence_threshold
        )

        if found_boxes:
            # Check whether all confidences are below the threshold
            if all(score < early_confidence_threshold for score in confidence_scores):
                logger.info(
                    f"All confidences for '{target_text}' are below "
                    f"{early_confidence_threshold}%. Assuming it has already been clicked."
                )
                return "skip"

            # Select the best result
            if early_match:
                selected_box_relative = found_boxes[0]
                logger.info(
                    f"Using early detection with confidence: {confidence_scores[0]:.2f}%"
                )
            elif task.get("best_confidence", True):
                best_index = confidence_scores.index(max(confidence_scores))
                selected_box_relative = found_boxes[best_index]
                logger.info(
                    f"Selected detection with the highest confidence: {max(confidence_scores):.2f}%"
                )
            else:
                # Legacy behavior with occurrence
                occurrence = task.get("occurrence", 1)
                if len(found_boxes) >= occurrence:
                    selected_box_relative = found_boxes[occurrence - 1]
                else:
                    selected_box_relative = found_boxes[-1]

            # Convert relative coordinates to absolute
            selected_box = (
                region[0] + selected_box_relative[0],
                region[1] + selected_box_relative[1],
                selected_box_relative[2],
                selected_box_relative[3],
            )

            logger.info(
                f"Text '{target_text}' found at position {selected_box_relative} "
                f"within region {region}"
            )
            return selected_box
        else:
            logger.warning(f"Text '{target_text}' not found in region {region}")
            return None

    def _find_image_location(
        self, task: Dict[str, Any], attempt: int
    ) -> Optional[Tuple]:
        """
        Finds the location of an image.

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            tuple: Coordinates of the location or None
        """
        image_path = task.get("image")
        confidence = task.get("confidence", self.default_confidence)
        region = task.get("region")
        specific = task.get("specific", True)

        if specific and region:
            logger.debug(
                f"Searching for {image_path} in region {region} "
                f"with confidence {confidence} (attempt {attempt + 1} of {self.max_attempts})"
            )
            location = self._locate_image_with_retry(
                image_path, region=region, confidence=confidence
            )
        else:
            logger.debug(
                f"Searching for {image_path} on the whole screen "
                f"with confidence {confidence} (attempt {attempt + 1} of {self.max_attempts})"
            )
            location = self._locate_image_with_retry(image_path, confidence=confidence)

        return location

    def _find_image_with_wait(
        self, task: Dict[str, Any], attempt: int
    ) -> Optional[Tuple]:
        """
        Finds an image with smart wait parameters.

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            tuple: Coordinates of the location or None
        """
        wait_until_found = task.get("wait_until_found", False)
        wait_until_disappears = task.get("wait_until_disappears", False)
        wait_timeout = task.get("wait_timeout") or self.config.get("wait_timeout", 30)

        image_path = task.get("image")

        # Create a search function for the wait manager
        def search_image():
            return self._find_image_location(task, attempt)

        # STEP 1: If wait_until_found=True, wait for it to appear first
        if wait_until_found:
            logger.info(
                f"Waiting for image '{image_path}' to appear (timeout: {wait_timeout}s)"
            )
            result = self.wait_manager.wait_until_found(
                search_image, timeout=wait_timeout, description=f"image '{image_path}'"
            )
            if not result:
                return None  # Timeout while waiting for it to appear
        else:
            # If there is no wait_until_found, search normally
            result = search_image()
            if not result:
                return None  # Image not found

        # STEP 2: If found (or already visible) and it has wait_until_disappears
        if wait_until_disappears:
            # If it is only find_image (no click), wait for it to disappear immediately
            if task.get("type") != "click_image" and not task.get("mouse_button"):
                logger.info(
                    f"Waiting for image '{image_path}' to disappear (timeout: {wait_timeout}s)"
                )
                disappeared = self.wait_manager.wait_until_disappears(
                    search_image,
                    timeout=wait_timeout,
                    description=f"image '{image_path}'",
                )
                return result if disappeared else None
            else:
                # For click_image, mark that it should wait for it to disappear AFTER the click
                task["_wait_after_click"] = True
                task["_wait_timeout"] = wait_timeout
                task["_image_path"] = image_path

        return result

    def _find_text_with_wait(
        self, task: Dict[str, Any], attempt: int
    ) -> Optional[Union[str, Tuple]]:
        """
        Finds text with smart wait parameters.

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            tuple or str: Coordinates of the location, "skip" or None
        """
        wait_until_found = task.get("wait_until_found", False)
        wait_until_disappears = task.get("wait_until_disappears", False)
        wait_timeout = task.get("wait_timeout") or self.config.get("wait_timeout", 30)

        target_text = task.get("text")

        # Create a search function for the wait manager
        def search_text():
            return self._find_text_location(task, attempt)

        # STEP 1: If wait_until_found=True, wait for it to appear first
        if wait_until_found:
            logger.info(
                f"Waiting for text '{target_text}' to appear (timeout: {wait_timeout}s)"
            )
            result = self.wait_manager.wait_until_found(
                search_text, timeout=wait_timeout, description=f"text '{target_text}'"
            )
            if not result:
                return None  # Timeout while waiting for it to appear
        else:
            # If there is no wait_until_found, search normally
            result = search_text()
            if not result:
                return None  # Text not found

        # STEP 2: If found (or already visible) and it has wait_until_disappears,
        # store the position to click and schedule the wait for after the click
        if wait_until_disappears:
            # Mark that it should wait for it to disappear AFTER the click
            task["_wait_after_click"] = True
            task["_wait_timeout"] = wait_timeout
            task["_target_text"] = target_text

        return result

    def _capture_region(self, region: Tuple[int, int, int, int]) -> Image.Image:
        """
        Captures a screenshot of a region.

        Args:
            region (tuple): (x, y, width, height)

        Returns:
            PIL.Image: Captured image

        Raises:
            TaskExecutionError: If the capture fails
        """
        try:
            import pyautogui

            region_img = pyautogui.screenshot(region=region)

            if not region_img or region_img.width <= 1 or region_img.height <= 1:
                raise TaskExecutionError(f"Failed to capture region {region}")

            return region_img

        except Exception as e:
            raise TaskExecutionError(f"Error capturing the screen: {e}") from e

    def _locate_image_with_retry(
        self,
        image_path: str,
        region: Optional[Tuple] = None,
        confidence: float = 0.9,
        max_attempts: int = 3,
        scales: Optional[List[float]] = None,
    ) -> Optional[Tuple]:
        """
        Locates an image with multiple attempts and scales.

        Args:
            image_path (str): Path to the image
            region (tuple, optional): Region to search in
            confidence (float): Confidence level
            max_attempts (int): Maximum number of attempts
            scales (list, optional): Scales to test

        Returns:
            tuple: Coordinates of the image or None
        """
        if scales is None:
            scales = [
                1.0,
                0.95,
                1.05,
                0.71,
                1.41,
            ]  # Original scale, ±5%, and wider variations

        try:
            for attempt in range(max_attempts):
                # Test all scales in parallel
                location = self._parallel_scale_search(
                    image_path, scales, region, confidence
                )
                if location:
                    return location

                # If not found, reduce confidence and try again with all scales
                adjusted_confidence = max(0.7, confidence - 0.05 * (attempt + 1))
                logger.debug(
                    f"Adjusting confidence to {adjusted_confidence} on attempt {attempt + 1}"
                )

                location = self._parallel_scale_search(
                    image_path, scales, region, adjusted_confidence
                )
                if location:
                    return location

                # Small pause only between main attempts (not between scales)
                if attempt < max_attempts - 1:
                    time.sleep(0.2)

            return None

        except Exception as e:
            logger.error(f"Error locating image: {e}")
            return None

    def _parallel_scale_search(
        self,
        image_path: str,
        scales: List[float],
        region: Optional[Tuple],
        confidence: float,
    ) -> Optional[Tuple]:
        """
        Tests all scales simultaneously using parallel threads.

        Args:
            image_path (str): Path to the image
            scales (list): List of scales to test
            region (tuple, optional): Search region
            confidence (float): Minimum confidence

        Returns:
            tuple: Coordinates of the first image found or None
        """

        def search_single_scale(scale: float) -> Optional[Tuple]:
            """Searches for the image at a specific scale."""
            try:
                if scale == 1.0:
                    # Use the original image
                    import pyautogui

                    if region:
                        return pyautogui.locateOnScreen(
                            image_path, region=region, confidence=confidence
                        )
                    else:
                        return pyautogui.locateOnScreen(
                            image_path, confidence=confidence
                        )
                else:
                    # Use the resized image
                    return self._try_scaled_image(image_path, scale, region, confidence)
            except Exception as e:
                logger.debug(f"Error searching for image with scale {scale}: {e}")
                return None

        # Run the search in parallel for all scales
        with ThreadPoolExecutor(max_workers=len(scales)) as executor:
            # Submit all tasks
            future_to_scale = {
                executor.submit(search_single_scale, scale): scale for scale in scales
            }

            # Process results as they complete
            for future in as_completed(future_to_scale):
                scale = future_to_scale[future]
                try:
                    result = future.result()
                    if result:
                        logger.debug(f"Image found with scale {scale}: {result}")
                        return result
                except Exception as e:
                    logger.debug(f"Error in the thread for scale {scale}: {e}")
                    continue

        return None

    def _try_scaled_image(
        self, image_path: str, scale: float, region: Optional[Tuple], confidence: float
    ) -> Optional[Tuple]:
        """
        Attempts to locate an image at a specific scale.

        Args:
            image_path (str): Path to the image
            scale (float): Scale to apply
            region (tuple, optional): Search region
            confidence (float): Confidence

        Returns:
            tuple: Location or None
        """
        try:
            import pyautogui
            from PIL import Image

            # Load and resize the image
            ref_img = Image.open(image_path)
            new_width = int(ref_img.width * scale)
            new_height = int(ref_img.height * scale)
            scaled_img = ref_img.resize((new_width, new_height))

            # Save temporarily
            temp_path = f"temp_scaled_{scale}_{os.getpid()}.png"
            scaled_img.save(temp_path)

            try:
                if region:
                    location = pyautogui.locateOnScreen(
                        temp_path, region=region, confidence=confidence
                    )
                else:
                    location = pyautogui.locateOnScreen(
                        temp_path, confidence=confidence
                    )

                return location

            finally:
                # Remove the temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.debug(f"Error testing scaled image: {e}")
            return None

    def _perform_action(self, task: Dict[str, Any], location: Tuple) -> None:
        """
        Performs the action (click, typing) at the found location.

        Args:
            task (dict): Task configuration
            location (tuple): Coordinates where to perform the action
        """
        # Any physical input invalidates the region cache because the
        # screen contents have just changed.
        invalidate_screen_cache()
        # Stash the click target so direct callers (VisusBot.click_text /
        # click_image, etc.) can later read it back via
        # ``self.last_action_location`` to annotate a screenshot, even
        # though their public signature only returns bool.
        self.last_action_location = location
        delay = task.get("delay", 0)

        # Single overlay toggle: per-task ``show_overlay`` wins, otherwise
        # the global ``config["show_overlay"]`` (default True).
        show_overlay_flag = task.get("show_overlay")
        if show_overlay_flag is None:
            show_overlay_flag = self.config.get("show_overlay", True)

        if show_overlay_flag:
            overlay_duration = self.config.get("overlay_duration", 1000)
            overlay_color = self.config.get("overlay_color", "red")
            overlay_width = self.config.get("overlay_width", 4)

            # Win32 layered click-through window: lets the click below
            # land normally on any host tech (native, Java, Electron,
            # browsers). Fire-and-forget — no pre-click sleep, no join.
            scheduled = show_click_through_overlay(
                location,
                color=overlay_color,
                width=overlay_width,
                duration_ms=overlay_duration,
            )
            if not scheduled:
                # Non-Windows fallback: the legacy Tk overlay. It intercepts
                # clicks, so accept that on platforms where we can't do
                # click-through cleanly.
                threading.Thread(
                    target=show_overlay,
                    args=(location,),
                    kwargs={
                        "duration": overlay_duration,
                        "color": overlay_color,
                        "width": overlay_width,
                    },
                    daemon=True,
                ).start()

        # Perform the click
        self._perform_click(task, location)

        # Process text commands (only if not executed before)
        if (
            "sendtext" in task
            and task["sendtext"]
            and not task.get("_sendtext_executed", False)
        ):
            self._process_sendtext(task["sendtext"])
            task["_sendtext_executed"] = True  # Mark as executed to avoid duplication

        # STEP 3: If it should wait for it to disappear AFTER the click
        wait_until_disappears = task.get("wait_until_disappears", False)
        if wait_until_disappears or task.get("_wait_after_click", False):
            wait_timeout = task.get("wait_timeout") or task.get("_wait_timeout", 30)
            image_path = task.get("image") or task.get("_image_path")
            target_text = task.get("text") or task.get("_target_text")

            if image_path:
                logger.info(
                    f"Starting disappearance check for image '{image_path}' (timeout: {wait_timeout}s)"
                )

                # Create a search function to check whether it disappeared
                def search_image_after_click():
                    try:
                        # Use a copy of the task to avoid side effects
                        search_task = task.copy()
                        # Remove wait parameters for a direct search
                        search_task.pop("wait_until_found", None)
                        search_task.pop("wait_until_disappears", None)
                        search_task.pop("_wait_after_click", None)

                        # Debug: show search parameters
                        region_info = (
                            f"region {search_task.get('region')}"
                            if search_task.get("region")
                            else "whole screen"
                        )
                        confidence = search_task.get("confidence", 0.9)
                        specific = search_task.get("specific", True)
                        logger.debug(
                            f"Checking disappearance: {region_info}, confidence={confidence}, specific={specific}"
                        )

                        result = self._find_image_location(search_task, 0)

                        # Debug: search result
                        if result:
                            logger.debug(f"Image still found at: {result}")
                        else:
                            logger.debug("Image not found (disappeared)")

                        return result
                    except Exception as e:
                        logger.debug(
                            f"Error searching for image to check disappearance: {e}"
                        )
                        return None

                disappeared = self.wait_manager.wait_until_disappears(
                    search_image_after_click,
                    timeout=wait_timeout,
                    description=f"image '{image_path}'",
                )

                if disappeared:
                    logger.info(
                        f"Image '{image_path}' disappeared successfully - continuing RPA"
                    )
                else:
                    logger.warning(
                        f"Image '{image_path}' still visible after timeout - continuing RPA anyway"
                    )
            elif target_text:
                logger.info(
                    f"Starting disappearance check for text '{target_text}' (timeout: {wait_timeout}s)"
                )

                # Create a search function to check whether it disappeared
                def search_text_after_click():
                    try:
                        # Use a copy of the task to avoid side effects
                        search_task = task.copy()
                        # Remove wait parameters for a direct search
                        search_task.pop("wait_until_found", None)
                        search_task.pop("wait_until_disappears", None)
                        search_task.pop("_wait_after_click", None)
                        result = self._find_text_location(search_task, 0)
                        return result
                    except Exception as e:
                        logger.debug(
                            f"Error searching for text to check disappearance: {e}"
                        )
                        return None

                disappeared = self.wait_manager.wait_until_disappears(
                    search_text_after_click,
                    timeout=wait_timeout,
                    description=f"text '{target_text}'",
                )

                if disappeared:
                    logger.info(
                        f"Text '{target_text}' disappeared successfully - continuing RPA"
                    )
                else:
                    logger.warning(
                        f"Text '{target_text}' still visible after timeout - continuing RPA anyway"
                    )

            # Remove temporary flags
            task.pop("_wait_after_click", None)
            task.pop("_wait_timeout", None)
            task.pop("_image_path", None)
            task.pop("_target_text", None)

        time.sleep(delay)

    def _perform_click(self, task: Dict[str, Any], location: Tuple) -> None:
        """
        Performs a click at the location or just moves the mouse.
        Supports a configurable virtual mouse.

        Args:
            task (dict): Task configuration
            location (tuple): Coordinates of the click/movement
        """
        try:
            import pyautogui

            # Compute the center point
            click_point = pyautogui.center(location)

            # Determine the mouse button type
            mouse_button = task.get(
                "mouse_button", self.config.get("default_mouse_button", "left")
            ).lower()

            # Normalize mouse_button for the virtual mouse
            if mouse_button == "double left":
                mouse_button = "double"

            # Use the virtual or physical mouse based on the configuration
            # For the virtual mouse, pass the location info to ensure the exact center
            success = self.virtual_mouse.click(
                x=click_point.x,
                y=click_point.y,
                button=mouse_button,
                location_info=location,  # Pass full info of the found region
            )

            if success:
                if mouse_button == "move_to":
                    logger.info(
                        f"Mouse moved to position ({click_point.x}, {click_point.y}) (move only)"
                    )
                elif mouse_button == "right":
                    logger.info(
                        f"Right click performed at position ({click_point.x}, {click_point.y})"
                    )
                elif mouse_button in ["double", "double left"]:
                    logger.info(
                        f"Double click performed at position ({click_point.x}, {click_point.y})"
                    )
                else:
                    logger.info(
                        f"Left click performed at position ({click_point.x}, {click_point.y})"
                    )
            else:
                raise TaskExecutionError("Failed to perform the mouse action")

        except Exception as e:
            logger.error(f"Error performing the mouse action: {e}")
            raise TaskExecutionError(f"Mouse action failed: {e}") from e

    def _process_sendtext(self, text_command: str) -> None:
        """
        Processes special text commands and types text.

        Args:
            text_command (str): Text command with possible special commands
        """
        try:
            import pyautogui
            import pyperclip

            logger.info(f"Processing sendtext: '{text_command}'")

            text_to_write = text_command

            # Process special commands
            while True:
                original_text = text_to_write
                lower_text = text_to_write.lower()

                if lower_text.startswith("{ctrl}a"):
                    logger.info("Executing: CTRL+A")
                    pyautogui.hotkey("ctrl", "a")
                    text_to_write = text_to_write[len("{ctrl}a") :]
                    time.sleep(0.1)
                elif lower_text.startswith("{del}"):
                    logger.info("Executing: DELETE")
                    pyautogui.press("delete")
                    text_to_write = text_to_write[len("{del}") :]
                    time.sleep(0.1)
                elif lower_text.startswith("{tab}"):
                    logger.info("Executing: TAB")
                    pyautogui.press("tab")
                    text_to_write = text_to_write[len("{tab}") :]
                    time.sleep(0.1)
                elif lower_text.startswith("{enter}"):
                    logger.info("Executing: ENTER")
                    pyautogui.press("enter")
                    text_to_write = text_to_write[len("{enter}") :]
                    time.sleep(0.1)
                else:
                    break  # No more special commands

                # Protection against infinite loop
                if text_to_write == original_text:
                    break

            # Type the remaining text using the clipboard for better compatibility
            if text_to_write:
                logger.info(f"Pasting text: '{text_to_write}'")
                pyperclip.copy(text_to_write)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error processing sendtext: {e}")
            raise TaskExecutionError(f"sendtext failed: {e}") from e

    def _find_relative_image_location(
        self, task: Dict[str, Any], attempt: int
    ) -> Optional[Tuple]:
        """
        Finds the location of a relative image (anchor + target).

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            tuple: Coordinates of the location or None
        """
        anchor_image = task.get("anchor_image")
        target_image = task.get("target_image")
        confidence = task.get("confidence", self.default_confidence)
        max_distance = task.get("max_distance", 200)
        target_region = (
            task.get("target_region") if task.get("specific", False) else None
        )

        if not anchor_image or not target_image:
            raise TaskExecutionError(
                "Relative image requires 'anchor_image' and 'target_image'"
            )

        region_info = (
            f", target_region={target_region}" if target_region else ", whole_screen"
        )
        logger.info(
            f"Searching for relative image: anchor='{anchor_image}', target='{target_image}', "
            f"confidence={confidence}, max_distance={max_distance}px{region_info} "
            f"(attempt {attempt + 1} of {self.max_attempts})"
        )

        try:
            location = self.relative_detector.locate_relative_image(
                anchor_image, target_image, confidence, max_distance, target_region
            )
            return location
        except Exception as e:
            logger.error(f"Error in relative image detection: {e}")
            return None

    def _find_coordinate_location(
        self, task: Dict[str, Any], attempt: int
    ) -> Optional[Tuple]:
        """
        Finds a location based on specific coordinates.

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            tuple: Coordinates of the location or None
        """
        x = task.get("x")
        y = task.get("y")

        if x is None or y is None:
            raise TaskExecutionError("Direct click requires 'x' and 'y' coordinates")

        logger.info(
            f"Performing click at coordinates ({x}, {y}) "
            f"(attempt {attempt + 1} of {self.max_attempts})"
        )

        # Create a small region at the specified position
        return (x, y, 1, 1)

    def _execute_type_text(self, task: Dict[str, Any], attempt: int) -> str:
        """
        Performs text typing.

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            str: "skip" to indicate that no click is needed
        """
        text = task.get("text", "")
        interval = task.get("interval", 0.05)

        logger.info(
            f"Typing text: '{text}' (attempt {attempt + 1} of {self.max_attempts})"
        )

        try:
            # Token-aware + clipboard-robust: expands {enter}/{tab}/{esc}/
            # {backspace}/{del}/{ctrl}a anywhere in the string and pastes
            # literal text so characters are never dropped under load.
            self.keyboard_commander.type_with_tokens(text, interval)
            return "skip"  # Mark to skip the click
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return None

    def _execute_keyboard_command(self, task: Dict[str, Any], attempt: int) -> str:
        """
        Executes a keyboard command.

        Args:
            task (dict): Task configuration
            attempt (int): Current attempt number

        Returns:
            str: "skip" to indicate that no click is needed
        """
        command = task.get("command", "")

        logger.info(
            f"Executing keyboard command: '{command}' "
            f"(attempt {attempt + 1} of {self.max_attempts})"
        )

        try:
            success = self.keyboard_commander.execute_command(command)
            if success:
                return "skip"  # Mark to skip the click
            else:
                return None
        except Exception as e:
            logger.error(f"Error executing keyboard command: {e}")
            return None

    def _execute_hybrid(self, task: Dict[str, Any], attempt: int) -> Optional[Tuple]:
        """Resolve a ``{"type": "hybrid", "name": ...}`` task via ``hybrid_find``.

        Returns the located ``(x, y, w, h)`` box or ``None`` so the
        executor's standard "no location -> failure" path engages.
        """
        if self._hybrid_finder is None:
            logger.warning(
                "Hybrid task requires a hybrid_finder; falling back to OCR."
            )
            return self._find_text_location(
                {**task, "text": task.get("name", "")}, attempt
            )
        name = task.get("name")
        region = task.get("region")
        try:
            return self._hybrid_finder(name, region=region)
        except Exception as exc:
            logger.debug("hybrid_finder raised %s: %s", type(exc).__name__, exc)
            return None

    def _execute_extract_text(self, task: Dict[str, Any], attempt: int) -> str:
        """
        Performs text extraction from a specific region.

        Args:
            task (dict): Task configuration with fields:
                - region (tuple, optional): Region to extract text from
                - filter_type (str): Filter type ("numbers", "letters", "both")
                - confidence_threshold (float): Minimum confidence threshold
                - return_full_data (bool): Whether to return full data
                - backtrack (bool): Whether to try multiple times
            attempt (int): Current attempt number

        Returns:
            str: "skip" to indicate that no click is needed
        """
        region = task.get("region")
        filter_type = task.get("filter_type", "both")
        confidence_threshold = task.get("confidence_threshold", 50.0)
        return_full_data = task.get("return_full_data", False)

        logger.info(
            f"Extracting text from region {region} with filter '{filter_type}' "
            f"(attempt {attempt + 1} of {self.max_attempts})"
        )

        try:
            if region is None:
                # If no region was specified, capture the whole screen
                import pyautogui

                screen = pyautogui.screenshot()
                region = (0, 0, screen.width, screen.height)
                region_img = screen
            else:
                region_img = self._capture_region(region)

            # Use the extract_all_text method of the OCR engine
            ocr_results = self.ocr_engine.extract_all_text(region_img, filter_type)

            # Filter by confidence - adjust the threshold based on the attempt
            adjusted_threshold = confidence_threshold - (
                attempt * 10.0
            )  # Reduce by 10% each attempt
            adjusted_threshold = max(30.0, adjusted_threshold)  # Minimum of 30%

            filtered_results = [
                result
                for result in ocr_results
                if result.confidence >= adjusted_threshold
            ]

            if return_full_data:
                # Prepare full data with absolute coordinates
                full_data = []
                for result in filtered_results:
                    absolute_box = (
                        (
                            region[0] + result.box[0],
                            region[1] + result.box[1],
                            result.box[2],
                            result.box[3],
                        )
                        if region != (0, 0, region_img.width, region_img.height)
                        else result.box
                    )

                    full_data.append(
                        {
                            "text": result.text,
                            "confidence": result.confidence,
                            "box": result.box,  # Coordinates relative to the region
                            "absolute_box": absolute_box,  # Absolute coordinates on the screen
                        }
                    )

                # Store the result for later retrieval
                self.last_extracted_text = full_data
                logger.info(
                    f"Text extracted with full data: {len(full_data)} elements found"
                )
            else:
                # Extract only the texts
                texts = [result.text for result in filtered_results]
                self.last_extracted_text = texts
                logger.info(f"Text extracted: {len(texts)} elements found - {texts}")

            return "skip"  # Mark to skip the click

        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return None


def summarize(results: List[TaskResult]) -> Dict[str, Any]:
    """Aggregate a list of ``TaskResult`` objects into a report dict.

    Returns a small dict suitable for logging, HTML reports, or JSON
    sinks. Keys are stable so downstream tooling can rely on them.

    Phase 2 / O4. Empty input returns a zeroed dict rather than raising
    so dashboards never need to special-case the no-run case.
    """
    total = len(results)
    if total == 0:
        return {
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "success_rate": 0.0,
            "total_duration_ms": 0,
            "mean_duration_ms": 0.0,
            "total_attempts": 0,
        }
    succeeded = sum(1 for r in results if r.success)
    total_duration = sum(getattr(r, "duration_ms", 0) for r in results)
    total_attempts = sum(getattr(r, "attempts", 0) for r in results)
    return {
        "total": total,
        "succeeded": succeeded,
        "failed": total - succeeded,
        "success_rate": succeeded / total,
        "total_duration_ms": total_duration,
        "mean_duration_ms": total_duration / total,
        "total_attempts": total_attempts,
    }


# Convenience functions
def execute_tasks(tasks, config: Optional[BotVisionConfig] = None) -> List[TaskResult]:
    """
    Convenience function to execute tasks.
    Supports both a simple list and a list of lists (multiple sets of tasks).

    Args:
        tasks: List of tasks or list of lists of tasks
        config (BotVisionConfig, optional): Configuration

    Returns:
        list: List of results (may be a list of lists if the input is a list of lists)
    """
    # Check whether it is a list of lists (multiple sets of tasks)
    if isinstance(tasks, list) and tasks:
        if isinstance(tasks[0], list):
            logger.info(
                f"Detected multiple sets of tasks ({len(tasks)} sets). Executing sequentially."
            )
            all_results = []

            for i, task_list in enumerate(tasks):
                if isinstance(task_list, list):
                    logger.info(
                        f"--- Starting task set {i + 1}/{len(tasks)} ({len(task_list)} tasks) ---"
                    )
                    executor = TaskExecutor(config)
                    results = executor.execute_tasks(task_list)
                    all_results.append(results)
                    logger.info(f"--- Finished task set {i + 1}/{len(tasks)} ---")
                else:
                    logger.warning(
                        f"Item {i} in the main list is not a list of tasks. Skipping."
                    )
                    all_results.append([])

            return all_results
        else:
            # Simple list of tasks
            logger.info("Detected a simple list of tasks. Executing.")
            executor = TaskExecutor(config)
            return executor.execute_tasks(tasks)
    elif isinstance(tasks, list) and not tasks:
        logger.info("The task list is empty. Nothing to execute.")
        return []
    else:
        logger.error(
            f"The imported tasks are not a list. Type: {type(tasks)}. Cannot execute."
        )
        return []


def click_images(tasks, default_confidence: float = 0.9, default_margin: int = 50):
    """
    Function for full compatibility with legacy code.
    Supports both a simple list and a list of lists (multiple sets of tasks).

    Args:
        tasks: List of tasks or list of lists of tasks
        default_confidence (float): Default confidence
        default_margin (int): Default margin

    Returns:
        list: List of results (may be a list of lists if the input is a list of lists)
    """
    config = BotVisionConfig()
    config.set("default_confidence", default_confidence)
    config.set("default_margin", default_margin)

    return execute_tasks(tasks, config)

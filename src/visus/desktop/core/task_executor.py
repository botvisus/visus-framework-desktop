"""
Visus Desktop - Task Executor

This module manages the execution of automation tasks, including
text/image detection, clicks, typing, and navigation with backtracking.
"""

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image

from ..exceptions import TaskExecutionError, TextNotFoundError
from ..utils.config import BotVisionConfig
from .keyboard_commands import KeyboardCommander
from .ocr_engine import OCREngine
from .overlay import show_overlay
from .relative_image import RelativeImageDetector
from .virtual_mouse import VirtualMouse
from .wait_manager import WaitManager

logger = logging.getLogger(__name__)


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


class TaskExecutor:
    """
    Automation task executor with support for OCR, image detection,
    and robust execution with backtracking.
    """

    def __init__(self, config: Optional[BotVisionConfig] = None):
        """
        Initializes the task executor.

        Args:
            config (BotVisionConfig, optional): Library configuration
        """
        self.config = config or BotVisionConfig()
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

        self._setup_pyautogui()

    def _setup_pyautogui(self) -> None:
        """Configures PyAutoGUI with the appropriate settings."""
        try:
            import pyautogui

            # Safety and performance settings
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
        except ImportError as e:
            raise TaskExecutionError("PyAutoGUI is not installed") from e

    def execute_tasks(self, tasks: List[Dict[str, Any]]) -> List[TaskResult]:
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

        logger.info(f"Starting execution of {len(tasks)} tasks")

        results = []
        i = 0
        backtrack_stack = []  # Stack to track backtracks

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
                # Task failed, check backtracking
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
            result = TaskResult(task_index, False, task_name, error=last_error)

        result.attempts = attempts
        return result

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

        # Validate region
        if not region:
            raise TextNotFoundError("No region defined for OCR")

        logger.debug(
            f"Searching for text '{target_text}' in region {region} "
            f"with filter '{filter_type}' (attempt {attempt + 1} of {self.max_attempts})"
        )

        # Capture a screenshot of the region
        region_img = self._capture_region(region)

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
        delay = task.get("delay", 0)
        show_overlay_enabled = task.get("show_overlay")

        # If not specified in the task, use the global configuration
        if show_overlay_enabled is None:
            show_overlay_enabled = self.config.get("show_overlay", True)

        # Show the visual overlay only if enabled
        if show_overlay_enabled:
            # Get overlay settings from the configuration
            overlay_duration = self.config.get("overlay_duration", 1000)
            overlay_color = self.config.get("overlay_color", "red")
            overlay_width = self.config.get("overlay_width", 4)

            overlay_thread = threading.Thread(
                target=show_overlay,
                args=(location,),
                kwargs={
                    "duration": overlay_duration,
                    "color": overlay_color,
                    "width": overlay_width,
                },
            )
            overlay_thread.start()

            # Small delay to display the overlay
            time.sleep(0.2)
        else:
            overlay_thread = None

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

        # Wait for the overlay to finish if it was created
        if overlay_thread:
            overlay_thread.join()

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
            self.keyboard_commander.type_text(text, interval)
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

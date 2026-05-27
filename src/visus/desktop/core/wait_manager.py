"""
Visus Desktop - Wait Manager

This module implements smart wait functionalities for images,
including wait_until_found and wait_until_disappears with a configurable timeout.
"""

import logging
import time
from typing import Any, Callable, Optional

from ..utils.config import BotVisionConfig

logger = logging.getLogger(__name__)


class WaitManager:
    """
    Manager for smart wait operations for images and texts.
    """

    def __init__(self, config: Optional[BotVisionConfig] = None):
        """
        Initializes the wait manager.

        Args:
            config (BotVisionConfig, optional): Library configuration
        """
        from ..utils.config import get_default_config

        self.config = config or get_default_config()

    def wait_until_found(
        self,
        search_function: Callable[[], Any],
        timeout: Optional[int] = None,
        check_interval: float = 0.5,
        description: str = "element",
    ) -> Any:
        """
        Waits until an element is found.

        Args:
            search_function (Callable): Search function that returns the element or None
            timeout (int, optional): Timeout in seconds. If None, uses the global configuration
            check_interval (float): Interval between checks in seconds
            description (str): Description of the element for logs

        Returns:
            Any: Result of the search function when found, or None on timeout

        Example:
            >>> def search_image():
            ...     return bot.find_image('button.png')
            >>>
            >>> result = wait_manager.wait_until_found(search_image, timeout=30)
        """
        timeout = timeout or self.config.get("wait_timeout", 30)
        start_time = time.time()

        logger.debug(f"Waiting for {description} to appear (timeout: {timeout}s)")

        while (time.time() - start_time) < timeout:
            try:
                result = search_function()
                if result:
                    elapsed = time.time() - start_time
                    logger.debug(f"{description} found after {elapsed:.1f}s")
                    return result

            except Exception as e:
                logger.debug(f"Error while searching for {description}: {e}")

            time.sleep(check_interval)

        elapsed = time.time() - start_time
        logger.debug(f"Timeout reached for {description} after {elapsed:.1f}s")
        return None

    def wait_until_disappears(
        self,
        search_function: Callable[[], Any],
        timeout: Optional[int] = None,
        check_interval: float = 0.1,
        description: str = "element",
    ) -> bool:
        """
        Waits until an element disappears.

        Args:
            search_function (Callable): Search function that returns the element or None
            timeout (int, optional): Timeout in seconds. If None, uses the global configuration
            check_interval (float): Interval between checks in seconds
            description (str): Description of the element for logs

        Returns:
            bool: True if the element disappeared, False on timeout

        Example:
            >>> def search_loading():
            ...     return bot.find_image('loading.png')
            >>>
            >>> disappeared = wait_manager.wait_until_disappears(search_loading, timeout=60)
        """
        timeout = timeout or self.config.get("wait_timeout", 30)
        start_time = time.time()
        check_count = 0

        logger.info(f"Waiting for {description} to disappear (timeout: {timeout}s)")

        while (time.time() - start_time) < timeout:
            check_count += 1
            try:
                result = search_function()
                if not result:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"SUCCESS: {description} disappeared after {elapsed:.1f}s (check #{check_count})"
                    )
                    return True
                else:
                    # Image is still visible - log only every 2 seconds to avoid clutter
                    elapsed = time.time() - start_time
                    if (
                        check_count == 1
                        or elapsed % 2.0 < check_interval
                        or elapsed > timeout - 1
                    ):
                        logger.info(
                            f"WAITING: {description} still visible after {elapsed:.1f}s (check #{check_count})"
                        )

            except Exception as e:
                logger.debug(f"Error while checking {description}: {e}")
                # If there is an error in the search, we consider that it disappeared
                elapsed = time.time() - start_time
                logger.info(
                    f"SUCCESS: {description} not found (disappeared) after {elapsed:.1f}s"
                )
                return True

            time.sleep(check_interval)

        elapsed = time.time() - start_time
        logger.warning(
            f"TIMEOUT: {description} still visible after {elapsed:.1f}s - timeout reached"
        )
        return False

    def wait_with_condition(
        self,
        condition_function: Callable[[], bool],
        timeout: Optional[int] = None,
        check_interval: float = 0.5,
        description: str = "condition",
    ) -> bool:
        """
        Waits until a specific condition is met.

        Args:
            condition_function (Callable): Function that returns True when the condition is met
            timeout (int, optional): Timeout in seconds. If None, uses the global configuration
            check_interval (float): Interval between checks in seconds
            description (str): Description of the condition for logs

        Returns:
            bool: True if the condition was met, False on timeout

        Example:
            >>> def check_window_active():
            ...     return bot.is_window_active('MyApp')
            >>>
            >>> success = wait_manager.wait_with_condition(check_window_active, timeout=10)
        """
        timeout = timeout or self.config.get("wait_timeout", 30)
        start_time = time.time()

        logger.debug(f"Waiting for {description} to be met (timeout: {timeout}s)")

        while (time.time() - start_time) < timeout:
            try:
                if condition_function():
                    elapsed = time.time() - start_time
                    logger.debug(f"{description} met after {elapsed:.1f}s")
                    return True

            except Exception as e:
                logger.debug(f"Error while checking {description}: {e}")

            time.sleep(check_interval)

        elapsed = time.time() - start_time
        logger.debug(f"Timeout reached for {description} after {elapsed:.1f}s")
        return False

    def create_image_search_function(
        self, image_path: str, **search_kwargs
    ) -> Callable[[], Any]:
        """
        Creates an image search function to use with the wait methods.

        Args:
            image_path (str): Path to the image
            **search_kwargs: Arguments for the image search function

        Returns:
            Callable: Function that performs the image search

        Example:
            >>> search_func = wait_manager.create_image_search_function(
            ...     'button.png', confidence=0.9, region=(100, 100, 200, 50)
            ... )
            >>> result = wait_manager.wait_until_found(search_func)
        """

        def search_image():
            # This function will be defined when integrated with TaskExecutor
            # For now, returns None as a placeholder
            return None

        return search_image

    def create_text_search_function(
        self, text: str, **search_kwargs
    ) -> Callable[[], Any]:
        """
        Creates a text search function to use with the wait methods.

        Args:
            text (str): Text to search for
            **search_kwargs: Arguments for the text search function

        Returns:
            Callable: Function that performs the text search

        Example:
            >>> search_func = wait_manager.create_text_search_function(
            ...     'Login', region=(50, 50, 300, 100)
            ... )
            >>> result = wait_manager.wait_until_found(search_func)
        """

        def search_text():
            # This function will be defined when integrated with TaskExecutor
            # For now, returns None as a placeholder
            return None

        return search_text

    def smart_retry(
        self,
        action_function: Callable[[], Any],
        success_condition: Callable[[Any], bool],
        max_attempts: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[int] = None,
        description: str = "operation",
    ) -> Any:
        """
        Executes an action with smart retry and a success condition.

        Args:
            action_function (Callable): Function that performs the action
            success_condition (Callable): Function that checks whether the action succeeded
            max_attempts (int): Maximum number of attempts
            retry_delay (float): Delay between attempts in seconds
            timeout (int, optional): Total timeout in seconds
            description (str): Description of the operation for logs

        Returns:
            Any: Result of the action if successful, None otherwise

        Example:
            >>> def click_button():
            ...     return bot.click_image('button.png')
            >>>
            >>> def check_success(result):
            ...     return result is not None
            >>>
            >>> result = wait_manager.smart_retry(click_button, check_success)
        """
        timeout = timeout or self.config.get("wait_timeout", 30)
        start_time = time.time()

        logger.debug(
            f"Starting smart retry for {description} (max: {max_attempts} attempts, timeout: {timeout}s)"
        )

        for attempt in range(1, max_attempts + 1):
            # Check timeout
            if (time.time() - start_time) >= timeout:
                logger.debug(f"Timeout reached during {description}")
                break

            try:
                logger.debug(f"Attempt {attempt}/{max_attempts} for {description}")
                result = action_function()

                if success_condition(result):
                    elapsed = time.time() - start_time
                    logger.debug(
                        f"{description} executed successfully on attempt {attempt} after {elapsed:.1f}s"
                    )
                    return result

            except Exception as e:
                logger.debug(f"Error on attempt {attempt} for {description}: {e}")

            # Delay between attempts (except on the last one)
            if attempt < max_attempts:
                time.sleep(retry_delay)

        elapsed = time.time() - start_time
        logger.debug(
            f"{description} failed after {max_attempts} attempts in {elapsed:.1f}s"
        )
        return None

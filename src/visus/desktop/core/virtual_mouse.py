"""

Visus Desktop - Virtual Mouse



This module implements virtual mouse functionality that allows

performing clicks without moving the physical mouse cursor.

"""

import logging
import platform
import time
from typing import Optional, Tuple

from ..utils.config import BotVisionConfig

logger = logging.getLogger(__name__)


class VirtualMouse:
    """

    Class for virtual mouse control that allows clicks

    without moving the physical mouse cursor.

    """

    def __init__(self, config: Optional[BotVisionConfig] = None):
        """

        Initializes the virtual mouse.



        Args:

            config (BotVisionConfig, optional): Library configuration

        """

        from ..utils.config import get_default_config

        self.config = config or get_default_config()

        self.system = platform.system().lower()

        self.original_cursor_pos = None
        # How the last click() went: "virtual" (window messages, cursor left
        # alone), "physical", or "virtual-refused" (strict mode: the virtual
        # click failed and the real mouse was deliberately NOT used).
        self.last_click: Optional[str] = None

        # Detect whether the virtual mouse is available on the system

        self.virtual_available = self._check_virtual_mouse_availability()

        if not self.virtual_available and self.config.get("use_virtual_mouse", False):
            logger.warning(
                "WARNING: use_virtual_mouse=True but the virtual mouse is not available on the system!"
            )

            logger.warning("FALLBACK: All clicks will use the physical mouse")

    def _check_virtual_mouse_availability(self) -> bool:
        """

        Checks whether the virtual mouse is available on the current system.



        Returns:

            bool: True if the virtual mouse is available

        """

        if self.system == "windows":
            try:
                import win32api  # noqa: F401  # availability probe
                import win32con  # noqa: F401  # availability probe
                import win32gui  # noqa: F401  # availability probe

                return True

            except ImportError:
                logger.debug(
                    "win32 modules not available. Windows virtual mouse unavailable."
                )

                return False

        elif self.system in ["linux", "darwin"]:
            # For Linux/macOS, it can be implemented using Xlib or other libraries

            # For now, returns False to use the fallback

            logger.debug(
                f"Virtual mouse not implemented for {self.system}. Using fallback."
            )

            return False

        return False

    def _resolve_client_coordinates(
        self,
        hwnd: int,
        logical_point: Tuple[int, int],
    ) -> Tuple[int, int, int, int]:
        """Convert a screen point to the target window's client coordinates.

        The incoming point and ScreenToClient share the same coordinate space
        (matching this process's DPI awareness), so NO manual DPI scaling is
        applied here: scaling the client offset misplaces the click on
        high-DPI / scaled displays (it was the cause of "clicks in the wrong
        position"). PostMessage expects plain client coordinates.
        """
        import win32gui

        screen_x = int(round(logical_point[0]))
        screen_y = int(round(logical_point[1]))

        try:
            client_x, client_y = win32gui.ScreenToClient(hwnd, (screen_x, screen_y))
            return int(client_x), int(client_y), screen_x, screen_y
        except Exception as inner:
            logger.debug(f"Failed to convert coordinates to client: {inner}")
            return screen_x, screen_y, screen_x, screen_y

    def save_cursor_position(self):
        """Saves the current cursor position."""

        try:
            import pyautogui

            self.original_cursor_pos = pyautogui.position()

            logger.debug(f"Cursor position saved: {self.original_cursor_pos}")

        except Exception as e:
            logger.debug(f"Error saving cursor position: {e}")

    def restore_cursor_position(self):
        """Restores the cursor to its original position."""

        if self.original_cursor_pos:
            try:
                import pyautogui

                pyautogui.moveTo(
                    self.original_cursor_pos.x, self.original_cursor_pos.y, duration=0
                )

                logger.debug(f"Cursor restored to: {self.original_cursor_pos}")

            except Exception as e:
                logger.debug(f"Error restoring cursor position: {e}")

    def _click_virtual_windows(self, x: int, y: int, button: str = "left") -> bool:
        """
        Performs a virtual click on Windows using the Win32 API.

        Args:
            x (int): X coordinate
            y (int): Y coordinate
            button (str): Mouse button ('left', 'right', 'double')

        Returns:
            bool: True if the click was performed successfully
        """
        try:
            import win32api
            import win32con
            import win32gui

            logical_point = (int(round(x)), int(round(y)))

            hwnd = win32gui.WindowFromPoint(logical_point)
            if not hwnd:
                return False

            client_x, client_y, screen_x, screen_y = self._resolve_client_coordinates(
                hwnd, logical_point
            )

            if client_x < 0 or client_y < 0:
                logger.debug(
                    f"Coordinates outside the client area: ({client_x}, {client_y})"
                )
                return False

            lParam = win32api.MAKELONG(int(client_x), int(client_y))

            # Ensure the window receives the updated position before the click
            win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lParam)

            if button == "left":
                win32gui.PostMessage(
                    hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam
                )
                time.sleep(0.05)
                win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            elif button == "right":
                win32gui.PostMessage(
                    hwnd, win32con.WM_RBUTTONDOWN, win32con.MK_RBUTTON, lParam
                )
                time.sleep(0.05)
                win32gui.PostMessage(hwnd, win32con.WM_RBUTTONUP, 0, lParam)
            elif button == "double":
                win32gui.PostMessage(
                    hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam
                )
                time.sleep(0.05)
                win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)
                time.sleep(0.05)
                win32gui.PostMessage(
                    hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam
                )
                time.sleep(0.05)
                win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lParam)

            window_title = win32gui.GetWindowText(hwnd)
            logger.debug(
                f"Virtual click performed on window: {window_title} - screen ({screen_x}, {screen_y}) -> client ({client_x}, {client_y})"
            )
            return True

        except Exception as e:
            logger.debug(f"Error in Windows virtual click: {e}")
            return False

    def _click_virtual_linux(self, x: int, y: int, button: str = "left") -> bool:
        """

        Performs a virtual click on Linux (placeholder for future implementation).



        Args:

            x (int): X coordinate

            y (int): Y coordinate

            button (str): Mouse button



        Returns:

            bool: True if the click was performed successfully

        """

        # TODO: Implement using Xlib or other Linux libraries

        logger.debug("Linux virtual click not implemented. Using fallback.")

        return False

    def _click_virtual_macos(self, x: int, y: int, button: str = "left") -> bool:
        """

        Performs a virtual click on macOS (placeholder for future implementation).



        Args:

            x (int): X coordinate

            y (int): Y coordinate

            button (str): Mouse button



        Returns:

            bool: True if the click was performed successfully

        """

        # TODO: Implement using Quartz or other macOS libraries

        logger.debug("macOS virtual click not implemented. Using fallback.")

        return False

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        use_virtual: Optional[bool] = None,
        location_info: Optional[tuple] = None,
    ) -> bool:
        """

        Performs a click using the virtual or physical mouse based on the configuration.



        Args:

            x (int): X coordinate

            y (int): Y coordinate

            button (str): Mouse button ('left', 'right', 'double', 'move_to')

            use_virtual (bool, optional): Force the use of the virtual mouse (overrides the configuration)

            location_info (tuple, optional): Info of the found region (x, y, width, height) to recompute the center



        Returns:

            bool: True if the click was performed successfully

        """

        # Determine whether the virtual mouse should be used

        should_use_virtual = (
            use_virtual
            if use_virtual is not None
            else self.config.get("use_virtual_mouse", False)
        )

        # If using the virtual mouse and there is location info, recompute the exact center

        if should_use_virtual and location_info:
            center_x = location_info[0] + (location_info[2] // 2)

            center_y = location_info[1] + (location_info[3] // 2)

            logger.info(
                f"VIRTUAL: Recomputing image center: original({x}, {y}) -> exact_center({center_x}, {center_y})"
            )

            x, y = center_x, center_y

        # Strict: the caller promised the person their mouse stays theirs, so a
        # failed virtual click must fail -- never quietly move the real cursor.
        strict = bool(should_use_virtual and self.config.get("virtual_mouse_strict", False))

        # If it is only a movement, no virtual click is needed

        if button == "move_to":
            if strict:
                logger.warning("REFUSED: move_to needs the real cursor (virtual_mouse_strict)")
                self.last_click = "virtual-refused"
                return False
            self.last_click = "physical"
            return self._move_to_physical(x, y)

        # Try the virtual mouse if available and configured

        if should_use_virtual and self.virtual_available:
            logger.info(f"Performing VIRTUAL click at ({x}, {y}) with button {button}")

            if self.system == "windows":
                success = self._click_virtual_windows(x, y, button)

                if success:
                    logger.info(
                        f"SUCCESS: Virtual click performed successfully at ({x}, {y})"
                    )
                    self.last_click = "virtual"
                    return True

                else:
                    logger.warning(
                        f"FAILURE: Virtual click failed at ({x}, {y}) - falling back to the physical mouse"
                    )

            elif self.system == "linux":
                success = self._click_virtual_linux(x, y, button)

                if success:
                    logger.info(
                        f"SUCCESS: Linux virtual click performed successfully at ({x}, {y})"
                    )
                    self.last_click = "virtual"
                    return True

                else:
                    logger.warning(
                        f"FAILURE: Linux virtual click failed at ({x}, {y}) - falling back to the physical mouse"
                    )

            elif self.system == "darwin":
                success = self._click_virtual_macos(x, y, button)

                if success:
                    logger.info(
                        f"SUCCESS: macOS virtual click performed successfully at ({x}, {y})"
                    )
                    self.last_click = "virtual"
                    return True

                else:
                    logger.warning(
                        f"FAILURE: macOS virtual click failed at ({x}, {y}) - falling back to the physical mouse"
                    )

        # Fallback to the physical mouse

        if strict:
            logger.warning(
                f"REFUSED: virtual click at ({x}, {y}) failed and virtual_mouse_strict "
                "forbids the physical fallback"
            )
            self.last_click = "virtual-refused"
            return False

        if should_use_virtual:
            logger.warning(
                f"FALLBACK: use_virtual_mouse=True but using the physical mouse at ({x}, {y})"
            )

        else:
            logger.info(f"Performing PHYSICAL click at ({x}, {y}) with button {button}")

        self.last_click = "physical"
        return self._click_physical(x, y, button)

    def _move_to_physical(self, x: int, y: int) -> bool:
        """

        Moves the cursor to the specified position.



        Args:

            x (int): X coordinate

            y (int): Y coordinate



        Returns:

            bool: True if the movement was performed successfully

        """

        try:
            import pyautogui

            pyautogui.moveTo(x, y, duration=self.config.get("movement_duration", 0.1))

            logger.debug(f"Cursor moved to ({x}, {y})")

            return True

        except Exception as e:
            logger.error(f"Error moving cursor: {e}")

            return False

    def _click_physical(self, x: int, y: int, button: str) -> bool:
        """

        Performs a click using the physical mouse with position preservation.



        Args:

            x (int): X coordinate

            y (int): Y coordinate

            button (str): Mouse button



        Returns:

            bool: True if the click was performed successfully

        """

        try:
            import pyautogui

            # Save the current position if the virtual mouse was being attempted

            should_preserve = self.config.get("use_virtual_mouse", False)

            if should_preserve:
                self.save_cursor_position()

            # Perform the physical click

            if button == "left":
                pyautogui.click(x, y, duration=self.config.get("click_duration", 0.1))

            elif button == "right":
                pyautogui.rightClick(x, y)

            elif button == "double":
                pyautogui.doubleClick(x, y)

            elif button == "move_to":
                pyautogui.moveTo(
                    x, y, duration=self.config.get("movement_duration", 0.1)
                )

            # Restore the position if the virtual mouse was being used

            if should_preserve:
                self.restore_cursor_position()

            logger.debug(f"Physical click performed at ({x}, {y}) with button {button}")

            return True

        except Exception as e:
            logger.error(f"Error in physical click: {e}")

            return False

    def is_virtual_available(self) -> bool:
        """

        Checks whether the virtual mouse is available.



        Returns:

            bool: True if the virtual mouse is available

        """

        return self.virtual_available

    def get_cursor_position(self) -> Optional[Tuple[int, int]]:
        """

        Gets the current cursor position.



        Returns:

            Tuple[int, int]: Cursor (x, y) coordinates or None on error

        """

        try:
            import pyautogui

            pos = pyautogui.position()

            return (pos.x, pos.y)

        except Exception as e:
            logger.error(f"Error getting cursor position: {e}")

            return None

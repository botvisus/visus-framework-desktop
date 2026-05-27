"""
Visus Desktop - Visual Overlay

This module manages the display of visual overlays to highlight regions on the screen.
"""

import logging
import os
import sys
import threading
import tkinter as tk
from typing import Tuple

logger = logging.getLogger(__name__)


class VisualOverlay:
    """
    Class to create visual overlays on the screen.

    Allows highlighting specific regions of the screen with colored rectangles,
    useful for debugging and visual feedback during automation.
    """

    def __init__(self, color: str = "red", width: int = 4, duration: int = 1000):
        """
        Initializes the overlay.

        Args:
            color (str): Overlay color (red, blue, green, etc.)
            width (int): Width of the rectangle line
            duration (int): Duration in milliseconds
        """
        self.color = color
        self.width = width
        self.duration = duration
        self._root = None
        self._tkinter_available = self._check_tkinter_availability()

    def _check_tkinter_availability(self) -> bool:
        """
        Checks whether Tkinter is available and working.

        Returns:
            bool: True if Tkinter is working
        """
        try:
            # Simple window creation test
            test_root = tk.Tk()
            test_root.withdraw()  # Hide the window
            test_root.destroy()
            return True
        except Exception as e:
            logger.debug(f"Tkinter not available: {e}")
            return False

    def _fix_tkinter_environment(self) -> bool:
        """
        Attempts to fix common Tkinter problems dynamically.

        Returns:
            bool: True if it managed to fix
        """
        try:
            import glob
            import platform

            # Method 1: Automatically detect TCL/TK
            python_path = sys.executable
            python_dir = os.path.dirname(python_path)

            # Search for TCL versions dynamically
            tcl_search_patterns = []

            # For any Python environment (venv, conda, system)
            base_dirs = [
                python_dir,  # Directory of the Python executable
                os.path.dirname(python_dir),  # Parent directory
                os.path.join(python_dir, ".."),  # Relative
            ]

            # Add system-specific locations if they exist
            if platform.system() == "Windows":
                # Detect default Windows installations
                program_files = [
                    os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                    os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
                ]

                for pf in program_files:
                    if pf and os.path.exists(pf):
                        # Search for any Python version
                        python_installs = glob.glob(os.path.join(pf, "Python*"))
                        base_dirs.extend(python_installs)

            # Search patterns for TCL
            for base_dir in base_dirs:
                if not base_dir or not os.path.exists(base_dir):
                    continue

                # Search for TCL in several possible locations
                tcl_patterns = [
                    os.path.join(base_dir, "tcl*"),
                    os.path.join(base_dir, "lib", "tcl*"),
                    os.path.join(base_dir, "Scripts", "tcl*"),
                    os.path.join(base_dir, "Lib", "tcl*"),
                    os.path.join(base_dir, "share", "tcl*"),
                    os.path.join(base_dir, "Library", "lib", "tcl*"),  # Conda
                ]

                tcl_search_patterns.extend(tcl_patterns)

            # Search for TCL using the patterns
            tcl_paths = []
            for pattern in tcl_search_patterns:
                matches = glob.glob(pattern)
                tcl_paths.extend([m for m in matches if os.path.isdir(m)])

            # Remove duplicates and sort (most recent versions first)
            tcl_paths = sorted(list(set(tcl_paths)), reverse=True)

            logger.debug(f"Found {len(tcl_paths)} possible TCL paths")

            # Test each TCL path found
            for tcl_path in tcl_paths:
                try:
                    os.environ["TCL_LIBRARY"] = tcl_path

                    # Search for the matching TK
                    tk_path = tcl_path.replace("tcl", "tk")
                    if not os.path.exists(tk_path):
                        # Try other patterns for TK
                        tk_dir = os.path.dirname(tcl_path)
                        tk_patterns = [
                            os.path.join(tk_dir, "tk*"),
                            tcl_path.replace("tcl", "tk"),
                        ]
                        for tk_pattern in tk_patterns:
                            tk_matches = glob.glob(tk_pattern)
                            if tk_matches:
                                tk_path = tk_matches[0]
                                break

                    if os.path.exists(tk_path):
                        os.environ["TK_LIBRARY"] = tk_path

                    # Test whether it worked
                    if self._check_tkinter_availability():
                        logger.info(f"✅ Tkinter fixed - TCL: {tcl_path}")
                        if "TK_LIBRARY" in os.environ:
                            logger.info(f"✅ TK: {os.environ['TK_LIBRARY']}")
                        return True

                except Exception as e:
                    logger.debug(f"Error testing {tcl_path}: {e}")
                    continue

            logger.debug("No TCL/TK path worked")
            return False

        except Exception as e:
            logger.debug(f"Error trying to fix Tkinter: {e}")

            # Alternative method: try importing tkinter directly
            try:
                import tkinter as tk_test

                test_root = tk_test.Tk()
                test_root.withdraw()
                test_root.destroy()
                logger.info("✅ Tkinter worked without environment fix")
                return True
            except Exception as e2:
                logger.debug(f"Tkinter completely unavailable: {e2}")
                return False

    def _create_overlay_alternative(self, region: Tuple[int, int, int, int]) -> None:
        """
        Creates an overlay using an alternative method (Windows only).

        Args:
            region (tuple): (x, y, width, height) of the region
        """
        try:
            import ctypes
            import time

            x, y, w, h = region

            # Use the Windows API to create the overlay
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32

            # Get the screen DC
            screen_dc = user32.GetDC(0)
            if not screen_dc:
                raise Exception("Could not get the screen DC")

            try:
                # Define colors (BGR format for Windows)
                colors = {
                    "red": 0x0000FF,  # BGR: Blue=0, Green=0, Red=255
                    "blue": 0xFF0000,  # BGR: Blue=255, Green=0, Red=0
                    "green": 0x00FF00,  # BGR: Blue=0, Green=255, Red=0
                    "yellow": 0x00FFFF,  # BGR: Blue=0, Green=255, Red=255
                    "purple": 0xFF0080,  # BGR: Blue=255, Green=0, Red=128 (purple)
                    "orange": 0x0080FF,  # BGR: Blue=0, Green=128, Red=255 (orange)
                    "cyan": 0xFFFF00,  # BGR: Blue=255, Green=255, Red=0
                    "magenta": 0xFF00FF,  # BGR: Blue=255, Green=0, Red=255
                    "white": 0xFFFFFF,  # BGR: Blue=255, Green=255, Red=255
                    "black": 0x000000,  # BGR: Blue=0, Green=0, Red=0
                }

                pen_color = colors.get(self.color.lower(), colors["red"])

                # Create a thicker pen for better visibility
                pen_width = max(4, self.width)
                pen = gdi32.CreatePen(0, pen_width, pen_color)
                if not pen:
                    raise Exception("Could not create pen")

                old_pen = gdi32.SelectObject(screen_dc, pen)

                # Simple method: draw multiple lines to form a thick rectangle
                for i in range(pen_width):
                    # Top line
                    gdi32.MoveToEx(
                        screen_dc, ctypes.c_int(x), ctypes.c_int(y + i), None
                    )
                    gdi32.LineTo(screen_dc, ctypes.c_int(x + w), ctypes.c_int(y + i))

                    # Bottom line
                    gdi32.MoveToEx(
                        screen_dc, ctypes.c_int(x), ctypes.c_int(y + h - i), None
                    )
                    gdi32.LineTo(
                        screen_dc, ctypes.c_int(x + w), ctypes.c_int(y + h - i)
                    )

                    # Left line
                    gdi32.MoveToEx(
                        screen_dc, ctypes.c_int(x + i), ctypes.c_int(y), None
                    )
                    gdi32.LineTo(screen_dc, ctypes.c_int(x + i), ctypes.c_int(y + h))

                    # Right line
                    gdi32.MoveToEx(
                        screen_dc, ctypes.c_int(x + w - i), ctypes.c_int(y), None
                    )
                    gdi32.LineTo(
                        screen_dc, ctypes.c_int(x + w - i), ctypes.c_int(y + h)
                    )

                # Force an immediate refresh
                gdi32.GdiFlush()

                # Wait for the duration
                time.sleep(self.duration / 1000.0)

                logger.info(
                    f"✅ Visual overlay displayed in region: x={x}, y={y}, width={w}, height={h}"
                )

            finally:
                # Clean up resources
                if old_pen:
                    gdi32.SelectObject(screen_dc, old_pen)
                if pen:
                    gdi32.DeleteObject(pen)
                user32.ReleaseDC(0, screen_dc)

                # Force a screen repaint to remove the overlay
                user32.InvalidateRect(0, None, True)
                user32.UpdateWindow(0)

            logger.info(
                f"✅ Alternative overlay (Windows API) created in region: x={x}, y={y}, w={w}, h={h}"
            )

        except Exception as e:
            logger.warning(f"Alternative overlay failed: {e}")
            # Fallback implementation using print with coordinates
            center_x = x + w // 2
            center_y = y + h // 2
            logger.info(
                f"🎯 HIGHLIGHTED REGION: Position({x}, {y}) Size({w}x{h}) Center({center_x}, {center_y})"
            )
            logger.info(
                f"📍 Click location would be approximately: ({center_x}, {center_y})"
            )

    def show(self, region: Tuple[int, int, int, int], blocking: bool = False) -> None:
        """
        Displays the overlay on the specified region.

        Args:
            region (tuple): (x, y, width, height) of the region to highlight
            blocking (bool): If True, blocks until the overlay disappears
        """
        if blocking:
            self._create_overlay_with_fallback(region)
        else:
            thread = threading.Thread(
                target=self._create_overlay_with_fallback, args=(region,)
            )
            thread.daemon = True
            thread.start()

    def _create_overlay_with_fallback(self, region: Tuple[int, int, int, int]) -> None:
        """
        Creates an overlay with multiple fallback methods.

        Args:
            region (tuple): (x, y, width, height) of the region
        """
        # Method 1: Try Tkinter directly
        if self._tkinter_available:
            if self._create_overlay_tkinter(region):
                return

        # Method 2: Try to fix Tkinter and use it
        if self._fix_tkinter_environment():
            if self._create_overlay_tkinter(region):
                return

        # Method 3: Alternative overlay (Windows)
        if os.name == "nt":
            self._create_overlay_alternative(region)
            return

        # Method 4: Log only
        x, y, w, h = region
        logger.info(f"💡 Visual overlay in region: x={x}, y={y}, width={w}, height={h}")

    def _create_overlay_tkinter(self, region: Tuple[int, int, int, int]) -> bool:
        """
        Creates an overlay using Tkinter.

        Args:
            region (tuple): (x, y, width, height) of the region

        Returns:
            bool: True if created successfully
        """
        try:
            x, y, w, h = region

            # Create transparent window
            root = tk.Tk()
            root.withdraw()  # Hide temporarily
            root.overrideredirect(True)
            root.attributes("-topmost", True)

            # Windows-specific settings for transparency
            if os.name == "nt":
                try:
                    # Try to make the window semi-transparent
                    root.attributes("-alpha", 0.7)
                    root.config(bg="black")
                    root.attributes("-transparentcolor", "black")
                except Exception as e:
                    logger.debug(f"Transparency not available: {e}")
                    root.config(bg="gray10")
            else:
                root.config(bg="black")

            # Set the screen size
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.geometry(f"{screen_width}x{screen_height}+0+0")

            # Create a canvas that covers the whole screen
            canvas = tk.Canvas(
                root,
                width=screen_width,
                height=screen_height,
                bg="black" if os.name == "nt" else "gray10",
                highlightthickness=0,
                bd=0,
            )
            canvas.pack(fill="both", expand=True)

            # Define more visible colors
            colors = {
                "red": "#FF0000",
                "blue": "#0080FF",
                "green": "#00FF00",
                "yellow": "#FFFF00",
                "magenta": "#FF00FF",
                "cyan": "#00FFFF",
                "white": "#FFFFFF",
                "purple": "#800080",
                "orange": "#FF8000",
                "black": "#000000",
            }

            overlay_color = colors.get(self.color.lower(), colors["red"])
            line_width = max(3, self.width)

            # Draw the rectangle highlighting the region
            canvas.create_rectangle(
                x,
                y,
                x + w,
                y + h,
                outline=overlay_color,
                width=line_width,
                fill="",  # No fill
            )

            # Add a point at the center to indicate where it will be clicked
            center_x = x + w // 2
            center_y = y + h // 2

            # Draw a cross at the center
            cross_size = min(10, w // 4, h // 4)
            canvas.create_line(
                center_x - cross_size,
                center_y,
                center_x + cross_size,
                center_y,
                fill=overlay_color,
                width=line_width,
            )
            canvas.create_line(
                center_x,
                center_y - cross_size,
                center_x,
                center_y + cross_size,
                fill=overlay_color,
                width=line_width,
            )

            # Show the window
            root.deiconify()
            root.lift()
            root.focus_force()

            # Schedule window destruction
            root.after(self.duration, root.destroy)

            # Start the main loop
            root.mainloop()

            logger.info(
                f"✅ Tkinter overlay created successfully in region: x={x}, y={y}, w={w}, h={h}"
            )
            return True

        except Exception as e:
            logger.debug(f"Tkinter overlay failure: {e}")
            return False

    def show_multiple(self, regions: list, blocking: bool = False) -> None:
        """
        Displays multiple overlays simultaneously.

        Args:
            regions (list): List of (x, y, width, height) tuples
            blocking (bool): If True, blocks until all overlays disappear
        """
        if blocking:
            self._create_multiple_overlays(regions)
        else:
            thread = threading.Thread(
                target=self._create_multiple_overlays, args=(regions,)
            )
            thread.daemon = True
            thread.start()

    def _create_multiple_overlays(self, regions: list) -> None:
        """
        Creates multiple overlays with fallback.

        Args:
            regions (list): List of regions
        """
        # Try with Tkinter first
        if self._tkinter_available or self._fix_tkinter_environment():
            if self._create_multiple_overlays_tkinter(regions):
                return

        # Fallback: individual overlay for each region
        for region in regions:
            self._create_overlay_with_fallback(region)

    def _create_multiple_overlays_tkinter(self, regions: list) -> bool:
        """
        Creates multiple overlays using Tkinter.

        Args:
            regions (list): List of regions

        Returns:
            bool: True if created successfully
        """
        try:
            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.config(bg="black")

            if os.name == "nt":
                try:
                    root.attributes("-transparentcolor", "black")
                    root.attributes("-alpha", 0.3)
                except Exception:
                    pass

            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.geometry(f"{screen_width}x{screen_height}+0+0")

            canvas = tk.Canvas(
                root,
                width=screen_width,
                height=screen_height,
                bg="black",
                highlightthickness=0,
            )
            canvas.pack()

            # Draw all the rectangles
            for region in regions:
                x, y, w, h = region
                canvas.create_rectangle(
                    x, y, x + w, y + h, outline=self.color, width=self.width
                )

            root.after(self.duration, root.destroy)
            root.mainloop()

            logger.info(f"✅ Multiple overlays created: {len(regions)} regions")
            return True

        except Exception as e:
            logger.debug(f"Multiple Tkinter overlays failure: {e}")
            return False


def show_overlay(
    region: Tuple[int, int, int, int],
    duration: int = 1000,
    color: str = "red",
    width: int = 4,
) -> None:
    """
    Convenience function to quickly display an overlay.

    Args:
        region (tuple): (x, y, width, height) of the region to highlight
        duration (int): Duration in milliseconds
        color (str): Overlay color
        width (int): Line width

    Examples:
        >>> show_overlay((100, 100, 200, 50), duration=2000, color="blue")
    """
    overlay = VisualOverlay(color=color, width=width, duration=duration)
    overlay.show(region, blocking=False)


def show_overlay_blocking(
    region: Tuple[int, int, int, int],
    duration: int = 1000,
    color: str = "red",
    width: int = 4,
) -> None:
    """
    Convenience function to display an overlay in a blocking manner.

    Args:
        region (tuple): (x, y, width, height) of the region to highlight
        duration (int): Duration in milliseconds
        color (str): Overlay color
        width (int): Line width
    """
    overlay = VisualOverlay(color=color, width=width, duration=duration)
    overlay.show(region, blocking=True)


def show_multiple_overlays(
    regions: list, duration: int = 1000, color: str = "red", width: int = 4
) -> None:
    """
    Convenience function to display multiple overlays.

    Args:
        regions (list): List of (x, y, width, height) tuples
        duration (int): Duration in milliseconds
        color (str): Overlay color
        width (int): Line width

    Examples:
        >>> regions = [(100, 100, 200, 50), (300, 200, 150, 30)]
        >>> show_multiple_overlays(regions, duration=2000, color="green")
    """
    overlay = VisualOverlay(color=color, width=width, duration=duration)
    overlay.show_multiple(regions, blocking=False)

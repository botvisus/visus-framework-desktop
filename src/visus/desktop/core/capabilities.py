"""Capability mixin that adds BotCity-core-style helpers to ``VisusBot``.

These methods are thin, well-documented delegations to the focused capability
modules (``files``, ``clipboard``, ``screen``, ``process``, ``window``,
``mouse_extra``, ``image_map``). Keeping them here avoids bloating the main
``VisusBot`` definition while exposing everything through a single object:

    >>> from visus.desktop import VisusBot
    >>> bot = VisusBot()
    >>> bot.register_image("save", "save.png")
    >>> bot.wait_for_file("report.pdf", timeout=30)
"""

from __future__ import annotations

import webbrowser
from typing import Any

from ..utils import clipboard as _clipboard
from ..utils import files as _files
from . import mouse_extra as _mouse
from . import process as _process
from . import screen as _screen
from . import window as _window
from .image_map import ImageMap


class CapabilitiesMixin:
    """Mixin providing process, window, screen, clipboard, file and mouse helpers."""

    @property
    def image_map(self) -> ImageMap:
        """The per-bot image registry (created lazily on first access)."""
        registry = self.__dict__.get("_image_map")
        if registry is None:
            registry = ImageMap()
            self.__dict__["_image_map"] = registry
        return registry

    # --- Files -----------------------------------------------------------
    def wait_for_file(
        self, path: str, timeout: float = 10.0, poll_interval: float = 0.5
    ) -> bool:
        """Wait until ``path`` exists and is readable. Returns True if it appeared."""
        return _files.wait_for_file(path, timeout, poll_interval)

    def wait_for_file_stable(
        self,
        path: str,
        timeout: float = 30.0,
        stable_for: float = 1.0,
        poll_interval: float = 0.5,
    ) -> bool:
        """Wait until ``path`` exists and its size stops changing (download done)."""
        return _files.wait_for_file_stable(path, timeout, stable_for, poll_interval)

    # --- Clipboard -------------------------------------------------------
    def copy(self, text: str) -> None:
        """Copy ``text`` to the system clipboard."""
        _clipboard.copy(text)

    def paste(self) -> str:
        """Return the current system clipboard contents."""
        return _clipboard.paste()

    def get_clipboard(self) -> str:
        """Return the current system clipboard contents (alias of :meth:`paste`)."""
        return _clipboard.get_clipboard()

    # --- Screen ----------------------------------------------------------
    def take_screenshot(self, region: tuple | None = None):
        """Capture the screen (or ``region`` = (x, y, w, h)) and return a PIL Image."""
        return _screen.capture_screen(region)

    def save_screenshot(self, path: str, region: tuple | None = None) -> str:
        """Capture the screen (or ``region``) and save it to ``path``."""
        return _screen.save_screenshot(path, region)

    def get_display_size(self) -> tuple:
        """Return the primary display size as ``(width, height)``."""
        return _screen.get_display_size()

    # --- Process / application -------------------------------------------
    def launch(self, path: str) -> None:
        """Launch an application or open a file using the OS default handler."""
        _process.launch(path)

    def find_process(self, name: str | None = None, pid: int | None = None):
        """Return the first running process matching ``name`` or ``pid`` (or None)."""
        return _process.find_process(name=name, pid=pid)

    def is_process_running(self, name: str) -> bool:
        """Return whether a process whose name contains ``name`` is running."""
        return _process.is_process_running(name)

    def kill_process(self, target: Any) -> bool:
        """Terminate a process by Process object, pid, or name substring."""
        return _process.kill_process(target)

    # --- Window ----------------------------------------------------------
    def focus_window(self, title_substring: str) -> bool:
        """Bring the first window whose title contains ``title_substring`` to front."""
        return _window.focus_window(title_substring)

    def maximize_window(self, title_substring: str) -> bool:
        """Maximize the first window whose title contains ``title_substring``."""
        return _window.maximize_window(title_substring)

    def minimize_window(self, title_substring: str) -> bool:
        """Minimize the first window whose title contains ``title_substring``."""
        return _window.minimize_window(title_substring)

    def close_window(self, title_substring: str) -> bool:
        """Close the first window whose title contains ``title_substring``."""
        return _window.close_window(title_substring)

    # --- Image map -------------------------------------------------------
    def register_image(self, label: str, path: str) -> None:
        """Register an image under ``label`` so it can be found by name."""
        self.image_map.register(label, path)

    def register_images(self, mapping: dict) -> None:
        """Register several ``label -> path`` image pairs at once."""
        self.image_map.register_many(mapping)

    def get_image(self, label: str) -> str:
        """Return the registered path for ``label``."""
        return self.image_map.get(label)

    # --- Mouse (extras) --------------------------------------------------
    def scroll(self, amount: int, x: int | None = None, y: int | None = None) -> None:
        """Scroll the wheel ``amount`` clicks (positive = up, negative = down)."""
        _mouse.scroll(amount, x, y)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: str = "left",
    ) -> None:
        """Press at the start point, drag to the end point, and release."""
        _mouse.drag(start_x, start_y, end_x, end_y, duration, button)

    def triple_click(
        self, x: int | None = None, y: int | None = None, interval: float = 0.05
    ) -> None:
        """Triple-click at ``(x, y)`` (or the current cursor position)."""
        _mouse.triple_click(x, y, interval)

    def move_random(
        self, x: int, y: int, max_offset: int = 3, duration: float = 0.2
    ) -> None:
        """Move the cursor to ``(x, y)`` with a small human-like jitter."""
        _mouse.move_random(x, y, max_offset, duration)

    # --- Web -------------------------------------------------------------
    def browse(self, url: str) -> None:
        """Open ``url`` in the system default web browser."""
        webbrowser.open(url)

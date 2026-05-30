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

import time
import webbrowser
from typing import Any

from ..utils import clipboard as _clipboard
from ..utils import files as _files
from . import locate as _locate
from . import mouse_extra as _mouse
from . import native as _native
from . import process as _process
from . import screen as _screen
from . import window as _window
from .image_map import ImageMap
from .native import Backend, NativeError


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
    def _should_show_overlay(self, override: bool | None) -> bool:
        """Resolve the per-call ``show_overlay`` flag against the bot config.

        Tolerant when the host has no ``config`` attribute (e.g. lightweight
        test hosts using the mixin in isolation): defaults to ``False``.
        """
        if override is not None:
            return bool(override)
        config = getattr(self, "config", None)
        if config is None:
            return False
        try:
            return bool(config.get("show_overlay", True))
        except Exception:
            return False

    def _resolve_wait_timeout(self, override: int | None) -> int:
        """Return ``override`` if set, else the bot ``wait_timeout`` config (default 30).

        Tolerant when the host has no ``config`` attribute.
        """
        if override is not None:
            return override
        config = getattr(self, "config", None)
        if config is None:
            return 30
        try:
            return int(config.get("wait_timeout", 30))
        except Exception:
            return 30

    def _highlight_briefly(self, region: tuple) -> None:
        """Draw a brief visual overlay over ``region`` (best-effort, never raises)."""
        try:
            from .overlay import show_overlay as _show_overlay

            _show_overlay(
                region,
                duration=self.config.get("overlay_duration", 1000),
                color=self.config.get("overlay_color", "red"),
                width=self.config.get("overlay_width", 4),
            )
        except Exception:
            # Overlay is purely visual; never let it break the action.
            pass

    def scroll(
        self,
        amount: int,
        x: int | None = None,
        y: int | None = None,
        delay: float = 0,
    ) -> None:
        """Scroll the wheel ``amount`` clicks (positive = up, negative = down)."""
        _mouse.scroll(amount, x, y)
        if delay:
            time.sleep(delay)

    def drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.5,
        button: str = "left",
        delay: float = 0,
        show_overlay: bool | None = None,
    ) -> None:
        """Press at the start point, drag to the end point, and release.

        Honors ``show_overlay`` (briefly highlights the start point, like
        :meth:`click_image` does) and ``delay`` (sleeps after the drag) so it
        slots into the same workflow as the original visus click methods.
        """
        if self._should_show_overlay(show_overlay):
            self._highlight_briefly((start_x - 10, start_y - 10, 20, 20))
        _mouse.drag(start_x, start_y, end_x, end_y, duration, button)
        if delay:
            time.sleep(delay)

    def triple_click(
        self,
        x: int | None = None,
        y: int | None = None,
        interval: float = 0.05,
        delay: float = 0,
        show_overlay: bool | None = None,
    ) -> None:
        """Triple-click at ``(x, y)`` (or the current cursor position)."""
        if (
            x is not None
            and y is not None
            and self._should_show_overlay(show_overlay)
        ):
            self._highlight_briefly((x - 10, y - 10, 20, 20))
        _mouse.triple_click(x, y, interval)
        if delay:
            time.sleep(delay)

    def move_random(
        self,
        x: int,
        y: int,
        max_offset: int = 3,
        duration: float = 0.2,
        delay: float = 0,
    ) -> None:
        """Move the cursor to ``(x, y)`` with a small human-like jitter."""
        _mouse.move_random(x, y, max_offset, duration)
        if delay:
            time.sleep(delay)

    def mouse_down(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        delay: float = 0,
    ) -> None:
        """Press a mouse button at ``(x, y)`` (or current position) without releasing.

        Pair with :meth:`mouse_up` for custom press-and-hold patterns. For atomic
        press → move → release use :meth:`drag` instead.
        """
        _mouse.mouse_down(x, y, button)
        if delay:
            time.sleep(delay)

    def mouse_up(
        self,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        delay: float = 0,
    ) -> None:
        """Release a previously-pressed mouse button at ``(x, y)`` (or current position)."""
        _mouse.mouse_up(x, y, button)
        if delay:
            time.sleep(delay)

    # --- Web -------------------------------------------------------------
    def browse(self, url: str) -> None:
        """Open ``url`` in the system default web browser."""
        webbrowser.open(url)

    # --- Image: find all / multiple -------------------------------------
    def find_all(
        self,
        image: str,
        region: tuple | None = None,
        confidence: float = 0.9,
        grayscale: bool = False,
        max_attempts: int = 1,
        backtrack: bool = False,
        wait_until_found: bool = False,
        wait_until_disappears: bool = False,
        wait_timeout: int | None = None,
    ) -> list:
        """Return ALL on-screen matches of an image (label or path) as boxes.

        Mirrors :meth:`find_image`'s parameter style:

        * ``max_attempts`` + ``backtrack`` retry with progressively lowered
          confidence (5% per attempt, floor 0.7).
        * ``wait_until_found`` polls until at least one match appears (or
          ``wait_timeout`` seconds elapse, falling back to the configured
          global ``wait_timeout`` when ``None``).
        * ``wait_until_disappears`` polls until no match remains.

        Returns a list of ``(left, top, width, height)`` tuples (empty if none).
        """
        import time as _time

        resolved = self.image_map.resolve(image)

        def _do_find(conf: float) -> list:
            return _locate.find_all(resolved, region, conf, grayscale)

        timeout = self._resolve_wait_timeout(wait_timeout)

        if wait_until_found:
            deadline = _time.monotonic() + timeout
            while True:
                result = _do_find(confidence)
                if result:
                    return result
                if _time.monotonic() >= deadline:
                    return []
                _time.sleep(0.5)

        if wait_until_disappears:
            deadline = _time.monotonic() + timeout
            while True:
                result = _do_find(confidence)
                if not result:
                    return []
                if _time.monotonic() >= deadline:
                    return result
                _time.sleep(0.5)

        current_conf = confidence
        attempts = max(1, max_attempts)
        for attempt in range(attempts):
            result = _do_find(current_conf)
            if result:
                return result
            if backtrack and attempt < attempts - 1:
                current_conf = max(0.7, current_conf - 0.05)
            else:
                break
        return []

    def find_multiple(
        self,
        images,
        region: tuple | None = None,
        confidence: float = 0.9,
        grayscale: bool = False,
        max_attempts: int = 1,
        backtrack: bool = False,
        wait_until_found: bool = False,
        wait_until_disappears: bool = False,
        wait_timeout: int | None = None,
    ) -> dict:
        """Locate several images (labels or paths) at once -> ``{key: box | None}``.

        Same wait/backtrack semantics as :meth:`find_all`, but the wait targets
        the combined result: ``wait_until_found`` waits until *every* image is
        found; ``wait_until_disappears`` waits until *none* are found.
        """
        import time as _time

        if isinstance(images, dict):
            resolved = {k: self.image_map.resolve(v) for k, v in images.items()}
        else:
            resolved = {item: self.image_map.resolve(item) for item in images}

        def _do_find(conf: float) -> dict:
            return _locate.find_multiple(resolved, region, conf, grayscale)

        timeout = self._resolve_wait_timeout(wait_timeout)

        if wait_until_found:
            deadline = _time.monotonic() + timeout
            while True:
                result = _do_find(confidence)
                if result and all(v is not None for v in result.values()):
                    return result
                if _time.monotonic() >= deadline:
                    return result
                _time.sleep(0.5)

        if wait_until_disappears:
            deadline = _time.monotonic() + timeout
            while True:
                result = _do_find(confidence)
                if not any(result.values()):
                    return result
                if _time.monotonic() >= deadline:
                    return result
                _time.sleep(0.5)

        current_conf = confidence
        attempts = max(1, max_attempts)
        last_result: dict = {}
        for attempt in range(attempts):
            last_result = _do_find(current_conf)
            if all(v is not None for v in last_result.values()):
                return last_result
            if backtrack and attempt < attempts - 1:
                current_conf = max(0.7, current_conf - 0.05)
            else:
                break
        return last_result

    # --- Native (accessibility) automation ------------------------------
    def connect_to_app(
        self,
        backend: Backend | str = Backend.UIA,
        timeout: float = 60.0,
        poll_interval: float = 0.5,
        **selectors,
    ):
        """Connect to a running application for native (UIA/Win32) automation.

        Stores the connected application on ``self.app`` and returns it.
        """
        self.app = _native.connect_to_app(
            backend, timeout, poll_interval, **selectors
        )
        return self.app

    def find_app_window(self, timeout: float = 10.0, **selectors):
        """Find a window of the connected application (call connect_to_app first)."""
        app = getattr(self, "app", None)
        if app is None:
            raise NativeError(
                "Not connected to an application; call connect_to_app() first."
            )
        return _native.find_window(app, timeout, **selectors)

    def find_app_element(self, from_parent_window=None, timeout: float = 10.0, **selectors):
        """Find a control of the connected application by accessibility selectors."""
        app = getattr(self, "app", None)
        if app is None:
            raise NativeError(
                "Not connected to an application; call connect_to_app() first."
            )
        return _native.find_element(app, from_parent_window, timeout, **selectors)

    # --- Coordinate helpers ---------------------------------------------
    @staticmethod
    def get_element_coords(location: tuple) -> tuple:
        """Return the top-left ``(x, y)`` of a ``(x, y, width, height)`` location box."""
        return (location[0], location[1])

    @staticmethod
    def get_element_coords_centered(location: tuple) -> tuple:
        """Return the center ``(x, y)`` of a ``(x, y, width, height)`` location box."""
        x, y, width, height = location
        return (x + width // 2, y + height // 2)

    def click_relative(
        self,
        image: str,
        x_offset: int = 0,
        y_offset: int = 0,
        region: tuple | None = None,
        confidence: float = 0.9,
        delay: float = 0,
        mouse_button: str = "left",
        max_attempts: int = 3,
        backtrack: bool = False,
        sendtext: str | None = None,
        show_overlay: bool | None = None,
        wait_until_found: bool = False,
        wait_until_disappears: bool = False,
        wait_timeout: int | None = None,
        centered: bool = False,
    ) -> bool:
        """Find an image (label or path), then click at a coordinate offset from it.

        Mirrors the full parameter style of :meth:`click_image` / :meth:`click_text`
        so it integrates with the same backtrack, wait, virtual-mouse, overlay and
        sendtext pipeline as the original visus methods. The click lands at the
        image's top-left ``+ (x_offset, y_offset)``, or at its center ``+`` the
        offset when ``centered=True``.

        Args:
            image: Registered label or path of the reference image.
            x_offset / y_offset: Pixel offset from the reference point.
            region: Optional search region for the image.
            confidence: Image match confidence (0.0-1.0).
            delay: Seconds to pause after the click.
            mouse_button: ``"left"`` / ``"right"`` / ``"double"`` / ``"move_to"``.
            max_attempts: Retry attempts (forwarded to :meth:`find_image`).
            backtrack: When ``True``, lowers confidence on each retry and
                participates in the active backtrack session.
            sendtext: Optional text to type after the click (special sequences
                like ``{ctrl}a``, ``{tab}``, ``{enter}`` are honored).
            show_overlay: Force the visual overlay on/off; ``None`` uses the
                configured default.
            wait_until_found / wait_until_disappears / wait_timeout: forwarded to
                :meth:`find_image` to synchronize with the UI.
            centered: Offset from the image center instead of its top-left.

        Returns:
            bool: True if the image was found AND the click was performed.
        """
        location = self.find_image(
            image,
            region=region,
            confidence=confidence,
            max_attempts=max_attempts,
            backtrack=backtrack,
            wait_until_found=wait_until_found,
            wait_until_disappears=wait_until_disappears,
            wait_timeout=wait_timeout,
        )
        if location is None:
            return False
        if centered:
            base_x, base_y = self.get_element_coords_centered(location)
        else:
            base_x, base_y = self.get_element_coords(location)
        # Synthetic 20x20 location whose center is the target point: this lets
        # us reuse click_at (which routes through the virtual mouse and the
        # overlay system, just like click_image does).
        target_location = (
            base_x + x_offset - 10,
            base_y + y_offset - 10,
            20,
            20,
        )
        success = self.click_at(
            target_location,
            mouse_button=mouse_button,
            delay=delay,
            show_overlay=show_overlay,
        )
        if success and sendtext is not None:
            self.executor.keyboard_commander.process_sendtext_command(sendtext)
        return success

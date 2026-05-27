"""Visus Desktop - Image locate helpers.

Self-contained, BotCity-style image location utilities built on top of
``pyautogui``. Provides:

* :func:`find_all` - return every match of a single template image.
* :func:`find_multiple` - locate the first match of several template images
  in one call.

All coordinates are 4-tuples ``(left, top, width, height)``. ``pyautogui`` is
imported lazily inside each function so this module imports cleanly even in
headless environments where the GUI backend may be unavailable. The helpers are
deliberately defensive about ``pyautogui`` version differences: depending on the
installed version, "not found" may be signalled either by returning ``None`` /
an empty iterator or by raising ``pyautogui.ImageNotFoundException``, and the
``confidence`` keyword requires OpenCV (raising ``NotImplementedError`` /
``ValueError`` when it is missing).
"""

from __future__ import annotations

import logging
from typing import Iterable, Mapping, Optional, Union

logger = logging.getLogger(__name__)

# Type aliases for clarity.
Region = Optional[tuple[int, int, int, int]]
Box = tuple[int, int, int, int]
ImagesInput = Union[Mapping[str, str], Iterable[str]]


def _box_to_tuple(box) -> Box:
    """Convert a pyautogui ``Box`` (or any 4-tuple-like) to a plain int tuple.

    Args:
        box: A pyautogui ``Box`` namedtuple or any object exposing
            ``left``/``top``/``width``/``height`` attributes, falling back to
            iterable unpacking otherwise.

    Returns:
        A plain ``(left, top, width, height)`` tuple of ints.
    """
    try:
        return (int(box.left), int(box.top), int(box.width), int(box.height))
    except AttributeError:
        left, top, width, height = box
        return (int(left), int(top), int(width), int(height))


def _is_not_found_exception(pyautogui, exc: Exception) -> bool:
    """Return ``True`` if ``exc`` represents a pyautogui "image not found"."""
    not_found = getattr(pyautogui, "ImageNotFoundException", None)
    return not_found is not None and isinstance(exc, not_found)


def _is_opencv_confidence_error(exc: Exception) -> bool:
    """Return ``True`` if ``exc`` looks like a missing-OpenCV/confidence error.

    ``pyautogui`` raises ``NotImplementedError`` when OpenCV is not installed but
    ``confidence`` is requested, and may raise ``ValueError`` mentioning OpenCV
    in some versions.
    """
    if isinstance(exc, NotImplementedError):
        return True
    if isinstance(exc, ValueError) and "opencv" in str(exc).lower():
        return True
    return False


def find_all(
    image_path: str,
    region: Region = None,
    confidence: float = 0.9,
    grayscale: bool = False,
) -> list[Box]:
    """Locate every occurrence of a template image on the screen.

    Wraps ``pyautogui.locateAllOnScreen`` and converts each result to a plain
    ``(left, top, width, height)`` tuple.

    Args:
        image_path: Path to the template image to search for.
        region: Optional search region as ``(left, top, width, height)``. When
            ``None`` (the default) the whole screen is searched.
        confidence: Match confidence in the ``0.0``-``1.0`` range. Requires
            OpenCV; if OpenCV is unavailable the search is retried without it.
        grayscale: When ``True``, perform a faster grayscale match.

    Returns:
        A list of ``(left, top, width, height)`` tuples, one per match. Returns
        an empty list if nothing is found (including when ``pyautogui`` raises
        ``ImageNotFoundException``).
    """
    import pyautogui

    def _run(use_confidence: bool):
        kwargs = {"region": region, "grayscale": grayscale}
        if use_confidence:
            kwargs["confidence"] = confidence
        return pyautogui.locateAllOnScreen(image_path, **kwargs)

    try:
        matches = _run(use_confidence=True)
    except Exception as exc:  # noqa: BLE001 - normalise version differences
        if _is_not_found_exception(pyautogui, exc):
            return []
        if _is_opencv_confidence_error(exc):
            logger.debug("Confidence unsupported (%s); retrying without it", exc)
            try:
                matches = _run(use_confidence=False)
            except Exception as exc2:  # noqa: BLE001
                if _is_not_found_exception(pyautogui, exc2):
                    return []
                logger.debug("locateAllOnScreen failed without confidence: %s", exc2)
                return []
        else:
            logger.debug("locateAllOnScreen failed: %s", exc)
            return []

    if matches is None:
        return []

    try:
        return [_box_to_tuple(box) for box in matches]
    except Exception as exc:  # noqa: BLE001 - guard against odd iterables
        logger.debug("Failed iterating locateAllOnScreen results: %s", exc)
        return []


def find_multiple(
    images: ImagesInput,
    region: Region = None,
    confidence: float = 0.9,
    grayscale: bool = False,
) -> dict[str, Box | None]:
    """Locate the first match of several template images in a single call.

    Each image is searched independently with ``pyautogui.locateOnScreen`` and
    only its first (best) match is reported.

    Args:
        images: Either a mapping of ``{label: image_path}`` or an iterable of
            image paths. For an iterable input the paths themselves are used as
            the result keys.
        region: Optional search region as ``(left, top, width, height)`` applied
            to every image. When ``None`` (the default) the whole screen is
            searched.
        confidence: Match confidence in the ``0.0``-``1.0`` range. Requires
            OpenCV; if OpenCV is unavailable the search is retried without it.
        grayscale: When ``True``, perform a faster grayscale match.

    Returns:
        A dict mapping each label (or path) to its first match as a
        ``(left, top, width, height)`` tuple, or ``None`` when that image was
        not found or the lookup raised an error.
    """
    if isinstance(images, Mapping):
        items = list(images.items())
    else:
        items = [(path, path) for path in images]

    results: dict[str, Box | None] = {}
    for label, path in items:
        results[label] = _locate_one(
            path, region=region, confidence=confidence, grayscale=grayscale
        )
    return results


def _locate_one(
    image_path: str,
    region: Region = None,
    confidence: float = 0.9,
    grayscale: bool = False,
) -> Box | None:
    """Locate the first match of a single image, returning ``None`` on failure.

    Defensive wrapper around ``pyautogui.locateOnScreen`` mirroring the
    robustness of :func:`find_all`.
    """
    import pyautogui

    def _run(use_confidence: bool):
        kwargs = {"region": region, "grayscale": grayscale}
        if use_confidence:
            kwargs["confidence"] = confidence
        return pyautogui.locateOnScreen(image_path, **kwargs)

    try:
        match = _run(use_confidence=True)
    except Exception as exc:  # noqa: BLE001 - normalise version differences
        if _is_not_found_exception(pyautogui, exc):
            return None
        if _is_opencv_confidence_error(exc):
            logger.debug("Confidence unsupported (%s); retrying without it", exc)
            try:
                match = _run(use_confidence=False)
            except Exception as exc2:  # noqa: BLE001
                if _is_not_found_exception(pyautogui, exc2):
                    return None
                logger.debug("locateOnScreen failed without confidence: %s", exc2)
                return None
        else:
            logger.debug("locateOnScreen failed: %s", exc)
            return None

    if match is None:
        return None

    try:
        return _box_to_tuple(match)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Failed converting locateOnScreen result: %s", exc)
        return None

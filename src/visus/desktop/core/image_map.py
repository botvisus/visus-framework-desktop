"""
Visus Desktop - Image Map

This module provides a small registry that maps human-readable string labels
to image file paths. It lets callers refer to images by a stable name instead
of repeating file system paths throughout their automation scripts.
"""

from __future__ import annotations

import os


class ImageMap:
    """A registry mapping string labels to image file paths.

    Instead of repeating image paths across an automation script, users can
    register each image once under a label and then refer to it by that label.
    The :meth:`resolve` method additionally accepts raw paths, so APIs that
    consume images can transparently support either form.
    """

    def __init__(self) -> None:
        """Initialize an empty image map."""
        self._mapping: dict[str, str] = {}

    def register(self, label: str, path: str) -> None:
        """Register a single ``label -> path`` pair.

        Args:
            label: The non-empty name used to refer to the image.
            path: The file system path to the image. Must exist.

        Raises:
            ValueError: If ``label`` is empty.
            FileNotFoundError: If ``path`` does not point to an existing file.
        """
        if not label:
            raise ValueError("label must be a non-empty string")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Image path does not exist: {path}")
        self._mapping[label] = path

    def register_many(self, mapping: dict[str, str]) -> None:
        """Register multiple ``label -> path`` pairs at once.

        Args:
            mapping: A dictionary of label/path pairs. Each pair is registered
                using :meth:`register`, so the same validation rules apply.

        Raises:
            ValueError: If any label is empty.
            FileNotFoundError: If any path does not exist.
        """
        for label, path in mapping.items():
            self.register(label, path)

    def get(self, label: str) -> str:
        """Return the registered path for ``label``.

        Args:
            label: The label to look up.

        Returns:
            The path previously associated with ``label``.

        Raises:
            KeyError: If the label is not registered.
        """
        if label not in self._mapping:
            raise KeyError(f"Unknown image label: {label!r}")
        return self._mapping[label]

    def resolve(self, label_or_path: str) -> str:
        """Resolve a value that may be either a label or a direct path.

        If ``label_or_path`` matches a registered label, the associated path is
        returned. Otherwise the value is returned unchanged and treated as a
        direct path. This allows callers to accept either a registered label or
        a raw path interchangeably.

        Args:
            label_or_path: A registered label or a direct file path.

        Returns:
            The resolved path.
        """
        if label_or_path in self._mapping:
            return self._mapping[label_or_path]
        return label_or_path

    def __contains__(self, label: str) -> bool:
        """Return ``True`` if ``label`` is registered."""
        return label in self._mapping

    def labels(self) -> list[str]:
        """Return a sorted list of all registered labels."""
        return sorted(self._mapping)

    def clear(self) -> None:
        """Remove all registered label/path pairs."""
        self._mapping.clear()

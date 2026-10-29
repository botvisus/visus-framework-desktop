"""Reading order for on-screen matches: the one numbering every finder shares.

``find-all`` prints ``#1 #2 #3`` and ``--occurrence N`` picks the Nth, for text
(OCR) and images alike -- so both must sort the same way, and the way a person
reads: top to bottom, then left to right. A plain ``(y, x)`` sort is not that:
two buttons on one line whose tops differ by 2 px (anti-aliasing, OCR box
jitter) would swap places. Here boxes whose vertical centers sit within half
the shorter height of a line's first box belong to that line.
"""

from __future__ import annotations

from typing import Callable, Sequence, TypeVar

T = TypeVar("T")
Box = Sequence[int]


def reading_order(items: Sequence[T], key: Callable[[T], Box] = lambda item: item) -> list[T]:  # type: ignore[assignment,return-value]
    """``items`` sorted line by line, left to right; ``key`` gives each one's
    ``(x, y, w, h)`` box (default: the item is the box)."""

    def center_y(item: T) -> float:
        _x, y, _w, h = key(item)
        return y + h / 2

    lines: list[tuple[float, float, list[T]]] = []  # (anchor center y, anchor height, members)
    for item in sorted(items, key=center_y):
        h = key(item)[3]
        if lines and abs(center_y(item) - lines[-1][0]) <= min(h, lines[-1][1]) / 2:
            lines[-1][2].append(item)
        else:
            lines.append((center_y(item), h, [item]))
    return [item for _cy, _h, members in lines for item in sorted(members, key=lambda i: key(i)[0])]

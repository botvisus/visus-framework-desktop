"""Standalone retry decorator (Phase 1, R1).

``backtrack`` retries inside an ``execute_tasks`` list. ``@retry`` covers
the unrelated case of a single callable that can fail transiently --
network calls, file I/O contention, flaky third-party APIs. Pure Python,
no dependency on the task executor.

Example::

    from visus.desktop.utils.retry import retry

    @retry(attempts=5, backoff="expo", base_delay=0.5,
           exceptions=(ConnectionError, TimeoutError))
    def fetch():
        return requests.get(url).json()
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)

_VALID_BACKOFFS = ("fixed", "expo")


def retry(
    attempts: int = 3,
    backoff: str = "expo",
    base_delay: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable:
    """Re-invoke the wrapped callable on transient failures.

    Args:
        attempts: Total invocations including the first try. Must be >= 1.
        backoff: Either ``'fixed'`` (constant ``base_delay`` between tries)
            or ``'expo'`` (``base_delay * 2 ** attempt``).
        base_delay: Seconds to sleep before the next attempt. ``0`` skips
            the sleep entirely (useful in tests).
        exceptions: Tuple of exception types eligible for retry. Anything
            else propagates immediately, exposing genuine bugs without
            burying them under retry noise.

    Returns:
        The decorator. After ``attempts`` exhaustion the most recent
        exception is re-raised so the caller sees the real failure.

    Raises:
        ValueError: If ``attempts < 1`` or ``backoff`` is unknown. These
            are programmer errors detected at decoration time, not at the
            call site, so they fail fast.
    """
    if attempts < 1:
        raise ValueError(f"attempts must be >= 1, got {attempts}")
    if backoff not in _VALID_BACKOFFS:
        raise ValueError(
            f"backoff must be one of {_VALID_BACKOFFS}, got {backoff!r}"
        )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc: BaseException | None = None
            for attempt in range(attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    remaining = attempts - attempt - 1
                    if remaining == 0:
                        break
                    delay = (
                        base_delay
                        if backoff == "fixed"
                        else base_delay * (2 ** attempt)
                    )
                    logger.debug(
                        "retry(%s): attempt %s/%s failed (%s); sleeping %.3fs",
                        func.__qualname__,
                        attempt + 1,
                        attempts,
                        exc,
                        delay,
                    )
                    if delay > 0:
                        time.sleep(delay)
            assert last_exc is not None  # loop body either returns or sets last_exc
            raise last_exc

        return wrapper

    return decorator

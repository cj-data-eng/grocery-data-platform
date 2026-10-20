"""A small retry helper with exponential backoff and jitter."""

import logging
import random
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def retry[T](
    func: Callable[[], T],
    *,
    attempts: int = 4,
    base_delay: float = 0.5,
    should_retry: Callable[[Exception], bool] = lambda exc: True,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``func`` until it succeeds, retrying failures that ``should_retry`` accepts.

    The wait doubles after each failure (0.5s, 1s, 2s, ...) plus a little random jitter
    so that many clients do not retry in lockstep. The last error is re-raised once
    ``attempts`` is used up, and errors that should not be retried are raised immediately.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    attempt = 1
    while True:
        try:
            return func()
        except Exception as exc:
            if attempt >= attempts or not should_retry(exc):
                raise
            delay = base_delay * 2 ** (attempt - 1)
            delay += random.uniform(0, delay / 2)
            logger.warning(
                "attempt failed, retrying",
                extra={"attempt": attempt, "max_attempts": attempts, "delay_s": round(delay, 2)},
            )
            sleep(delay)
            attempt += 1

"""Database retry decorators and utilities."""

import asyncio
import functools
import random
from collections.abc import Callable
from typing import Any, TypeVar

from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    OperationalError,
    TimeoutError,
)
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..metrics import get_db_metrics

# Type variables
F = TypeVar("F", bound=Callable[..., Any])

# Retryable database exceptions
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    OperationalError,
    DisconnectionError,
    TimeoutError,
    DBAPIError,
)

# Deadlock error codes (PostgreSQL)
DEADLOCK_ERROR_CODES = {"40001", "40P01"}


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable."""
    # Check if it's a known retryable exception type
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True

    # Check for deadlock errors
    if hasattr(error, "orig") and hasattr(error.orig, "pgcode"):
        return error.orig.pgcode in DEADLOCK_ERROR_CODES

    return False


def before_retry_callback(retry_state) -> None:
    """Callback to execute before retry with metrics."""
    metrics = get_db_metrics()
    attempt = retry_state.attempt_number
    error = retry_state.outcome.exception()

    # Log retry attempt
    tags = [
        f"attempt:{attempt}",
        f"error_type:{type(error).__name__}",
    ]
    metrics.statsd.increment("db.retry.attempt", tags=tags)


def db_retry(
    max_attempts: int = 3,
    min_wait: float = 0.1,
    max_wait: float = 2.0,
    multiplier: float = 2.0,
    randomize: bool = True,
) -> Callable[[F], F]:
    """
    Decorator for retrying database operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        multiplier: Multiplier for exponential backoff
        randomize: Add jitter to wait times
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metrics = get_db_metrics()

            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(
                    multiplier=multiplier,
                    min=min_wait,
                    max=max_wait,
                ),
                retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
                before=before_retry_callback,
                reraise=True,
            )
            def _retry_wrapper():
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if is_retryable_error(e):
                        if randomize:
                            # Add jitter to prevent thundering herd
                            jitter = random.uniform(0, min_wait)
                            asyncio.get_event_loop().call_later(jitter, lambda: None)
                        raise
                    else:
                        # Non-retryable error, propagate immediately
                        raise

            try:
                return _retry_wrapper()
            except RetryError as e:
                # Max retries exceeded
                metrics.statsd.increment(
                    "db.retry.exhausted",
                    tags=[f"error_type:{type(e.last_attempt.exception()).__name__}"],
                )
                raise e.last_attempt.exception() from e

        return wrapper  # type: ignore

    return decorator


def async_db_retry(
    max_attempts: int = 3,
    min_wait: float = 0.1,
    max_wait: float = 2.0,
    multiplier: float = 2.0,
    randomize: bool = True,
) -> Callable[[F], F]:
    """
    Decorator for retrying async database operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        multiplier: Multiplier for exponential backoff
        randomize: Add jitter to wait times
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_db_metrics()

            @retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(
                    multiplier=multiplier,
                    min=min_wait,
                    max=max_wait,
                ),
                retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
                before=before_retry_callback,
                reraise=True,
            )
            async def _retry_wrapper():
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if is_retryable_error(e):
                        if randomize:
                            # Add jitter to prevent thundering herd
                            jitter = random.uniform(0, min_wait)
                            await asyncio.sleep(jitter)
                        raise
                    else:
                        # Non-retryable error, propagate immediately
                        raise

            try:
                return await _retry_wrapper()
            except RetryError as e:
                # Max retries exceeded
                metrics.statsd.increment(
                    "db.retry.exhausted",
                    tags=[f"error_type:{type(e.last_attempt.exception()).__name__}"],
                )
                raise e.last_attempt.exception() from e

        return wrapper  # type: ignore

    return decorator

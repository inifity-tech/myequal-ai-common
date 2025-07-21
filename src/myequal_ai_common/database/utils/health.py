"""Database health check utilities."""

import time

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..engines import get_sync_engine
from ..metrics import get_db_metrics
from ..sessions import get_async_db


def check_database_health(
    timeout: float = 5.0,
    check_write: bool = False,
) -> dict[str, any]:
    """
    Check database health and connectivity.

    Args:
        timeout: Query timeout in seconds
        check_write: Also test write operations

    Returns:
        Dictionary with health check results
    """
    metrics = get_db_metrics()
    start_time = time.time()
    result = {
        "healthy": False,
        "response_time_ms": None,
        "error": None,
        "checks": {
            "connection": False,
            "read": False,
            "write": False,
        },
    }

    try:
        engine = get_sync_engine()

        # Test connection
        with engine.connect() as conn:
            result["checks"]["connection"] = True

            # Test read
            query_result = conn.execute(text("SELECT 1"))
            if query_result.scalar() == 1:
                result["checks"]["read"] = True

            # Test write if requested
            if check_write:
                # Create and drop a temporary table
                conn.execute(text("CREATE TEMP TABLE health_check_temp (id INT)"))
                conn.execute(text("INSERT INTO health_check_temp VALUES (1)"))
                conn.execute(text("DROP TABLE health_check_temp"))
                result["checks"]["write"] = True

        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        result["response_time_ms"] = response_time
        result["healthy"] = all(
            result["checks"][check]
            for check in ["connection", "read"]
            if check != "write" or check_write
        )

    except SQLAlchemyError as e:
        result["error"] = str(e)
        response_time = (time.time() - start_time) * 1000
        result["response_time_ms"] = response_time
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        response_time = (time.time() - start_time) * 1000
        result["response_time_ms"] = response_time

    # Record metrics
    metrics.record_health_check(
        healthy=result["healthy"],
        response_time=result["response_time_ms"],
        error=type(result.get("error")).__name__ if result.get("error") else None,
    )

    return result


async def async_check_database_health(
    timeout: float = 5.0,
    check_write: bool = False,
) -> dict[str, any]:
    """
    Async version of database health check.

    Args:
        timeout: Query timeout in seconds
        check_write: Also test write operations

    Returns:
        Dictionary with health check results
    """
    metrics = get_db_metrics()
    start_time = time.time()
    result = {
        "healthy": False,
        "response_time_ms": None,
        "error": None,
        "checks": {
            "connection": False,
            "read": False,
            "write": False,
        },
    }

    try:
        async with get_async_db() as session:
            # Test connection is established
            result["checks"]["connection"] = True

            # Test read
            query_result = await session.execute(text("SELECT 1"))
            if query_result.scalar() == 1:
                result["checks"]["read"] = True

            # Test write if requested
            if check_write:
                # Create and drop a temporary table
                await session.execute(
                    text("CREATE TEMP TABLE health_check_temp (id INT)")
                )
                await session.execute(text("INSERT INTO health_check_temp VALUES (1)"))
                await session.execute(text("DROP TABLE health_check_temp"))
                result["checks"]["write"] = True
                await session.commit()

        # Calculate response time
        response_time = (time.time() - start_time) * 1000
        result["response_time_ms"] = response_time
        result["healthy"] = all(
            result["checks"][check]
            for check in ["connection", "read"]
            if check != "write" or check_write
        )

    except SQLAlchemyError as e:
        result["error"] = str(e)
        response_time = (time.time() - start_time) * 1000
        result["response_time_ms"] = response_time
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        response_time = (time.time() - start_time) * 1000
        result["response_time_ms"] = response_time

    # Record metrics
    metrics.record_health_check(
        healthy=result["healthy"],
        response_time=result["response_time_ms"],
        error=type(result.get("error")).__name__ if result.get("error") else None,
    )

    return result

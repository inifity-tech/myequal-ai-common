"""Database-specific metrics collection."""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, List, Optional, TypeVar, Union

from datadog import DogStatsd

from .config import get_database_config

# Type variables
F = TypeVar("F", bound=Callable[..., Any])

# Global metrics client
_metrics_client: Optional["DatabaseMetrics"] = None


class DatabaseMetrics:
    """Database-specific metrics collection with Datadog."""

    def __init__(self, statsd_client: Optional[DogStatsd] = None):
        """Initialize database metrics."""
        self.config = get_database_config()
        self.statsd = statsd_client or DogStatsd(
            host="localhost",
            port=8125,
            namespace="myequal",
            constant_tags=[
                f"service:{self.config.service_name}",
                f"environment:{self.config.environment}",
            ],
        )
        self._base_tags = [
            f"service:{self.config.service_name}",
            f"environment:{self.config.environment}",
        ]

    def _get_tags(
        self,
        table: Optional[str] = None,
        operation: Optional[str] = None,
        status: Optional[str] = None,
        additional_tags: Optional[List[str]] = None,
    ) -> List[str]:
        """Build tags for metrics."""
        tags = self._base_tags.copy()
        
        if table:
            tags.append(f"table:{table}")
        if operation:
            tags.append(f"operation:{operation}")
        if status:
            tags.append(f"status:{status}")
        if additional_tags:
            tags.extend(additional_tags)
            
        return tags

    @contextmanager
    def record_query(
        self,
        table: str,
        operation: str,
        additional_tags: Optional[List[str]] = None,
    ):
        """Context manager to record query metrics."""
        start_time = time.time()
        status = "success"
        
        try:
            yield
        except Exception as e:
            status = "error"
            error_type = type(e).__name__
            tags = self._get_tags(table, operation, status, additional_tags)
            tags.append(f"error_type:{error_type}")
            
            # Record error
            self.statsd.increment("db.query.error", tags=tags)
            raise
        finally:
            # Record duration
            duration = (time.time() - start_time) * 1000  # Convert to ms
            tags = self._get_tags(table, operation, status, additional_tags)
            
            self.statsd.histogram("db.query.duration", duration, tags=tags)
            self.statsd.increment("db.query.count", tags=tags)

    @contextmanager
    def record_transaction(
        self,
        tables: Optional[List[str]] = None,
        additional_tags: Optional[List[str]] = None,
    ):
        """Context manager to record transaction metrics."""
        start_time = time.time()
        status = "success"
        rollback = False
        
        try:
            yield
        except Exception as e:
            status = "error"
            rollback = True
            error_type = type(e).__name__
            tags = self._get_tags(
                table=",".join(tables) if tables else None,
                operation="transaction",
                status=status,
                additional_tags=additional_tags,
            )
            tags.append(f"error_type:{error_type}")
            
            # Record error
            self.statsd.increment("db.transaction.error", tags=tags)
            raise
        finally:
            # Record duration
            duration = (time.time() - start_time) * 1000  # Convert to ms
            tags = self._get_tags(
                table=",".join(tables) if tables else None,
                operation="transaction",
                status=status,
                additional_tags=additional_tags,
            )
            
            self.statsd.histogram("db.transaction.duration", duration, tags=tags)
            self.statsd.increment("db.transaction.count", tags=tags)
            
            if rollback:
                self.statsd.increment("db.transaction.rollback", tags=tags)

    def record_pool_stats(
        self,
        pool_size: int,
        checked_in: int,
        checked_out: int,
        overflow: int,
        total: int,
    ):
        """Record connection pool statistics."""
        tags = self._base_tags
        
        self.statsd.gauge("db.pool.size", pool_size, tags=tags)
        self.statsd.gauge("db.pool.connections.checked_in", checked_in, tags=tags)
        self.statsd.gauge("db.pool.connections.checked_out", checked_out, tags=tags)
        self.statsd.gauge("db.pool.connections.overflow", overflow, tags=tags)
        self.statsd.gauge("db.pool.connections.total", total, tags=tags)

    def record_health_check(
        self,
        healthy: bool,
        response_time: Optional[float] = None,
        error: Optional[str] = None,
    ):
        """Record database health check result."""
        tags = self._base_tags.copy()
        tags.append(f"healthy:{str(healthy).lower()}")
        
        if error:
            tags.append(f"error_type:{error}")
        
        self.statsd.gauge("db.health.status", 1 if healthy else 0, tags=tags)
        
        if response_time is not None:
            self.statsd.histogram("db.health.response_time", response_time, tags=tags)

    def query_timer(
        self,
        table: str,
        operation: str,
        additional_tags: Optional[List[str]] = None,
    ):
        """Decorator to time database queries."""
        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.record_query(table, operation, additional_tags):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def async_query_timer(
        self,
        table: str,
        operation: str,
        additional_tags: Optional[List[str]] = None,
    ):
        """Decorator to time async database queries."""
        def decorator(func: F) -> F:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                with self.record_query(table, operation, additional_tags):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator


def get_db_metrics() -> DatabaseMetrics:
    """Get or create database metrics instance."""
    global _metrics_client
    if _metrics_client is None:
        _metrics_client = DatabaseMetrics()
    return _metrics_client
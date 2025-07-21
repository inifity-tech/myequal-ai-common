"""Database engine factories with connection pooling and metrics."""

import asyncio
import threading

from sqlalchemy import NullPool, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as async_create_engine

from .config import get_database_config
from .metrics import get_db_metrics

# Thread-safe engine storage
_sync_engine: Engine | None = None
_async_engine: AsyncEngine | None = None
_engine_lock = threading.Lock()


def _setup_pool_metrics(engine: Engine) -> None:
    """Set up connection pool metrics collection."""
    metrics = get_db_metrics()

    def collect_pool_metrics():
        """Collect and send pool metrics."""
        pool = engine.pool
        if hasattr(pool, "size"):
            metrics.record_pool_stats(
                pool_size=pool.size(),  # type: ignore
                checked_in=pool.checkedin(),  # type: ignore
                checked_out=pool.checkedout(),  # type: ignore
                overflow=pool.overflow(),  # type: ignore
                total=pool.total_connections(),  # type: ignore
            )

    # Set up periodic collection (every 30 seconds)
    def schedule_metrics():
        while True:
            try:
                collect_pool_metrics()
            except Exception:
                pass  # Don't let metrics collection break the app
            asyncio.get_event_loop().call_later(30, schedule_metrics)

    # Start metrics collection
    if not isinstance(engine.pool, NullPool):
        threading.Thread(target=schedule_metrics, daemon=True).start()


def create_sync_engine(database_url: str | None = None, **kwargs) -> Engine:
    """Create a synchronous database engine with metrics."""
    config = get_database_config()
    url = database_url or config.sync_url

    # Get engine configuration
    engine_kwargs = config.get_engine_kwargs(is_async=False)
    engine_kwargs.update(kwargs)

    # Handle poolclass string
    if isinstance(engine_kwargs.get("poolclass"), str):
        if engine_kwargs["poolclass"] == "NullPool":
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.pop("poolclass", None)

    # Create engine
    engine = create_engine(url, **engine_kwargs)

    # Set up pool metrics if not using NullPool
    if not isinstance(engine.pool, NullPool):
        _setup_pool_metrics(engine)

    # Add connection event listeners for metrics
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Track connection creation."""
        metrics = get_db_metrics()
        metrics.statsd.increment("db.connection.created", tags=metrics._base_tags)

    @event.listens_for(engine, "close")
    def receive_close(dbapi_conn, connection_record):
        """Track connection closure."""
        metrics = get_db_metrics()
        metrics.statsd.increment("db.connection.closed", tags=metrics._base_tags)

    return engine


def create_async_engine(database_url: str | None = None, **kwargs) -> AsyncEngine:
    """Create an asynchronous database engine with metrics."""
    config = get_database_config()
    url = database_url or config.async_url

    # Get engine configuration
    engine_kwargs = config.get_engine_kwargs(is_async=True)
    engine_kwargs.update(kwargs)

    # Handle poolclass string
    if isinstance(engine_kwargs.get("poolclass"), str):
        if engine_kwargs["poolclass"] == "NullPool":
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs.pop("poolclass", None)

    # Create engine
    engine = async_create_engine(url, **engine_kwargs)

    # Note: Pool metrics for async engines need to be handled differently
    # due to the async nature of the connection pool

    return engine


def get_sync_engine() -> Engine:
    """Get or create the global sync engine."""
    global _sync_engine

    if _sync_engine is None:
        with _engine_lock:
            if _sync_engine is None:
                _sync_engine = create_sync_engine()

    return _sync_engine


def get_async_engine() -> AsyncEngine:
    """Get or create the global async engine."""
    global _async_engine

    if _async_engine is None:
        with _engine_lock:
            if _async_engine is None:
                _async_engine = create_async_engine()

    return _async_engine


async def close_async_engine() -> None:
    """Close the async engine and cleanup connections."""
    global _async_engine

    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None


def close_sync_engine() -> None:
    """Close the sync engine and cleanup connections."""
    global _sync_engine

    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None

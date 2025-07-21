"""Database session management with automatic metrics."""

from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from .engines import get_async_engine, get_sync_engine
from .metrics import get_db_metrics

# Global session makers
_sync_session_maker: sessionmaker | None = None
_async_session_maker: async_sessionmaker | None = None


def get_sync_session_maker() -> sessionmaker:
    """Get or create sync session maker."""
    global _sync_session_maker

    if _sync_session_maker is None:
        engine = get_sync_engine()
        _sync_session_maker = sessionmaker(
            bind=engine,
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )

    return _sync_session_maker


def get_async_session_maker() -> async_sessionmaker:
    """Get or create async session maker."""
    global _async_session_maker

    if _async_session_maker is None:
        engine = get_async_engine()
        _async_session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    return _async_session_maker


# Convenience aliases
SyncSessionMaker = sessionmaker
AsyncSessionMaker = async_sessionmaker


@contextmanager
def get_sync_db() -> Generator[Session, None, None]:
    """Get a sync database session with automatic cleanup and metrics."""
    metrics = get_db_metrics()
    session_maker = get_sync_session_maker()
    session = session_maker()

    try:
        # Track session creation
        metrics.statsd.increment("db.session.created", tags=metrics._base_tags)
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        # Track session closure
        metrics.statsd.increment("db.session.closed", tags=metrics._base_tags)


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session with automatic cleanup and metrics."""
    metrics = get_db_metrics()
    session_maker = get_async_session_maker()

    async with session_maker() as session:
        try:
            # Track session creation
            metrics.statsd.increment("db.session.created", tags=metrics._base_tags)
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            # Track session closure
            metrics.statsd.increment("db.session.closed", tags=metrics._base_tags)


@contextmanager
def get_sync_transactional_db() -> Generator[Session, None, None]:
    """Get a sync database session with automatic transaction management."""
    metrics = get_db_metrics()

    with get_sync_db() as session:
        with metrics.record_transaction():
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


@asynccontextmanager
async def get_async_transactional_db() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session with automatic transaction management."""
    metrics = get_db_metrics()

    async with get_async_db() as session:
        with metrics.record_transaction():
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# FastAPI dependency functions
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for sync database sessions."""
    with get_sync_db() as session:
        yield session


async def get_async_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database sessions."""
    async with get_async_db() as session:
        yield session

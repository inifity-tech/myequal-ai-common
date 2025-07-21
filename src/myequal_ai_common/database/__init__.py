"""Database module for MyEqual AI common utilities."""

from .base_manager import AsyncBaseDBManager, BaseDBManager
from .config import DatabaseConfig, get_database_config
from .engines import (
    close_async_engine,
    close_sync_engine,
    create_async_engine,
    create_sync_engine,
    get_async_engine,
    get_sync_engine,
)
from .examples import AsyncUserManager, User, UserManager
from .exceptions import (
    ConnectionError,
    DatabaseError,
    DuplicateRecordError,
    PoolExhaustedError,
    RecordNotFoundError,
    TransactionError,
    ValidationError,
)
from .metrics import DatabaseMetrics, get_db_metrics
from .sessions import (
    AsyncSessionMaker,
    SyncSessionMaker,
    get_async_db,
    get_async_db_dependency,
    get_async_transactional_db,
    get_db,
    get_sync_db,
    get_sync_transactional_db,
)
from .utils import (
    async_check_database_health,
    async_db_retry,
    check_database_health,
    db_retry,
)

__all__ = [
    # Configuration
    "DatabaseConfig",
    "get_database_config",
    # Engines
    "create_async_engine",
    "create_sync_engine",
    "get_async_engine",
    "get_sync_engine",
    "close_async_engine",
    "close_sync_engine",
    # Sessions
    "AsyncSessionMaker",
    "SyncSessionMaker",
    "get_async_db",
    "get_sync_db",
    "get_async_transactional_db",
    "get_sync_transactional_db",
    "get_db",
    "get_async_db_dependency",
    # Base Managers
    "BaseDBManager",
    "AsyncBaseDBManager",
    # Metrics
    "DatabaseMetrics",
    "get_db_metrics",
    # Exceptions
    "DatabaseError",
    "ConnectionError",
    "PoolExhaustedError",
    "TransactionError",
    "RecordNotFoundError",
    "DuplicateRecordError",
    "ValidationError",
    # Utils
    "db_retry",
    "async_db_retry",
    "check_database_health",
    "async_check_database_health",
    # Examples
    "User",
    "UserManager",
    "AsyncUserManager",
]

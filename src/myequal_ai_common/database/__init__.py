"""Database module for MyEqual AI common utilities."""

# Core database components
from .base_manager import AsyncBaseDBManager, BaseDBManager
from .config import DatabaseConfig, get_database_config
from .sessions import get_async_db, get_sync_db

# Exception handling
from .exceptions import DatabaseError

# Utilities
from .utils import async_check_database_health, check_database_health

__all__ = [
    # Core components
    "BaseDBManager",
    "AsyncBaseDBManager", 
    "DatabaseConfig",
    "get_database_config",
    "get_async_db",
    "get_sync_db",
    # Exception handling
    "DatabaseError",
    # Health checks
    "check_database_health",
    "async_check_database_health",
]

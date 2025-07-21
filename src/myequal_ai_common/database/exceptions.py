"""Database-specific exceptions."""

from typing import Any


class DatabaseError(Exception):
    """Base exception for database operations."""

    def __init__(
        self,
        message: str,
        table: str | None = None,
        operation: str | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize database error with context."""
        super().__init__(message)
        self.table = table
        self.operation = operation
        self.original_error = original_error

    def __str__(self) -> str:
        """String representation with context."""
        parts = [str(self.args[0])]
        if self.table:
            parts.append(f"Table: {self.table}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.original_error:
            parts.append(
                f"Original error: {type(self.original_error).__name__}: {self.original_error}"
            )
        return " | ".join(parts)


class ConnectionError(DatabaseError):
    """Database connection errors."""

    pass


class PoolExhaustedError(ConnectionError):
    """Connection pool exhausted error."""

    def __init__(self, pool_size: int, timeout: float):
        """Initialize with pool details."""
        super().__init__(
            f"Connection pool exhausted. Size: {pool_size}, Timeout: {timeout}s"
        )
        self.pool_size = pool_size
        self.timeout = timeout


class TransactionError(DatabaseError):
    """Transaction-related errors."""

    pass


class RecordNotFoundError(DatabaseError):
    """Record not found error."""

    def __init__(self, table: str, id: Any):
        """Initialize with record details."""
        super().__init__(
            "Record not found",
            table=table,
            operation="get",
        )
        self.record_id = id


class DuplicateRecordError(DatabaseError):
    """Duplicate record error."""

    def __init__(self, table: str, field: str, value: Any):
        """Initialize with duplicate details."""
        super().__init__(
            f"Duplicate value for {field}: {value}",
            table=table,
            operation="insert",
        )
        self.field = field
        self.value = value


class ValidationError(DatabaseError):
    """Data validation error."""

    def __init__(self, message: str, field: str, value: Any):
        """Initialize with validation details."""
        super().__init__(message)
        self.field = field
        self.value = value

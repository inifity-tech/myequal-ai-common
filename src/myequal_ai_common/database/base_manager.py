"""Base database manager classes with built-in metrics."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, TypeVar

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from .metrics import get_db_metrics

# Type variable for model classes
ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseDBManager[ModelType: SQLModel](ABC):
    """Base class for sync database managers with metrics."""

    def __init__(self, db_session: Session):
        """Initialize the manager with a database session."""
        self.db = db_session
        self.metrics = get_db_metrics()
        self._in_transaction = False

    @property
    @abstractmethod
    def model_class(self) -> type[ModelType]:
        """Return the model class this manager handles."""
        pass

    @property
    def table_name(self) -> str:
        """Get the table name from the model."""
        return self.model_class.__tablename__

    @contextmanager
    def transaction(self):
        """Context manager for transactions with metrics."""
        if self._in_transaction:
            # Already in a transaction, just yield
            yield
        else:
            self._in_transaction = True
            with self.metrics.record_transaction(tables=[self.table_name]):
                try:
                    yield
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    raise
                finally:
                    self._in_transaction = False

    def create(self, **kwargs) -> ModelType:
        """Create a new record with metrics."""
        with self.metrics.record_query(self.table_name, "insert"):
            instance = self.model_class(**kwargs)
            self.db.add(instance)

            if not self._in_transaction:
                self.db.commit()
                self.db.refresh(instance)

            return instance

    def get(self, id: Any) -> ModelType | None:
        """Get a record by ID with metrics."""
        with self.metrics.record_query(self.table_name, "select"):
            query = select(self.model_class).where(self.model_class.id == id)
            result = self.db.execute(query)
            return result.scalar_one_or_none()

    def get_by(self, **filters) -> ModelType | None:
        """Get a single record by filters with metrics."""
        with self.metrics.record_query(self.table_name, "select"):
            query = select(self.model_class).filter_by(**filters)
            result = self.db.execute(query)
            return result.scalar_one_or_none()

    def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
    ) -> list[ModelType]:
        """List records with optional filters and pagination with metrics."""
        with self.metrics.record_query(self.table_name, "select"):
            query = select(self.model_class)

            if filters:
                conditions = []
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        conditions.append(getattr(self.model_class, key) == value)
                if conditions:
                    query = query.where(and_(*conditions))

            if order_by:
                if order_by.startswith("-"):
                    query = query.order_by(
                        getattr(self.model_class, order_by[1:]).desc()
                    )
                else:
                    query = query.order_by(getattr(self.model_class, order_by))

            if offset:
                query = query.offset(offset)

            if limit:
                query = query.limit(limit)

            result = self.db.execute(query)
            return result.scalars().all()

    def update(self, id: Any, **kwargs) -> ModelType | None:
        """Update a record with metrics."""
        with self.metrics.record_query(self.table_name, "update"):
            instance = self.get(id)
            if not instance:
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            if not self._in_transaction:
                self.db.commit()
                self.db.refresh(instance)

            return instance

    def delete(self, id: Any) -> bool:
        """Delete a record with metrics."""
        with self.metrics.record_query(self.table_name, "delete"):
            instance = self.get(id)
            if not instance:
                return False

            self.db.delete(instance)

            if not self._in_transaction:
                self.db.commit()

            return True

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filters with metrics."""
        with self.metrics.record_query(self.table_name, "count"):
            query = select(func.count()).select_from(self.model_class)

            if filters:
                conditions = []
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        conditions.append(getattr(self.model_class, key) == value)
                if conditions:
                    query = query.where(and_(*conditions))

            result = self.db.execute(query)
            return result.scalar() or 0

    def exists(self, **filters) -> bool:
        """Check if a record exists with metrics."""
        with self.metrics.record_query(self.table_name, "exists"):
            query = (
                select(func.count())
                .select_from(self.model_class)
                .filter_by(**filters)
                .limit(1)
            )
            result = self.db.execute(query)
            return (result.scalar() or 0) > 0

    def execute_query(self, query, operation: str = "custom") -> Any:
        """Execute a custom query with metrics."""
        with self.metrics.record_query(self.table_name, operation):
            result = self.db.execute(query)
            if not self._in_transaction:
                self.db.commit()
            return result

    def execute_raw_sql(
        self, sql: str, params: dict[str, Any] | None = None, operation: str = "raw_sql"
    ) -> Any:
        """Execute raw SQL with metrics."""
        with self.metrics.record_query(self.table_name, operation):
            result = self.db.execute(text(sql), params or {})
            if not self._in_transaction:
                self.db.commit()
            return result

    def bulk_create(self, instances: list[ModelType]) -> list[ModelType]:
        """Bulk create records with metrics."""
        with self.metrics.record_query(self.table_name, "bulk_insert"):
            self.db.add_all(instances)
            if not self._in_transaction:
                self.db.commit()
                for instance in instances:
                    self.db.refresh(instance)
            return instances

    def bulk_update(self, updates: list[dict[str, Any]]) -> int:
        """Bulk update records with metrics."""
        with self.metrics.record_query(self.table_name, "bulk_update"):
            # Each update dict should have 'id' and fields to update
            count = 0
            for update_data in updates:
                id_value = update_data.pop("id", None)
                if id_value and update_data:
                    result = self.db.execute(
                        self.model_class.__table__.update()
                        .where(self.model_class.id == id_value)
                        .values(**update_data)
                    )
                    count += result.rowcount

            if not self._in_transaction:
                self.db.commit()
            return count


class AsyncBaseDBManager[ModelType: SQLModel](ABC):
    """Base class for async database managers with metrics."""

    def __init__(self, db_session: AsyncSession):
        """Initialize the manager with an async database session."""
        self.db = db_session
        self.metrics = get_db_metrics()
        self._in_transaction = False

    @property
    @abstractmethod
    def model_class(self) -> type[ModelType]:
        """Return the model class this manager handles."""
        pass

    @property
    def table_name(self) -> str:
        """Get the table name from the model."""
        return self.model_class.__tablename__

    @contextmanager
    def transaction(self):
        """Context manager for transactions with metrics."""
        if self._in_transaction:
            # Already in a transaction, just yield
            yield
        else:
            self._in_transaction = True
            with self.metrics.record_transaction(tables=[self.table_name]):
                try:
                    yield
                    # Note: commit needs to be awaited in the async context
                except Exception:
                    # Note: rollback needs to be awaited in the async context
                    raise
                finally:
                    self._in_transaction = False

    async def create(self, **kwargs) -> ModelType:
        """Create a new record with metrics."""
        with self.metrics.record_query(self.table_name, "insert"):
            instance = self.model_class(**kwargs)
            self.db.add(instance)

            if not self._in_transaction:
                await self.db.commit()
                await self.db.refresh(instance)

            return instance

    async def get(self, id: Any) -> ModelType | None:
        """Get a record by ID with metrics."""
        with self.metrics.record_query(self.table_name, "select"):
            query = select(self.model_class).where(self.model_class.id == id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

    async def get_by(self, **filters) -> ModelType | None:
        """Get a single record by filters with metrics."""
        with self.metrics.record_query(self.table_name, "select"):
            query = select(self.model_class).filter_by(**filters)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

    async def list(
        self,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        order_by: str | None = None,
    ) -> list[ModelType]:
        """List records with optional filters and pagination with metrics."""
        with self.metrics.record_query(self.table_name, "select"):
            query = select(self.model_class)

            if filters:
                conditions = []
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        conditions.append(getattr(self.model_class, key) == value)
                if conditions:
                    query = query.where(and_(*conditions))

            if order_by:
                if order_by.startswith("-"):
                    query = query.order_by(
                        getattr(self.model_class, order_by[1:]).desc()
                    )
                else:
                    query = query.order_by(getattr(self.model_class, order_by))

            if offset:
                query = query.offset(offset)

            if limit:
                query = query.limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()

    async def update(self, id: Any, **kwargs) -> ModelType | None:
        """Update a record with metrics."""
        with self.metrics.record_query(self.table_name, "update"):
            instance = await self.get(id)
            if not instance:
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            if not self._in_transaction:
                await self.db.commit()
                await self.db.refresh(instance)

            return instance

    async def delete(self, id: Any) -> bool:
        """Delete a record with metrics."""
        with self.metrics.record_query(self.table_name, "delete"):
            instance = await self.get(id)
            if not instance:
                return False

            await self.db.delete(instance)

            if not self._in_transaction:
                await self.db.commit()

            return True

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count records with optional filters with metrics."""
        with self.metrics.record_query(self.table_name, "count"):
            query = select(func.count()).select_from(self.model_class)

            if filters:
                conditions = []
                for key, value in filters.items():
                    if hasattr(self.model_class, key):
                        conditions.append(getattr(self.model_class, key) == value)
                if conditions:
                    query = query.where(and_(*conditions))

            result = await self.db.execute(query)
            return result.scalar() or 0

    async def exists(self, **filters) -> bool:
        """Check if a record exists with metrics."""
        with self.metrics.record_query(self.table_name, "exists"):
            query = (
                select(func.count())
                .select_from(self.model_class)
                .filter_by(**filters)
                .limit(1)
            )
            result = await self.db.execute(query)
            return (result.scalar() or 0) > 0

    async def execute_query(self, query, operation: str = "custom") -> Any:
        """Execute a custom query with metrics."""
        with self.metrics.record_query(self.table_name, operation):
            result = await self.db.execute(query)
            if not self._in_transaction:
                await self.db.commit()
            return result

    async def execute_raw_sql(
        self, sql: str, params: dict[str, Any] | None = None, operation: str = "raw_sql"
    ) -> Any:
        """Execute raw SQL with metrics."""
        with self.metrics.record_query(self.table_name, operation):
            result = await self.db.execute(text(sql), params or {})
            if not self._in_transaction:
                await self.db.commit()
            return result

    async def bulk_create(self, instances: list[ModelType]) -> list[ModelType]:
        """Bulk create records with metrics."""
        with self.metrics.record_query(self.table_name, "bulk_insert"):
            self.db.add_all(instances)
            if not self._in_transaction:
                await self.db.commit()
                for instance in instances:
                    await self.db.refresh(instance)
            return instances

    async def bulk_update(self, updates: list[dict[str, Any]]) -> int:
        """Bulk update records with metrics."""
        with self.metrics.record_query(self.table_name, "bulk_update"):
            # Each update dict should have 'id' and fields to update
            count = 0
            for update_data in updates:
                id_value = update_data.pop("id", None)
                if id_value and update_data:
                    result = await self.db.execute(
                        self.model_class.__table__.update()
                        .where(self.model_class.id == id_value)
                        .values(**update_data)
                    )
                    count += result.rowcount

            if not self._in_transaction:
                await self.db.commit()
            return count

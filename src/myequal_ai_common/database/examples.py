"""Example implementations of database managers."""

from datetime import datetime

from sqlalchemy import select
from sqlmodel import Field, SQLModel

from .base_manager import AsyncBaseDBManager, BaseDBManager


# Example model
class User(SQLModel, table=True):
    """Example user model."""

    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserManager(BaseDBManager[User]):
    """Example sync manager for User model."""

    @property
    def model_class(self) -> type[User]:
        """Return the User model class."""
        return User

    def get_by_email(self, email: str) -> User | None:
        """Get user by email with metrics."""
        return self.get_by(email=email)

    def get_active_users(self, limit: int = 100) -> list[User]:
        """Get active users using custom query."""
        query = select(User).where(User.is_active.is_(True)).limit(limit)
        result = self.execute_query(query, operation="get_active_users")
        return result.scalars().all()

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user using raw SQL."""
        sql = """
            UPDATE users
            SET is_active = false, updated_at = :updated_at
            WHERE id = :user_id AND is_active = true
        """
        result = self.execute_raw_sql(
            sql,
            {"user_id": user_id, "updated_at": datetime.utcnow()},
            operation="deactivate_user",
        )
        return result.rowcount > 0

    def bulk_create_users(self, users_data: list[dict]) -> list[User]:
        """Create multiple users at once."""
        users = [User(**data) for data in users_data]
        return self.bulk_create(users)

    def get_user_stats(self) -> dict:
        """Get user statistics using raw SQL."""
        sql = """
            SELECT
                COUNT(*) as total_users,
                COUNT(*) FILTER (WHERE is_active = true) as active_users,
                COUNT(*) FILTER (WHERE created_at > CURRENT_DATE - INTERVAL '7 days') as new_users_7d
            FROM users
        """
        result = self.execute_raw_sql(sql, operation="user_stats")
        row = result.fetchone()
        return {"total_users": row[0], "active_users": row[1], "new_users_7d": row[2]}


class AsyncUserManager(AsyncBaseDBManager[User]):
    """Example async manager for User model."""

    @property
    def model_class(self) -> type[User]:
        """Return the User model class."""
        return User

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email with metrics."""
        return await self.get_by(email=email)

    async def get_active_users(self, limit: int = 100) -> list[User]:
        """Get active users using custom query."""
        query = select(User).where(User.is_active.is_(True)).limit(limit)
        result = await self.execute_query(query, operation="get_active_users")
        return result.scalars().all()

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user using raw SQL."""
        sql = """
            UPDATE users
            SET is_active = false, updated_at = :updated_at
            WHERE id = :user_id AND is_active = true
        """
        result = await self.execute_raw_sql(
            sql,
            {"user_id": user_id, "updated_at": datetime.utcnow()},
            operation="deactivate_user",
        )
        return result.rowcount > 0

    async def bulk_create_users(self, users_data: list[dict]) -> list[User]:
        """Create multiple users at once."""
        users = [User(**data) for data in users_data]
        return await self.bulk_create(users)

    async def get_user_stats(self) -> dict:
        """Get user statistics using raw SQL."""
        sql = """
            SELECT
                COUNT(*) as total_users,
                COUNT(*) FILTER (WHERE is_active = true) as active_users,
                COUNT(*) FILTER (WHERE created_at > CURRENT_DATE - INTERVAL '7 days') as new_users_7d
            FROM users
        """
        result = await self.execute_raw_sql(sql, operation="user_stats")
        row = result.fetchone()
        return {"total_users": row[0], "active_users": row[1], "new_users_7d": row[2]}


# Usage examples in comments:
"""
# Sync usage:
from myequal_ai_common.database import get_sync_db
from myequal_ai_common.database.examples import UserManager

with get_sync_db() as db:
    user_manager = UserManager(db)

    # Basic CRUD
    user = user_manager.create(email="test@example.com", name="Test User")
    user = user_manager.get(user.id)
    user = user_manager.update(user.id, name="Updated Name")

    # Custom queries
    active_users = user_manager.get_active_users()
    stats = user_manager.get_user_stats()

    # Transactions
    with user_manager.transaction():
        user1 = user_manager.create(email="user1@example.com", name="User 1")
        user2 = user_manager.create(email="user2@example.com", name="User 2")


# Async usage:
from myequal_ai_common.database import get_async_db
from myequal_ai_common.database.examples import AsyncUserManager

async with get_async_db() as db:
    user_manager = AsyncUserManager(db)

    # Basic CRUD
    user = await user_manager.create(email="test@example.com", name="Test User")
    user = await user_manager.get(user.id)
    user = await user_manager.update(user.id, name="Updated Name")

    # Custom queries
    active_users = await user_manager.get_active_users()
    stats = await user_manager.get_user_stats()

    # Transactions
    with user_manager.transaction():
        user1 = await user_manager.create(email="user1@example.com", name="User 1")
        user2 = await user_manager.create(email="user2@example.com", name="User 2")
"""

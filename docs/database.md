# Database Module Usage Guide

The `myequal_ai_common.database` module provides a comprehensive database management solution with built-in Datadog metrics, connection pooling, retry logic, and health checks.

## Features

- **Dual Support**: Both synchronous and asynchronous database operations
- **Automatic Metrics**: Every database operation is tracked in Datadog
- **Connection Pooling**: Production-ready connection pool management
- **Retry Logic**: Automatic retry with exponential backoff for transient errors
- **Health Checks**: Database connectivity and performance monitoring
- **Base Manager Classes**: Consistent CRUD operations with metrics
- **Transaction Management**: Simplified transaction handling

## Configuration

Set up database configuration via environment variables:

```bash
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/mydb

# Optional
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_QUERY_TIMEOUT=30
DATABASE_SERVICE_NAME=my-service
DATABASE_ENVIRONMENT=production
```

Or programmatically:

```python
from myequal_ai_common.database import DatabaseConfig

config = DatabaseConfig(
    url="postgresql://user:password@localhost:5432/mydb",
    pool_size=10,
    service_name="my-service",
    environment="production"
)
```

## Basic Usage

### Synchronous Operations

```python
from myequal_ai_common.database import get_sync_db, BaseDBManager
from sqlmodel import SQLModel, Field

# Define your model
class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str
    email: str

# Create a manager
class UserManager(BaseDBManager[User]):
    @property
    def model_class(self):
        return User

# Use in your application
with get_sync_db() as db:
    user_manager = UserManager(db)
    
    # Create
    user = user_manager.create(name="John", email="john@example.com")
    
    # Read
    user = user_manager.get(1)
    users = user_manager.list(filters={"name": "John"})
    
    # Update
    user = user_manager.update(1, email="newemail@example.com")
    
    # Delete
    success = user_manager.delete(1)
```

### Asynchronous Operations

```python
from myequal_ai_common.database import get_async_db, AsyncBaseDBManager

class AsyncUserManager(AsyncBaseDBManager[User]):
    @property
    def model_class(self):
        return User

# Use in your async application
async with get_async_db() as db:
    user_manager = AsyncUserManager(db)
    
    # All operations are async
    user = await user_manager.create(name="Jane", email="jane@example.com")
    users = await user_manager.list()
```

### FastAPI Integration

```python
from fastapi import Depends
from myequal_ai_common.database import get_db, get_async_db_dependency

# Sync endpoint
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    user_manager = UserManager(db)
    return user_manager.list()

# Async endpoint
@app.get("/async-users")
async def get_async_users(db: AsyncSession = Depends(get_async_db_dependency)):
    user_manager = AsyncUserManager(db)
    return await user_manager.list()
```

## Advanced Features

### Transaction Management

```python
# Sync transactions
with get_sync_db() as db:
    manager = UserManager(db)
    
    with manager.transaction():
        user1 = manager.create(name="User1", email="user1@example.com")
        user2 = manager.create(name="User2", email="user2@example.com")
        # Both are committed together

# Async transactions
async with get_async_transactional_db() as db:
    manager = AsyncUserManager(db)
    user = await manager.create(name="User", email="user@example.com")
    # Automatically committed
```

### Retry Logic

```python
from myequal_ai_common.database import db_retry, async_db_retry

@db_retry(max_attempts=3)
def risky_operation(db):
    # This will retry on connection errors, deadlocks, etc.
    return db.execute("SELECT * FROM large_table")

@async_db_retry(max_attempts=5, max_wait=10.0)
async def async_risky_operation(db):
    # Async version with custom retry parameters
    return await db.execute("UPDATE users SET active = true")
```

### Health Checks

```python
from myequal_ai_common.database import check_database_health

# Sync health check
health = check_database_health(timeout=5.0, check_write=True)
print(health)
# {
#     "healthy": True,
#     "response_time_ms": 12.5,
#     "checks": {
#         "connection": True,
#         "read": True,
#         "write": True
#     }
# }

# Async health check
health = await async_check_database_health()
```

## Metrics

All database operations are automatically tracked in Datadog:

### Query Metrics
- `myequal.db.query.count` - Number of queries by service/table/operation
- `myequal.db.query.duration` - Query execution time (histogram)
- `myequal.db.query.error` - Query errors

### Transaction Metrics
- `myequal.db.transaction.count` - Transaction count
- `myequal.db.transaction.duration` - Transaction duration
- `myequal.db.transaction.rollback` - Rollback count

### Connection Pool Metrics
- `myequal.db.pool.size` - Pool size
- `myequal.db.pool.connections.checked_in` - Available connections
- `myequal.db.pool.connections.checked_out` - In-use connections
- `myequal.db.pool.connections.overflow` - Overflow connections

### Health Check Metrics
- `myequal.db.health.status` - Health status (0 or 1)
- `myequal.db.health.response_time` - Health check response time

### Session Metrics
- `myequal.db.session.created` - Session creation count
- `myequal.db.session.closed` - Session closure count

### Retry Metrics
- `myequal.db.retry.attempt` - Retry attempts
- `myequal.db.retry.exhausted` - Max retries exceeded

## Custom Managers

Extend the base managers for custom functionality:

```python
class AdvancedUserManager(BaseDBManager[User]):
    @property
    def model_class(self):
        return User
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Custom method with automatic metrics."""
        # Metrics are automatically collected via base class
        return self.get_by(email=email)
    
    def bulk_create(self, users_data: List[dict]) -> List[User]:
        """Bulk create with transaction."""
        with self.transaction():
            users = []
            for data in users_data:
                user = self.create(**data)
                users.append(user)
            return users
```

## Error Handling

The module provides custom exceptions for better error handling:

```python
from myequal_ai_common.database import (
    RecordNotFoundError,
    DuplicateRecordError,
    ConnectionError,
    TransactionError
)

try:
    user = manager.get(999)
except RecordNotFoundError as e:
    print(f"User not found: {e}")

try:
    user = manager.create(email="duplicate@example.com")
except DuplicateRecordError as e:
    print(f"Email already exists: {e}")
```

## Migration Example

Migrating from existing code to the common library:

```python
# Before (in service)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# After (using common library)
from myequal_ai_common.database import get_db
# That's it! Metrics and all features included
```

## Environment-Specific Configuration

The library automatically adjusts behavior based on environment:

- **Production**: Connection pooling enabled, metrics collected
- **Development**: NullPool (no pooling), debug logging available

## Best Practices

1. **Use Managers**: Always use the base manager classes for consistent metrics
2. **Environment Variables**: Configure via environment for easy deployment
3. **Service Names**: Set unique `DATABASE_SERVICE_NAME` for each service
4. **Health Checks**: Implement health endpoints using the provided utilities
5. **Transaction Scope**: Keep transactions as small as possible
6. **Retry Carefully**: Only use retry decorators for idempotent operations

## Troubleshooting

### Connection Pool Exhausted

If you see pool exhaustion errors:
1. Check `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW`
2. Look for connection leaks (sessions not being closed)
3. Monitor `db.pool.connections.*` metrics in Datadog

### Slow Queries

Monitor `db.query.duration` metrics by table and operation to identify bottlenecks.

### Failed Health Checks

Check `db.health.*` metrics and logs for specific error types.

## Complete Example

Here's a complete example for a user service:

```python
from typing import Optional, List
from sqlmodel import Field, SQLModel
from myequal_ai_common.database import (
    BaseDBManager,
    get_sync_db,
    db_retry,
    check_database_health
)

# Model
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    active: bool = Field(default=True)

# Manager
class UserManager(BaseDBManager[User]):
    @property
    def model_class(self):
        return User
    
    @db_retry(max_attempts=3)
    def find_active_users(self) -> List[User]:
        """Find all active users with retry logic."""
        return self.list(filters={"active": True})
    
    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user."""
        return self.update(user_id, active=False)

# Usage
def main():
    # Check health
    health = check_database_health()
    if not health["healthy"]:
        raise Exception("Database unhealthy")
    
    # Use the manager
    with get_sync_db() as db:
        manager = UserManager(db)
        
        # Create user
        user = manager.create(
            email="test@example.com",
            name="Test User"
        )
        
        # Find active users
        active_users = manager.find_active_users()
        
        # Deactivate user
        manager.deactivate_user(user.id)

if __name__ == "__main__":
    main()
```

This example demonstrates models, custom managers, retry logic, health checks, and proper session management - all with automatic Datadog metrics!
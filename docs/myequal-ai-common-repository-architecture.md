# MyEqual AI Common Repository Architecture

## Executive Summary

This document outlines the architecture for a centralized common components repository (`myequal-ai-common`) for the MyEqual AI platform. This repository will house shared frameworks, utilities, domain models, and libraries used across all microservices, promoting code reuse, consistency, and maintainability in our production environment.

## Problem Statement

Currently, MyEqual's microservices contain significant code duplication across:
- Domain models and enums (call statuses, event schemas)
- Authentication and authorization logic (both internal and public)
- Database abstraction layers  
- External service client implementations
- Logging and metrics configurations (Datadog integration)
- Event publishing infrastructure
- Common utilities and helpers

This duplication leads to:
- Inconsistent implementations across services
- Different call status definitions across services
- Duplicated event schemas
- Increased maintenance burden
- Higher risk of bugs
- Slower development velocity

## Proposed Solution

Create a centralized `myequal-ai-common` repository containing shared components that can be imported as a dependency by all services.

## Architecture Overview

### Repository Structure

```
myequal-ai-common/
├── pyproject.toml                    # Package configuration
├── README.md                         # Documentation
├── CHANGELOG.md                      # Version history
├── .github/
│   └── workflows/
│       ├── test.yml                  # CI/CD pipeline
│       └── release.yml               # Automated releases
├── src/
│   └── myequal_common/
│       ├── __init__.py
│       ├── domain/                   # Shared domain models
│       │   ├── __init__.py
│       │   ├── call_status.py        # Common call statuses
│       │   ├── events.py             # Event schemas
│       │   ├── models.py             # Shared models
│       │   └── enums.py              # Common enums
│       ├── auth/                     # Authentication framework
│       │   ├── __init__.py
│       │   ├── public.py             # Public/client authentication
│       │   ├── internal.py           # Service-to-service auth
│       │   ├── dependencies.py       # FastAPI dependencies
│       │   └── models.py             # Auth models
│       ├── database/                 # Database abstraction
│       │   ├── __init__.py
│       │   ├── base.py               # Base DB interface
│       │   ├── postgres.py           # PostgreSQL implementation
│       │   ├── cosmosdb.py          # Azure Cosmos DB implementation
│       │   ├── datalake.py           # Data lake implementation
│       │   └── factory.py             # Database factory pattern
│       ├── middleware/               # Common middleware
│       ├── clients/                  # External service clients
│       ├── observability/            # Logging, metrics, tracing
│       ├── events/                   # Event publishing
│       ├── cache/                    # Redis and caching utilities
│       ├── utils/                    # Common utilities
│       ├── config/                   # Configuration management
│       └── exceptions/               # Base exceptions
└── tests/                            # Comprehensive test suite
```

## Core Components

### 1. Domain Models and Shared Schemas

```python
# myequal_common/domain/call_status.py
from enum import Enum

class CallStatus(str, Enum):
    """Unified call status across all services"""
    INITIATED = "initiated"
    RINGING = "ringing" 
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    CANCELLED = "cancelled"
    
class CallFailureReason(str, Enum):
    """Standardized failure reasons"""
    NETWORK_ERROR = "network_error"
    USER_BUSY = "user_busy"
    NO_ANSWER = "no_answer"
    REJECTED = "rejected"
    SYSTEM_ERROR = "system_error"
    INVALID_NUMBER = "invalid_number"
    INSUFFICIENT_BALANCE = "insufficient_balance"

# myequal_common/domain/events.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

class BaseEvent(BaseModel):
    """Base event schema for all events"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_service: str
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CallCompletedEvent(BaseEvent):
    """Standard call completed event"""
    event_type: str = "call.completed"
    call_id: str
    phone_number: str
    duration_seconds: int
    status: CallStatus
    failure_reason: Optional[CallFailureReason] = None

class MemoryUpdatedEvent(BaseEvent):
    """Memory update event"""
    event_type: str = "memory.updated"
    entity_id: str
    memory_type: str
    operation: str  # "create", "update", "delete"

class TranscriptProcessedEvent(BaseEvent):
    """Transcript processing completed event"""
    event_type: str = "transcript.processed"
    call_id: str
    session_id: str
    processing_status: str
    transcript_available: bool

# myequal_common/domain/models.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class BaseModel(SQLModel):
    """Base model for all database models"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True
```

### 2. Authentication Framework (Public vs Internal)

```python
# myequal_common/auth/config.py
from pydantic import BaseModel
from typing import Optional, List

class AuthConfig(BaseModel):
    """Base authentication configuration"""
    enabled: bool = True
    
class PublicAuthConfig(AuthConfig):
    """Configuration for public/client authentication"""
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    enable_refresh_tokens: bool = True
    token_url: str = "/token"
    
class InternalAuthConfig(AuthConfig):
    """Configuration for service-to-service authentication"""
    api_key_header: str = "X-API-Key"
    service_keys: Dict[str, str] = {}  # service_name -> api_key
    enable_mutual_tls: bool = False
    allowed_services: List[str] = []

# myequal_common/auth/public.py
from typing import Optional, Dict, Any, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import PublicAuthConfig
import jwt

security = HTTPBearer()

class PublicAuthManager:
    """Manager for public/client authentication"""
    
    def __init__(self, config: Optional[PublicAuthConfig] = None):
        self.config = config or PublicAuthConfig()
        
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token with configured settings"""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def get_current_user_dependency(self):
        """Returns FastAPI dependency for user authentication"""
        async def dependency(
            credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
        ) -> Dict[str, Any]:
            if not self.config.enabled:
                return {"user_id": "anonymous", "authenticated": False}
            
            token = credentials.credentials
            return await self.verify_token(token)
        
        return dependency

# myequal_common/auth/internal.py
from typing import Optional, Annotated
from fastapi import Header, HTTPException, status
from .config import InternalAuthConfig

class InternalAuthManager:
    """Manager for internal service-to-service authentication"""
    
    def __init__(self, config: Optional[InternalAuthConfig] = None):
        self.config = config or InternalAuthConfig()
        
    async def verify_service_key(self, api_key: str) -> str:
        """Verify API key and return service name"""
        for service_name, key in self.config.service_keys.items():
            if api_key == key:
                if self.config.allowed_services and service_name not in self.config.allowed_services:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Service {service_name} not allowed"
                    )
                return service_name
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    def get_service_auth_dependency(self):
        """Returns FastAPI dependency for service authentication"""
        async def dependency(
            api_key: Annotated[Optional[str], Header(alias=self.config.api_key_header)] = None
        ) -> str:
            if not self.config.enabled:
                return "anonymous-service"
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required"
                )
            
            return await self.verify_service_key(api_key)
        
        return dependency

# Usage example:
# For public endpoints
public_auth = PublicAuthManager(
    config=PublicAuthConfig(jwt_secret_key=settings.jwt_secret)
)
get_current_user = public_auth.get_current_user_dependency()

@router.get("/user/profile")
async def get_profile(user: Annotated[dict, Depends(get_current_user)]):
    return {"user": user}

# For internal endpoints
internal_auth = InternalAuthManager(
    config=InternalAuthConfig(
        service_keys={
            "post-processing": settings.post_processing_api_key,
            "ai-backend": settings.ai_backend_api_key
        }
    )
)
verify_service = internal_auth.get_service_auth_dependency()

@router.post("/internal/process")
async def internal_endpoint(
    service: Annotated[str, Depends(verify_service)],
    data: dict
):
    return {"processed_by": service}
```

### 3. Generic Database Interface

```python
# myequal_common/database/config.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class DatabaseConfig(BaseModel):
    """Base database configuration"""
    connection_string: str
    pool_size: int = 20
    max_overflow: int = 40
    timeout: int = 30
    custom_config: Dict[str, Any] = {}

# myequal_common/database/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any
from contextlib import asynccontextmanager

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository interface for all database implementations"""
    
    @abstractmethod
    async def get(self, id: str) -> Optional[T]:
        """Get entity by ID"""
        pass
    
    @abstractmethod
    async def get_many(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[T]:
        """Get multiple entities with filters"""
        pass
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity"""
        pass
    
    @abstractmethod
    async def update(self, id: str, updates: Dict[str, Any]) -> Optional[T]:
        """Update entity"""
        pass
    
    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity"""
        pass
    
    @abstractmethod
    async def count(self, filters: Dict[str, Any]) -> int:
        """Count entities matching filters"""
        pass

class BaseDatabaseManager(ABC):
    """Base database manager for all database types"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
    
    @abstractmethod
    @asynccontextmanager
    async def get_session(self):
        """Get database session/connection"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check database connectivity"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close all connections"""
        pass

# myequal_common/database/postgres.py
from sqlmodel import create_engine, Session, select
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any, Type
from .base import BaseRepository, BaseDatabaseManager
from .config import DatabaseConfig

class PostgresRepository(BaseRepository[T]):
    """PostgreSQL implementation of repository pattern"""
    
    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    async def get(self, id: str) -> Optional[T]:
        return self.session.get(self.model_class, id)
    
    async def get_many(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[T]:
        statement = select(self.model_class)
        for key, value in filters.items():
            statement = statement.where(getattr(self.model_class, key) == value)
        statement = statement.limit(limit).offset(offset)
        return self.session.exec(statement).all()
    
    async def create(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity
    
    async def update(self, id: str, updates: Dict[str, Any]) -> Optional[T]:
        entity = await self.get(id)
        if entity:
            for key, value in updates.items():
                setattr(entity, key, value)
            self.session.commit()
            self.session.refresh(entity)
        return entity
    
    async def delete(self, id: str) -> bool:
        entity = await self.get(id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False
    
    async def count(self, filters: Dict[str, Any]) -> int:
        statement = select(func.count()).select_from(self.model_class)
        for key, value in filters.items():
            statement = statement.where(getattr(self.model_class, key) == value)
        return self.session.exec(statement).one()

class PostgresManager(BaseDatabaseManager):
    """PostgreSQL database manager"""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._engine = None
    
    @property
    def engine(self):
        if not self._engine:
            self._engine = create_engine(
                self.config.connection_string,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
                **self.config.custom_config
            )
        return self._engine
    
    @asynccontextmanager
    async def get_session(self):
        async with Session(self.engine) as session:
            yield session
    
    async def health_check(self) -> bool:
        try:
            async with self.get_session() as session:
                session.exec(text("SELECT 1"))
                return True
        except Exception:
            return False
    
    async def close(self):
        if self._engine:
            self._engine.dispose()

# myequal_common/database/cosmosdb.py
from azure.cosmos.aio import CosmosClient, DatabaseProxy, ContainerProxy
from azure.cosmos import exceptions
from typing import Optional, List, Dict, Any, Type
from .base import BaseRepository, BaseDatabaseManager
from .config import DatabaseConfig
import logging

logger = logging.getLogger(__name__)

class CosmosDBRepository(BaseRepository[T]):
    """Azure Cosmos DB implementation of repository pattern"""
    
    def __init__(self, container: ContainerProxy, partition_key: str = "id"):
        self.container = container
        self.partition_key = partition_key
    
    async def get(self, id: str) -> Optional[Dict[str, Any]]:
        try:
            item = await self.container.read_item(
                item=id,
                partition_key=id
            )
            return item
        except exceptions.CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error reading item {id}: {e}")
            raise
    
    async def get_many(self, filters: Dict[str, Any], limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        # Build query
        conditions = []
        parameters = []
        
        for idx, (key, value) in enumerate(filters.items()):
            conditions.append(f"c.{key} = @param{idx}")
            parameters.append({"name": f"@param{idx}", "value": value})
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM c WHERE {where_clause} OFFSET {offset} LIMIT {limit}"
        
        items = []
        async for item in self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ):
            items.append(item)
        
        return items
    
    async def create(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure partition key exists
        if self.partition_key not in entity:
            entity[self.partition_key] = entity.get("id")
        
        created_item = await self.container.create_item(body=entity)
        return created_item
    
    async def update(self, id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            # Read existing item
            existing = await self.get(id)
            if not existing:
                return None
            
            # Apply updates
            existing.update(updates)
            
            # Replace item
            updated_item = await self.container.replace_item(
                item=id,
                body=existing
            )
            return updated_item
        except Exception as e:
            logger.error(f"Error updating item {id}: {e}")
            raise
    
    async def delete(self, id: str) -> bool:
        try:
            await self.container.delete_item(
                item=id,
                partition_key=id
            )
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error deleting item {id}: {e}")
            raise
    
    async def count(self, filters: Dict[str, Any]) -> int:
        # Build count query
        conditions = []
        parameters = []
        
        for idx, (key, value) in enumerate(filters.items()):
            conditions.append(f"c.{key} = @param{idx}")
            parameters.append({"name": f"@param{idx}", "value": value})
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT VALUE COUNT(1) FROM c WHERE {where_clause}"
        
        async for count in self.container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ):
            return count
        
        return 0

class CosmosDBManager(BaseDatabaseManager):
    """Azure Cosmos DB database manager"""
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._client = None
        self._database = None
        self._containers = {}
    
    @property
    def client(self):
        if not self._client:
            self._client = CosmosClient(
                url=self.config.connection_string,
                credential=self.config.custom_config.get("key"),
                connection_timeout=self.config.timeout,
                **self.config.custom_config.get("client_options", {})
            )
        return self._client
    
    async def get_database(self, database_name: str) -> DatabaseProxy:
        if not self._database:
            self._database = self.client.get_database_client(database_name)
        return self._database
    
    async def get_container(self, database_name: str, container_name: str) -> ContainerProxy:
        key = f"{database_name}/{container_name}"
        if key not in self._containers:
            database = await self.get_database(database_name)
            self._containers[key] = database.get_container_client(container_name)
        return self._containers[key]
    
    @asynccontextmanager
    async def get_session(self):
        # For Cosmos DB, we return the client itself
        # Actual container selection happens at repository level
        yield self
    
    async def health_check(self) -> bool:
        try:
            # Read database properties to check connectivity
            database_name = self.config.custom_config.get("database_name", "myequal")
            database = await self.get_database(database_name)
            await database.read()
            return True
        except Exception as e:
            logger.error(f"Cosmos DB health check failed: {e}")
            return False
    
    async def close(self):
        if self._client:
            await self._client.close()

# myequal_common/database/factory.py
from typing import Type
from .base import BaseDatabaseManager
from .config import DatabaseConfig
from .postgres import PostgresManager
from .cosmosdb import CosmosDBManager

def create_database_manager(
    db_type: str,
    config: DatabaseConfig
) -> BaseDatabaseManager:
    """Factory for creating database managers"""
    managers = {
        "postgres": PostgresManager,
        "cosmosdb": CosmosDBManager,
        # Add more as needed: "mongodb", "cassandra", etc.
    }
    
    manager_class = managers.get(db_type)
    if not manager_class:
        raise ValueError(f"Unknown database type: {db_type}")
    
    return manager_class(config)

# Usage:
db_config = DatabaseConfig(
    connection_string=settings.database_url,
    pool_size=30
)
db_manager = create_database_manager("postgres", db_config)

# For Cosmos DB
cosmos_config = DatabaseConfig(
    connection_string=settings.cosmos_endpoint,
    custom_config={
        "key": settings.cosmos_key,
        "database_name": "myequal",
        "client_options": {
            "connection_retry_policy": {
                "retry_total": 3,
                "retry_backoff_max": 30
            }
        }
    }
)
cosmos_manager = create_database_manager("cosmosdb", cosmos_config)
```

### 4. Observability Framework

Standardized logging and metrics collection across all services based on proven patterns from the backend service.

**Components:**
- **MetricsClient**: Wrapper around DogStatsD with automatic namespacing
  - Context manager for timing operations
  - Support for counters, gauges, and histograms
  - Automatic tag merging (global + local tags)
- **LogManager**: Dictionary-based logging configuration
  - JSON structured logging with pythonjsonlogger
  - Datadog trace context integration (dd.trace_id, dd.span_id)
  - Environment-specific formatters (local vs production)
  - Azure SDK noise reduction

**Key Features:**
- Automatic metric namespacing with configured prefix
- Built-in timing context manager for performance measurement
- Structured JSON logging for production environments
- Datadog APM integration with trace propagation
- Session and request context in log messages
- FastAPI dependency injection support

### 5. Redis and Distributed Systems

```python
# myequal_common/cache/config.py
from pydantic import BaseModel
from typing import Optional

class RedisConfig(BaseModel):
    """Configurable Redis settings"""
    decode_responses: bool = True
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30

# myequal_common/cache/redis_manager.py
import redis.asyncio as redis
from typing import Optional, AsyncGenerator, List, Dict
from contextlib import asynccontextmanager
from .config import RedisConfig
import asyncio
import uuid

class RedisManager:
    """Comprehensive Redis client with streams, pub/sub, and locking"""
    
    def __init__(self, url: str, config: Optional[RedisConfig] = None):
        self.url = url
        self.config = config or RedisConfig()
        self._pool = None
        self._client = None
    
    @property
    def pool(self):
        if not self._pool:
            self._pool = redis.ConnectionPool.from_url(
                self.url,
                decode_responses=self.config.decode_responses,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval,
            )
        return self._pool
    
    @property
    def client(self):
        if not self._client:
            self._client = redis.Redis(connection_pool=self.pool)
        return self._client
    
    # Basic operations
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        return await self.client.set(key, value, ex=ex)
    
    async def delete(self, key: str) -> int:
        return await self.client.delete(key)
    
    # Stream operations for event processing
    async def xadd(self, stream: str, fields: dict, maxlen: Optional[int] = None, id: str = "*"):
        """Add to stream with optional max length"""
        return await self.client.xadd(stream, fields, maxlen=maxlen, id=id)
    
    async def xread(self, streams: Dict[str, str], count: Optional[int] = None, block: Optional[int] = None):
        """Read from streams"""
        return await self.client.xread(streams, count=count, block=block)
    
    async def xreadgroup(
        self, 
        group: str, 
        consumer: str, 
        streams: Dict[str, str], 
        count: Optional[int] = None,
        block: Optional[int] = None,
        noack: bool = False
    ):
        """Read from consumer group"""
        return await self.client.xreadgroup(
            group, consumer, streams, count=count, block=block, noack=noack
        )
    
    async def create_consumer_group(self, stream: str, group: str, id: str = "$", mkstream: bool = True):
        """Create consumer group with automatic stream creation"""
        try:
            await self.client.xgroup_create(stream, group, id=id, mkstream=mkstream)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
    
    async def delete_consumer(self, stream: str, group: str, consumer: str) -> int:
        """Delete consumer from group"""
        return await self.client.xgroup_delconsumer(stream, group, consumer)
    
    async def xack(self, stream: str, group: str, *ids: str) -> int:
        """Acknowledge messages"""
        return await self.client.xack(stream, group, *ids)
    
    async def xpending(self, stream: str, group: str) -> Dict:
        """Get pending messages info"""
        return await self.client.xpending(stream, group)
    
    # Pub/Sub operations
    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel"""
        return await self.client.publish(channel, message)
    
    @asynccontextmanager
    async def subscribe(self, *channels: str) -> AsyncGenerator:
        """Subscribe to channels with automatic cleanup"""
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        try:
            yield pubsub
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()
    
    # Cleanup
    async def close(self):
        """Close all connections"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()

# myequal_common/cache/distributed_lock.py
import asyncio
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
import uuid
import time

class DistributedLock:
    """Redis-based distributed lock with safety features"""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
        
    @asynccontextmanager
    async def acquire(
        self,
        resource: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: Optional[float] = None,
        retry_delay: float = 0.1
    ) -> AsyncGenerator[bool, None]:
        """
        Acquire distributed lock with safety guarantees
        
        Args:
            resource: Resource name to lock
            timeout: Lock expiration in seconds
            blocking: Whether to wait for lock
            blocking_timeout: Max time to wait for lock
            retry_delay: Delay between retries
        """
        lock_id = str(uuid.uuid4())
        lock_key = f"lock:{resource}"
        
        acquired = False
        start_time = time.time()
        
        # Try to acquire lock
        while True:
            acquired = await self.redis.client.set(
                lock_key,
                lock_id,
                nx=True,
                ex=timeout
            )
            
            if acquired or not blocking:
                break
                
            # Check timeout
            if blocking_timeout:
                if time.time() - start_time >= blocking_timeout:
                    break
            
            # Wait before retry
            await asyncio.sleep(retry_delay)
        
        try:
            yield acquired
        finally:
            if acquired:
                # Lua script for safe deletion (only delete if we own the lock)
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                await self.redis.client.eval(lua_script, 1, lock_key, lock_id)

# Usage example:
redis_manager = RedisManager(settings.redis_url)
lock = DistributedLock(redis_manager)

async with lock.acquire("critical_resource", timeout=30, blocking_timeout=5) as acquired:
    if acquired:
        # Perform critical operation
        await process_critical_task()
    else:
        # Could not acquire lock
        logger.warning("Could not acquire lock for critical_resource")
```

### 6. Event Publishing Infrastructure

```python
# myequal_common/events/config.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class EventPublisherConfig(BaseModel):
    """Configurable event publisher settings"""
    batch_size: int = 100
    flush_interval_seconds: int = 5
    max_retries: int = 3
    timeout_seconds: int = 30
    soft_fail: bool = True  # Don't crash on publish failures
    custom_config: Dict[str, Any] = {}

# myequal_common/events/publisher.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import logging
from .config import EventPublisherConfig
from ..domain.events import BaseEvent

logger = logging.getLogger(__name__)

class EventPublisher(ABC):
    """Base event publisher interface with soft failure support"""
    
    def __init__(self, config: Optional[EventPublisherConfig] = None):
        self.config = config or EventPublisherConfig()
    
    async def safe_publish(self, event: BaseEvent) -> bool:
        """Publish with soft failure handling"""
        try:
            await self.publish(event)
            return True
        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            if not self.config.soft_fail:
                raise
            return False
    
    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publish single event"""
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[BaseEvent]) -> None:
        """Publish batch of events"""
        pass

# myequal_common/events/azure.py
from azure.eventgrid import EventGridPublisherClient, EventGridEvent
from azure.core.credentials import AzureKeyCredential
from typing import List, Optional
from .publisher import EventPublisher
from ..domain.events import BaseEvent

class AzureEventGridPublisher(EventPublisher):
    """Azure Event Grid implementation matching current pattern"""
    
    def __init__(
        self, 
        endpoint: str, 
        key: str, 
        config: Optional[EventPublisherConfig] = None
    ):
        super().__init__(config)
        self.endpoint = endpoint
        self.client = EventGridPublisherClient(
            endpoint, 
            AzureKeyCredential(key)
        )
    
    async def publish(self, event: BaseEvent) -> None:
        """Publish single event"""
        grid_event = EventGridEvent(
            subject=f"{event.source_service}/{event.event_type}",
            event_type=event.event_type,
            data=event.dict(),
            data_version="1.0"
        )
        await self.client.send_event(grid_event)
    
    async def publish_batch(self, events: List[BaseEvent]) -> None:
        """Publish batch of events"""
        grid_events = []
        for event in events:
            grid_events.append(
                EventGridEvent(
                    subject=f"{event.source_service}/{event.event_type}",
                    event_type=event.event_type,
                    data=event.dict(),
                    data_version="1.0"
                )
            )
        
        # Batch by configured size
        for i in range(0, len(grid_events), self.config.batch_size):
            batch = grid_events[i:i + self.config.batch_size]
            await self.client.send_events(batch)
```

## Package Management with UV

Since you're using UV across all services, here's the setup:

```toml
# pyproject.toml for myequal-ai-common
[project]
name = "myequal-ai-common"
version = "1.0.0"
description = "Common utilities for MyEqual AI services"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "sqlmodel>=0.0.22",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "httpx>=0.28.0",
    "redis>=5.2.0",
    "datadog>=0.51.0",
    "azure-eventgrid>=4.22.0",
    "python-json-logger>=3.3.0",
    "azure-cosmos>=4.5.0",  # For Cosmos DB support
    "tenacity>=9.1.0",
    "pyjwt>=2.8.0",
]

[project.optional-dependencies]
azure = [
    "azure-eventgrid>=4.22.0",
    "azure-storage-blob>=12.25.0",
    "azure-cognitiveservices-speech>=1.42.0",
]
all = ["myequal-ai-common[azure]"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/myequal_common"]
```

### Publishing to GitHub Packages with UV

```bash
# Build the package
uv build

# Configure GitHub registry
export UV_INDEX_URL=https://pypi.org/simple
export UV_EXTRA_INDEX_URL=https://npm.pkg.github.com/@inifity-tech
export UV_FIND_LINKS=https://github.com/inifity-tech/myequal-ai-common/releases/download/v1.0.0/

# Publish (you might need to use standard tools for publishing)
python -m twine upload --repository-url https://npm.pkg.github.com/@inifity-tech dist/*
```

### Using in Services with UV

```toml
# In service's pyproject.toml
[project]
dependencies = [
    "myequal-ai-common>=1.0.0,<2.0.0",
    # other deps...
]

[[tool.uv.index]]
name = "github"
url = "https://npm.pkg.github.com/@inifity-tech"
```

Or install directly:
```bash
# Using git+https (simpler approach)
uv add "myequal-ai-common @ git+https://github.com/inifity-tech/myequal-ai-common.git@v1.0.0"
```

## Migration Example

Here's how services would migrate to use the common library:

```python
# Before (duplicated in each service)
from app.models import CallStatus  # Different definitions
from app.event_publishers import EventPublisher  # Duplicated code
from app.db import get_db_session  # Similar implementations
from app.logging_config import logger  # Repeated configs

# After (using common library)
from myequal_common.domain import CallStatus, CallCompletedEvent
from myequal_common.events import AzureEventGridPublisher
from myequal_common.database import create_database_manager
from myequal_common.observability import LogManager, MetricsClient
from myequal_common.cache import RedisManager, DistributedLock
from myequal_common.auth import PublicAuthManager, InternalAuthManager

# Setup once in main.py or settings
log_manager = LogManager()
logger = log_manager.setup(service_name="user-service")

# Database (configurable for different types)
db_manager = create_database_manager(
    "postgres",
    DatabaseConfig(connection_string=settings.database_url)
)

# Redis with distributed locking
redis_manager = RedisManager(settings.redis_url)
lock = DistributedLock(redis_manager)

# Authentication
public_auth = PublicAuthManager(
    PublicAuthConfig(jwt_secret_key=settings.jwt_secret)
)
internal_auth = InternalAuthManager(
    InternalAuthConfig(service_keys=settings.service_api_keys)
)

# Use standardized events
event = CallCompletedEvent(
    source_service="user-service",
    call_id=call_id,
    phone_number=phone_number,
    duration_seconds=duration,
    status=CallStatus.COMPLETED  # Consistent enum
)

publisher = AzureEventGridPublisher(
    settings.event_grid_endpoint,
    settings.event_grid_key
)
await publisher.safe_publish(event)  # With soft failure
```

## Benefits

1. **Consistency**: Unified call statuses, event schemas, and patterns
2. **Flexibility**: Support for multiple databases, auth types, and providers
3. **Production Ready**: Distributed locking, stream processing, metrics
4. **Configurable**: Everything uses config objects, no hardcoding
5. **Type Safety**: Full typing with generics for database abstraction
6. **Observability**: Built-in metrics and logging matching current patterns

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)
- Set up repository and CI/CD
- Implement domain models and events
- Create database abstraction layer
- Port metrics and logging from PRs

### Phase 2: Authentication & Redis (Week 3)
- Implement dual authentication system
- Add Redis manager with streams support
- Create distributed locking

### Phase 3: Event System (Week 4)
- Port event publishing with soft failures
- Add batch processing support
- Create event factories

### Phase 4: Service Migration (Weeks 5-8)
- Start with one service as pilot
- Create migration guides
- Gradually migrate all services
- Ensure backward compatibility
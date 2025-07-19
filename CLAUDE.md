# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the `myequal-ai-common` repository, which serves as the centralized location for shared components across the MyEqual AI platform's microservices. The platform consists of:

- **myequal-ai-backend**: Real-time phone assistant service (FastAPI, Ultravox integration)
- **myequal-ai-user-services**: User management and call session handling
- **memory-service**: Static memory storage for phone conversations
- **myequal-ai-app**: Android mobile application (Kotlin/Jetpack Compose)
- **Internal-Dashboard**: Administrative web dashboard (Node.js/Express)
- **myequal-api-gateway**: NGINX-based API gateway
- **myequal-ai-deployments**: Infrastructure as Code (OpenTofu/Terraform)

## Development Commands

### Python Services (Backend, User Services, Memory Service)
```bash
# Package management (use UV, not pip)
uv sync                           # Install/update dependencies
uv add package-name               # Add new dependency
uv remove package-name            # Remove dependency

# Development
uv run fastapi run app/main.py    # Run development server
uv run pytest                     # Run all tests
uv run pytest tests/test_file.py  # Run specific test file
uv run pytest -k "test_name"      # Run specific test

# Code quality
uv run ruff check . --fix         # Lint and auto-fix
uv run ruff format .              # Format code
uv run pyright                    # Type checking

# Database
uv run alembic upgrade head       # Apply migrations
uv run alembic revision -m "msg"  # Create new migration
uv run alembic downgrade -1       # Rollback one migration
```

### Android App
```bash
./gradlew build                   # Build project
./gradlew assembleDebug           # Build debug APK
./gradlew test                    # Run unit tests
./gradlew lint                    # Run lint checks
```

### Node.js Dashboard
```bash
npm install                       # Install dependencies
npm run dev                       # Development mode (nodemon)
npm start                         # Production mode
```

### Infrastructure (Deployments)
```bash
tofu init                         # Initialize Terraform
tofu plan -var-file="production.tfvars"   # Plan changes
tofu apply -var-file="production.tfvars"  # Apply changes
sops -d production.tfvars.encrypted > production.tfvars  # Decrypt vars
```

## Architecture and Code Structure

### Microservices Pattern
All Python services follow this structure:
```
service-name/
├── app/ or backend/
│   ├── api/v1/              # FastAPI routes
│   ├── models/              # SQLModel database models
│   ├── services/            # Business logic layer
│   ├── db_*_manager.py      # Database access patterns
│   ├── *_client.py          # External service clients
│   ├── event_publishers/    # Azure Event Grid publishers
│   ├── settings.py          # Pydantic configuration
│   ├── main.py              # FastAPI app initialization
│   └── logging_config.py    # Structured logging setup
├── tests/                   # pytest test suite
├── migrations/              # Alembic database migrations
└── pyproject.toml          # UV dependencies
```

### Key Development Patterns

1. **Dependency Injection**: Use FastAPI's `Depends` with type annotations
   ```python
   from typing import Annotated
   from fastapi import Depends
   
   async def endpoint(
       settings: Annotated[Settings, Depends(get_settings)],
       db: Annotated[Session, Depends(get_db)]
   ):
       pass
   ```

2. **Async Everything**: All database operations, external calls, and business logic must use async/await

3. **Manager Pattern**: Database operations go through manager classes
   ```python
   manager = CallLogManager(db)
   result = await manager.create(data)
   ```

4. **Event Publishing**: Use soft failures to prevent cascading issues
   ```python
   await event_publisher.publish(event, soft_fail=True)
   ```

5. **Metrics Collection**: Use Datadog metrics client
   ```python
   with metrics.record_timing("operation.duration"):
       metrics.increment("operation.count")
   ```

### Testing Requirements

- Use `pytest` with `anyio` for async tests (NOT `pytest-asyncio`)
- Test files must start with `test_`
- Use transaction rollback for database test isolation
- Mock external services using `unittest.mock`
- Integration tests should use FastAPI's TestClient

### Common Components (This Repository)

This repository centralizes:
- **Shared Models**: User, CallLog, CallSession, Memory models
- **Event Schemas**: Standardized event definitions
- **Enums**: CallStatus, UserRole, MemoryType
- **Utilities**: Authentication, logging, metrics, error handling
- **Base Classes**: Abstract managers, clients, publishers
- **Common Settings**: Shared configuration patterns

### Integration Points

1. **Database**: PostgreSQL with SQLModel ORM
2. **Caching**: Redis for real-time data and distributed locks
3. **Events**: Azure Event Grid for service communication
4. **Auth**: Dual authentication (JWT for users, API keys for services)
5. **Monitoring**: Datadog APM with distributed tracing
6. **External APIs**: Ultravox (AI), Twilio (telephony), Azure services

### Important Considerations

1. **UV Package Manager**: Always use `uv` commands, never `pip`
2. **Python 3.12+**: Use modern Python features
3. **Type Safety**: Full type annotations required
4. **Error Handling**: Comprehensive try/except with proper logging
5. **Soft Failures**: Event publishing should not crash endpoints
6. **Migration Safety**: Always include existence checks in migrations
7. **Async Sessions**: Proper database session management is critical
8. **Service Discovery**: Services communicate via configured base URLs
9. **Correlation IDs**: Track requests across service boundaries
10. **Performance**: Use connection pooling and caching appropriately

### Current Implementation Focus

The common repository is being built to:
- Eliminate code duplication across services
- Standardize patterns and implementations
- Centralize maintenance and updates
- Ensure consistency in models and schemas
- Provide reusable utilities and base classes

When implementing features, always check if they should be:
1. Service-specific (stays in the service repository)
2. Shared (belongs in myequal-ai-common)
3. Infrastructure-related (belongs in deployments)

## Package Publishing and Consumption

### Publishing to GitHub Packages

The common library is published to GitHub Packages. To publish a new version:

```bash
# Tag the release
git tag v0.1.0
git push origin v0.1.0

# The GitHub Action will automatically publish to GitHub Packages
```

### Consuming in Services

Services consume the common library via GitHub repository reference:

```toml
# In service's pyproject.toml
[project]
dependencies = [
    "myequal-ai-common @ git+https://github.com/inifity-tech/myequal-ai-common.git@v0.1.0",
    # Other dependencies...
]

[tool.hatch.metadata]
allow-direct-references = true
```

To add/update the dependency with UV:
```bash
# Add specific version
uv add "myequal-ai-common @ git+https://github.com/inifity-tech/myequal-ai-common.git@v0.1.0"

# Update to latest version
uv add "myequal-ai-common @ git+https://github.com/inifity-tech/myequal-ai-common.git@main" --upgrade
```

### Versioning Strategy

- **0.1.0**: Core domain models and database abstractions
- **0.2.0**: Authentication and event system
- **0.3.0**: Redis infrastructure and utilities
- **1.0.0**: Production-ready with all features

Services should pin to minor versions for stability:
```toml
"myequal-ai-common @ git+https://github.com/inifity-tech/myequal-ai-common.git@v0.3.0"
```

### Import Examples

```python
# Domain models
from myequal_common.domain.enums import CallStatus, CallFailureReason
from myequal_common.domain.events import CallCompletedEvent

# Database
from myequal_common.database import DatabaseManager, get_db

# Authentication
from myequal_common.auth import PublicAuthManager, InternalAuthManager

# Observability
from myequal_common.observability import MetricsClient, LogManager

# Event publishing
from myequal_common.events import EventPublisher

# Redis
from myequal_common.redis import RedisManager, DistributedLock
```
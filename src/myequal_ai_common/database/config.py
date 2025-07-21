"""Database configuration for MyEqual AI services."""

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        extra="ignore",
    )

    # Connection settings
    url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection URL",
        examples=["postgresql://user:pass@localhost:5432/dbname"],
    )

    # Pool settings
    pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of connections to maintain in pool",
    )
    max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum overflow connections above pool_size",
    )
    pool_timeout: float = Field(
        default=30.0,
        gt=0,
        description="Timeout in seconds for getting connection from pool",
    )
    pool_recycle: int = Field(
        default=3600,
        description="Recycle connections after this many seconds",
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Test connections before using them",
    )

    # Query settings
    query_timeout: int | None = Field(
        default=30,
        description="Default query timeout in seconds",
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL queries (debug mode)",
    )

    # SSL settings
    ssl_mode: str | None = Field(
        default=None,
        description="SSL mode (disable, allow, prefer, require, verify-ca, verify-full)",
    )

    # Async specific
    use_async: bool = Field(
        default=True,
        description="Use async engine (asyncpg) or sync (psycopg2)",
    )

    # Environment
    environment: str = Field(
        default="development",
        description="Environment name for metrics tagging",
    )
    service_name: str = Field(
        default="unknown",
        description="Service name for metrics tagging",
    )

    @computed_field
    @property
    def async_url(self) -> str:
        """Convert sync URL to async URL for asyncpg."""
        url_str = str(self.url)
        if url_str.startswith("postgresql://"):
            return url_str.replace("postgresql://", "postgresql+asyncpg://")
        elif url_str.startswith("postgres://"):
            return url_str.replace("postgres://", "postgresql+asyncpg://")
        return url_str

    @computed_field
    @property
    def sync_url(self) -> str:
        """Ensure sync URL for psycopg2."""
        url_str = str(self.url)
        if url_str.startswith("postgres://"):
            return url_str.replace("postgres://", "postgresql://")
        return url_str

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ("production", "prod")

    def get_engine_kwargs(self, is_async: bool = False) -> dict:
        """Get engine configuration kwargs."""
        kwargs = {
            "echo": self.echo,
            "pool_pre_ping": self.pool_pre_ping,
            "pool_recycle": self.pool_recycle,
        }

        # Add pool configuration for production
        if self.is_production:
            kwargs.update(
                {
                    "pool_size": self.pool_size,
                    "max_overflow": self.max_overflow,
                }
            )
            if not is_async:
                kwargs["pool_timeout"] = self.pool_timeout
        else:
            # Use NullPool for development
            kwargs["poolclass"] = "NullPool"

        # Add query timeout if specified
        if self.query_timeout and not is_async:
            kwargs["connect_args"] = {
                "command_timeout": self.query_timeout,
                "options": f"-c statement_timeout={self.query_timeout * 1000}",
            }

        return kwargs


# Global instance
_database_config: DatabaseConfig | None = None


def get_database_config() -> DatabaseConfig:
    """Get or create database configuration."""
    global _database_config
    if _database_config is None:
        _database_config = DatabaseConfig()  # type: ignore
    return _database_config

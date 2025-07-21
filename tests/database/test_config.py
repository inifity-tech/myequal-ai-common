"""Tests for database configuration."""

import os

import pytest

from myequal_ai_common.database import DatabaseConfig, get_database_config


class TestDatabaseConfig:
    """Test database configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost:5432/test")
        
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30.0
        assert config.pool_recycle == 3600
        assert config.pool_pre_ping is True
        assert config.query_timeout == 30
        assert config.echo is False
        assert config.use_async is True
        assert config.environment == "development"
        assert config.service_name == "unknown"

    def test_async_url_conversion(self):
        """Test sync to async URL conversion."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost:5432/test")
        assert config.async_url == "postgresql+asyncpg://user:pass@localhost:5432/test"
        
        # Test with postgres:// prefix
        config = DatabaseConfig(url="postgres://user:pass@localhost:5432/test")
        assert config.async_url == "postgresql+asyncpg://user:pass@localhost:5432/test"

    def test_sync_url_conversion(self):
        """Test URL normalization for sync."""
        config = DatabaseConfig(url="postgres://user:pass@localhost:5432/test")
        assert config.sync_url == "postgresql://user:pass@localhost:5432/test"
        
        # Already normalized
        config = DatabaseConfig(url="postgresql://user:pass@localhost:5432/test")
        assert config.sync_url == "postgresql://user:pass@localhost:5432/test"

    def test_is_production(self):
        """Test production environment detection."""
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/test",
            environment="production"
        )
        assert config.is_production is True
        
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/test",
            environment="prod"
        )
        assert config.is_production is True
        
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/test",
            environment="development"
        )
        assert config.is_production is False

    def test_engine_kwargs_production(self):
        """Test engine kwargs for production."""
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/test",
            environment="production"
        )
        kwargs = config.get_engine_kwargs(is_async=False)
        
        assert kwargs["pool_size"] == 5
        assert kwargs["max_overflow"] == 10
        assert kwargs["pool_timeout"] == 30.0
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_recycle"] == 3600
        assert "poolclass" not in kwargs

    def test_engine_kwargs_development(self):
        """Test engine kwargs for development."""
        config = DatabaseConfig(
            url="postgresql://user:pass@localhost:5432/test",
            environment="development"
        )
        kwargs = config.get_engine_kwargs(is_async=False)
        
        assert kwargs["poolclass"] == "NullPool"
        assert "pool_size" not in kwargs
        assert "max_overflow" not in kwargs

    def test_env_var_loading(self, monkeypatch):
        """Test loading from environment variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://env:pass@host:5432/db")
        monkeypatch.setenv("DATABASE_POOL_SIZE", "20")
        monkeypatch.setenv("DATABASE_SERVICE_NAME", "test-service")
        
        config = DatabaseConfig()
        
        assert str(config.url) == "postgresql://env:pass@host:5432/db"
        assert config.pool_size == 20
        assert config.service_name == "test-service"

    def test_global_config_singleton(self, monkeypatch):
        """Test global config is singleton."""
        # Set required DATABASE_URL
        monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
        
        # Reset global instance
        from myequal_ai_common.database import config as config_module
        config_module._database_config = None
        
        config1 = get_database_config()
        config2 = get_database_config()
        
        assert config1 is config2
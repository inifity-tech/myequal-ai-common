"""Test base manager custom query methods with mocked database."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlmodel import Field, SQLModel

from myequal_ai_common.database import AsyncBaseDBManager, BaseDBManager


# Test model
class Product(SQLModel, table=True):
    """Test product model."""

    __tablename__ = "test_products"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    price: float
    category: str
    in_stock: bool = Field(default=True)


class ProductManager(BaseDBManager[Product]):
    """Test sync manager."""

    @property
    def model_class(self) -> type[Product]:
        return Product


class AsyncProductManager(AsyncBaseDBManager[Product]):
    """Test async manager."""

    @property
    def model_class(self) -> type[Product]:
        return Product


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up test environment."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("DATABASE_SERVICE_NAME", "test-service")
    monkeypatch.setenv("DATABASE_ENVIRONMENT", "test")

    # Reset global instances
    from myequal_ai_common.database import config as config_module
    from myequal_ai_common.database import metrics as metrics_module

    config_module._database_config = None
    metrics_module._metrics_client = None


class TestBaseManagerCustomMethods:
    """Test custom query methods with mocked database."""

    def test_execute_query(self):
        """Test execute_query method."""
        # Mock database session
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            Product(id=1, name="Test Product", price=99.99, category="Electronics")
        ]
        mock_db.execute.return_value = mock_result

        # Test the method
        manager = ProductManager(mock_db)
        query = select(Product).where(Product.price > 50.0)
        result = manager.execute_query(query, operation="expensive_products")

        # Verify
        mock_db.execute.assert_called_once()
        assert mock_db.commit.called
        products = result.scalars().all()
        assert len(products) == 1

    def test_execute_raw_sql(self):
        """Test execute_raw_sql method."""
        # Mock database session
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        mock_db.execute.return_value = mock_result

        # Test the method
        manager = ProductManager(mock_db)
        sql = "SELECT COUNT(*) FROM test_products WHERE category = :category"
        result = manager.execute_raw_sql(
            sql, {"category": "Electronics"}, operation="count_by_category"
        )

        # Verify
        mock_db.execute.assert_called_once()
        assert mock_db.commit.called
        count = result.scalar()
        assert count == 2

    def test_bulk_create(self):
        """Test bulk_create method."""
        # Mock database session
        mock_db = MagicMock()

        # Test the method
        manager = ProductManager(mock_db)
        products = [
            Product(name=f"Product {i}", price=i * 10.0, category="Test")
            for i in range(3)
        ]
        result = manager.bulk_create(products)

        # Verify
        mock_db.add_all.assert_called_once_with(products)
        assert mock_db.commit.called
        assert mock_db.refresh.call_count == 3
        assert result == products

    def test_bulk_update(self):
        """Test bulk_update method."""
        # Mock database session
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute.return_value = mock_result

        # Test the method
        manager = ProductManager(mock_db)
        updates = [
            {"id": 1, "price": 80.0},
            {"id": 2, "price": 90.0},
            {"id": 3, "in_stock": False},
        ]
        count = manager.bulk_update(updates)

        # Verify
        assert mock_db.execute.call_count == 3
        assert mock_db.commit.called
        assert count == 3  # 1 per update

    def test_transaction_context(self):
        """Test transaction context manager."""
        # Mock database session
        mock_db = MagicMock()

        # Test the method
        manager = ProductManager(mock_db)

        with manager.transaction():
            manager.create(name="Product 1", price=10.0, category="Test")
            manager.create(name="Product 2", price=20.0, category="Test")

        # Verify
        assert mock_db.add.call_count == 2
        assert mock_db.commit.call_count == 1  # Only once at the end
        assert not mock_db.rollback.called

    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        # Mock database session
        mock_db = MagicMock()

        # Test the method
        manager = ProductManager(mock_db)

        with pytest.raises(ValueError):
            with manager.transaction():
                manager.create(name="Product 1", price=10.0, category="Test")
                raise ValueError("Test error")

        # Verify
        assert mock_db.rollback.called
        assert not mock_db.commit.called


class TestAsyncBaseManagerCustomMethods:
    """Test async custom query methods with mocked database."""

    @pytest.mark.anyio
    async def test_execute_query(self):
        """Test async execute_query method."""
        # Mock database session
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            Product(id=1, name="Test Product", price=99.99, category="Electronics")
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)

        # Test the method
        manager = AsyncProductManager(mock_db)
        query = select(Product).where(Product.price > 50.0)
        result = await manager.execute_query(query, operation="expensive_products")

        # Verify
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        products = result.scalars().all()
        assert len(products) == 1

    @pytest.mark.anyio
    async def test_execute_raw_sql(self):
        """Test async execute_raw_sql method."""
        # Mock database session
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)

        # Test the method
        manager = AsyncProductManager(mock_db)
        sql = "SELECT COUNT(*) FROM test_products WHERE category = :category"
        result = await manager.execute_raw_sql(
            sql, {"category": "Electronics"}, operation="count_by_category"
        )

        # Verify
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        count = result.scalar()
        assert count == 2

    @pytest.mark.anyio
    async def test_bulk_create(self):
        """Test async bulk_create method."""
        # Mock database session
        mock_db = MagicMock()
        mock_db.commit = AsyncMock(return_value=None)
        mock_db.refresh = AsyncMock(return_value=None)

        # Test the method
        manager = AsyncProductManager(mock_db)
        products = [
            Product(name=f"Product {i}", price=i * 10.0, category="Test")
            for i in range(3)
        ]
        result = await manager.bulk_create(products)

        # Verify
        mock_db.add_all.assert_called_once_with(products)
        mock_db.commit.assert_called_once()
        assert mock_db.refresh.call_count == 3
        assert result == products

    @pytest.mark.anyio
    async def test_bulk_update(self):
        """Test async bulk_update method."""
        # Mock database session
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock(return_value=None)

        # Test the method
        manager = AsyncProductManager(mock_db)
        updates = [
            {"id": 1, "price": 80.0},
            {"id": 2, "price": 90.0},
            {"id": 3, "in_stock": False},
        ]
        count = await manager.bulk_update(updates)

        # Verify
        assert mock_db.execute.call_count == 3
        mock_db.commit.assert_called_once()
        assert count == 3  # 1 per update

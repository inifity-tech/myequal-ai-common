"""Pytest configuration."""

import pytest


def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    """Only use asyncio backend for async tests."""
    return request.param

"""
Unit tests for get_pool() search_path logic.
No real database required — asyncpg.create_pool is mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings


@pytest.mark.asyncio
async def test_db_schema_sets_search_path(monkeypatch):
    """When db_schema is non-empty, get_pool must SET search_path."""
    monkeypatch.setattr(settings, "db_schema", "test_schema")

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    # pool.acquire() must be an async context manager
    mock_acquire_cm = MagicMock()
    mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_cm.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)

    import app.models.database as db_module

    with patch("app.models.database._pool", None), \
         patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
        # Reset module-level _pool so get_pool() enters the init branch
        db_module._pool = None
        result = await db_module.get_pool()

    mock_conn.execute.assert_called_once_with(
        "SET search_path TO test_schema, public"
    )
    assert result is mock_pool


@pytest.mark.asyncio
async def test_empty_db_schema_skips_search_path(monkeypatch):
    """When db_schema is empty string, SET search_path must NOT be called."""
    monkeypatch.setattr(settings, "db_schema", "")

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=None)

    mock_acquire_cm = MagicMock()
    mock_acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire_cm.__aexit__ = AsyncMock(return_value=False)

    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_acquire_cm)

    import app.models.database as db_module

    with patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)):
        db_module._pool = None
        result = await db_module.get_pool()

    mock_conn.execute.assert_not_called()
    assert result is mock_pool

"""
Unit tests for get_pool() search_path logic via server_settings.
No real database required — asyncpg.create_pool is mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import settings


@pytest.mark.asyncio
async def test_db_schema_passes_search_path_to_pool(monkeypatch):
    """When db_schema is non-empty, get_pool must pass server_settings
    with search_path to create_pool so every pool connection gets it."""
    monkeypatch.setattr(settings, "db_schema", "test_schema")

    mock_pool = MagicMock()

    import app.models.database as db_module

    with patch("app.models.database._pool", None), \
         patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)) as mock_create:
        db_module._pool = None
        result = await db_module.get_pool()

    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args
    assert kwargs.get("server_settings") == {"search_path": "test_schema,public"}, (
        f"Expected server_settings with search_path, got {kwargs.get('server_settings')}"
    )
    assert result is mock_pool


@pytest.mark.asyncio
async def test_empty_db_schema_omits_search_path(monkeypatch):
    """When db_schema is empty string, server_settings must be empty dict
    (no search_path override)."""
    monkeypatch.setattr(settings, "db_schema", "")

    mock_pool = MagicMock()

    import app.models.database as db_module

    with patch("asyncpg.create_pool", AsyncMock(return_value=mock_pool)) as mock_create:
        db_module._pool = None
        result = await db_module.get_pool()

    mock_create.assert_called_once()
    _, kwargs = mock_create.call_args
    assert kwargs.get("server_settings") == {}, (
        f"Expected empty server_settings, got {kwargs.get('server_settings')}"
    )
    assert result is mock_pool

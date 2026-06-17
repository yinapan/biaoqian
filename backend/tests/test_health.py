import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.routers.health import health_check


@pytest.mark.asyncio
async def test_health_all_ok():
    """PG and ES both reachable -> 200, status: ok."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    mock_es = AsyncMock()
    mock_es.ping = AsyncMock(return_value=True)

    with (
        patch("app.routers.health.get_pool", return_value=mock_pool),
        patch("app.routers.health.get_es", return_value=mock_es),
    ):
        resp = await health_check()

    assert resp.status_code == 200
    assert resp.body == b'{"status":"ok","pg":true,"es":true}'


@pytest.mark.asyncio
async def test_health_pg_down():
    """PG unreachable -> 503, status: error."""
    mock_es = AsyncMock()
    mock_es.ping = AsyncMock(return_value=True)

    with (
        patch("app.routers.health.get_pool", side_effect=Exception("pg down")),
        patch("app.routers.health.get_es", return_value=mock_es),
    ):
        resp = await health_check()

    assert resp.status_code == 503
    assert resp.body == b'{"status":"error","pg":false,"es":true}'


@pytest.mark.asyncio
async def test_health_es_down():
    """ES unreachable -> 503, status: error."""
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=mock_conn),
        __aexit__=AsyncMock(return_value=False),
    ))

    with (
        patch("app.routers.health.get_pool", return_value=mock_pool),
        patch("app.routers.health.get_es", side_effect=Exception("es down")),
    ):
        resp = await health_check()

    assert resp.status_code == 503
    assert resp.body == b'{"status":"error","pg":true,"es":false}'

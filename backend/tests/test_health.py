import json
from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.routers.health import health_check
from app.routers.health import ready_check


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
    data = json.loads(resp.body)
    assert data == {"status": "ok", "pg": True, "es": True}


@pytest.mark.asyncio
async def test_ready_is_shallow_startup_probe():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ready=True)))
    data = await ready_check(request)
    assert data == {"status": "ready"}


@pytest.mark.asyncio
async def test_ready_returns_503_until_startup_dependencies_finish():
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(ready=False)))
    resp = await ready_check(request)
    assert resp.status_code == 503
    assert json.loads(resp.body) == {"status": "starting"}


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
    data = json.loads(resp.body)
    assert data == {"status": "error", "pg": False, "es": True}


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
    data = json.loads(resp.body)
    assert data == {"status": "error", "pg": True, "es": False}

"""
Integration tests for GET /api/v1/health (3 cases).

Task 2.8: health endpoint shape validation.
NOTE: The health endpoint returns {"status": str, "pg": bool, "es": bool}.
      `es` is a plain boolean, NOT an object with an alias field.
"""
import pytest


@pytest.mark.asyncio
async def test_health_returns_200(test_client):
    """Health endpoint returns 200 and status == 'ok' when services are up."""
    resp = await test_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_checks_es_alias(test_client, seeded_db):
    """After seeding, ES is available; es field is True (bool, not object)."""
    resp = await test_client.get("/api/v1/health")
    data = resp.json()
    assert "es" in data
    # es is a plain boolean — True means ES ping succeeded
    assert data["es"] is True


@pytest.mark.asyncio
async def test_health_init_matcher_empty_state_first_request(test_client):
    """init_matcher 空字典状态下首次请求不报错 — GET /health 不崩溃。"""
    resp = await test_client.get("/api/v1/health")
    assert resp.status_code == 200

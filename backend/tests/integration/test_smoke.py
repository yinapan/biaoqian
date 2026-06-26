"""
Smoke test: verifies the full fixture chain (test_schema -> test_client -> seeded_db).
Requires docker-compose.test.yml (Task 2.4) and fixture JSON files (Task 2.6).
Run with: RUN_ID=local python -m pytest tests/integration/test_smoke.py -v
"""
import pytest


@pytest.mark.asyncio
async def test_fixture_loads(test_client, seeded_db):
    resp = await test_client.get("/api/v1/health")
    assert resp.status_code == 200

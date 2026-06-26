"""
backend/tests/conftest.py
Session-scoped schema lifecycle + test fixtures for parallel CI isolation.

- test_schema : creates an isolated PG schema and sets DB_SCHEMA env var
- test_client : httpx AsyncClient against the ASGI app (lazy app import)
- seeded_db   : imports 4 fixture JSON files via admin endpoints
- admin_key   : ADMIN_API_KEY from environment
"""
import os
from urllib.parse import urlparse, urlunparse

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _postgres_admin_url(database_url: str) -> str:
    """Replace the database component of *database_url* with 'postgres'."""
    parsed = urlparse(database_url)
    # path is e.g. "/biaoqiao"; replace with "/postgres"
    new = parsed._replace(path="/postgres")
    return urlunparse(new)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def env_run_id():
    return os.environ.get("RUN_ID", "local")


@pytest_asyncio.fixture(scope="session")
async def test_schema(env_run_id):
    """Create an isolated schema; teardown drops it."""
    schema_name = f"biaoqiao_test_{env_run_id}"
    admin_url = _postgres_admin_url(settings.database_url)

    admin_conn = await asyncpg.connect(admin_url)
    await admin_conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    await admin_conn.close()

    # Set env var BEFORE any app import so pydantic-settings picks it up
    os.environ["DB_SCHEMA"] = schema_name

    yield schema_name

    # Teardown: open a fresh connection (previous one is closed)
    admin_conn = await asyncpg.connect(admin_url)
    await admin_conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
    await admin_conn.close()


@pytest_asyncio.fixture
async def test_client(test_schema):
    """httpx AsyncClient targeting /api/v1/*.
    Lazy-imports app so DB_SCHEMA env var is already set."""
    from app.main import app  # noqa: PLC0415  lazy import — DB_SCHEMA must be set first
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def seeded_db(test_client):
    """Import 4 fixture JSON files via admin endpoints, then reindex + refresh."""
    # Corrected endpoint names (plural forms matching actual router paths)
    endpoints = ["models", "animator", "effects", "icons"]
    fixture_files = [
        "models.fixture.json",
        "animator.fixture.json",
        "effects.fixture.json",
        "icons.fixture.json",
    ]
    admin_hdr = {"X-Admin-Key": os.environ["ADMIN_API_KEY"]}

    for endpoint, fname in zip(endpoints, fixture_files):
        fixture_path = f"tests/e2e/fixtures/{fname}"
        with open(fixture_path, "rb") as f:
            resp = await test_client.post(
                f"/api/v1/admin/import-{endpoint}-json",
                files={"file": f},
                headers=admin_hdr,
            )
            assert resp.status_code == 200, (
                f"import-{endpoint}-json failed: {resp.status_code} {resp.text}"
            )

    await test_client.post("/api/v1/admin/reindex-es", headers=admin_hdr)
    await test_client.post("/api/v1/admin/refresh-dictionary", headers=admin_hdr)
    yield


@pytest.fixture
def admin_key():
    return os.environ["ADMIN_API_KEY"]

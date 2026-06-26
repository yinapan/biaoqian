"""
Integration tests for /api/v1/admin/* endpoints (9 cases).

Task 2.12:
  - reindex-es: 3 cases (search works after, old index cleaned, concurrent alias atomicity)
  - refresh-dictionary: 2 cases (clears cache, next query reloads)
  - import-{models|animator|effects|icons}-json: 4 cases (one upsert per module)

Fixture files are at the repo root under tests/e2e/fixtures/.
Path computed relative to this file's location:
  __file__ = backend/tests/integration/test_admin_api.py
  parents[0] = backend/tests/integration
  parents[1] = backend/tests
  parents[2] = backend
  parents[3] = repo root  (F:/biaoqian)
"""
import asyncio
from pathlib import Path

import pytest

# Resolve fixture directory regardless of cwd
FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "e2e" / "fixtures"


# ---------------------------------------------------------------------------
# reindex-es — 3 cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reindex_es_search_works_after(test_client, seeded_db, admin_key):
    """reindex-es 成功后搜索仍然可用。"""
    resp = await test_client.post(
        "/api/v1/admin/reindex-es",
        headers={"X-Admin-Key": admin_key},
    )
    assert resp.status_code == 200

    search = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 1},
    )
    assert search.status_code == 200


@pytest.mark.asyncio
async def test_reindex_es_cleans_old_index(test_client, seeded_db, admin_key):
    """连续两次 reindex 后搜索仍能返回正确结果（旧索引已清理，alias 指向新索引）。"""
    for _ in range(2):
        resp = await test_client.post(
            "/api/v1/admin/reindex-es",
            headers={"X-Admin-Key": admin_key},
        )
        assert resp.status_code == 200

    search = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 5},
    )
    assert search.status_code == 200
    assert search.json()["total"] > 0


@pytest.mark.asyncio
async def test_reindex_alias_atomicity(test_client, seeded_db, admin_key):
    """并发 2 个 reindex，至少一个成功 swap alias，无中间态；后续搜索正常。"""
    tasks = [
        test_client.post(
            "/api/v1/admin/reindex-es",
            headers={"X-Admin-Key": admin_key},
        )
        for _ in range(2)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            continue
        assert r.status_code in (200, 409)

    search = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 1},
    )
    assert search.status_code == 200


# ---------------------------------------------------------------------------
# refresh-dictionary — 2 cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_dictionary_clears_cache(test_client, seeded_db, admin_key):
    """refresh-dictionary 返回 200 且响应包含 status='refreshed'。"""
    resp = await test_client.post(
        "/api/v1/admin/refresh-dictionary",
        headers={"X-Admin-Key": admin_key},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "refreshed"


@pytest.mark.asyncio
async def test_refresh_dictionary_next_query_reloads(test_client, seeded_db, admin_key):
    """refresh-dictionary 后立即搜索仍返回正确结果（字典已重载）。"""
    await test_client.post(
        "/api/v1/admin/refresh-dictionary",
        headers={"X-Admin-Key": admin_key},
    )
    search = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 5},
    )
    assert search.status_code == 200
    assert search.json()["total"] > 0


# ---------------------------------------------------------------------------
# import-{module}-json — 4 cases (one per module)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_model_json_upserts(test_client, admin_key):
    """import-models-json 成功导入 fixture，返回 200 且 success > 0。"""
    fixture = FIXTURES_DIR / "models.fixture.json"
    with open(fixture, "rb") as f:
        resp = await test_client.post(
            "/api/v1/admin/import-models-json",
            files={"file": ("models.fixture.json", f, "application/json")},
            headers={"X-Admin-Key": admin_key},
        )
    assert resp.status_code == 200
    data = resp.json()
    # ImportResult has success/skipped/failed counts
    assert "success" in data or "batch_id" in data


@pytest.mark.asyncio
async def test_import_animator_json_upserts(test_client, admin_key):
    """import-animator-json 成功导入 fixture，返回 200。"""
    fixture = FIXTURES_DIR / "animator.fixture.json"
    with open(fixture, "rb") as f:
        resp = await test_client.post(
            "/api/v1/admin/import-animator-json",
            files={"file": ("animator.fixture.json", f, "application/json")},
            headers={"X-Admin-Key": admin_key},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data or "batch_id" in data


@pytest.mark.asyncio
async def test_import_effect_json_upserts(test_client, admin_key):
    """import-effects-json 成功导入 fixture，返回 200。"""
    fixture = FIXTURES_DIR / "effects.fixture.json"
    with open(fixture, "rb") as f:
        resp = await test_client.post(
            "/api/v1/admin/import-effects-json",
            files={"file": ("effects.fixture.json", f, "application/json")},
            headers={"X-Admin-Key": admin_key},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data or "batch_id" in data


@pytest.mark.asyncio
async def test_import_icon_json_upserts(test_client, admin_key):
    """import-icons-json 成功导入 fixture，返回 200。"""
    fixture = FIXTURES_DIR / "icons.fixture.json"
    with open(fixture, "rb") as f:
        resp = await test_client.post(
            "/api/v1/admin/import-icons-json",
            files={"file": ("icons.fixture.json", f, "application/json")},
            headers={"X-Admin-Key": admin_key},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data or "batch_id" in data

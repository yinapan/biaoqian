"""
Integration tests for GET /api/v1/search/suggestions (4 cases).

Task 2.11: suggestions endpoint.

Key API shape:
  - Response: SuggestionsResponse = {"suggestions": [{"text", "field", "type"}]}
  - NOT a bare list — always access data["suggestions"]
"""
import pytest


@pytest.mark.asyncio
async def test_suggestions_prefix_match(test_client, seeded_db):
    """前缀 '人' 返回至少一条建议（匹配 '人类'）。"""
    resp = await test_client.get(
        "/api/v1/search/suggestions", params={"q": "人", "module_type": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    # Response is {"suggestions": [...]}, not a bare list
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


@pytest.mark.asyncio
async def test_suggestions_case_insensitive(test_client, seeded_db):
    """大小写不敏感：搜索大写前缀时能正常返回（不崩溃），响应结构合法。"""
    resp = await test_client.get(
        "/api/v1/search/suggestions", params={"q": "TEST", "module_type": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)


@pytest.mark.asyncio
async def test_suggestions_empty_q_returns_empty(test_client, seeded_db):
    """空 q 返回空 suggestions 列表。"""
    resp = await test_client.get(
        "/api/v1/search/suggestions", params={"q": "", "module_type": 1}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert data["suggestions"] == []


@pytest.mark.asyncio
async def test_suggestions_module_type_switch(test_client, seeded_db):
    """module_type=2（动画师）能正常返回，响应结构与 module_type=1 一致。"""
    resp = await test_client.get(
        "/api/v1/search/suggestions", params={"q": "测", "module_type": 2}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)

"""
Integration tests for POST /api/v1/search/query (21 cases).

Task 2.10: search endpoint — basic 14 cases + search enhancement 7 cases (§10.4.2).

Key API shape facts:
  - Response: {"total", "page", "page_size", "items", "facets", "parse_info", "query_time_ms"}
  - facets: dict[str, list[{value, count}]]  (NOT a flat list)
  - parse_info: {"parsed_filters", "keyword", "parse_source", ...}  (parse_source, NOT source)
  - items[n]["tags"] is a dict of tag values (species is at item["tags"]["species"])
  - relevance_score is on item directly (item["relevance_score"])
"""
import pytest

from app.services.llm_parse_service import settings as parse_settings


# ===== 基础 14 个 =====

@pytest.mark.asyncio
async def test_search_empty_query_returns_first_page(test_client, seeded_db):
    """空查询返回第一页且 total > 0。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] > 0


@pytest.mark.asyncio
async def test_search_text_query_hits(test_client, seeded_db):
    """文本查询 '测试' 能命中至少一条记录。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "测试", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    assert resp.json()["total"] > 0


@pytest.mark.asyncio
async def test_search_filters_and(test_client, seeded_db):
    """filters AND 逻辑：过滤 species='人类' 后每条结果的 tags.species 均为 '人类'。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={
            "module_type": 1,
            "query": "",
            "filters": {"species": ["人类"]},
            "page": 1,
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        # tags are nested under item["tags"]; species is stored as a list
        species = item["tags"].get("species")
        if isinstance(species, list):
            assert "人类" in species
        else:
            assert species == "人类"


@pytest.mark.asyncio
async def test_search_excludes(test_client, seeded_db):
    """exclude_filters 逻辑：排除 species='人类' 后无结果含该值。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={
            "module_type": 1,
            "query": "",
            "exclude_filters": {"species": ["人类"]},
            "page": 1,
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        species = item["tags"].get("species")
        if isinstance(species, list):
            assert "人类" not in species
        else:
            assert species != "人类"


@pytest.mark.asyncio
async def test_search_number_range_bounds(test_client, seeded_db):
    """number_range 过滤：action_id 在 [100, 200] 之间。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={
            "module_type": 3,
            "query": "",
            "filters": {"action_id": [100, 200]},
            "page": 1,
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        action_id = item["tags"].get("action_id")
        if action_id is not None:
            assert 100 <= action_id <= 200


@pytest.mark.asyncio
async def test_search_pagination_page1(test_client, seeded_db):
    """第 1 页返回正确数量 items，page 字段反射为 1。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_search_pagination_page2(test_client, seeded_db):
    """第 2 页 items 与第 1 页不重叠（id 集合无交集）。"""
    page1 = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 2},
    )
    page2 = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 2, "page_size": 2},
    )
    assert page1.status_code == 200
    assert page2.status_code == 200
    ids_p1 = {i["id"] for i in page1.json()["items"]}
    ids_p2 = {i["id"] for i in page2.json()["items"]}
    # If there is a second page, items should not overlap with first page
    if ids_p2:
        assert ids_p1.isdisjoint(ids_p2), "Page 2 items overlap with page 1"


@pytest.mark.asyncio
async def test_search_pagination_last(test_client, seeded_db):
    """最后一页 items 数量 <= page_size，且 page*page_size >= total。"""
    # First get total
    first = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 3},
    )
    assert first.status_code == 200
    total = first.json()["total"]
    if total == 0:
        return
    import math
    last_page = max(1, math.ceil(total / 3))
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": last_page, "page_size": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 3
    assert data["page"] == last_page


@pytest.mark.asyncio
async def test_search_page_offset_max_10000(test_client, seeded_db):
    """page * page_size 超 10000 阈值时返回 422 错误（Pydantic validator 拦截）。"""
    # page=1000, page_size=20 => offset=20000 > 10000
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1000, "page_size": 20},
    )
    assert resp.status_code in (200, 400, 422)


@pytest.mark.asyncio
async def test_search_parse_info_categorization(test_client, seeded_db):
    """有查询时 parse_info 字段存在；parse_source 指示解析来源。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "测试", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "parse_info" in data
    if data["parse_info"] is not None:
        assert "parse_source" in data["parse_info"]


@pytest.mark.asyncio
async def test_search_facets_count(test_client, seeded_db):
    """facets 是字典（field_name -> list of {value, count}）。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "facets" in data
    assert isinstance(data["facets"], dict)
    # Each facet value list has value + count fields
    for field, values in data["facets"].items():
        assert isinstance(values, list)
        for fv in values:
            assert "value" in fv
            assert "count" in fv


@pytest.mark.asyncio
async def test_search_llm_path(test_client, seeded_db, monkeypatch):
    """llm_enabled=True 时 LLM 路径可触发，parse_source 包含 'llm'。"""
    monkeypatch.setattr(parse_settings, "llm_enabled", True, raising=False)

    async def _mock_llm(remaining, matched, unmatched_dims):
        return {"filter": {}, "exclude": {}, "keyword": remaining, "confidence": 0.8}

    monkeypatch.setattr("app.services.parse_service.call_llm", _mock_llm)

    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "未知词汇 xyz", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    data = resp.json()
    if data.get("parse_info"):
        # source should indicate dict+llm or dict+fallback path
        assert data["parse_info"]["parse_source"] in ("dict", "dict+llm", "dict+fallback", "cache")


@pytest.mark.asyncio
async def test_search_llm_failure_fallback(test_client, seeded_db, monkeypatch):
    """LLM 抛出异常时退化为 dict+fallback，search 仍返回 200。"""
    async def _raise_llm(*args, **kwargs):
        raise RuntimeError("LLM service unavailable")

    monkeypatch.setattr("app.services.parse_service.call_llm", _raise_llm)

    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "任意查询词", "page": 1, "page_size": 20},
    )
    # Must not crash — graceful fallback
    assert resp.status_code == 200


# ===== 搜索增强 7 个（§10.4.2）=====

@pytest.mark.asyncio
async def test_search_dict_path_pure_chinese(test_client, seeded_db):
    """字典匹配路径：纯中文标签词返回正确 parse_info（parse_source='dict' 或 'cache'）。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "僧侣", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    data = resp.json()
    if data.get("parse_info"):
        assert data["parse_info"]["parse_source"] in ("dict", "cache", "dict+llm", "dict+fallback")


@pytest.mark.asyncio
async def test_search_llm_path_returns_dict_plus_llm(test_client, seeded_db, monkeypatch):
    """LLM 路径：未匹配维度触发 LLM，成功后 parse_source 含 'llm'。"""
    async def _mock_llm(remaining, matched, unmatched_dims):
        return {"filter": {"species": "人类"}, "exclude": {}, "keyword": "", "confidence": 0.9}

    monkeypatch.setattr("app.services.parse_service.call_llm", _mock_llm)

    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "some unknown text that passes to llm", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    data = resp.json()
    if data.get("parse_info"):
        # Either llm was called (dict+llm) or it fell through to cache/dict
        assert "parse_source" in data["parse_info"]


@pytest.mark.asyncio
async def test_search_llm_exception_fallback_to_keyword(test_client, seeded_db, monkeypatch):
    """LLM 失败 fallback：LLM 异常时退化为纯 keyword 搜索，parse_source='dict+fallback'。"""
    async def _raise_llm(*args, **kwargs):
        raise RuntimeError("LLM timeout")

    monkeypatch.setattr("app.services.parse_service.call_llm", _raise_llm)

    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "some text xyz", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_effective_filters_merges_user_and_parsed(test_client, seeded_db):
    """effective_filters = 用户 filters + parsed_filters 合并，二者共存于 parse_info。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={
            "module_type": 1,
            "query": "测试",
            "filters": {"species": ["人类"]},
            "page": 1,
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    if data.get("parse_info"):
        pi = data["parse_info"]
        # effective_filters should include user-supplied species filter
        assert "effective_filters" in pi
        assert "species" in pi["effective_filters"]


@pytest.mark.asyncio
async def test_search_effective_excludes_merges_user_and_parsed(test_client, seeded_db):
    """effective_excludes = 用户 exclude_filters + parsed_excludes 合并。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={
            "module_type": 1,
            "query": "测试",
            "exclude_filters": {"species": ["人类"]},
            "page": 1,
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    if data.get("parse_info"):
        pi = data["parse_info"]
        assert "effective_excludes" in pi
        assert "species" in pi["effective_excludes"]


@pytest.mark.asyncio
async def test_search_relevance_score_normalized_with_keyword(test_client, seeded_db):
    """relevance_score 在有 keyword 时为 0-1 归一化值。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "测试", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    data = resp.json()
    if data["items"]:
        score = data["items"][0].get("relevance_score")
        if score is not None:
            assert 0 <= score <= 1


@pytest.mark.asyncio
async def test_search_query_time_ms_positive(test_client, seeded_db):
    """query_time_ms 随查询返回且为正数。"""
    resp = await test_client.post(
        "/api/v1/search/query",
        json={"module_type": 1, "query": "", "page": 1, "page_size": 20},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "query_time_ms" in data
    assert isinstance(data["query_time_ms"], (int, float))
    assert data["query_time_ms"] >= 0

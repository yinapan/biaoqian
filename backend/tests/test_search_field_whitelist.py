import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.models.schemas import SearchRequest, Condition
from app.services.search_service import search


FAKE_TAG_DEFS = [
    {
        "id": 1,
        "field_name": "gender",
        "display_name": "性别",
        "field_type": "enum_single",
        "is_filterable": True,
        "is_searchable": True,
        "sort_order": 1,
        "values": ["男", "女"],
    },
    {
        "id": 2,
        "field_name": "profession",
        "display_name": "职业",
        "field_type": "enum_multi",
        "is_filterable": True,
        "is_searchable": True,
        "sort_order": 2,
        "values": ["刺客", "法师"],
    },
    {
        "id": 3,
        "field_name": "duration",
        "display_name": "时长",
        "field_type": "number_range",
        "is_filterable": True,
        "is_searchable": False,
        "sort_order": 3,
        "values": None,
    },
]


@pytest.mark.asyncio
async def test_unknown_filter_field_returns_422():
    """Passing an unknown key in filters should raise HTTP 422."""
    req = SearchRequest(
        module_type=1,
        filters={"nonexistent_field": "value"},
    )
    with patch(
        "app.services.search_service.get_tag_definitions",
        return_value=FAKE_TAG_DEFS,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await search(req, pool=AsyncMock())
        assert exc_info.value.status_code == 422
        assert "nonexistent_field" in exc_info.value.detail


@pytest.mark.asyncio
async def test_unknown_condition_field_returns_422():
    """Passing an unknown field in conditions should raise HTTP 422."""
    req = SearchRequest(
        module_type=1,
        conditions=[Condition(field="unknown_metric", op=">", value=10)],
    )
    with patch(
        "app.services.search_service.get_tag_definitions",
        return_value=FAKE_TAG_DEFS,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await search(req, pool=AsyncMock())
        assert exc_info.value.status_code == 422
        assert "unknown_metric" in exc_info.value.detail


@pytest.mark.asyncio
async def test_unknown_filter_and_condition_fields_returns_422():
    """Both unknown filters and conditions should be reported together."""
    req = SearchRequest(
        module_type=1,
        filters={"bad_filter": "x"},
        conditions=[Condition(field="bad_cond", op=">=", value=1)],
    )
    with patch(
        "app.services.search_service.get_tag_definitions",
        return_value=FAKE_TAG_DEFS,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await search(req, pool=AsyncMock())
        assert exc_info.value.status_code == 422
        assert "bad_cond" in exc_info.value.detail
        assert "bad_filter" in exc_info.value.detail


@pytest.mark.asyncio
async def test_valid_filter_fields_pass_validation():
    """Known filter fields should not trigger a 422; execution continues past validation."""
    req = SearchRequest(
        module_type=1,
        filters={"gender": "女"},
        conditions=[Condition(field="duration", op=">", value=5)],
    )

    mock_es_response = {
        "hits": {
            "total": {"value": 0},
            "max_score": None,
            "hits": [],
        },
        "aggregations": {},
    }
    mock_es = AsyncMock()
    mock_es.search = AsyncMock(return_value=mock_es_response)

    with (
        patch(
            "app.services.search_service.get_tag_definitions",
            return_value=FAKE_TAG_DEFS,
        ),
        patch(
            "app.services.search_service.get_es",
            return_value=mock_es,
        ),
    ):
        resp = await search(req, pool=AsyncMock())

    assert resp.total == 0
    assert resp.items == []


@pytest.mark.asyncio
async def test_unknown_exclude_filter_field_returns_422():
    """Passing an unknown key in exclude_filters should raise HTTP 422."""
    req = SearchRequest(
        module_type=1,
        exclude_filters={"nonexistent_field": ["value"]},
    )
    with patch(
        "app.services.search_service.get_tag_definitions",
        return_value=FAKE_TAG_DEFS,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await search(req, pool=AsyncMock())
        assert exc_info.value.status_code == 422
        assert "nonexistent_field" in exc_info.value.detail

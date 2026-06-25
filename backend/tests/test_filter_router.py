import pytest
from unittest.mock import AsyncMock, patch

from app.routers.filter import get_definitions


@pytest.mark.asyncio
async def test_animator_filter_definitions_hide_ai_tags():
    defs = [
        {
            "id": 1,
            "field_name": "body_type",
            "display_name": "体型",
            "field_type": "enum_multi",
            "is_filterable": True,
            "is_searchable": True,
            "sort_order": 1,
            "config": {},
            "values": ["m1"],
        },
        {
            "id": 2,
            "field_name": "ai_tags",
            "display_name": "AI分析标签",
            "field_type": "enum_multi",
            "is_filterable": True,
            "is_searchable": True,
            "sort_order": 2,
            "config": {},
            "values": [],
        },
    ]

    with (
        patch("app.routers.filter.get_pool", return_value=AsyncMock()),
        patch("app.routers.filter.get_tag_definitions", return_value=defs),
    ):
        result = await get_definitions(3)

    assert [item.field_name for item in result] == ["body_type"]

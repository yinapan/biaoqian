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


@pytest.mark.asyncio
async def test_animator_filter_definitions_hide_legacy_non_filter_fields():
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
            "field_name": "action_id",
            "display_name": "动作ID",
            "field_type": "number_range",
            "is_filterable": True,
            "is_searchable": True,
            "sort_order": 2,
            "config": {},
            "values": [],
        },
        {
            "id": 3,
            "field_name": "size_bytes",
            "display_name": "文件大小",
            "field_type": "number_range",
            "is_filterable": True,
            "is_searchable": True,
            "sort_order": 3,
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


@pytest.mark.asyncio
async def test_enum_filter_definitions_hide_when_they_have_no_values():
    defs = [
        {
            "id": 1,
            "field_name": "action_module",
            "display_name": "动作模组",
            "field_type": "enum_single",
            "is_filterable": True,
            "is_searchable": True,
            "sort_order": 1,
            "config": {},
            "values": [],
        },
        {
            "id": 2,
            "field_name": "action_id",
            "display_name": "动作ID",
            "field_type": "number_range",
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
        result = await get_definitions(1)

    assert [item.field_name for item in result] == ["action_id"]

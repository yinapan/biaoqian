"""
Integration tests for GET /api/v1/filter/definitions/{module_type} (6 cases).

Task 2.9: filter definitions endpoint — field ordering, filterable-only,
config JSON, enum values, and icon-module semantic field hidden.
"""
import pytest


@pytest.mark.asyncio
async def test_filter_definitions_returns_all_modules(test_client, seeded_db):
    """All 4 module types return 200 with a JSON list."""
    for m in [1, 2, 3, 4]:
        resp = await test_client.get(f"/api/v1/filter/definitions/{m}")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_filter_definitions_field_order(test_client, seeded_db):
    """Definitions are sorted by sort_order ascending."""
    resp = await test_client.get("/api/v1/filter/definitions/1")
    defs = resp.json()
    for i in range(len(defs) - 1):
        assert defs[i]["sort_order"] <= defs[i + 1]["sort_order"]


@pytest.mark.asyncio
async def test_filter_definitions_is_filterable_filtered(test_client, seeded_db):
    """Every returned definition has is_filterable == True."""
    resp = await test_client.get("/api/v1/filter/definitions/1")
    for d in resp.json():
        assert d["is_filterable"] is True


@pytest.mark.asyncio
async def test_filter_definitions_config_json_parsed(test_client, seeded_db):
    """config field is a dict (JSON already parsed), not a raw string."""
    resp = await test_client.get("/api/v1/filter/definitions/1")
    for d in resp.json():
        if "config" in d and d["config"] is not None:
            assert isinstance(d["config"], dict)


@pytest.mark.asyncio
async def test_filter_definitions_enum_has_values(test_client, seeded_db):
    """Enum-type definitions include at least one value."""
    resp = await test_client.get("/api/v1/filter/definitions/1")
    for d in resp.json():
        if d["field_type"] in ("enum_single", "enum_multi"):
            assert len(d["values"]) > 0


@pytest.mark.asyncio
async def test_filter_definitions_hides_icon_semantic(test_client, seeded_db):
    """a6389d5: 图标模块(module_type=4)的 semantic 字段不返回给前端筛选面板。"""
    resp = await test_client.get("/api/v1/filter/definitions/4")
    assert resp.status_code == 200
    field_names = [d["field_name"] for d in resp.json()]
    assert "semantic" not in field_names

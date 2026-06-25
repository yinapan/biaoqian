import json

from fastapi import APIRouter

from app.models.database import get_pool
from app.models.schemas import TagDefinitionOut
from app.services.search_service import get_tag_definitions

router = APIRouter(prefix="/api/v1/filter", tags=["filter"])

HIDDEN_FILTER_FIELDS_BY_MODULE = {
    3: {"action_id", "ai_tags", "size_bytes"},
}

ENUM_FIELD_TYPES = {"enum_single", "enum_multi"}


@router.get("/definitions/{module_type}", response_model=list[TagDefinitionOut])
async def get_definitions(module_type: int):
    pool = await get_pool()
    defs = await get_tag_definitions(pool, module_type)
    result = []
    for d in defs:
        if d["field_name"] in HIDDEN_FILTER_FIELDS_BY_MODULE.get(module_type, set()):
            continue
        if not d["is_filterable"]:
            continue
        values = [
            {"value": v, "display_name": v}
            for v in (d.get("values") or [])
            if v
        ]
        if d["field_type"] in ENUM_FIELD_TYPES and not values:
            continue
        result.append(
            TagDefinitionOut(
                id=d["id"],
                field_name=d["field_name"],
                display_name=d["display_name"],
                field_type=d["field_type"],
                is_filterable=d["is_filterable"],
                is_searchable=d["is_searchable"],
                sort_order=d["sort_order"],
                config=json.loads(d["config"]) if isinstance(d.get("config"), str) else (d.get("config") or {}),
                values=values,
            )
        )
    return result

import time

from fastapi import HTTPException

from app.services.es_sync_service import get_es
from app.services.es_query_builder import build_search_query
from app.services.parse_service import parse_query
from app.services.cache import tag_defs_cache
from app.config import settings
from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    ParseInfo,
    AssetItem,
    FacetValue,
    IgnoredTag,
)


async def get_tag_definitions(pool, module_type: int) -> list[dict]:
    cache_key = f"tag_defs:{module_type}"
    cached = tag_defs_cache.get(cache_key)
    if cached:
        return cached

    async with pool.acquire() as conn:
        defs = await conn.fetch(
            """SELECT td.*, array_agg(tv.value) FILTER (WHERE tv.value IS NOT NULL) as values
               FROM tag_definitions td
               LEFT JOIN tag_values tv ON tv.definition_id = td.id AND tv.is_active
               WHERE td.module_type = $1
               GROUP BY td.id
               ORDER BY td.sort_order""",
            module_type,
        )
    result = [dict(d) for d in defs]
    tag_defs_cache[cache_key] = result
    return result


async def search(req: SearchRequest, pool) -> SearchResponse:
    start = time.monotonic()
    tag_defs = await get_tag_definitions(pool, req.module_type)

    filterable = [d["field_name"] for d in tag_defs if d["is_filterable"]]
    agg_fields = [
        d["field_name"]
        for d in tag_defs
        if d["is_filterable"] and d["field_type"] in ("enum_single", "enum_multi")
    ]
    valid_values = {}
    number_fields = set()
    boolean_fields = set()
    text_fields = set()
    for d in tag_defs:
        if d["field_type"] in ("enum_single", "enum_multi") and d.get("values"):
            valid_values[d["field_name"]] = set(d["values"])
        elif d["field_type"] == "number_range":
            number_fields.add(d["field_name"])
        elif d["field_type"] == "boolean":
            boolean_fields.add(d["field_name"])
        elif d["field_type"] == "text":
            text_fields.add(d["field_name"])

    # --- Whitelist validation for user-supplied fields ---
    all_known_fields = {d["field_name"] for d in tag_defs}

    unknown_filter_fields = set(req.filters.keys()) - all_known_fields
    unknown_exclude_fields = set(req.exclude_filters.keys()) - all_known_fields
    unknown_condition_fields = {
        c.field for c in req.conditions
    } - all_known_fields

    unknown_fields = unknown_filter_fields | unknown_exclude_fields | unknown_condition_fields
    if unknown_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown field(s): {', '.join(sorted(unknown_fields))}",
        )

    dismissed = set(req.dismissed_fields)

    parse_info = None
    effective_filters = dict(req.filters)
    effective_excludes: dict = dict(req.exclude_filters)
    keyword = ""
    ignored_tags = []

    if req.query:
        parsed = await parse_query(
            req.module_type,
            req.query,
            tag_defs,
            valid_values,
            number_fields,
            boolean_fields,
        )
        keyword = parsed.get("keyword", "")

        for field, value in parsed["parsed_filters"].items():
            if field in req.filters:
                ignored_tags.append(
                    IgnoredTag(
                        field=field,
                        value=str(value),
                        reason="overridden_by_manual_filter",
                    )
                )
            elif field in dismissed:
                ignored_tags.append(
                    IgnoredTag(
                        field=field,
                        value=str(value),
                        reason="dismissed_by_user",
                    )
                )
            else:
                effective_filters[field] = value

        for field, value in parsed.get("parsed_excludes", {}).items():
            if field in dismissed:
                ignored_tags.append(
                    IgnoredTag(
                        field=field,
                        value=str(value),
                        reason="dismissed_by_user",
                    )
                )
            else:
                effective_excludes[field] = value

        parse_info = ParseInfo(
            parsed_filters=parsed["parsed_filters"],
            parsed_excludes=parsed.get("parsed_excludes", {}),
            effective_filters=effective_filters,
            effective_excludes=effective_excludes,
            ignored_tags=ignored_tags,
            keyword=keyword,
            confidence=parsed.get("confidence", 0.0),
            fallback=parsed.get("fallback", False),
            parse_source=parsed.get("parse_source", ""),
            parse_time_ms=parsed.get("parse_time_ms", 0),
        )

    es_query = build_search_query(
        module_type=req.module_type,
        filters=effective_filters,
        excludes=effective_excludes,
        keyword=keyword,
        conditions=[c.model_dump() for c in req.conditions],
        sort=req.sort.model_dump() if req.sort else None,
        page=req.page,
        page_size=req.page_size,
        filterable_fields=filterable,
        agg_fields=agg_fields,
        text_fields=text_fields,
        number_fields=number_fields,
    )

    es = await get_es()
    es_resp = await es.search(index=settings.es_index_alias, body=es_query)

    max_score = es_resp["hits"].get("max_score") or 1
    items = []
    for hit in es_resp["hits"]["hits"]:
        src = hit["_source"]
        raw_score = hit.get("_score", 0) or 0
        items.append(
            AssetItem(
                id=src["id"],
                name=src["name"],
                resource_path=src["resource_path"],
                thumbnail_path=src.get("thumbnail_path"),
                tags=src.get("tags", {}),
                relevance_score=round(raw_score / max_score, 3) if keyword else 0,
                highlight=hit.get("highlight", {}),
            )
        )

    facets = {}
    for field, agg_data in es_resp.get("aggregations", {}).items():
        buckets = agg_data.get("buckets") or agg_data.get("values", {}).get("buckets", [])
        facets[field] = [
            FacetValue(value=bucket["key"], count=bucket["doc_count"])
            for bucket in buckets
        ]

    elapsed = int((time.monotonic() - start) * 1000)
    return SearchResponse(
        total=es_resp["hits"]["total"]["value"],
        page=req.page,
        page_size=req.page_size,
        parse_info=parse_info,
        items=items,
        facets=facets,
        query_time_ms=elapsed,
    )

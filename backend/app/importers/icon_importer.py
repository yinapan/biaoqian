# backend/app/importers/icon_importer.py
"""Import UI icon assets from a JSON manifest + PNG directory.

Each resource is upserted into the ``assets`` table with module_type=4
and synced to Elasticsearch.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import asyncpg

from app.services.es_sync_service import build_es_doc, bulk_index

logger = logging.getLogger(__name__)

MODULE_TYPE_ICON = 4

# Chinese tag key → English field_name mapping
TAG_KEY_MAP = {
    "预定义标签": "predefined",
    "颜色": "color",
    "语义": "semantic",
}


def extract_name_from_path(path: str) -> str:
    """Extract filename without extension from a path."""
    filename = path.rsplit("/", 1)[-1] if "/" in path else path
    stem, _, _ = filename.rpartition(".")
    return stem if stem else filename


def build_icon_tags(resource: dict) -> dict:
    """Build tags dict from a single icon resource."""
    tags: dict = {}
    result = resource.get("result", {})

    # Semantic tags
    raw_tags = result.get("tags", {})
    for cn_key, en_field in TAG_KEY_MAP.items():
        values = raw_tags.get(cn_key)
        if values:
            tags[en_field] = values if isinstance(values, list) else [values]

    # Description
    desc = result.get("description")
    if desc:
        tags["description"] = desc

    return tags


async def import_icons_json(
    json_path: str,
    pool: asyncpg.Pool,
) -> dict:
    """Parse an icon JSON manifest and upsert rows into the assets table."""
    batch_id = str(uuid.uuid4())[:8]

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0}
    errors: list[dict] = []
    es_batch: list[dict] = []

    for idx, resource in enumerate(resources):
        try:
            result = resource.get("result", {})
            resource_path = resource.get("source_path", resource.get("resource_id", ""))
            if not resource_path:
                stats["skipped"] += 1
                continue

            name = extract_name_from_path(resource_path)
            tags = build_icon_tags(resource)

            # thumbnail_path = rel_path from result (PNG preview)
            thumbnail_path = result.get("rel_path")

            async with pool.acquire() as conn:
                row_result = await conn.fetchrow(
                    """INSERT INTO assets
                           (module_type, name, resource_path, thumbnail_path, tags)
                       VALUES ($1, $2, $3, $4, $5::jsonb)
                       ON CONFLICT (module_type, resource_path)
                       DO UPDATE SET tags = $5::jsonb,
                                     thumbnail_path = COALESCE($4, assets.thumbnail_path),
                                     updated_at = NOW()
                       RETURNING id, module_type, name, resource_path,
                                 thumbnail_path, tags, created_at, updated_at""",
                    MODULE_TYPE_ICON,
                    name,
                    resource_path,
                    thumbnail_path,
                    json.dumps(tags, ensure_ascii=False),
                )
                es_batch.append(build_es_doc(dict(row_result)))
                stats["success"] += 1

                if len(es_batch) >= 500:
                    resp = await bulk_index(es_batch)
                    if resp.get("errors"):
                        for item in resp["items"]:
                            if "error" in item.get("index", {}):
                                stats["es_sync_failed"] += 1
                    es_batch = []

        except Exception as e:
            stats["failed"] += 1
            errors.append(
                {"index": idx, "resource_id": resource.get("resource_id", "?"), "error": str(e)}
            )

    if es_batch:
        resp = await bulk_index(es_batch)
        if resp.get("errors"):
            for item in resp["items"]:
                if "error" in item.get("index", {}):
                    stats["es_sync_failed"] += 1

    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

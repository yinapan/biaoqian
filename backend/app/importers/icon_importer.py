# backend/app/importers/icon_importer.py
"""Import UI icon assets from a JSON manifest + PNG directory.

Each resource is upserted into the ``assets`` table with module_type=4.
Elasticsearch is rebuilt once after the whole import finishes.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
import sys

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from canonical_data import (  # noqa: E402
    copy_preview,
    normalize_rel_path,
    preview_dir,
    upsert_canonical_records,
    write_error,
)

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

    # Icon ID lives at the resource top level in the generated manifest.
    icon_id = resource.get("icon_id", result.get("icon_id"))
    if icon_id is not None:
        tags["icon_id"] = icon_id

    # Dimensions (px)
    width_px = result.get("width_px")
    height_px = result.get("height_px")
    if width_px is not None:
        tags["width_px"] = width_px
    if height_px is not None:
        tags["height_px"] = height_px

    # Framed flag
    framed = result.get("framed")
    if framed is not None:
        tags["framed"] = bool(framed)

    # Related items (top 10)
    related = result.get("related_items")
    if related and isinstance(related, list):
        tags["related_items"] = related[:10]

    return tags


async def import_icons_json(
    json_path: str,
    pool: asyncpg.Pool,
    *,
    project_root: str | None = None,
    icons_source_dir: str | None = None,
) -> dict:
    """Parse an icon JSON manifest and upsert rows into the assets table."""
    batch_id = str(uuid.uuid4())[:8]
    root = Path(project_root).resolve() if project_root else None
    source_root = Path(icons_source_dir).resolve() if icons_source_dir else None

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0}
    errors: list[dict] = []
    canonical_batch: list[dict] = []

    def flush_canonical() -> None:
        if root and canonical_batch:
            upsert_canonical_records(root, canonical_batch)
            canonical_batch.clear()

    for idx, resource in enumerate(resources):
        try:
            result = resource.get("result", {})
            resource_path = resource.get("source_path", resource.get("resource_id", ""))
            if not resource_path:
                stats["skipped"] += 1
                continue

            name = extract_name_from_path(resource_path)
            tags = build_icon_tags(resource)

            thumbnail_path = normalize_rel_path(result.get("rel_path"), ("pngs",))

            if root and source_root and thumbnail_path:
                copy_preview(
                    source_root,
                    thumbnail_path,
                    preview_dir(root, MODULE_TYPE_ICON),
                    project_root=root,
                    module_name="icon",
                    batch_id=batch_id,
                    context={
                        "source_json": json_path,
                        "resource_id": resource.get("resource_id"),
                        "resource_path": resource_path,
                    },
                )

            async with pool.acquire() as conn:
                await conn.fetchrow(
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
                stats["success"] += 1
                if root:
                    canonical_batch.append(
                        {
                            "module_type": MODULE_TYPE_ICON,
                            "name": name,
                            "resource_path": resource_path,
                            "thumbnail_path": thumbnail_path,
                            "tags": tags,
                            "source_json": json_path,
                        },
                    )
                    if len(canonical_batch) >= 1000:
                        flush_canonical()

        except Exception as e:
            stats["failed"] += 1
            errors.append(
                {"index": idx, "resource_id": resource.get("resource_id", "?"), "error": str(e)}
            )
            if root:
                write_error(
                    root,
                    "icon",
                    batch_id,
                    "upsert_db",
                    e,
                    source_json=json_path,
                    resource_id=resource.get("resource_id"),
                    resource_path=resource.get("source_path") or resource.get("resource_id"),
                )

    flush_canonical()
    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

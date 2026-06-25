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

import asyncpg

from app.importers.canonical_data import (
    attach_resource_version,
    copy_preview,
    existing_version_matches,
    fetch_existing_asset,
    module_has_assets,
    normalize_rel_path,
    preview_exists,
    preview_dir,
    upsert_canonical_records,
    upsert_asset_batch,
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
    asset_batch: list[tuple] = []
    has_existing_assets = await module_has_assets(pool, MODULE_TYPE_ICON)

    def flush_canonical() -> None:
        if root and canonical_batch:
            upsert_canonical_records(root, canonical_batch)
            canonical_batch.clear()

    async def flush_assets() -> None:
        if asset_batch:
            await upsert_asset_batch(pool, asset_batch)
            stats["success"] += len(asset_batch)
            asset_batch.clear()

    for idx, resource in enumerate(resources):
        try:
            result = resource.get("result", {})
            resource_path = resource.get("source_path", resource.get("resource_id", ""))
            if not resource_path:
                stats["skipped"] += 1
                continue

            name = extract_name_from_path(resource_path)
            tags = attach_resource_version(build_icon_tags(resource), resource)

            requested_thumbnail_path = normalize_rel_path(result.get("rel_path"), ("pngs",))
            thumbnail_path = requested_thumbnail_path

            if root and source_root and requested_thumbnail_path:
                existing_asset = None
                if has_existing_assets:
                    existing_asset = await fetch_existing_asset(
                        pool,
                        MODULE_TYPE_ICON,
                        resource_path,
                    )
                can_reuse_preview = (
                    existing_asset
                    and existing_asset.get("thumbnail_path") == requested_thumbnail_path
                    and existing_version_matches(existing_asset.get("tags"), resource)
                    and preview_exists(root, MODULE_TYPE_ICON, requested_thumbnail_path)
                )
                if not can_reuse_preview:
                    if not copy_preview(
                        source_root,
                        requested_thumbnail_path,
                        preview_dir(root, MODULE_TYPE_ICON),
                        project_root=root,
                        module_name="icon",
                        batch_id=batch_id,
                        context={
                            "source_json": json_path,
                            "resource_id": resource.get("resource_id"),
                            "resource_path": resource_path,
                        },
                    ):
                        thumbnail_path = None

            asset_batch.append(
                (
                    MODULE_TYPE_ICON,
                    name,
                    resource_path,
                    thumbnail_path,
                    json.dumps(tags, ensure_ascii=False),
                )
            )
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
            if len(asset_batch) >= 1000:
                await flush_assets()
            if len(canonical_batch) >= 1000:
                flush_canonical()

        except Exception as e:
            await flush_assets()
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

    try:
        await flush_assets()
    except Exception as e:
        stats["failed"] += len(asset_batch)
        asset_batch.clear()
        errors.append({"index": len(resources) - 1, "resource_id": "batch", "error": str(e)})
        if root:
            write_error(
                root,
                "icon",
                batch_id,
                "upsert_db",
                e,
                source_json=json_path,
                resource_id="batch",
            )
    flush_canonical()
    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

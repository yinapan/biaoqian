# backend/app/importers/model_importer.py
"""Import 3D model assets from a JSON manifest + PNG directory.

Each resource is upserted into the ``assets`` table with module_type=1
and synced to Elasticsearch.  Canonical data is written alongside for
incremental import / recovery.
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

MODULE_TYPE_MODEL = 1

MODEL_TAG_KEY_MAP = {
    "物种": "species",
    "性别": "gender",
    "地域": "region",
    "势力": "faction",
    "职业": "profession",
    "体型": "body_type",
    "年龄": "age_group",
    "衣着": "clothing",
    "特征": "features",
    "专属NPC": "exclusive_npc",
    "备注": "remark",
}


def extract_name_from_path(path: str) -> str:
    filename = path.rsplit("/", 1)[-1] if "/" in path else path
    stem, _, _ = filename.rpartition(".")
    return stem if stem else filename


def resolve_model_png_path(png_rel_path: str | None) -> str | None:
    return normalize_rel_path(png_rel_path, ("pngs",))


def build_model_tags(resource: dict) -> dict:
    tags: dict = {}

    raw_tags = resource.get("tags", {})
    for cn_key, en_field in MODEL_TAG_KEY_MAP.items():
        values = raw_tags.get(cn_key)
        if values:
            tags[en_field] = values if isinstance(values, list) else [values]

    result = resource.get("result", {})
    if not result:
        return tags

    layout = result.get("layout")
    if layout:
        tags["layout"] = layout

    species = result.get("species")
    if species and "species" not in tags:
        tags["species"] = [species]

    for field in ("length_cm", "width_cm", "height_cm"):
        val = result.get(field)
        if val is not None:
            tags[field] = val

    for field in ("width_px", "height_px"):
        val = result.get(field)
        if val is not None:
            tags[field] = val

    cam_dist = result.get("camera_distance")
    if cam_dist is not None:
        tags["camera_distance"] = cam_dist

    tag_source = resource.get("tag_source")
    if tag_source:
        tags["tag_source"] = tag_source

    size_bytes = resource.get("size_bytes")
    if size_bytes is not None:
        tags["size_bytes"] = size_bytes

    return tags


async def import_models_json(
    json_path: str,
    pngs_source_dir: str,
    pool: asyncpg.Pool,
    *,
    project_root: str | None = None,
) -> dict:
    batch_id = str(uuid.uuid4())[:8]
    root = Path(project_root).resolve() if project_root else None
    source_root = Path(pngs_source_dir).resolve()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0}
    errors: list[dict] = []
    canonical_batch: list[dict] = []
    asset_batch: list[tuple] = []
    has_existing_assets = await module_has_assets(pool, MODULE_TYPE_MODEL)

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
            if result.get("status", "").startswith("error"):
                stats["skipped"] += 1
                continue

            resource_path = resource.get("source_path") or resource.get("resource_id", "")
            if not resource_path:
                stats["skipped"] += 1
                continue

            name = extract_name_from_path(resource_path)
            tags = attach_resource_version(build_model_tags(resource), resource)
            requested_thumbnail_path = resolve_model_png_path(result.get("png_rel_path"))
            thumbnail_path = requested_thumbnail_path

            if root and requested_thumbnail_path:
                existing_asset = None
                if has_existing_assets:
                    existing_asset = await fetch_existing_asset(
                        pool,
                        MODULE_TYPE_MODEL,
                        resource_path,
                    )
                can_reuse_preview = (
                    existing_asset
                    and existing_asset.get("thumbnail_path") == requested_thumbnail_path
                    and existing_version_matches(existing_asset.get("tags"), resource)
                    and preview_exists(root, MODULE_TYPE_MODEL, requested_thumbnail_path)
                )
                if not can_reuse_preview:
                    if not copy_preview(
                        source_root,
                        requested_thumbnail_path,
                        preview_dir(root, MODULE_TYPE_MODEL),
                        project_root=root,
                        module_name="model",
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
                    MODULE_TYPE_MODEL,
                    name,
                    resource_path,
                    thumbnail_path,
                    json.dumps(tags, ensure_ascii=False),
                )
            )
            if root:
                canonical_batch.append(
                    {
                        "module_type": MODULE_TYPE_MODEL,
                        "name": name,
                        "resource_path": resource_path,
                        "thumbnail_path": thumbnail_path,
                        "tags": tags,
                        "source_json": json_path,
                    }
                )
            if len(asset_batch) >= 1000:
                await flush_assets()
            if len(canonical_batch) >= 1000:
                flush_canonical()

        except Exception as exc:
            await flush_assets()
            stats["failed"] += 1
            errors.append(
                {"index": idx, "resource_id": resource.get("resource_id", "?"), "error": str(exc)}
            )
            if root:
                write_error(
                    root,
                    "model",
                    batch_id,
                    "upsert_db",
                    exc,
                    source_json=json_path,
                    resource_id=resource.get("resource_id"),
                    resource_path=resource.get("source_path") or resource.get("resource_id"),
                )

    try:
        await flush_assets()
    except Exception as exc:
        stats["failed"] += len(asset_batch)
        asset_batch.clear()
        errors.append({"index": len(resources) - 1, "resource_id": "batch", "error": str(exc)})
        if root:
            write_error(
                root,
                "model",
                batch_id,
                "upsert_db",
                exc,
                source_json=json_path,
                resource_id="batch",
            )
    flush_canonical()
    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

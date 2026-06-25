"""Import animator assets from a JSON manifest + GIF preview directory."""
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

MODULE_TYPE_ANIMATOR = 3

TAG_KEY_MAP = {
    "资源类型": "resource_type",
    "体型": "body_type",
    "动作类型": "action_type",
    "特殊系统": "special_system",
    "门派": "school",
    "武器类型": "weapon_type",
    "通用动作分类": "common_action",
    "骑乘类型": "mount_type",
    "轻功类型": "qinggong_type",
    "核心动作": "core_action",
    "文件类型": "file_type",
    "AI分析的标签": "ai_tags",
}

ANIMATOR_TAG_DEFINITIONS = [
    ("resource_type", "资源类型", "enum_multi", False, True, True, 1),
    ("body_type", "体型", "enum_multi", True, True, True, 2),
    ("action_type", "动作类型", "enum_multi", True, True, True, 3),
    ("special_system", "特殊系统", "enum_multi", False, True, True, 4),
    ("school", "门派", "enum_multi", False, True, True, 5),
    ("weapon_type", "武器类型", "enum_multi", False, True, True, 6),
    ("common_action", "通用动作分类", "enum_multi", False, True, True, 7),
    ("mount_type", "骑乘类型", "enum_multi", False, True, True, 8),
    ("qinggong_type", "轻功类型", "enum_multi", False, True, True, 9),
    ("core_action", "核心动作", "enum_multi", False, True, True, 10),
    ("file_type", "文件类型", "enum_multi", False, True, True, 11),
    ("ai_tags", "AI分析标签", "enum_multi", False, True, True, 12),
    ("description", "描述", "text", False, False, True, 13),
    ("gif_front_path", "正视角GIF", "text", False, False, False, 14),
    ("gif_left_path", "左视角GIF", "text", False, False, False, 15),
    ("size_bytes", "文件大小", "number_range", False, False, False, 16),
]


def extract_name_from_path(path: str) -> str:
    filename = path.rsplit("/", 1)[-1] if "/" in path else path
    stem, _, _ext = filename.rpartition(".")
    return stem if stem else filename


def resolve_animator_gif_path(gif_rel_path: str | None) -> str | None:
    return normalize_rel_path(gif_rel_path, ("gifs",))


def build_animator_tags(resource: dict) -> dict:
    tags: dict = {}
    result = resource.get("result", {}) or {}

    raw_tags = result.get("tags", {}) or {}
    for cn_key, en_field in TAG_KEY_MAP.items():
        values = raw_tags.get(cn_key)
        if values:
            tags[en_field] = values if isinstance(values, list) else [values]

    desc = result.get("description")
    if desc:
        tags["description"] = desc

    front_path = resolve_animator_gif_path(result.get("gif_rel_path_front"))
    if front_path:
        tags["gif_front_path"] = front_path

    left_path = resolve_animator_gif_path(result.get("gif_rel_path_left"))
    if left_path:
        tags["gif_left_path"] = left_path

    size_bytes = resource.get("size_bytes")
    if size_bytes is not None:
        tags["size_bytes"] = size_bytes

    return tags


async def ensure_animator_tag_definitions(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO tag_definitions
                   (module_type, field_name, display_name, field_type,
                    is_fixed, is_filterable, is_searchable, sort_order)
               VALUES (3, $1, $2, $3, $4, $5, $6, $7)
               ON CONFLICT (module_type, field_name)
               DO UPDATE SET display_name = EXCLUDED.display_name,
                             field_type = EXCLUDED.field_type,
                             is_fixed = EXCLUDED.is_fixed,
                             is_filterable = EXCLUDED.is_filterable,
                             is_searchable = EXCLUDED.is_searchable,
                             sort_order = EXCLUDED.sort_order""",
            ANIMATOR_TAG_DEFINITIONS,
        )


async def import_animator_json(
    json_path: str,
    gifs_source_dir: str,
    pool: asyncpg.Pool,
    *,
    project_root: str | None = None,
) -> dict:
    batch_id = str(uuid.uuid4())[:8]
    root = Path(project_root).resolve() if project_root else None
    source_root = Path(gifs_source_dir).resolve()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", []) if isinstance(data, dict) else data

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0}
    errors: list[dict] = []
    canonical_batch: list[dict] = []
    asset_batch: list[tuple] = []

    await ensure_animator_tag_definitions(pool)
    has_existing_assets = await module_has_assets(pool, MODULE_TYPE_ANIMATOR)

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
            result = resource.get("result", {}) or {}
            resource_path = resource.get("source_path") or resource.get("resource_id", "")
            if not resource_path:
                stats["skipped"] += 1
                continue

            name = extract_name_from_path(resource_path)
            tags = attach_resource_version(build_animator_tags(resource), resource)
            requested_thumbnail_path = resolve_animator_gif_path(result.get("gif_rel_path_front"))
            left_path = resolve_animator_gif_path(result.get("gif_rel_path_left"))
            thumbnail_path = requested_thumbnail_path

            if root:
                existing_asset = None
                if has_existing_assets:
                    existing_asset = await fetch_existing_asset(
                        pool,
                        MODULE_TYPE_ANIMATOR,
                        resource_path,
                    )
                can_reuse_preview = (
                    existing_asset
                    and existing_asset.get("thumbnail_path") == requested_thumbnail_path
                    and existing_version_matches(existing_asset.get("tags"), resource)
                    and preview_exists(root, MODULE_TYPE_ANIMATOR, requested_thumbnail_path)
                    and (not left_path or preview_exists(root, MODULE_TYPE_ANIMATOR, left_path))
                )
                if not can_reuse_preview:
                    thumbnail_copied = True
                    for rel_path in (requested_thumbnail_path, left_path):
                        if rel_path:
                            copied = copy_preview(
                                source_root,
                                rel_path,
                                preview_dir(root, MODULE_TYPE_ANIMATOR),
                                project_root=root,
                                module_name="animator",
                                batch_id=batch_id,
                                context={
                                    "source_json": json_path,
                                    "resource_id": resource.get("resource_id"),
                                    "resource_path": resource_path,
                                },
                            )
                            if rel_path == requested_thumbnail_path:
                                thumbnail_copied = copied
                    if requested_thumbnail_path and not thumbnail_copied:
                        thumbnail_path = None

            asset_batch.append(
                (
                    MODULE_TYPE_ANIMATOR,
                    name,
                    resource_path,
                    thumbnail_path,
                    json.dumps(tags, ensure_ascii=False),
                )
            )
            if root:
                canonical_batch.append(
                    {
                        "module_type": MODULE_TYPE_ANIMATOR,
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
                    "animator",
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
                "animator",
                batch_id,
                "upsert_db",
                exc,
                source_json=json_path,
                resource_id="batch",
            )
    flush_canonical()
    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

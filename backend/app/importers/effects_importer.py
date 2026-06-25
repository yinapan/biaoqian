# backend/app/importers/effects_importer.py
"""Import game effect assets from a JSON manifest + GIF directory.

Data source:
- A JSON file containing a ``resources`` array with SFX metadata,
  AI-generated semantic tags, descriptions, and render results.
- A directory of GIF preview files referenced by relative paths in the JSON.

Each resource is upserted into the ``assets`` table with module_type=2.
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

MODULE_TYPE_EFFECT = 2

# ---------------------------------------------------------------------------
# Chinese tag key → English field_name mapping
# ---------------------------------------------------------------------------

TAG_KEY_MAP = {
    "颜色": "color",
    "形态结构": "form_structure",
    "时间动态": "time_dynamic",
    "元素属性": "element",
    "战斗技能": "combat_skill",
    "场景环境": "scene_env",
    "状态Buff": "status_buff",
    "法阵地面": "magic_circle",
    "UI提示": "ui_hint",
    "业务用途": "biz_usage",
    "角色动作": "char_action",
    "道具物品": "item_prop",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def extract_name_from_path(path: str) -> str:
    """Extract a human-readable name from a resource path.

    Takes the last path segment and strips the file extension.
    E.g. ``"data/source/other/.../d_毒雾01.pss"`` -> ``"d_毒雾01"``.
    """
    filename = path.rsplit("/", 1)[-1] if "/" in path else path
    stem, _, _ext = filename.rpartition(".")
    return stem if stem else filename


def build_effect_tags(resource: dict) -> dict:
    """Build a tags dict from a single resource entry.

    Maps Chinese tag keys from ``result.tags`` to English field names,
    includes the AI description, and keeps useful numeric fields.
    """
    tags: dict = {}
    result = resource.get("result", {})

    # Semantic tags: map Chinese keys to English field_names
    raw_tags = result.get("tags", {})
    for cn_key, en_field in TAG_KEY_MAP.items():
        values = raw_tags.get(cn_key)
        if values:
            tags[en_field] = values if isinstance(values, list) else [values]

    # AI-generated description
    desc = result.get("description")
    if desc:
        tags["description"] = desc

    # Numeric fields
    _NUMERIC_FIELDS = (
        "effect_duration_sec",
        "length_cm", "width_cm", "height_cm",
        "camera_distance", "camera_scale",
        "area_ratio", "span_max",
    )
    for num_field in _NUMERIC_FIELDS:
        val = result.get(num_field)
        if val is not None:
            tags[num_field] = val

    return tags


def _resolve_gif_filename(gif_rel_path: str) -> str | None:
    """Extract the GIF filename from a relative path like 'gifs/xxx.gif'.

    The GIF files are copied into runtime_data/effect/gifs and served from
    the mounted /data/gifs/ volume.
    """
    return normalize_rel_path(gif_rel_path, ("gifs",))


# ---------------------------------------------------------------------------
# Main import routine
# ---------------------------------------------------------------------------


async def import_effects_json(
    json_path: str,
    gifs_source_dir: str,
    pool: asyncpg.Pool,
    previews_dir: str,
    *,
    project_root: str | None = None,
) -> dict:
    """Parse an effects JSON manifest and upsert rows into the *assets* table.

    Parameters
    ----------
    json_path:
        Path to the ``effect_gif_results.json`` file.
    gifs_source_dir:
        Directory containing the GIF files (parent of the ``gifs/`` folder
        referenced by ``gif_rel_path`` in the JSON).
    pool:
        asyncpg connection pool.
    previews_dir:
        Target directory for preview assets (unused for effects, kept for
        API compatibility).

    Returns
    -------
    dict
        Summary with ``batch_id``, ``success``, ``skipped``, ``failed``,
        ``es_sync_failed``, and ``errors`` keys.
    """
    batch_id = str(uuid.uuid4())[:8]
    root = Path(project_root).resolve() if project_root else None
    source_root = Path(gifs_source_dir).resolve()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0}
    errors: list[dict] = []
    canonical_batch: list[dict] = []
    asset_batch: list[tuple] = []
    has_existing_assets = await module_has_assets(pool, MODULE_TYPE_EFFECT)

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

            # Skip non-ok resources
            if result.get("status") != "ok":
                stats["skipped"] += 1
                continue

            resource_path = resource["resource_id"]
            name = extract_name_from_path(resource_path)
            tags = attach_resource_version(build_effect_tags(resource), resource)

            # Resolve GIF filename (files are already in the mounted volume)
            gif_rel_path = result.get("gif_rel_path")
            requested_thumbnail_path = _resolve_gif_filename(gif_rel_path)
            thumbnail_path = requested_thumbnail_path

            if root and requested_thumbnail_path:
                existing_asset = None
                if has_existing_assets:
                    existing_asset = await fetch_existing_asset(
                        pool,
                        MODULE_TYPE_EFFECT,
                        resource_path,
                    )
                can_reuse_preview = (
                    existing_asset
                    and existing_asset.get("thumbnail_path") == requested_thumbnail_path
                    and existing_version_matches(existing_asset.get("tags"), resource)
                    and preview_exists(root, MODULE_TYPE_EFFECT, requested_thumbnail_path)
                )
                if not can_reuse_preview:
                    if not copy_preview(
                        source_root,
                        requested_thumbnail_path,
                        preview_dir(root, MODULE_TYPE_EFFECT),
                        project_root=root,
                        module_name="effect",
                        batch_id=batch_id,
                        context={
                            "source_json": json_path,
                            "resource_id": resource.get("resource_id"),
                            "resource_path": resource_path,
                        },
                    ):
                        thumbnail_path = None
                    grid_path = requested_thumbnail_path.replace(".gif", "_grid.gif")
                    if (source_root / grid_path).exists():
                        copy_preview(
                            source_root,
                            grid_path,
                            preview_dir(root, MODULE_TYPE_EFFECT),
                            project_root=root,
                            module_name="effect",
                            batch_id=batch_id,
                            context={
                                "source_json": json_path,
                                "resource_id": resource.get("resource_id"),
                                "resource_path": resource_path,
                            },
                        )

            asset_batch.append(
                (
                    MODULE_TYPE_EFFECT,
                    name,
                    resource_path,
                    thumbnail_path,
                    json.dumps(tags, ensure_ascii=False),
                )
            )
            if root:
                canonical_batch.append(
                    {
                        "module_type": MODULE_TYPE_EFFECT,
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
                    "effect",
                    batch_id,
                    "upsert_db",
                    e,
                    source_json=json_path,
                    resource_id=resource.get("resource_id"),
                    resource_path=resource.get("resource_id"),
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
                "effect",
                batch_id,
                "upsert_db",
                e,
                source_json=json_path,
                resource_id="batch",
            )
    flush_canonical()
    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

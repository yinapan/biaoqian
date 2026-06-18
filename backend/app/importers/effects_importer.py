# backend/app/importers/effects_importer.py
"""Import game effect assets from a JSON manifest + GIF directory.

Data source:
- A JSON file containing a ``resources`` array with SFX metadata,
  AI-generated semantic tags, descriptions, and render results.
- A directory of GIF preview files referenced by relative paths in the JSON.

Each resource is upserted into the ``assets`` table with module_type=2
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

    The GIF files are served directly from the mounted /data/gifs/ volume,
    so no copying is needed — just return the filename.
    """
    if not gif_rel_path:
        return None
    return Path(gif_rel_path).name


# ---------------------------------------------------------------------------
# Main import routine
# ---------------------------------------------------------------------------


async def import_effects_json(
    json_path: str,
    gifs_source_dir: str,
    pool: asyncpg.Pool,
    previews_dir: str,
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

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resources = data.get("resources", [])

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0}
    errors: list[dict] = []
    es_batch: list[dict] = []

    for idx, resource in enumerate(resources):
        try:
            result = resource.get("result", {})

            # Skip non-ok resources
            if result.get("status") != "ok":
                stats["skipped"] += 1
                continue

            resource_path = resource["resource_id"]
            name = extract_name_from_path(resource_path)
            tags = build_effect_tags(resource)

            # Resolve GIF filename (files are already in the mounted volume)
            gif_rel_path = result.get("gif_rel_path")
            thumbnail_path = _resolve_gif_filename(gif_rel_path)

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
                    MODULE_TYPE_EFFECT,
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

    # Flush remaining ES batch
    if es_batch:
        resp = await bulk_index(es_batch)
        if resp.get("errors"):
            for item in resp["items"]:
                if "error" in item.get("index", {}):
                    stats["es_sync_failed"] += 1

    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

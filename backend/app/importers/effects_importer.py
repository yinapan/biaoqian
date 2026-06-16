# backend/app/importers/effects_importer.py
"""Import game effect assets from a JSON manifest + GIF directory.

Data source:
- A JSON file containing a ``resources`` array with SFX metadata and
  render results (dimensions, durations, camera params, etc.).
- A directory of GIF preview files referenced by relative paths in the JSON.

Each resource is upserted into the ``assets`` table with module_type=2
and synced to Elasticsearch.
"""
from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path

import asyncpg

from app.services.es_sync_service import build_es_doc, bulk_index

logger = logging.getLogger(__name__)

MODULE_TYPE_EFFECT = 2

# Result fields that are internal / not useful as searchable tags.
_RESULT_EXCLUDE_KEYS = frozenset({
    "status",
    "run_id",
    "gif_rel_path",
    "gif_grid_rel_path",
})


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def extract_name_from_resource_id(resource_id: str) -> str:
    """Extract a human-readable name from the resource_id path.

    Takes the last path segment and strips the file extension.
    E.g. ``"data/source/other/.../d_毒雾01.sfx"`` -> ``"d_毒雾01"``.
    """
    filename = resource_id.rsplit("/", 1)[-1] if "/" in resource_id else resource_id
    stem, _, _ext = filename.rpartition(".")
    return stem if stem else filename


def build_effect_tags(resource: dict) -> dict:
    """Build a tags dict from a single resource entry.

    Includes:
    - ``source_name``: extracted from resource_id
    - ``size_bytes``: from the top-level field
    - All meaningful fields from ``result`` (numeric, boolean, string)
      excluding internal/path fields.
    """
    tags: dict = {}
    tags["source_name"] = extract_name_from_resource_id(resource["resource_id"])
    tags["size_bytes"] = resource.get("size_bytes")

    result = resource.get("result", {})
    for key, value in result.items():
        if key in _RESULT_EXCLUDE_KEYS:
            continue
        if value is None:
            continue
        tags[key] = value

    return tags


def _copy_gif_and_generate_thumbnail(
    gif_rel_path: str,
    gifs_source_dir: str,
    previews_dir: str,
) -> str | None:
    """Copy a GIF to the previews directory and generate a PNG thumbnail.

    Returns the relative thumbnail path (e.g. ``"effects/xxx.png"``)
    or ``None`` if the source GIF does not exist.
    """
    src = Path(gifs_source_dir) / gif_rel_path
    if not src.exists():
        logger.warning("GIF not found, skipping thumbnail: %s", src)
        return None

    effects_dir = Path(previews_dir) / "effects"
    effects_dir.mkdir(parents=True, exist_ok=True)

    gif_filename = Path(gif_rel_path).name
    dst_gif = effects_dir / gif_filename
    shutil.copy2(str(src), str(dst_gif))

    # Generate PNG thumbnail from the first frame
    png_filename = Path(gif_filename).stem + ".png"
    dst_png = effects_dir / png_filename

    try:
        from PIL import Image

        with Image.open(str(dst_gif)) as im:
            # Seek to first frame (default)
            im.seek(0)
            # Convert to RGB (GIFs may have palette mode)
            frame = im.convert("RGBA")
            frame.save(str(dst_png), "PNG")
    except Exception:
        logger.warning("Failed to generate PNG thumbnail for %s", gif_filename, exc_info=True)
        return None

    return f"effects/{png_filename}"


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
        Target directory for preview assets (GIF copies + PNG thumbnails).

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
            name = extract_name_from_resource_id(resource_path)
            tags = build_effect_tags(resource)

            # Generate thumbnail
            gif_rel_path = result.get("gif_rel_path")
            thumbnail_path = None
            if gif_rel_path:
                thumbnail_path = _copy_gif_and_generate_thumbnail(
                    gif_rel_path, gifs_source_dir, previews_dir
                )

            async with pool.acquire() as conn:
                row_result = await conn.fetchrow(
                    """INSERT INTO assets
                           (module_type, name, resource_path, thumbnail_path, tags)
                       VALUES ($1, $2, $3, $4, $5::jsonb)
                       ON CONFLICT (module_type, resource_path)
                       DO UPDATE SET tags = $5::jsonb,
                                     thumbnail_path = $4,
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

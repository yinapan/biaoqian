# backend/app/importers/excel_importer.py
"""Import game asset data from Excel workbooks into PostgreSQL + Elasticsearch.

Supports two sheet types:
- Model sheets (module_type=1): character/NPC model assets
- Action sheets (module_type=3): animation/action module assets

Sheet names matching ``^[PMFA]\\d{0,3}`` are treated as model sheets.
The sheet named "动作模组" is treated as the action sheet.
Known non-data sheets (rules, statistics, etc.) are skipped.
"""
from __future__ import annotations

import json
import os
import re
import uuid
import zipfile

import asyncpg
import openpyxl

from app.importers.wps_image_extractor import extract_wps_images
from app.services.es_sync_service import build_es_doc, bulk_index

# ---------------------------------------------------------------------------
# Column mappings
# ---------------------------------------------------------------------------

COLUMN_MAP = {
    "资源完整路径": "resource_path",
    "截图": "_thumbnail",
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

ACTION_COLUMN_MAP = {
    "体型": "body_type",
    "动作模组": "action_module",
    "备注": "remark",
    "动作ID": "action_id",
    "动作类型": "action_type",
    "动作资源": "resource_path",
    "插槽": "slot_name",
    "插槽路径": "slot_path",
    "特效资源": "effect_path",
    "动作说明": "remark",
}

SKIP_SHEETS = {
    "通用规则",
    "进度统计",
    "需要新增的动作",
    "特效标签",
    "问题模型记录区",
    "WpsReserved_CellImgList",
}

MULTI_VALUE_FIELDS = {
    "region",
    "faction",
    "profession",
    "clothing",
    "features",
    "scene",
    "color",
    "description",
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def classify_sheet(name: str) -> int | None:
    """Return module_type for a sheet name, or ``None`` to skip.

    - Known skip sheets -> None
    - "动作模组" -> 3 (action)
    - Names starting with P/M/F/A followed by optional digits -> 1 (model)
    - Everything else -> None
    """
    if name in SKIP_SHEETS:
        return None
    if name == "动作模组":
        return 3
    if re.match(r"^[PMFA]\d{0,3}", name):
        return 1
    return None


def parse_multi_value(val) -> list[str]:
    """Split a cell value on newlines or `` / `` into a list of strings.

    Returns an empty list for ``None`` or empty strings.
    """
    if not val:
        return []
    s = str(val).strip()
    if not s:
        return []
    if "\n" in s:
        parts = s.split("\n")
    elif " / " in s:
        parts = s.split(" / ")
    else:
        parts = [s]
    return [p.strip() for p in parts if p.strip()]


def normalize_path(path: str) -> str:
    """Normalize a Windows-style resource path to forward slashes."""
    return path.strip().replace("\\", "/").rstrip("\n").strip()


# ---------------------------------------------------------------------------
# Main import routine
# ---------------------------------------------------------------------------


async def import_excel(
    filepath: str,
    pool: asyncpg.Pool,
    previews_dir: str,
) -> dict:
    """Parse an Excel workbook and upsert rows into the *assets* table.

    Returns a summary dict with counts and any error details.
    """
    batch_id = str(uuid.uuid4())[:8]
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    wps_images = extract_wps_images(filepath)

    os.makedirs(previews_dir, exist_ok=True)

    # Pre-open the xlsx as a zip for image extraction
    xlsx_zip = zipfile.ZipFile(filepath)

    stats = {"success": 0, "skipped": 0, "failed": 0, "es_sync_failed": 0, "images_extracted": 0}
    errors: list[dict] = []
    es_batch: list[dict] = []

    for sheet_name in wb.sheetnames:
        module_type = classify_sheet(sheet_name)
        if module_type is None:
            continue

        ws = wb[sheet_name]
        headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
        col_map = ACTION_COLUMN_MAP if module_type == 3 else COLUMN_MAP

        # Some model sheets have a resource path value in col 0 instead of
        # the header "资源完整路径".  Detect and fix.
        if (
            module_type == 1
            and headers
            and headers[0]
            and headers[0] not in col_map
            and ("/" in headers[0] or "\\" in headers[0])
        ):
            headers[0] = "资源完整路径"

        for row_idx, row in enumerate(
            ws.iter_rows(min_row=3, values_only=True), start=3
        ):
            try:
                mapped: dict = {}
                for col_idx, header in enumerate(headers):
                    if not header or header not in col_map:
                        continue
                    field = col_map[header]
                    val = row[col_idx] if col_idx < len(row) else None

                    if field == "_thumbnail":
                        continue

                    if field == "resource_path":
                        mapped["resource_path"] = (
                            normalize_path(str(val)) if val else ""
                        )
                        continue

                    if field == "action_id" and val is not None:
                        try:
                            mapped[field] = int(val)
                        except (ValueError, TypeError):
                            mapped[field] = None
                        continue

                    if field in MULTI_VALUE_FIELDS:
                        mapped[field] = parse_multi_value(val)
                    else:
                        mapped[field] = str(val).strip() if val else ""

                if not mapped.get("resource_path"):
                    stats["skipped"] += 1
                    continue

                resource_path = mapped.pop("resource_path")
                name = (
                    resource_path.rsplit("/", 1)[-1]
                    if "/" in resource_path
                    else resource_path
                )
                tags = {k: v for k, v in mapped.items() if v}
                tags["source_sheet"] = sheet_name

                # Extract thumbnail from WPS embedded images
                thumbnail_path = None
                sheet_images = wps_images.get(sheet_name, {})
                media_path = sheet_images.get(row_idx)
                if media_path:
                    ext = os.path.splitext(media_path)[1] or ".png"
                    thumb_filename = f"{os.path.splitext(name)[0]}{ext}"
                    thumb_full_path = os.path.join(previews_dir, thumb_filename)
                    if not os.path.exists(thumb_full_path):
                        try:
                            img_data = xlsx_zip.read(media_path)
                            with open(thumb_full_path, "wb") as f:
                                f.write(img_data)
                            stats["images_extracted"] += 1
                        except (KeyError, OSError):
                            thumb_filename = None
                    thumbnail_path = thumb_filename

                async with pool.acquire() as conn:
                    row_result = await conn.fetchrow(
                        """INSERT INTO assets (module_type, name, resource_path,
                                              thumbnail_path, tags)
                           VALUES ($1, $2, $3, $4, $5::jsonb)
                           ON CONFLICT (module_type, resource_path)
                           DO UPDATE SET thumbnail_path = COALESCE($4, assets.thumbnail_path),
                                         tags = $5::jsonb, updated_at = NOW()
                           RETURNING id, module_type, name, resource_path,
                                     thumbnail_path, tags, created_at, updated_at""",
                        module_type,
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
                    {"sheet": sheet_name, "row": row_idx, "error": str(e)}
                )

    # Flush remaining ES batch
    if es_batch:
        resp = await bulk_index(es_batch)
        if resp.get("errors"):
            for item in resp["items"]:
                if "error" in item.get("index", {}):
                    stats["es_sync_failed"] += 1

    wb.close()
    xlsx_zip.close()
    return {"batch_id": batch_id, **stats, "errors": errors[:50]}

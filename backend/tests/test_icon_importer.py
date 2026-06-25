"""Tests for the icon importer."""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from app.importers.icon_importer import build_icon_tags, import_icons_json


def test_build_icon_tags_uses_top_level_icon_id():
    resource = {
        "icon_id": 5,
        "source_path": "mui/Resource/icon/System/quest/QuestItem.png",
        "result": {
            "rel_path": "pngs/System/quest/QuestItem.png",
            "width_px": 44.0,
            "height_px": 88.0,
        },
    }

    tags = build_icon_tags(resource)

    assert tags["icon_id"] == 5


def test_build_icon_tags_prefers_top_level_icon_id_over_result_fallback():
    resource = {
        "icon_id": 5,
        "result": {
            "icon_id": 999,
        },
    }

    tags = build_icon_tags(resource)

    assert tags["icon_id"] == 5


class _FakeAcquireCtx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self):
        self.rows = []

    def acquire(self):
        return _FakeAcquireCtx(self)

    async def fetchrow(
        self,
        query,
        module_type,
        name,
        resource_path,
        thumbnail_path,
        tags_json,
    ):
        row = {
            "id": len(self.rows) + 1,
            "module_type": module_type,
            "name": name,
            "resource_path": resource_path,
            "thumbnail_path": thumbnail_path,
            "tags": json.loads(tags_json),
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 1),
        }
        self.rows.append(row)
        return row


@pytest.mark.asyncio
async def test_import_icons_json_defers_es_sync_to_reindex(tmp_path):
    json_path = tmp_path / "icons.json"
    json_path.write_text(
        json.dumps(
            {
                "resources": [
                    {
                        "icon_id": 5,
                        "source_path": "mui/Resource/icon/System/quest/QuestItem.png",
                        "result": {"rel_path": "pngs/System/quest/QuestItem.png"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    pool = _FakePool()

    result = await import_icons_json(str(json_path), pool)

    assert result["success"] == 1
    assert result["failed"] == 0
    assert pool.rows[0]["tags"]["icon_id"] == 5

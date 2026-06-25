"""Tests for model JSON + PNG importer."""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.importers.model_importer import import_models_json


SAMPLE_MODEL_RESOURCE = {
    "resource_id": "data/source/model/P080/P080001b.model",
    "source_path": "data/source/model/P080/P080001b.model",
    "result": {
        "status": "ok",
        "png_rel_path": "pngs/P080001b_HD.png",
    },
    "svn": {
        "last_changed_revision": "123",
        "last_changed_author": "artist",
        "last_changed_date": "2026-06-25 12:00:00",
    },
}


class _FakeAcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


def _make_mock_pool():
    fake_row = {
        "id": 1,
        "module_type": 1,
        "name": "P080001b",
        "resource_path": "data/source/model/P080/P080001b.model",
        "thumbnail_path": "P080001b_HD.png",
        "tags": {},
        "created_at": datetime(2026, 6, 25, 12, 0, 0),
        "updated_at": datetime(2026, 6, 25, 12, 0, 0),
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fake_row)
    pool = MagicMock()
    pool.acquire.return_value = _FakeAcquireCtx(conn)
    return pool, conn


def _make_json_data(resources: list[dict]) -> dict:
    return {"version": 1, "resources": resources}


@pytest.mark.asyncio
async def test_import_models_json_does_not_store_missing_thumbnail(tmp_path):
    json_file = tmp_path / "models.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_MODEL_RESOURCE])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    result = await import_models_json(
        str(json_file),
        str(tmp_path / "pngs"),
        pool,
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    assert conn.fetchrow.call_args.args[4] is None
    assert list((tmp_path / "runtime_data/logs/imports").glob("*_model_errors.jsonl"))


@pytest.mark.asyncio
async def test_import_models_json_skips_preview_copy_when_svn_unchanged(tmp_path):
    json_file = tmp_path / "models.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_MODEL_RESOURCE])), encoding="utf-8")
    existing_preview = tmp_path / "runtime_data/model/previews/P080001b_HD.png"
    existing_preview.parent.mkdir(parents=True)
    existing_preview.write_bytes(b"old")

    pool, conn = _make_mock_pool()
    conn.fetchrow.side_effect = [
        {
            "thumbnail_path": "P080001b_HD.png",
            "tags": {"__svn": SAMPLE_MODEL_RESOURCE["svn"]},
        },
        {
            "id": 1,
            "module_type": 1,
            "name": "P080001b",
            "resource_path": "data/source/model/P080/P080001b.model",
            "thumbnail_path": "P080001b_HD.png",
            "tags": {},
            "created_at": datetime(2026, 6, 25, 12, 0, 0),
            "updated_at": datetime(2026, 6, 25, 12, 0, 0),
        },
    ]

    result = await import_models_json(
        str(json_file),
        str(tmp_path / "pngs"),
        pool,
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    assert existing_preview.read_bytes() == b"old"
    assert conn.fetchrow.call_args.args[4] == "P080001b_HD.png"
    assert not list((tmp_path / "runtime_data/logs/imports").glob("*_model_errors.jsonl"))

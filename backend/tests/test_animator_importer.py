"""Tests for animator JSON + GIF importer."""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.importers.animator_importer import (
    build_animator_tags,
    ensure_animator_tag_definitions,
    extract_name_from_path,
    import_animator_json,
    resolve_animator_gif_path,
)


SAMPLE_ANIMATOR_RESOURCE = {
    "resource_id": "data/source/player/m1/actions/run.ani",
    "source_path": "data/source/player/M1/actions/run.ani",
    "size_bytes": 12345,
    "svn": {
        "last_changed_revision": "1867279",
        "last_changed_author": "artist",
        "last_changed_date": "2026-06-17 16:10:42",
    },
    "result": {
        "gif_rel_path_front": "gifs/data/source/player/M1/actions/run.ani_front.gif",
        "gif_rel_path_left": "gifs/data/source/player/M1/actions/run.ani_left.gif",
        "tags": {
            "资源类型": ["player"],
            "体型": ["m1"],
            "动作类型": ["非战斗动作"],
            "特殊系统": [],
            "门派": ["万花"],
            "武器类型": ["长柄武器"],
            "通用动作分类": ["通用"],
            "骑乘类型": [],
            "轻功类型": [],
            "核心动作": ["跑步"],
            "文件类型": ["ani"],
            "AI分析的标签": ["移动"],
        },
        "description": "run animation",
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
        "module_type": 3,
        "name": "run",
        "resource_path": "data/source/player/M1/actions/run.ani",
        "thumbnail_path": "data/source/player/M1/actions/run.ani_front.gif",
        "tags": {},
        "created_at": datetime(2026, 6, 25, 12, 0, 0),
        "updated_at": datetime(2026, 6, 25, 12, 0, 0),
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fake_row)
    conn.fetchval = AsyncMock(return_value=1)
    conn.executemany = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value = _FakeAcquireCtx(conn)
    return pool, conn


def _make_json_data(resources: list[dict]) -> dict:
    return {"version": 1, "resources": resources}


def test_extract_name_from_animator_path():
    assert extract_name_from_path("data/source/player/M1/actions/run.ani") == "run"


def test_resolve_animator_gif_path_strips_gifs_prefix():
    assert (
        resolve_animator_gif_path("gifs/data/source/player/M1/actions/run.ani_front.gif")
        == "data/source/player/M1/actions/run.ani_front.gif"
    )


def test_build_animator_tags_maps_json_tags_and_left_preview():
    tags = build_animator_tags(SAMPLE_ANIMATOR_RESOURCE)

    assert tags["resource_type"] == ["player"]
    assert tags["body_type"] == ["m1"]
    assert tags["action_type"] == ["非战斗动作"]
    assert tags["school"] == ["万花"]
    assert tags["weapon_type"] == ["长柄武器"]
    assert tags["common_action"] == ["通用"]
    assert tags["core_action"] == ["跑步"]
    assert tags["file_type"] == ["ani"]
    assert tags["ai_tags"] == ["移动"]
    assert tags["description"] == "run animation"
    assert tags["gif_left_path"] == "data/source/player/M1/actions/run.ani_left.gif"


@pytest.mark.asyncio
async def test_import_animator_json_upserts_module_3_and_copies_front_gif(tmp_path):
    json_file = tmp_path / "animator.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_ANIMATOR_RESOURCE])), encoding="utf-8")
    gifs_root = tmp_path / "gifs"
    front = gifs_root / "data/source/player/M1/actions/run.ani_front.gif"
    left = gifs_root / "data/source/player/M1/actions/run.ani_left.gif"
    front.parent.mkdir(parents=True)
    front.write_bytes(b"front")
    left.write_bytes(b"left")

    pool, conn = _make_mock_pool()
    result = await import_animator_json(
        str(json_file),
        str(gifs_root),
        pool,
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    row = conn.executemany.call_args.args[1][0]
    assert row[0] == 3
    assert row[1] == "run"
    assert row[3] == "data/source/player/M1/actions/run.ani_front.gif"
    tags = json.loads(row[4])
    assert tags["gif_left_path"] == "data/source/player/M1/actions/run.ani_left.gif"
    assert (
        tmp_path
        / "runtime_data/animator/previews/data/source/player/M1/actions/run.ani_front.gif"
    ).read_bytes() == b"front"
    assert (
        tmp_path
        / "runtime_data/animator/previews/data/source/player/M1/actions/run.ani_left.gif"
    ).read_bytes() == b"left"


@pytest.mark.asyncio
async def test_import_animator_json_does_not_store_missing_thumbnail(tmp_path):
    json_file = tmp_path / "animator.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_ANIMATOR_RESOURCE])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    result = await import_animator_json(
        str(json_file),
        str(tmp_path / "gifs"),
        pool,
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    assert conn.executemany.call_args.args[1][0][3] is None
    assert list((tmp_path / "runtime_data/logs/imports").glob("*_animator_errors.jsonl"))


@pytest.mark.asyncio
async def test_import_animator_json_skips_preview_copy_when_svn_unchanged(tmp_path):
    json_file = tmp_path / "animator.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_ANIMATOR_RESOURCE])), encoding="utf-8")
    existing_front = (
        tmp_path / "runtime_data/animator/previews/data/source/player/M1/actions/run.ani_front.gif"
    )
    existing_left = (
        tmp_path / "runtime_data/animator/previews/data/source/player/M1/actions/run.ani_left.gif"
    )
    existing_front.parent.mkdir(parents=True)
    existing_front.write_bytes(b"front-old")
    existing_left.write_bytes(b"left-old")

    pool, conn = _make_mock_pool()
    conn.fetchrow.side_effect = [
        {
            "thumbnail_path": "data/source/player/M1/actions/run.ani_front.gif",
            "tags": {"__svn": SAMPLE_ANIMATOR_RESOURCE["svn"]},
        },
        {
            "id": 1,
            "module_type": 3,
            "name": "run",
            "resource_path": "data/source/player/M1/actions/run.ani",
            "thumbnail_path": "data/source/player/M1/actions/run.ani_front.gif",
            "tags": {},
            "created_at": datetime(2026, 6, 25, 12, 0, 0),
            "updated_at": datetime(2026, 6, 25, 12, 0, 0),
        },
    ]

    result = await import_animator_json(
        str(json_file),
        str(tmp_path / "gifs"),
        pool,
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    assert existing_front.read_bytes() == b"front-old"
    assert existing_left.read_bytes() == b"left-old"
    assert conn.executemany.call_args.args[1][0][3] == "data/source/player/M1/actions/run.ani_front.gif"
    assert not list((tmp_path / "runtime_data/logs/imports").glob("*_animator_errors.jsonl"))


@pytest.mark.asyncio
async def test_import_animator_json_skips_existing_lookup_for_empty_module(tmp_path):
    json_file = tmp_path / "animator.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_ANIMATOR_RESOURCE])), encoding="utf-8")
    front = tmp_path / "runtime_data/animator/previews/data/source/player/M1/actions/run.ani_front.gif"
    left = tmp_path / "runtime_data/animator/previews/data/source/player/M1/actions/run.ani_left.gif"
    front.parent.mkdir(parents=True)
    front.write_bytes(b"front")
    left.write_bytes(b"left")

    pool, conn = _make_mock_pool()
    conn.fetchval.return_value = 0

    result = await import_animator_json(
        str(json_file),
        str(tmp_path / "gifs"),
        pool,
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    conn.fetchrow.assert_not_called()
    assert conn.executemany.call_count == 2


@pytest.mark.asyncio
async def test_import_animator_json_batches_asset_upserts(tmp_path):
    resources = []
    gifs_root = tmp_path / "gifs"
    for index in range(1001):
        resource = json.loads(json.dumps(SAMPLE_ANIMATOR_RESOURCE))
        resource["source_path"] = f"data/source/player/M1/actions/run_{index}.ani"
        resource["resource_id"] = resource["source_path"]
        resource["result"]["gif_rel_path_front"] = (
            f"gifs/data/source/player/M1/actions/run_{index}.ani_front.gif"
        )
        resource["result"]["gif_rel_path_left"] = (
            f"gifs/data/source/player/M1/actions/run_{index}.ani_left.gif"
        )
        resources.append(resource)
        front = gifs_root / f"data/source/player/M1/actions/run_{index}.ani_front.gif"
        left = gifs_root / f"data/source/player/M1/actions/run_{index}.ani_left.gif"
        front.parent.mkdir(parents=True, exist_ok=True)
        front.write_bytes(b"front")
        left.write_bytes(b"left")
    json_file = tmp_path / "animator.json"
    json_file.write_text(json.dumps(_make_json_data(resources)), encoding="utf-8")

    pool, conn = _make_mock_pool()
    conn.fetchval.return_value = 0

    result = await import_animator_json(
        str(json_file),
        str(gifs_root),
        pool,
        project_root=str(tmp_path),
    )

    assert result["success"] == 1001
    batch_sizes = [
        len(call.args[1])
        for call in conn.executemany.call_args_list
        if "INSERT INTO assets" in call.args[0]
    ]
    assert batch_sizes == [1000, 1]


@pytest.mark.asyncio
async def test_ensure_animator_tag_definitions_inserts_json_fields():
    pool, conn = _make_mock_pool()

    await ensure_animator_tag_definitions(pool)

    conn.executemany.assert_awaited_once()
    rows = conn.executemany.call_args.args[1]
    field_names = {row[0] for row in rows}
    assert "resource_type" in field_names
    assert "weapon_type" in field_names
    assert "core_action" in field_names
    assert "gif_left_path" in field_names
    by_field = {row[0]: row for row in rows}
    assert by_field["size_bytes"][4] is False

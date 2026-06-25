# backend/tests/test_effects_importer.py
"""Tests for the effects importer (JSON+GIF format)."""
from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.importers.effects_importer import (
    extract_name_from_path,
    build_effect_tags,
    _resolve_gif_filename,
    import_effects_json,
)

# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

SAMPLE_RESOURCE_OK = {
    "resource_id": "data/source/other/hd特效/ui_m/pss/achievement/ui_云雾.pss",
    "source_path": "data/source/other/HD特效/UI_M/Pss/Achievement/UI_云雾.pss",
    "size_bytes": 18938,
    "svn": {
        "last_changed_revision": "1395973",
        "last_changed_author": "xuanweiqin",
        "last_changed_date": "2024-05-10 15:30:25",
    },
    "result": {
        "gif_rel_path": "gifs/001_UI______94a9f160_angle45.gif",
        "gif_grid_rel_path": "gifs/001_UI______94a9f160_angle45_grid.gif",
        "status": "ok",
        "run_id": "effect_gif_run_dir_20260616",
        "length_cm": 2100.0,
        "width_cm": 1000.0,
        "height_cm": 1000.0,
        "effect_duration_sec": 0.0,
        "gif_duration_sec": 2.0,
        "camera_distance": 2211.92,
        "camera_scale": 0.575,
        "focus_offset": 0.26,
        "area_ratio": 0.195,
        "span_max": 0.428,
        "center_x": 0.5,
        "center_y": 0.521,
        "clipped": False,
        "fit_attempts": 10,
        "fit_stop_reason": "best_effort",
        "tags": {
            "颜色": ["白", "青"],
            "形态结构": ["点状", "扩散"],
            "时间动态": ["循环", "长持续"],
            "元素属性": ["光系"],
            "场景环境": ["场景氛围"],
            "范围大小": ["小范围"],
        },
        "description": "GIF展示了白色光点在灰色背景中缓慢飘动扩散的效果。",
    },
}

SAMPLE_RESOURCE_FAILED = {
    "resource_id": "data/source/other/hd特效/bad/broken.pss",
    "source_path": "data/source/other/HD特效/Bad/Broken.pss",
    "size_bytes": 500,
    "svn": {
        "last_changed_revision": "100000",
        "last_changed_author": "someone",
        "last_changed_date": "2020-01-01 00:00:00",
    },
    "result": {
        "status": "error",
        "error_message": "render failed",
    },
}


def _make_json_data(resources: list[dict]) -> dict:
    return {
        "version": 1,
        "generated_at": "2026-06-17 14:09:18",
        "meta": {"run_id": "effect_gif_run_dir_20260616"},
        "resources": resources,
    }


# ---------------------------------------------------------------------------
# extract_name_from_path
# ---------------------------------------------------------------------------


class TestExtractName:
    def test_normal_pss_path(self):
        path = "data/source/other/hd特效/ui_m/pss/achievement/ui_云雾.pss"
        assert extract_name_from_path(path) == "ui_云雾"

    def test_single_segment(self):
        assert extract_name_from_path("file.pss") == "file"

    def test_no_extension(self):
        assert extract_name_from_path("data/source/foo") == "foo"

    def test_multiple_dots(self):
        assert extract_name_from_path("data/some.thing/foo.bar.pss") == "foo.bar"


# ---------------------------------------------------------------------------
# _resolve_gif_filename
# ---------------------------------------------------------------------------


class TestResolveGifFilename:
    def test_normal_path(self):
        assert _resolve_gif_filename("gifs/001_test.gif") == "001_test.gif"

    def test_none_input(self):
        assert _resolve_gif_filename(None) is None

    def test_empty_string(self):
        assert _resolve_gif_filename("") is None


# ---------------------------------------------------------------------------
# build_effect_tags
# ---------------------------------------------------------------------------


class TestBuildEffectTags:
    def test_semantic_tags_mapped(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert tags["color"] == ["白", "青"]
        assert tags["form_structure"] == ["点状", "扩散"]
        assert tags["time_dynamic"] == ["循环", "长持续"]
        assert tags["element"] == ["光系"]
        assert tags["scene_env"] == ["场景氛围"]

    def test_description_included(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert "GIF展示了" in tags["description"]

    def test_numeric_fields_included(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert tags["effect_duration_sec"] == 0.0
        assert tags["length_cm"] == 2100.0
        assert tags["width_cm"] == 1000.0
        assert tags["height_cm"] == 1000.0
        assert tags["camera_distance"] == 2211.92
        assert tags["camera_scale"] == 0.575
        assert tags["area_ratio"] == 0.195
        assert tags["span_max"] == 0.428

    def test_excludes_internal_fields(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert "status" not in tags
        assert "run_id" not in tags
        assert "gif_rel_path" not in tags
        assert "gif_grid_rel_path" not in tags
        assert "gif_duration_sec" not in tags

    def test_missing_tags_graceful(self):
        resource = {
            "resource_id": "test.pss",
            "result": {"status": "ok", "effect_duration_sec": 1.0},
        }
        tags = build_effect_tags(resource)
        assert tags["effect_duration_sec"] == 1.0
        assert "color" not in tags


# ---------------------------------------------------------------------------
# import_effects_json — integration with mocks
# ---------------------------------------------------------------------------


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
        "module_type": 2,
        "name": "ui_云雾",
        "resource_path": "data/source/other/hd特效/ui_m/pss/achievement/ui_云雾.pss",
        "thumbnail_path": "001_UI______94a9f160_angle45.gif",
        "tags": {"color": ["白", "青"], "effect_duration_sec": 0.0},
        "created_at": datetime(2026, 6, 17, 12, 0, 0),
        "updated_at": datetime(2026, 6, 17, 12, 0, 0),
    }
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fake_row)
    pool = MagicMock()
    pool.acquire.return_value = _FakeAcquireCtx(conn)
    return pool, conn


@pytest.mark.asyncio
async def test_import_skips_non_ok(tmp_path):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_RESOURCE_FAILED])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    result = await import_effects_json(str(json_file), str(tmp_path), pool, str(tmp_path))

    assert result["success"] == 0
    assert result["skipped"] == 1
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_import_ok_resource(tmp_path):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_RESOURCE_OK])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    result = await import_effects_json(str(json_file), str(tmp_path), pool, str(tmp_path))

    assert result["success"] == 1
    assert result["failed"] == 0
    conn.fetchrow.assert_called_once()
    call_args = conn.fetchrow.call_args
    assert call_args[0][1] == 2  # module_type
    assert call_args[0][2] == "ui_云雾"  # name
    # Check tags contain semantic fields
    tags = json.loads(call_args[0][5])
    assert tags["color"] == ["白", "青"]
    assert tags["effect_duration_sec"] == 0.0
    assert "description" in tags


@pytest.mark.asyncio
async def test_import_thumbnail_is_gif_filename(tmp_path):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_RESOURCE_OK])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    await import_effects_json(str(json_file), str(tmp_path), pool, str(tmp_path))

    # $4 = thumbnail_path should be the GIF filename
    thumb = conn.fetchrow.call_args[0][4]
    assert thumb == "001_UI______94a9f160_angle45.gif"


@pytest.mark.asyncio
async def test_import_effects_json_does_not_store_missing_thumbnail(tmp_path):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_RESOURCE_OK])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    result = await import_effects_json(
        str(json_file),
        str(tmp_path / "gifs"),
        pool,
        str(tmp_path),
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    assert conn.fetchrow.call_args.args[4] is None
    assert list((tmp_path / "runtime_data/logs/imports").glob("*_effect_errors.jsonl"))


@pytest.mark.asyncio
async def test_import_effects_json_skips_preview_copy_when_svn_unchanged(tmp_path):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_RESOURCE_OK])), encoding="utf-8")
    existing_preview = tmp_path / "runtime_data/effect/gifs/001_UI______94a9f160_angle45.gif"
    existing_preview.parent.mkdir(parents=True)
    existing_preview.write_bytes(b"old")

    pool, conn = _make_mock_pool()
    conn.fetchrow.side_effect = [
        {
            "thumbnail_path": "001_UI______94a9f160_angle45.gif",
            "tags": {"__svn": SAMPLE_RESOURCE_OK["svn"]},
        },
        {
            "id": 1,
            "module_type": 2,
            "name": "ui_浜戦浘",
            "resource_path": SAMPLE_RESOURCE_OK["resource_id"],
            "thumbnail_path": "001_UI______94a9f160_angle45.gif",
            "tags": {},
            "created_at": datetime(2026, 6, 25, 12, 0, 0),
            "updated_at": datetime(2026, 6, 25, 12, 0, 0),
        },
    ]

    result = await import_effects_json(
        str(json_file),
        str(tmp_path / "gifs"),
        pool,
        str(tmp_path),
        project_root=str(tmp_path),
    )

    assert result["success"] == 1
    assert existing_preview.read_bytes() == b"old"
    assert conn.fetchrow.call_args.args[4] == "001_UI______94a9f160_angle45.gif"
    assert not list((tmp_path / "runtime_data/logs/imports").glob("*_effect_errors.jsonl"))


@pytest.mark.asyncio
async def test_import_mixed_resources(tmp_path):
    json_file = tmp_path / "effects.json"
    data = _make_json_data([SAMPLE_RESOURCE_OK, SAMPLE_RESOURCE_FAILED, SAMPLE_RESOURCE_OK])
    json_file.write_text(json.dumps(data), encoding="utf-8")

    pool, conn = _make_mock_pool()
    result = await import_effects_json(str(json_file), str(tmp_path), pool, str(tmp_path))

    assert result["success"] == 2
    assert result["skipped"] == 1


@pytest.mark.asyncio
async def test_import_empty_resources(tmp_path):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(_make_json_data([])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    result = await import_effects_json(str(json_file), str(tmp_path), pool, str(tmp_path))

    assert result["success"] == 0
    assert result["skipped"] == 0
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_import_db_error_counted(tmp_path):
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(_make_json_data([SAMPLE_RESOURCE_OK])), encoding="utf-8")

    pool, conn = _make_mock_pool()
    conn.fetchrow.side_effect = Exception("DB down")
    result = await import_effects_json(str(json_file), str(tmp_path), pool, str(tmp_path))

    assert result["failed"] == 1
    assert result["success"] == 0

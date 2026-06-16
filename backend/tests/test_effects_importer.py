# backend/tests/test_effects_importer.py
"""Tests for the effects importer (JSON+GIF format)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.importers.effects_importer import (
    extract_name_from_resource_id,
    build_effect_tags,
    import_effects_json,
)

# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

SAMPLE_RESOURCE_OK = {
    "resource_id": "data/source/other/特效/场景/sfx/云雾/d_毒雾01.sfx",
    "source_path": "data/source/other/特效/场景/SFX/云雾/D_毒雾01.Sfx",
    "size_bytes": 1524,
    "svn": {
        "last_changed_revision": "189555",
        "last_changed_author": "kuangyongxiong",
        "last_changed_date": "2013-04-26 11:48:40",
    },
    "result": {
        "gif_rel_path": "gifs/001_D_____01_d5e77d48_angle45.gif",
        "gif_grid_rel_path": "gifs/001_D_____01_d5e77d48_angle45_grid.gif",
        "status": "ok",
        "run_id": "dir_20260616_173357",
        "length_cm": 3500.0,
        "width_cm": 3500.0,
        "height_cm": 200.0,
        "effect_duration_sec": 5.05,
        "gif_duration_sec": 5.042,
        "camera_distance": 9272.8,
        "camera_scale": 1.606,
        "focus_offset": -0.08,
        "area_ratio": 0.273,
        "span_max": 0.774,
        "center_x": 0.496,
        "center_y": 0.503,
        "clipped": False,
        "fit_attempts": 10,
        "fit_stop_reason": "best_effort",
    },
}

SAMPLE_RESOURCE_FAILED = {
    "resource_id": "data/source/other/特效/bad/d_broken.sfx",
    "source_path": "data/source/other/特效/bad/D_broken.Sfx",
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
        "generated_at": "2026-06-16 20:30:53",
        "meta": {"run_id": "dir_20260616_173357"},
        "resources": resources,
    }


# ---------------------------------------------------------------------------
# extract_name_from_resource_id
# ---------------------------------------------------------------------------


class TestExtractName:
    def test_normal_sfx_path(self):
        rid = "data/source/other/特效/场景/sfx/云雾/d_毒雾01.sfx"
        assert extract_name_from_resource_id(rid) == "d_毒雾01"

    def test_single_segment(self):
        assert extract_name_from_resource_id("file.sfx") == "file"

    def test_no_extension(self):
        assert extract_name_from_resource_id("data/source/foo") == "foo"

    def test_multiple_dots(self):
        rid = "data/some.thing/foo.bar.sfx"
        # Should remove only the last extension
        assert extract_name_from_resource_id(rid) == "foo.bar"


# ---------------------------------------------------------------------------
# build_effect_tags
# ---------------------------------------------------------------------------


class TestBuildEffectTags:
    def test_basic_fields_present(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert tags["source_name"] == "d_毒雾01"
        assert tags["size_bytes"] == 1524
        assert tags["effect_duration_sec"] == 5.05
        assert tags["length_cm"] == 3500.0
        assert tags["width_cm"] == 3500.0
        assert tags["height_cm"] == 200.0

    def test_result_numeric_fields_included(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert tags["gif_duration_sec"] == 5.042
        assert tags["camera_distance"] == 9272.8
        assert tags["camera_scale"] == 1.606
        assert tags["focus_offset"] == -0.08
        assert tags["area_ratio"] == 0.273
        assert tags["span_max"] == 0.774
        assert tags["center_x"] == 0.496
        assert tags["center_y"] == 0.503

    def test_excludes_internal_fields(self):
        """Fields like status, run_id, gif paths are not useful as search tags."""
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert "status" not in tags
        assert "run_id" not in tags
        assert "gif_rel_path" not in tags
        assert "gif_grid_rel_path" not in tags

    def test_boolean_fields_included(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert tags["clipped"] is False

    def test_integer_fields_included(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert tags["fit_attempts"] == 10

    def test_string_fields_included(self):
        tags = build_effect_tags(SAMPLE_RESOURCE_OK)
        assert tags["fit_stop_reason"] == "best_effort"


# ---------------------------------------------------------------------------
# import_effects_json — integration with mocks
# ---------------------------------------------------------------------------


class _FakeAcquireCtx:
    """Minimal async context manager that mimics ``pool.acquire()``."""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


def _make_mock_pool():
    """Create a mock asyncpg pool with connection context manager."""
    fake_row = {
        "id": uuid.uuid4(),
        "module_type": 2,
        "name": "d_毒雾01",
        "resource_path": "data/source/other/特效/场景/sfx/云雾/d_毒雾01.sfx",
        "thumbnail_path": "effects/001_D_____01_d5e77d48_angle45.png",
        "tags": {"source_name": "d_毒雾01", "effect_duration_sec": 5.05},
        "version": None,
        "file_size": None,
        "created_at": datetime(2026, 6, 16, 12, 0, 0),
        "updated_at": datetime(2026, 6, 16, 12, 0, 0),
    }

    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=fake_row)
    conn.execute = AsyncMock()

    pool = MagicMock()
    pool.acquire.return_value = _FakeAcquireCtx(conn)
    return pool, conn


@pytest.mark.asyncio
async def test_import_skips_non_ok_status(tmp_path):
    """Resources with status != 'ok' should be skipped."""
    json_data = _make_json_data([SAMPLE_RESOURCE_FAILED])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk:
        mock_bulk.return_value = {"errors": False, "items": []}
        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["success"] == 0
    assert result["skipped"] == 1
    conn.fetchrow.assert_not_called()


@pytest.mark.asyncio
async def test_import_ok_resource_upserts(tmp_path):
    """A resource with status='ok' should be upserted into DB and queued for ES."""
    json_data = _make_json_data([SAMPLE_RESOURCE_OK])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    # Create a minimal fake GIF
    gifs_dir = tmp_path / "gifs"
    gifs_dir.mkdir()
    gif_path = gifs_dir / "001_D_____01_d5e77d48_angle45.gif"
    gif_path.write_bytes(b"GIF89a")  # Minimal GIF header

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer.build_es_doc") as mock_build_es,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        mock_build_es.return_value = {"id": "test"}
        mock_thumb.return_value = "effects/001_D_____01_d5e77d48_angle45.png"

        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["success"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0
    assert "batch_id" in result

    # Check UPSERT was called
    conn.fetchrow.assert_called_once()
    call_args = conn.fetchrow.call_args
    # module_type should be 2
    assert call_args[0][1] == 2
    # name
    assert call_args[0][2] == "d_毒雾01"
    # resource_path
    assert call_args[0][3] == "data/source/other/特效/场景/sfx/云雾/d_毒雾01.sfx"


@pytest.mark.asyncio
async def test_import_updates_thumbnail_path_in_upsert(tmp_path):
    """UPSERT SQL should include thumbnail_path."""
    json_data = _make_json_data([SAMPLE_RESOURCE_OK])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    thumb_rel = "effects/001_D_____01_d5e77d48_angle45.png"

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer.build_es_doc") as mock_build_es,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        mock_build_es.return_value = {"id": "test"}
        mock_thumb.return_value = thumb_rel

        await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    call_args = conn.fetchrow.call_args
    sql = call_args[0][0]
    assert "thumbnail_path" in sql


@pytest.mark.asyncio
async def test_import_mixed_resources(tmp_path):
    """Mix of ok and failed resources: only ok ones are processed."""
    json_data = _make_json_data([
        SAMPLE_RESOURCE_OK,
        SAMPLE_RESOURCE_FAILED,
        SAMPLE_RESOURCE_OK,
    ])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer.build_es_doc") as mock_build_es,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        mock_build_es.return_value = {"id": "test"}
        mock_thumb.return_value = "effects/test.png"

        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["success"] == 2
    assert result["skipped"] == 1
    assert conn.fetchrow.call_count == 2


@pytest.mark.asyncio
async def test_import_es_batch_flush(tmp_path):
    """When batch size >= 500, ES bulk_index should be called mid-import."""
    # Create 501 ok resources
    resources = []
    for i in range(501):
        r = {
            "resource_id": f"data/source/other/特效/test/d_test{i:04d}.sfx",
            "source_path": f"data/source/other/特效/test/D_test{i:04d}.Sfx",
            "size_bytes": 1000 + i,
            "svn": {
                "last_changed_revision": "100",
                "last_changed_author": "test",
                "last_changed_date": "2026-01-01 00:00:00",
            },
            "result": {
                "gif_rel_path": f"gifs/test_{i:04d}.gif",
                "gif_grid_rel_path": f"gifs/test_{i:04d}_grid.gif",
                "status": "ok",
                "run_id": "test_run",
                "length_cm": 100.0,
                "width_cm": 100.0,
                "height_cm": 100.0,
                "effect_duration_sec": 1.0,
                "gif_duration_sec": 1.0,
                "camera_distance": 500.0,
                "camera_scale": 1.0,
                "focus_offset": 0.0,
                "area_ratio": 0.5,
                "span_max": 0.5,
                "center_x": 0.5,
                "center_y": 0.5,
                "clipped": False,
                "fit_attempts": 1,
                "fit_stop_reason": "converged",
            },
        }
        resources.append(r)

    json_data = _make_json_data(resources)
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer.build_es_doc") as mock_build_es,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        mock_build_es.return_value = {"id": "test"}
        mock_thumb.return_value = "effects/test.png"

        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["success"] == 501
    # Should have flushed at 500 + final flush of 1 = 2 calls
    assert mock_bulk.call_count == 2


@pytest.mark.asyncio
async def test_import_es_sync_error_tracking(tmp_path):
    """ES sync errors should be counted in stats."""
    json_data = _make_json_data([SAMPLE_RESOURCE_OK])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer.build_es_doc") as mock_build_es,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {
            "errors": True,
            "items": [{"index": {"error": "mapping error"}}],
        }
        mock_build_es.return_value = {"id": "test"}
        mock_thumb.return_value = "effects/test.png"

        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["es_sync_failed"] == 1
    assert result["success"] == 1


@pytest.mark.asyncio
async def test_import_db_error_counted_as_failed(tmp_path):
    """Database errors should increment the failed counter."""
    json_data = _make_json_data([SAMPLE_RESOURCE_OK])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    conn.fetchrow.side_effect = Exception("DB connection lost")
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        mock_thumb.return_value = "effects/test.png"

        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["failed"] == 1
    assert result["success"] == 0
    assert len(result["errors"]) == 1


@pytest.mark.asyncio
async def test_import_thumbnail_failure_does_not_block(tmp_path):
    """If thumbnail generation fails, the resource is still imported (no thumbnail)."""
    json_data = _make_json_data([SAMPLE_RESOURCE_OK])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer.build_es_doc") as mock_build_es,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        mock_build_es.return_value = {"id": "test"}
        mock_thumb.return_value = None  # Thumbnail generation failed

        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["success"] == 1
    # Fetchrow should still be called — thumbnail_path will be None
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_import_tags_contain_all_numeric_result_fields(tmp_path):
    """Tags JSON should contain all meaningful result fields."""
    json_data = _make_json_data([SAMPLE_RESOURCE_OK])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with (
        patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.effects_importer.build_es_doc") as mock_build_es,
        patch("app.importers.effects_importer._copy_gif_and_generate_thumbnail") as mock_thumb,
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        mock_build_es.return_value = {"id": "test"}
        mock_thumb.return_value = "effects/test.png"

        await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    call_args = conn.fetchrow.call_args
    tags_json_str = call_args[0][5]  # $5 is the tags jsonb parameter
    tags = json.loads(tags_json_str)

    # Core tag fields
    assert tags["source_name"] == "d_毒雾01"
    assert tags["size_bytes"] == 1524
    assert tags["effect_duration_sec"] == 5.05
    assert tags["length_cm"] == 3500.0
    assert tags["width_cm"] == 3500.0
    assert tags["height_cm"] == 200.0
    # Extended result fields
    assert tags["gif_duration_sec"] == 5.042
    assert tags["camera_distance"] == 9272.8
    assert tags["fit_stop_reason"] == "best_effort"
    assert tags["clipped"] is False


@pytest.mark.asyncio
async def test_import_empty_resources(tmp_path):
    """Empty resources array should return zeroed stats."""
    json_data = _make_json_data([])
    json_file = tmp_path / "effects.json"
    json_file.write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    pool, conn = _make_mock_pool()
    previews_dir = tmp_path / "previews"
    previews_dir.mkdir()

    with patch("app.importers.effects_importer.bulk_index", new_callable=AsyncMock) as mock_bulk:
        mock_bulk.return_value = {"errors": False, "items": []}
        result = await import_effects_json(
            str(json_file), str(tmp_path), pool, str(previews_dir)
        )

    assert result["success"] == 0
    assert result["skipped"] == 0
    assert result["failed"] == 0
    conn.fetchrow.assert_not_called()

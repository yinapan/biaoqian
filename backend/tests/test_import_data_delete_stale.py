"""Tests for stale asset deletion in the host import script."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("import_data", ROOT / "scripts" / "import_data.py")
import_data = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(import_data)


class _FakeAcquireCtx:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, paths: list[str]):
        self.paths = paths
        self.deleted_paths: list[str] = []

    async def fetch(self, query, module_type, keep_paths):
        return [
            {"id": index + 1, "resource_path": path, "thumbnail_path": f"{index}.png"}
            for index, path in enumerate(self.paths)
            if path not in set(keep_paths)
        ]

    async def execute(self, query, ids):
        self.deleted_paths = [
            path for index, path in enumerate(self.paths) if index + 1 in set(ids)
        ]
        return f"DELETE {len(self.deleted_paths)}"


class _FakePool:
    def __init__(self, paths: list[str]):
        self.conn = _FakeConn(paths)

    def acquire(self):
        return _FakeAcquireCtx(self.conn)


class _ResetConn:
    def __init__(self):
        self.executed: list[str] = []

    async def execute(self, query):
        self.executed.append(" ".join(query.split()))
        return "OK"


class _ResetPool:
    def __init__(self):
        self.conn = _ResetConn()

    def acquire(self):
        return _FakeAcquireCtx(self.conn)


def _write_json(path: Path, resources: list[dict]) -> Path:
    path.write_text(json.dumps({"resources": resources}), encoding="utf-8")
    return path


def test_manifest_resource_paths_match_importable_model_resources(tmp_path):
    json_path = _write_json(
        tmp_path / "models.json",
        [
            {"source_path": "keep.model", "result": {"status": "ok"}},
            {"resource_id": "skip.model", "result": {"status": "error: broken"}},
            {"resource_id": "fallback.model", "result": {}},
        ],
    )

    assert import_data.manifest_resource_paths(json_path, 1) == {
        "keep.model",
        "fallback.model",
    }


def test_manifest_resource_paths_match_importable_effect_resources(tmp_path):
    json_path = _write_json(
        tmp_path / "effects.json",
        [
            {"resource_id": "keep.pss", "result": {"status": "ok"}},
            {"resource_id": "skip.pss", "result": {"status": "error"}},
        ],
    )

    assert import_data.manifest_resource_paths(json_path, 2) == {"keep.pss"}


@pytest.mark.asyncio
async def test_delete_stale_assets_dry_run_does_not_delete(tmp_path):
    json_path = _write_json(
        tmp_path / "icons.json",
        [{"source_path": "keep.png", "result": {}}],
    )
    pool = _FakePool(["keep.png", "old.png"])

    result = await import_data.delete_stale_assets_for_manifest(
        pool,
        4,
        json_path,
        apply=False,
    )

    assert result["stale"] == 1
    assert result["deleted"] == 0
    assert result["samples"] == ["old.png"]
    assert pool.conn.deleted_paths == []


@pytest.mark.asyncio
async def test_delete_stale_assets_apply_deletes_only_missing_paths(tmp_path):
    json_path = _write_json(
        tmp_path / "animator.json",
        [{"source_path": "keep.ani", "result": {}}],
    )
    pool = _FakePool(["keep.ani", "old.ani"])

    result = await import_data.delete_stale_assets_for_manifest(
        pool,
        3,
        json_path,
        apply=True,
    )

    assert result["stale"] == 1
    assert result["deleted"] == 1
    assert pool.conn.deleted_paths == ["old.ani"]


@pytest.mark.asyncio
async def test_reset_import_data_clears_only_rebuildable_tables():
    pool = _ResetPool()

    result = await import_data.reset_import_data(pool)

    assert result == {"assets": "cleared", "tag_values": "cleared", "import_errors": "cleared"}
    assert pool.conn.executed == [
        "DELETE FROM user_favorites",
        "DELETE FROM assets",
        "DELETE FROM tag_values",
        "DELETE FROM import_errors",
        "ALTER SEQUENCE assets_id_seq RESTART WITH 1",
    ]

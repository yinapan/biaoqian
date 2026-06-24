from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openpyxl import Workbook

from app.importers.excel_importer import (
    parse_multi_value, normalize_path, classify_sheet, COLUMN_MAP,
    import_excel, _dedupe_asset_batch,
)


def test_parse_multi_value_newline():
    assert parse_multi_value("中原\n东海\n西南") == ["中原", "东海", "西南"]


def test_parse_multi_value_slash():
    assert parse_multi_value("中原 / 东海") == ["中原", "东海"]


def test_parse_multi_value_single():
    assert parse_multi_value("人") == ["人"]


def test_parse_multi_value_empty():
    assert parse_multi_value("") == []
    assert parse_multi_value(None) == []


def test_normalize_path():
    assert normalize_path("data\\source\\NPC_source\\P080\\模型\\P080.mdl") == \
           "data/source/NPC_source/P080/模型/P080.mdl"


def test_classify_sheet_model():
    assert classify_sheet("P080【完成】") == 1
    assert classify_sheet("M1【完成】") == 1
    assert classify_sheet("F2【完成】") == 1
    assert classify_sheet("A") == 1


def test_classify_sheet_action():
    assert classify_sheet("动作模组") == 3


def test_classify_sheet_skip():
    assert classify_sheet("通用规则") is None
    assert classify_sheet("进度统计") is None
    assert classify_sheet("WpsReserved_CellImgList") is None


class _FakeAcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


def _make_mock_pool():
    conn = AsyncMock()
    conn.fetch = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value = _FakeAcquireCtx(conn)
    return pool, conn


def _create_excel(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "P080【完成】"
    ws.append(["资源完整路径", "物种", "性别", "地域"])
    ws.append(["example row", None, None, None])
    for row in rows:
        ws.append(row)
    wb.save(path)


def test_dedupe_asset_batch_keeps_last_duplicate_resource_path():
    rows = [
        (1, "old.mdl", "data/source/dup.mdl", None, '{"species":"old"}'),
        (1, "unique.mdl", "data/source/unique.mdl", None, '{"species":"unique"}'),
        (1, "new.mdl", "data/source/dup.mdl", "new.png", '{"species":"new"}'),
    ]

    deduped = _dedupe_asset_batch(rows)

    assert deduped == [
        (1, "unique.mdl", "data/source/unique.mdl", None, '{"species":"unique"}'),
        (1, "new.mdl", "data/source/dup.mdl", "new.png", '{"species":"new"}'),
    ]


@pytest.mark.asyncio
async def test_import_excel_uses_batch_upsert_and_prints_progress(tmp_path, capsys):
    excel_file = tmp_path / "assets.xlsx"
    _create_excel(
        excel_file,
        [
            ["data/source/NPC/P080001.mdl", "人", "女", "中原"],
            ["data/source/NPC/P080002.mdl", "妖", "男", "东海"],
        ],
    )

    pool, conn = _make_mock_pool()
    fake_rows = [
        {
            "id": 1,
            "module_type": 1,
            "name": "P080001.mdl",
            "resource_path": "data/source/NPC/P080001.mdl",
            "thumbnail_path": None,
            "tags": {"species": "人"},
            "created_at": datetime(2026, 6, 24, 12, 0, 0),
            "updated_at": datetime(2026, 6, 24, 12, 0, 0),
        },
        {
            "id": 2,
            "module_type": 1,
            "name": "P080002.mdl",
            "resource_path": "data/source/NPC/P080002.mdl",
            "thumbnail_path": None,
            "tags": {"species": "妖"},
            "created_at": datetime(2026, 6, 24, 12, 0, 0),
            "updated_at": datetime(2026, 6, 24, 12, 0, 0),
        },
    ]
    conn.fetch.return_value = fake_rows

    with (
        patch("app.importers.excel_importer.extract_wps_images", return_value={}),
        patch("app.importers.excel_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
        patch("app.importers.excel_importer.build_es_doc", side_effect=lambda row: row),
    ):
        mock_bulk.return_value = {"errors": False, "items": []}
        result = await import_excel(
            str(excel_file),
            pool,
            str(tmp_path),
            batch_size=2,
            progress_interval=1,
        )

    assert result["success"] == 2
    assert result["failed"] == 0
    conn.fetch.assert_called_once()
    conn.fetchrow.assert_not_called()
    mock_bulk.assert_awaited_once()
    output = capsys.readouterr().out
    assert "Excel progress:" in output
    assert "success=2" in output


@pytest.mark.asyncio
async def test_import_excel_can_skip_realtime_es_sync(tmp_path):
    excel_file = tmp_path / "assets.xlsx"
    _create_excel(
        excel_file,
        [["data/source/NPC/P080001.mdl", "人", "女", "中原"]],
    )

    pool, conn = _make_mock_pool()
    conn.fetch.return_value = [
        {
            "id": 1,
            "module_type": 1,
            "name": "P080001.mdl",
            "resource_path": "data/source/NPC/P080001.mdl",
            "thumbnail_path": None,
            "tags": {"species": "人"},
            "created_at": datetime(2026, 6, 24, 12, 0, 0),
            "updated_at": datetime(2026, 6, 24, 12, 0, 0),
        }
    ]

    with (
        patch("app.importers.excel_importer.extract_wps_images", return_value={}),
        patch("app.importers.excel_importer.bulk_index", new_callable=AsyncMock) as mock_bulk,
    ):
        result = await import_excel(
            str(excel_file),
            pool,
            str(tmp_path),
            batch_size=1,
            progress_interval=1,
            sync_es=False,
        )

    assert result["success"] == 1
    mock_bulk.assert_not_called()

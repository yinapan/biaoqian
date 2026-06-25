from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zipfile import ZipFile

import pytest
from openpyxl import Workbook

from app.importers.excel_importer import (
    ACTION_COLUMN_MAP,
    ACTION_SHEETS,
    COLUMN_MAP,
    MODEL_SHEETS,
    _dedupe_asset_batch,
    classify_sheet,
    import_excel,
    normalize_path,
    parse_multi_value,
)


def _header(mapping: dict[str, str], field_name: str) -> str:
    return next(key for key, value in mapping.items() if value == field_name)


MODEL_RESOURCE_HEADER = _header(COLUMN_MAP, "resource_path")
MODEL_THUMB_HEADER = _header(COLUMN_MAP, "_thumbnail")
MODEL_SPECIES_HEADER = _header(COLUMN_MAP, "species")
MODEL_GENDER_HEADER = _header(COLUMN_MAP, "gender")
MODEL_REGION_HEADER = _header(COLUMN_MAP, "region")
ACTION_RESOURCE_HEADER = _header(ACTION_COLUMN_MAP, "resource_path")
ACTION_BODY_HEADER = _header(ACTION_COLUMN_MAP, "body_type")
ACTION_ID_HEADER = _header(ACTION_COLUMN_MAP, "action_id")


def test_parse_multi_value_newline():
    assert parse_multi_value("alpha\nbeta\ngamma") == ["alpha", "beta", "gamma"]


def test_parse_multi_value_slash():
    assert parse_multi_value("alpha / beta") == ["alpha", "beta"]


def test_parse_multi_value_single():
    assert parse_multi_value("alpha") == ["alpha"]


def test_parse_multi_value_empty():
    assert parse_multi_value("") == []
    assert parse_multi_value(None) == []


def test_normalize_path():
    assert normalize_path("data\\source\\NPC_source\\P080\\model\\P080.mdl") == (
        "data/source/NPC_source/P080/model/P080.mdl"
    )


def test_classify_sheet_model():
    assert classify_sheet(next(iter(MODEL_SHEETS))) == 1


def test_classify_sheet_action():
    assert classify_sheet(next(iter(ACTION_SHEETS))) == 3


def test_classify_sheet_skip():
    assert classify_sheet("WpsReserved_CellImgList") is None
    assert classify_sheet("not-a-data-sheet") is None


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


def _create_model_excel(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = next(iter(MODEL_SHEETS))
    ws.append(
        [
            MODEL_RESOURCE_HEADER,
            MODEL_THUMB_HEADER,
            MODEL_SPECIES_HEADER,
            MODEL_GENDER_HEADER,
            MODEL_REGION_HEADER,
        ]
    )
    ws.append(["example row", None, None, None, None])
    for row in rows:
        ws.append(row)
    wb.save(path)


def _create_action_excel(path, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = next(iter(ACTION_SHEETS))
    ws.append([ACTION_RESOURCE_HEADER, ACTION_BODY_HEADER, ACTION_ID_HEADER])
    ws.append(["example row", None, None])
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
    _create_model_excel(
        excel_file,
        [
            ["data/source/NPC/P080001.mdl", None, "human", "female", "central"],
            ["data/source/NPC/P080002.mdl", None, "elf", "male", "east"],
        ],
    )

    pool, conn = _make_mock_pool()
    conn.fetch.return_value = [
        {
            "id": 1,
            "module_type": 1,
            "name": "P080001.mdl",
            "resource_path": "data/source/NPC/P080001.mdl",
            "thumbnail_path": None,
            "tags": {"species": "human"},
            "created_at": datetime(2026, 6, 24, 12, 0, 0),
            "updated_at": datetime(2026, 6, 24, 12, 0, 0),
        },
        {
            "id": 2,
            "module_type": 1,
            "name": "P080002.mdl",
            "resource_path": "data/source/NPC/P080002.mdl",
            "thumbnail_path": None,
            "tags": {"species": "elf"},
            "created_at": datetime(2026, 6, 24, 12, 0, 0),
            "updated_at": datetime(2026, 6, 24, 12, 0, 0),
        },
    ]

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
    _create_model_excel(
        excel_file,
        [["data/source/NPC/P080001.mdl", None, "human", "female", "central"]],
    )

    pool, conn = _make_mock_pool()
    conn.fetch.return_value = [
        {
            "id": 1,
            "module_type": 1,
            "name": "P080001.mdl",
            "resource_path": "data/source/NPC/P080001.mdl",
            "thumbnail_path": None,
            "tags": {"species": "human"},
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


@pytest.mark.asyncio
async def test_import_excel_stores_model_previews_under_model_prefix(tmp_path):
    excel_file = tmp_path / "assets.xlsx"
    _create_model_excel(
        excel_file,
        [["data/source/NPC/P080001.mdl", None, "human", "female", "central"]],
    )

    pool, conn = _make_mock_pool()
    conn.fetch.return_value = []

    with ZipFile(excel_file, "a") as zf:
        zf.writestr("xl/media/image1.png", b"model-preview")

    with patch(
        "app.importers.excel_importer.extract_wps_images",
        return_value={next(iter(MODEL_SHEETS)): {3: "xl/media/image1.png"}},
    ):
        await import_excel(str(excel_file), pool, str(tmp_path), sync_es=False)

    thumbnail_paths = conn.fetch.call_args.args[4]
    assert thumbnail_paths == ["model/P080001.png"]
    assert (tmp_path / "model" / "previews" / "P080001.png").read_bytes() == b"model-preview"


@pytest.mark.asyncio
async def test_import_excel_stores_action_previews_under_animator_prefix(tmp_path):
    excel_file = tmp_path / "actions.xlsx"
    _create_action_excel(excel_file, [["data/source/Action/run.anim", "M2", 101]])

    pool, conn = _make_mock_pool()
    conn.fetch.return_value = []

    with ZipFile(excel_file, "a") as zf:
        zf.writestr("xl/media/image1.png", b"animator-preview")

    with patch(
        "app.importers.excel_importer.extract_wps_images",
        return_value={next(iter(ACTION_SHEETS)): {3: "xl/media/image1.png"}},
    ):
        await import_excel(str(excel_file), pool, str(tmp_path), sync_es=False)

    thumbnail_paths = conn.fetch.call_args.args[4]
    assert thumbnail_paths == ["animator/run.png"]
    assert (tmp_path / "animator" / "previews" / "run.png").read_bytes() == b"animator-preview"

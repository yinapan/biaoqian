from app.importers.excel_importer import (
    parse_multi_value, normalize_path, classify_sheet, COLUMN_MAP,
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

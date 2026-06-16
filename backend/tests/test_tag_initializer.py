# backend/tests/test_tag_initializer.py
from app.importers.tag_initializer import COLUMN_MAP, SKIP_SHEETS


def test_column_map_covers_all_model_fields():
    expected = {"species", "gender", "region", "faction", "profession",
                "body_type", "age_group", "clothing", "features", "exclusive_npc"}
    assert set(COLUMN_MAP.values()) == expected


def test_skip_sheets():
    assert "通用规则" in SKIP_SHEETS
    assert "动作模组" in SKIP_SHEETS
    assert "P080【完成】" not in SKIP_SHEETS

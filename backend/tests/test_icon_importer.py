"""Tests for the icon importer."""
from __future__ import annotations

from app.importers.icon_importer import build_icon_tags


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

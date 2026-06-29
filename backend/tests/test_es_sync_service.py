from datetime import datetime

from app.services.es_sync_service import build_es_doc, extract_resource_search_terms


def test_extract_resource_search_terms_from_filename_without_extension():
    terms = extract_resource_search_terms(
        "data/source/player/M1/动作/M1b04ty_标女&正太_第一段.ani"
    )

    assert terms["resource_name"] == "M1b04ty_标女&正太_第一段"
    assert terms["resource_name_tokens"] == [
        "M1b04ty",
        "标女",
        "正太",
        "第一段",
    ]
    assert terms["resource_path_text"] == "data source player M1 动作 M1b04ty 标女 正太 第一段 ani"


def test_build_es_doc_indexes_resource_name_but_does_not_pollute_tags():
    row = {
        "id": 1,
        "module_type": 3,
        "name": "M1b04ty_标女&正太_第一段",
        "resource_path": "data/source/player/M1/动作/M1b04ty_标女&正太_第一段.ani",
        "thumbnail_path": "data/source/player/M1/动作/M1b04ty_标女&正太_第一段.ani_front.gif",
        "tags": {"action_type": ["非战斗动作"]},
        "version": None,
        "file_size": None,
        "created_at": datetime(2026, 6, 29, 12, 0, 0),
        "updated_at": datetime(2026, 6, 29, 12, 0, 0),
    }

    doc = build_es_doc(row)

    assert doc["resource_name"] == "M1b04ty_标女&正太_第一段"
    assert "正太" in doc["resource_name_tokens"]
    assert "M1b04ty_标女&正太_第一段" in doc["search_text"]
    assert "正太" in doc["search_text"]
    assert "resource_name" not in doc["tags"]
    assert "resource_name_tokens" not in doc["tags"]

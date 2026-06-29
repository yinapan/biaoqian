from app.services.es_mapping import build_index_settings_and_mappings, generate_tag_properties


def test_generate_tag_properties_enum():
    definitions = [
        {"field_name": "gender", "field_type": "enum_single"},
        {"field_name": "region", "field_type": "enum_multi"},
    ]
    props = generate_tag_properties(definitions)
    assert props["tags.gender"] == {"type": "keyword"}
    assert props["tags.region"] == {"type": "keyword"}


def test_generate_tag_properties_number():
    definitions = [{"field_name": "duration", "field_type": "number_range"}]
    props = generate_tag_properties(definitions)
    assert props["tags.duration"] == {"type": "float"}


def test_generate_tag_properties_boolean():
    definitions = [{"field_name": "loop", "field_type": "boolean"}]
    props = generate_tag_properties(definitions)
    assert props["tags.loop"] == {"type": "boolean"}


def test_generate_tag_properties_text():
    definitions = [{"field_name": "remark", "field_type": "text"}]
    props = generate_tag_properties(definitions)
    assert props["tags.remark"]["type"] == "keyword"


def test_mapping_indexes_resource_name_without_making_it_a_tag():
    body = build_index_settings_and_mappings([])
    props = body["mappings"]["properties"]

    assert props["resource_name"]["type"] == "text"
    assert props["resource_name"]["fields"]["keyword"]["type"] == "keyword"
    assert props["resource_name_tokens"]["type"] == "keyword"
    assert props["resource_path_text"]["type"] == "text"
    assert props["resource_path_text"]["fields"]["keyword"]["type"] == "keyword"
    assert "tags.resource_name" not in props

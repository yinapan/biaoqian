from app.services.es_mapping import generate_tag_properties


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

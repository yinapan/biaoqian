from app.services.parse_validator import validate_llm_result


def test_validate_valid_enum():
    valid_values = {"gender": {"男", "女"}, "body_type": {"标准", "壮硕"}}
    result = {
        "filter": {"gender": "女", "body_type": "标准"},
        "keyword": "",
        "confidence": 0.9,
    }
    validated = validate_llm_result(result, valid_values)
    assert validated["filter"]["gender"] == "女"
    assert validated["demoted_to_keyword"] == []


def test_validate_invalid_enum_demotes():
    valid_values = {"gender": {"男", "女"}}
    result = {"filter": {"gender": "外星人"}, "keyword": "", "confidence": 0.8}
    validated = validate_llm_result(result, valid_values)
    assert "gender" not in validated["filter"]
    assert "外星人" in validated["keyword"]


def test_validate_number_condition():
    valid_values = {}
    result = {
        "filter": {"duration": {"op": ">", "value": 5}},
        "keyword": "",
        "confidence": 0.9,
    }
    validated = validate_llm_result(result, valid_values, number_fields={"duration"})
    assert validated["filter"]["duration"] == {"op": ">", "value": 5}


def test_validate_unknown_dimension():
    valid_values = {"gender": {"男", "女"}}
    result = {"filter": {"nonexistent": "abc"}, "keyword": "test", "confidence": 0.5}
    validated = validate_llm_result(result, valid_values)
    assert "nonexistent" not in validated["filter"]
    assert "abc" in validated["keyword"]


def test_validate_list_values_partial_valid():
    """When a list has both valid and invalid values, keep valid ones and demote invalid."""
    valid_values = {"region": {"中原", "西域", "东海"}}
    result = {
        "filter": {"region": ["中原", "火星", "东海"]},
        "keyword": "",
        "confidence": 0.7,
    }
    validated = validate_llm_result(result, valid_values)
    assert validated["filter"]["region"] == ["中原", "东海"]
    assert "火星" in validated["demoted_to_keyword"]
    assert "火星" in validated["keyword"]


def test_validate_boolean_field():
    """Boolean fields are coerced to bool."""
    valid_values = {}
    result = {
        "filter": {"is_loop": 1},
        "keyword": "",
        "confidence": 0.9,
    }
    validated = validate_llm_result(
        result, valid_values, boolean_fields={"is_loop"}
    )
    assert validated["filter"]["is_loop"] is True


def test_validate_number_bad_value_demotes():
    """A number field with a non-numeric value should be demoted."""
    valid_values = {}
    result = {
        "filter": {"duration": {"op": ">", "value": "abc"}},
        "keyword": "",
        "confidence": 0.9,
    }
    validated = validate_llm_result(result, valid_values, number_fields={"duration"})
    assert "duration" not in validated["filter"]


def test_validate_number_bad_op_skips():
    """A number field with an invalid operator should be silently skipped."""
    valid_values = {}
    result = {
        "filter": {"duration": {"op": "LIKE", "value": 5}},
        "keyword": "",
        "confidence": 0.9,
    }
    validated = validate_llm_result(result, valid_values, number_fields={"duration"})
    assert "duration" not in validated["filter"]


def test_validate_preserves_confidence():
    valid_values = {}
    result = {"filter": {}, "keyword": "hello", "confidence": 0.42}
    validated = validate_llm_result(result, valid_values)
    assert validated["confidence"] == 0.42


def test_validate_empty_result():
    valid_values = {"gender": {"男", "女"}}
    result = {"filter": {}, "keyword": "", "confidence": 0.0}
    validated = validate_llm_result(result, valid_values)
    assert validated["filter"] == {}
    assert validated["keyword"] == ""
    assert validated["demoted_to_keyword"] == []

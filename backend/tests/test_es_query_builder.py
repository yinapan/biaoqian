from app.services.es_query_builder import build_search_query


def test_filter_only():
    q = build_search_query(
        module_type=1,
        filters={"gender": "女", "profession": ["刺客"]},
        page=1,
        page_size=20,
        filterable_fields=["gender", "profession"],
    )
    bool_filter = q["query"]["function_score"]["query"]["bool"]["filter"]
    assert {"term": {"module_type": "1"}} in bool_filter
    assert {"term": {"tags.gender": "女"}} in bool_filter
    assert {"terms": {"tags.profession": ["刺客"]}} in bool_filter


def test_keyword_search():
    q = build_search_query(
        module_type=1,
        keyword="红衣",
        page=1,
        page_size=20,
    )
    must = q["query"]["function_score"]["query"]["bool"]["must"]
    keyword_should = must[0]["bool"]["should"]
    assert any("match" in clause and "search_text" in clause["match"] for clause in keyword_should)


def test_keyword_search_covers_resource_name_and_path_fields():
    q = build_search_query(module_type=2, keyword="h_蝴蝶01a", page=1, page_size=20)

    must = q["query"]["function_score"]["query"]["bool"]["must"]
    keyword_clause = must[0]
    should_fields = keyword_clause["bool"]["should"]

    assert {"match": {"search_text": {"query": "h_蝴蝶01a", "analyzer": "ik_smart", "boost": 3}}} in should_fields
    assert {"match": {"resource_name": {"query": "h_蝴蝶01a", "analyzer": "ik_smart", "boost": 5}}} in should_fields
    assert {"term": {"resource_name.keyword": {"value": "h_蝴蝶01a", "boost": 20}}} in should_fields
    assert {"term": {"resource_name_tokens": {"value": "h_蝴蝶01a", "boost": 12}}} in should_fields
    assert {"match": {"resource_path_text": {"query": "h_蝴蝶01a", "analyzer": "ik_smart", "boost": 2}}} in should_fields


def test_parsed_filters_from_query_are_soft_when_keyword_exists():
    q = build_search_query(
        module_type=2,
        filters={"scene_env": ["蝴蝶"]},
        keyword="蝴蝶",
        parsed_filter_fields={"scene_env"},
        agg_fields=["scene_env"],
        page=1,
        page_size=20,
    )

    bool_query = q["query"]["function_score"]["query"]["bool"]
    assert {"term": {"module_type": "2"}} in bool_query["filter"]
    assert {"terms": {"tags.scene_env": ["蝴蝶"]}} not in bool_query["filter"]
    assert {"terms": {"tags.scene_env": ["蝴蝶"]}} in bool_query["should"]
    assert bool_query["minimum_should_match"] == 1


def test_range_condition():
    q = build_search_query(
        module_type=2,
        conditions=[{"field": "duration", "op": ">", "value": 5}],
        page=1,
        page_size=20,
    )
    bool_filter = q["query"]["function_score"]["query"]["bool"]["filter"]
    assert any("range" in f for f in bool_filter)


def test_pagination():
    q = build_search_query(module_type=1, page=3, page_size=20)
    assert q["from"] == 40
    assert q["size"] == 20


def test_query_tracks_exact_total_hits():
    q = build_search_query(module_type=3, page=1, page_size=60)
    assert q["track_total_hits"] is True


def test_dynamic_function_score():
    q = build_search_query(
        module_type=1,
        filters={"gender": "女", "profession": ["刺客"]},
        page=1,
        page_size=20,
        filterable_fields=["gender", "profession"],
    )
    functions = q["query"]["function_score"]["functions"]
    filter_funcs = [f for f in functions if "filter" in f]
    # 2 filter boosts (gender, profession) + 1 thumbnail_path exists boost
    assert len(filter_funcs) == 3


def test_aggregation_size_can_cover_large_enum_fields():
    q = build_search_query(
        module_type=4,
        page=1,
        page_size=20,
        agg_fields=["predefined", "color", "semantic"],
        agg_sizes={"predefined": 500, "color": 500, "semantic": 10838},
    )

    assert q["aggs"]["predefined"]["terms"]["size"] == 500
    assert q["aggs"]["color"]["terms"]["size"] == 500
    assert q["aggs"]["semantic"]["terms"]["size"] == 10838

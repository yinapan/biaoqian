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
    assert any("match" in clause for clause in must)


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

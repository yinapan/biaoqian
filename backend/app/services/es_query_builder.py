from app.config import settings

OP_MAP = {">": "gt", "<": "lt", ">=": "gte", "<=": "lte", "==": "gte"}


def _build_filter_clause(field: str, value, text_fields: set, number_fields: set | None = None) -> dict:
    number_fields = number_fields or set()
    if isinstance(value, list) and field in number_fields and len(value) == 2:
        return {"range": {f"tags.{field}": {"gte": value[0], "lte": value[1]}}}
    elif isinstance(value, list):
        return {"terms": {f"tags.{field}": value}}
    elif isinstance(value, dict) and "op" in value:
        es_op = OP_MAP.get(value["op"], "gte")
        range_q: dict = {f"tags.{field}": {es_op: value["value"]}}
        if value["op"] == "==":
            range_q[f"tags.{field}"]["lte"] = value["value"]
        return {"range": range_q}
    elif isinstance(value, str) and field in text_fields:
        return {"wildcard": {f"tags.{field}": {"value": f"*{value}*"}}}
    else:
        return {"term": {f"tags.{field}": value}}


def build_search_query(
    module_type: int,
    filters: dict | None = None,
    excludes: dict | None = None,
    keyword: str = "",
    keyword_excludes: list[str] | None = None,
    conditions: list[dict] | None = None,
    sort: dict | None = None,
    page: int = 1,
    page_size: int = 20,
    filterable_fields: list[str] | None = None,
    agg_fields: list[str] | None = None,
    agg_sizes: dict[str, int] | None = None,
    text_fields: set[str] | None = None,
    number_fields: set[str] | None = None,
) -> dict:
    filters = filters or {}
    excludes = excludes or {}
    conditions = conditions or []
    keyword_excludes = keyword_excludes or []
    filterable_fields = filterable_fields or []
    agg_fields = agg_fields or []
    agg_sizes = agg_sizes or {}
    text_fields = text_fields or set()
    number_fields = number_fields or set()
    agg_fields_set = set(agg_fields)

    base_filters: list[dict] = [{"term": {"module_type": str(module_type)}}]
    must_not_clauses: list[dict] = []
    facet_clauses: dict[str, dict] = {}
    bool_must: list[dict] = []

    # --- filters: separate facet (enum agg) vs non-facet ---
    for field, value in filters.items():
        clause = _build_filter_clause(field, value, text_fields, number_fields)
        if field in agg_fields_set:
            facet_clauses[field] = clause
        else:
            base_filters.append(clause)

    # --- excludes: build must_not clauses ---
    for field, value in excludes.items():
        if isinstance(value, list):
            must_not_clauses.append({"terms": {f"tags.{field}": value}})
        elif isinstance(value, str) and field in text_fields:
            must_not_clauses.append({"wildcard": {f"tags.{field}": {"value": f"*{value}*"}}})
        else:
            must_not_clauses.append({"term": {f"tags.{field}": value}})

    # --- keyword excludes: must_not against search_text ---
    for kw in keyword_excludes:
        must_not_clauses.append({"match": {"search_text": {"query": kw, "analyzer": "ik_smart"}}})

    # --- conditions (explicit range / comparison rules) ---
    for cond in conditions:
        es_op = OP_MAP.get(cond["op"], "gte")
        range_q = {f"tags.{cond['field']}": {es_op: cond["value"]}}
        if cond["op"] == "==":
            range_q[f"tags.{cond['field']}"]["lte"] = cond["value"]
        base_filters.append({"range": range_q})

    # --- keyword full-text search ---
    has_filters = len(filters) > 0
    if keyword:
        keyword_clause = {
            "match": {
                "search_text": {
                    "query": keyword,
                    "analyzer": "ik_smart",
                }
            }
        }
        if has_filters:
            bool_must.append(keyword_clause)
        else:
            bool_must.append(keyword_clause)

    bool_query: dict = {"filter": base_filters}
    if must_not_clauses:
        bool_query["must_not"] = must_not_clauses
    if bool_must:
        if has_filters and keyword:
            bool_query["should"] = bool_must
            bool_query["minimum_should_match"] = 0
        else:
            bool_query["must"] = bool_must

    # --- function_score: boost matched filters + time decay ---
    score_functions: list[dict] = []
    for field, value in filters.items():
        if isinstance(value, list):
            score_functions.append(
                {
                    "filter": {"terms": {f"tags.{field}": value}},
                    "weight": 10,
                }
            )
        elif not isinstance(value, dict):
            score_functions.append(
                {
                    "filter": {"term": {f"tags.{field}": value}},
                    "weight": 10,
                }
            )
    score_functions.append(
        {"filter": {"exists": {"field": "thumbnail_path"}}, "weight": 1000}
    )
    score_functions.append(
        {
            "linear": {
                "updated_at": {"origin": "now", "scale": "30d", "decay": 0.5}
            }
        }
    )

    query: dict = {
        "query": {
            "function_score": {
                "query": {"bool": bool_query},
                "functions": score_functions,
                "score_mode": "sum",
                "boost_mode": "sum",
            }
        },
        "from": (page - 1) * page_size,
        "size": page_size,
        "highlight": {
            "fields": {
                "search_text": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
                "name": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
            }
        },
    }

    # --- post_filter: facet filters applied to hits only (not aggs) ---
    if facet_clauses:
        query["post_filter"] = {"bool": {"filter": list(facet_clauses.values())}}

    # --- aggregations: each field excludes its own filter ---
    if agg_fields:
        aggs: dict = {}
        for agg_field in agg_fields:
            other_facet = [c for f, c in facet_clauses.items() if f != agg_field]
            size = max(500, min(int(agg_sizes.get(agg_field, 500)), 20000))
            inner = {"terms": {"field": f"tags.{agg_field}", "size": size}}
            if other_facet:
                aggs[agg_field] = {
                    "filter": {"bool": {"filter": other_facet}},
                    "aggs": {"values": inner},
                }
            else:
                aggs[agg_field] = inner
        query["aggs"] = aggs

    return query

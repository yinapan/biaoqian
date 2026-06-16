from app.config import settings

OP_MAP = {">": "gt", "<": "lt", ">=": "gte", "<=": "lte", "==": "gte"}


def build_search_query(
    module_type: int,
    filters: dict | None = None,
    keyword: str = "",
    conditions: list[dict] | None = None,
    sort: dict | None = None,
    page: int = 1,
    page_size: int = 20,
    filterable_fields: list[str] | None = None,
    agg_fields: list[str] | None = None,
) -> dict:
    filters = filters or {}
    conditions = conditions or []
    filterable_fields = filterable_fields or []
    agg_fields = agg_fields or []

    bool_filter: list[dict] = [{"term": {"module_type": str(module_type)}}]
    bool_must: list[dict] = []

    # --- filters (from faceted UI selections) ---
    for field, value in filters.items():
        if isinstance(value, list):
            bool_filter.append({"terms": {f"tags.{field}": value}})
        elif isinstance(value, dict) and "op" in value:
            es_op = OP_MAP.get(value["op"], "gte")
            range_q: dict = {f"tags.{field}": {es_op: value["value"]}}
            if value["op"] == "==":
                range_q[f"tags.{field}"]["lte"] = value["value"]
            bool_filter.append({"range": range_q})
        else:
            bool_filter.append({"term": {f"tags.{field}": value}})

    # --- conditions (explicit range / comparison rules) ---
    for cond in conditions:
        es_op = OP_MAP.get(cond["op"], "gte")
        range_q = {f"tags.{cond['field']}": {es_op: cond["value"]}}
        if cond["op"] == "==":
            range_q[f"tags.{cond['field']}"]["lte"] = cond["value"]
        bool_filter.append({"range": range_q})

    # --- keyword full-text search ---
    if keyword:
        bool_must.append(
            {
                "match": {
                    "search_text": {
                        "query": keyword,
                        "analyzer": "ik_smart",
                    }
                }
            }
        )

    bool_query: dict = {"filter": bool_filter}
    if bool_must:
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

    # --- aggregations for sidebar facet counts ---
    if agg_fields:
        aggs: dict = {}
        for field in agg_fields:
            aggs[field] = {"terms": {"field": f"tags.{field}", "size": 50}}
        query["aggs"] = aggs

    return query

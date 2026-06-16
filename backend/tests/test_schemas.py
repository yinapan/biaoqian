import pytest
from app.models.schemas import SearchRequest, SearchResponse, ParseInfo


def test_search_request_defaults():
    req = SearchRequest(module_type=1)
    assert req.page == 1
    assert req.page_size == 20
    assert req.query is None
    assert req.filters == {}


def test_search_request_page_size_limit():
    with pytest.raises(Exception):
        SearchRequest(module_type=1, page_size=200)


def test_search_request_offset_limit():
    with pytest.raises(Exception):
        SearchRequest(module_type=1, page=501, page_size=20)


def test_parse_info_structure():
    info = ParseInfo(
        parsed_filters={"gender": "女"},
        effective_filters={"gender": "女"},
        keyword="红衣",
        confidence=0.9,
        fallback=False,
        parse_source="dict",
        parse_time_ms=5,
    )
    assert info.ignored_tags == []

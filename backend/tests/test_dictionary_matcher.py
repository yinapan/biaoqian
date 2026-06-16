"""Tests for DictionaryMatcher — dictionary-based tag matching with synonym support."""

from app.services.dictionary_matcher import DictionaryMatcher, MatchResult


def make_matcher():
    m = DictionaryMatcher()
    m.load_from_data(
        tag_values={
            (1, "gender"): ["男", "女"],
            (1, "profession"): ["刺客", "僧侣", "战士", "书生"],
            (1, "region"): ["中原", "东海", "西南"],
            (1, "faction"): ["少林", "藏剑", "七秀"],
            (1, "body_type"): ["标准", "壮硕", "瘦子"],
        },
        synonyms=[
            {
                "module_type": 1,
                "field_name": "profession",
                "target_value": "僧侣",
                "synonym": "和尚",
                "priority": 10,
            },
            {
                "module_type": 1,
                "field_name": "body_type",
                "target_value": "壮硕",
                "synonym": "壮",
                "priority": 5,
            },
        ],
    )
    return m


def test_full_match():
    m = make_matcher()
    result = m.match(1, "女 刺客 中原")
    assert result.matched == {
        "gender": "女",
        "profession": ["刺客"],
        "region": ["中原"],
    }
    assert result.remaining == ""


def test_partial_match_with_remaining():
    m = make_matcher()
    result = m.match(1, "红衣女刺客 中原")
    assert "gender" in result.matched
    assert "profession" in result.matched
    assert "红衣" in result.remaining


def test_synonym_match():
    m = make_matcher()
    result = m.match(1, "壮老和尚 少林")
    assert result.matched.get("body_type") == "壮硕"
    assert "僧侣" in result.matched.get("profession", [])
    assert result.matched.get("faction") == ["少林"]


def test_prefix_search():
    m = make_matcher()
    suggestions = m.prefix_search(1, "刺")
    assert any(s["text"] == "刺客" for s in suggestions)


def test_match_result_defaults():
    """MatchResult should have sensible defaults."""
    r = MatchResult()
    assert r.matched == {}
    assert r.remaining == ""


def test_unknown_module_type_returns_remaining():
    """Querying a module_type with no loaded data returns everything as remaining."""
    m = make_matcher()
    result = m.match(999, "女 刺客")
    assert result.matched == {}
    assert result.remaining == "女 刺客"


def test_empty_query():
    """Empty query should return empty matched and empty remaining."""
    m = make_matcher()
    result = m.match(1, "")
    assert result.matched == {}
    assert result.remaining == ""


def test_multi_value_fields_always_list():
    """Multi-value fields like profession should always return a list, even for a single value."""
    m = make_matcher()
    result = m.match(1, "刺客")
    assert isinstance(result.matched.get("profession"), list)
    assert result.matched["profession"] == ["刺客"]


def test_single_value_field_returns_string():
    """Single-value fields like gender should return a string, not a list."""
    m = make_matcher()
    result = m.match(1, "女")
    assert result.matched["gender"] == "女"
    assert isinstance(result.matched["gender"], str)


def test_prefix_search_limit():
    """prefix_search should respect the limit parameter."""
    m = DictionaryMatcher()
    m.load_from_data(
        tag_values={
            (1, "profession"): [f"职业{i}" for i in range(20)],
        },
        synonyms=[],
    )
    results = m.prefix_search(1, "职业", limit=5)
    assert len(results) <= 5


def test_prefix_search_no_match():
    """prefix_search with no matching prefix returns empty list."""
    m = make_matcher()
    results = m.prefix_search(1, "不存在的前缀")
    assert results == []


def test_longest_match_priority():
    """Longer token matches should be preferred over shorter ones (greedy longest match)."""
    m = DictionaryMatcher()
    m.load_from_data(
        tag_values={
            (1, "region"): ["中", "中原"],
        },
        synonyms=[],
    )
    result = m.match(1, "中原")
    assert result.matched.get("region") == ["中原"]
    assert result.remaining == ""

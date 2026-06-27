"""Parse orchestration service.

Coordinates the full search-query parse pipeline:

    cache -> dictionary_matcher -> LLM -> validator -> merge

The result is a structured dict suitable for building an ES query.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.services.cache import get_parse_cache_key, parse_cache
from app.services.dictionary_matcher import DictionaryMatcher, MatchResult
from app.services.llm_parse_service import call_llm
from app.services.parse_validator import validate_llm_result

logger = logging.getLogger(__name__)

_matcher = DictionaryMatcher()


def get_matcher() -> DictionaryMatcher:
    """Return the module-level :class:`DictionaryMatcher` instance."""
    return _matcher


async def init_matcher(pool: Any) -> None:
    """Load the dictionary matcher from the database at startup."""
    await _matcher.load_from_db(pool)


async def parse_query(
    module_type: int,
    query: str,
    tag_definitions: list[dict],
    valid_values: dict[str, set[str]],
    number_fields: set[str],
    boolean_fields: set[str],
) -> dict:
    """Parse a user search query into structured filters + keyword.

    Pipeline:
        1. Check the TTL parse-cache.
        2. Run the dictionary matcher (fast, exact/synonym matching).
        3. If there is remaining text, call the LLM to extract more tags.
        4. Validate LLM output against known tag values.
        5. Merge dictionary and LLM filters.

    Returns:
        A dict with ``parsed_filters``, ``keyword``, ``confidence``,
        ``parse_source``, ``fallback``, and ``parse_time_ms``.
    """
    start = time.monotonic()

    # 1. Cache lookup
    cache_key = get_parse_cache_key(module_type, query)
    cached = parse_cache.get(cache_key)
    if cached is not None:
        cached["parse_source"] = "cache"
        cached["parse_time_ms"] = 0
        return cached

    # 2. Dictionary matching
    dict_result: MatchResult = _matcher.match(module_type, query)
    source = "dict"

    llm_filter: dict = {}
    llm_exclude: dict = {}
    llm_keyword = ""
    confidence = 1.0

    remaining = dict_result.remaining.strip()

    if remaining and len(remaining) > 1:
        # 3. LLM extraction for non-trivial remaining text
        unmatched_dims = [
            d
            for d in tag_definitions
            if d["field_name"] not in dict_result.matched
            and d["field_name"] not in dict_result.excluded
            and d["is_searchable"]
        ]

        try:
            llm_result = await call_llm(remaining, dict_result.matched, unmatched_dims)
        except Exception:
            logger.warning("LLM call failed unexpectedly", exc_info=True)
            llm_result = None

        if llm_result:
            # 4. Validate
            validated = validate_llm_result(
                llm_result,
                valid_values,
                number_fields,
                boolean_fields,
            )
            llm_filter = validated["filter"]
            llm_exclude = validated.get("exclude", {})
            llm_keyword = validated["keyword"]
            confidence = validated["confidence"]
            source = "dict+llm"
        else:
            llm_keyword = remaining
            confidence = 0.0
            source = "dict+fallback"
    elif remaining:
        # Single-char remainder -- not worth an LLM call.
        llm_keyword = remaining
        confidence = 1.0

    # 5. Merge
    merged = {**dict_result.matched, **llm_filter}
    merged_excludes = {**dict_result.excluded, **llm_exclude}
    elapsed_ms = int((time.monotonic() - start) * 1000)

    result = {
        "parsed_filters": merged,
        "parsed_excludes": merged_excludes,
        "excluded_keywords": dict_result.excluded_keywords,
        "keyword": llm_keyword,
        "confidence": confidence,
        "parse_source": source,
        "fallback": source.endswith("fallback"),
        "parse_time_ms": elapsed_ms,
    }

    parse_cache[cache_key] = result
    return result

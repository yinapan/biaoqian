"""Dictionary-based tag matcher with synonym support.

Provides forward-longest-match tokenization of search queries against a
pre-loaded dictionary of tag values and their synonyms.  This is the first
step in the search-parse pipeline (cache -> dictionary -> LLM -> validator).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Fields that always return a list (even when only one value matched).
MULTI_VALUE_FIELDS = frozenset(
    {
        "region",
        "faction",
        "profession",
        "clothing",
        "features",
        "scene",
        "color",
        "description",
    }
)


NEGATION_PREFIXES = ("不要", "不含", "排除", "去掉", "没有", "无", "非", "不是")


@dataclass
class MatchResult:
    """Result of dictionary matching against a query string.

    Attributes:
        matched: Mapping of field_name -> value (str for single-value fields,
                 list[str] for multi-value fields).
        excluded: Mapping of field_name -> value for negated terms.
        remaining: Characters from the query that were *not* matched.
    """

    matched: dict[str, Any] = field(default_factory=dict)
    excluded: dict[str, Any] = field(default_factory=dict)
    remaining: str = ""


class DictionaryMatcher:
    """Forward-longest-match dictionary matcher for search tag resolution.

    Usage::

        matcher = DictionaryMatcher()
        matcher.load_from_data(tag_values, synonyms)
        result = matcher.match(module_type=1, query="女 刺客 中原")
    """

    def __init__(self) -> None:
        # _tokens[module_type][surface_form] = [(field_name, target_value, priority), ...]
        self._tokens: dict[int, dict[str, list[tuple[str, str, int]]]] = {}
        # _all_values[module_type] = [{"text": ..., "field": ...}, ...]
        self._all_values: dict[int, list[dict[str, str]]] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_from_data(
        self,
        tag_values: dict[tuple[int, str], list[str]],
        synonyms: list[dict[str, Any]],
    ) -> None:
        """Load the matcher dictionary from in-memory data structures.

        Args:
            tag_values: Mapping of ``(module_type, field_name)`` to a list of
                canonical tag value strings.
            synonyms: List of synonym dicts, each containing ``module_type``,
                ``field_name``, ``target_value``, ``synonym``, ``priority``.
        """
        self._tokens = {}
        self._all_values = {}

        for (mod, field_name), values in tag_values.items():
            mod_tokens = self._tokens.setdefault(mod, {})
            mod_vals = self._all_values.setdefault(mod, [])
            for val in values:
                entries = mod_tokens.setdefault(val, [])
                entries.append((field_name, val, 0))
                mod_vals.append({"text": val, "field": field_name})

        for syn in synonyms:
            mod = syn["module_type"]
            mod_tokens = self._tokens.setdefault(mod, {})
            entries = mod_tokens.setdefault(syn["synonym"], [])
            entries.append(
                (syn["field_name"], syn["target_value"], syn["priority"])
            )

    async def load_from_db(self, pool: Any) -> None:
        """Load from PostgreSQL (tag_definitions + tag_values + tag_synonyms).

        Only active tag values (``is_active = true``) are loaded.
        """
        async with pool.acquire() as conn:
            vals = await conn.fetch(
                """SELECT td.module_type, td.field_name, tv.value
                   FROM tag_values tv
                   JOIN tag_definitions td ON tv.definition_id = td.id
                   WHERE tv.is_active = true"""
            )
            syns = await conn.fetch("SELECT * FROM tag_synonyms")

        tag_values: dict[tuple[int, str], list[str]] = {}
        for v in vals:
            key = (v["module_type"], v["field_name"])
            tag_values.setdefault(key, []).append(v["value"])

        self.load_from_data(
            tag_values=tag_values,
            synonyms=[dict(s) for s in syns],
        )

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def match(self, module_type: int, query: str) -> MatchResult:
        """Match *query* against the dictionary for *module_type*.

        The query is split on whitespace; each segment is then scanned with
        forward-longest-match (window up to 10 characters).  Synonyms are
        resolved to their canonical ``target_value``; when multiple synonyms
        match the same position, the one with the highest ``priority`` wins.

        Segments prefixed with negation words (不要, 排除, etc.) produce
        ``excluded`` entries instead of ``matched``.

        Multi-value fields always produce a ``list``; single-value fields
        produce a plain ``str``.
        """
        tokens = self._tokens.get(module_type, {})
        if not tokens:
            return MatchResult(remaining=query)

        segments = query.split()
        if not segments:
            return MatchResult()

        matched: dict[str, Any] = {}
        excluded: dict[str, Any] = {}
        remaining_parts: list[str] = []

        for segment in segments:
            negated = False
            clean = segment
            for prefix in NEGATION_PREFIXES:
                if clean.startswith(prefix) and len(clean) > len(prefix):
                    clean = clean[len(prefix):]
                    negated = True
                    break

            seg_matched, seg_remaining = self._match_segment(clean, tokens)

            if not seg_matched and negated:
                remaining_parts.append(segment)
                continue

            target = excluded if negated else matched
            for field_name, value in seg_matched.items():
                if field_name in target:
                    existing = target[field_name]
                    if isinstance(existing, list):
                        if value not in existing:
                            existing.append(value)
                    else:
                        if existing != value:
                            target[field_name] = [existing, value]
                else:
                    target[field_name] = value

            if seg_remaining:
                remaining_parts.append(seg_remaining)

        for collection in (matched, excluded):
            for k, v in collection.items():
                if k in MULTI_VALUE_FIELDS and not isinstance(v, list):
                    collection[k] = [v]

        return MatchResult(
            matched=matched,
            excluded=excluded,
            remaining=" ".join(remaining_parts),
        )

    # ------------------------------------------------------------------
    # Prefix search (for autocomplete / suggestions)
    # ------------------------------------------------------------------

    def prefix_search(
        self, module_type: int, prefix: str, limit: int = 10
    ) -> list[dict[str, str]]:
        """Return tag values whose text starts with *prefix*.

        Returns at most *limit* results as ``{"text": ..., "field": ...}``
        dicts.
        """
        vals = self._all_values.get(module_type, [])
        results: list[dict[str, str]] = []
        for item in vals:
            if item["text"].startswith(prefix):
                results.append(item)
                if len(results) >= limit:
                    break
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _match_segment(
        text: str,
        tokens: dict[str, list[tuple[str, str, int]]],
    ) -> tuple[dict[str, str], str]:
        """Forward-longest-match a single segment (no whitespace).

        Returns ``(matched_fields, remaining_chars)``.
        """
        matched: dict[str, str] = {}
        remaining: list[str] = []
        i = 0

        while i < len(text):
            best_len = 0
            best_field: str | None = None
            best_value: str | None = None

            # Try lengths from longest (max 10) down to 1.
            for length in range(min(len(text) - i, 10), 0, -1):
                candidate = text[i : i + length]
                entries = tokens.get(candidate)
                if entries:
                    top = max(entries, key=lambda e: e[2])
                    best_len = length
                    best_field = top[0]
                    best_value = top[1]
                    break  # longest match found

            if best_len > 0:
                matched[best_field] = best_value  # type: ignore[index]
                i += best_len
            else:
                remaining.append(text[i])
                i += 1

        return matched, "".join(remaining)

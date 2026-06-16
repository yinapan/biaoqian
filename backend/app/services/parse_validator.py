"""Validate and sanitise LLM-returned parse results.

Ensures that every field/value extracted by the LLM actually exists in the
known tag schema.  Invalid values are *demoted* into the free-text keyword
so they still influence full-text search.
"""

from __future__ import annotations

VALID_OPS = {">", "<", ">=", "<=", "=="}


def validate_llm_result(
    result: dict,
    valid_values: dict[str, set[str]],
    number_fields: set[str] | None = None,
    boolean_fields: set[str] | None = None,
) -> dict:
    """Validate and clean an LLM parse result.

    Args:
        result: Raw LLM output containing ``filter``, ``keyword``, ``confidence``.
        valid_values: Mapping of field_name -> set of allowed enum strings.
        number_fields: Fields that expect ``{"op": ..., "value": ...}`` dicts.
        boolean_fields: Fields that expect a boolean value.

    Returns:
        A dict with ``filter`` (cleaned), ``keyword`` (original + demoted
        values), ``confidence``, and ``demoted_to_keyword`` list.
    """
    number_fields = number_fields or set()
    boolean_fields = boolean_fields or set()
    known_fields = set(valid_values.keys()) | number_fields | boolean_fields

    validated_filter: dict = {}
    demoted: list[str] = []

    for field, value in result.get("filter", {}).items():
        # Unknown field -- demote the value to keyword.
        if field not in known_fields:
            demoted.append(str(value))
            continue

        # --- Numeric condition ---
        if field in number_fields:
            if isinstance(value, dict) and value.get("op") in VALID_OPS:
                try:
                    value["value"] = float(value["value"])
                    validated_filter[field] = value
                except (ValueError, TypeError):
                    demoted.append(f"{field}:{value}")
            # Silently skip non-dict or bad-operator entries (no demotion)
            continue

        # --- Boolean ---
        if field in boolean_fields:
            validated_filter[field] = bool(value)
            continue

        # --- Enum (single or multi-value) ---
        if field in valid_values:
            if isinstance(value, list):
                valid = [v for v in value if v in valid_values[field]]
                invalid = [v for v in value if v not in valid_values[field]]
                if valid:
                    validated_filter[field] = valid
                demoted.extend(invalid)
            elif value in valid_values[field]:
                validated_filter[field] = value
            else:
                demoted.append(str(value))
        else:
            # Field is known (e.g. number/boolean already handled above) but
            # has no explicit valid-value set -- keep as-is.
            validated_filter[field] = value

    # Merge demoted tokens into the keyword.
    original_keyword = result.get("keyword", "")
    extra = " ".join(demoted)
    keyword = f"{original_keyword} {extra}".strip() if extra else original_keyword

    return {
        "filter": validated_filter,
        "keyword": keyword,
        "confidence": result.get("confidence", 0.0),
        "demoted_to_keyword": demoted,
    }

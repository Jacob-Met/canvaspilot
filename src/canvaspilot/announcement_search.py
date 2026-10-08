"""Literal search over the existing full announcement reader's normalized rows."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def validate_query(query: str) -> str:
    """Keep significant whitespace and refuse a missing or blank query."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must contain a non-whitespace character")
    return query


def search_announcements(
    announcements: list[dict[str, Any]], query: str,
) -> dict[str, Any]:
    """Select title/body matches without changing, ranking or joining source rows."""
    query = validate_query(query)
    needle = query.casefold()
    if not isinstance(announcements, list):
        raise TypeError("announcements must be a list of normalized reader rows")
    matches = []
    for row in announcements:
        if not isinstance(row, dict):
            raise TypeError("announcements must contain normalized reader objects")
        fields = []
        for field in ("title", "message_text"):
            value = row.get(field)
            if isinstance(value, str) and needle in value.casefold():
                fields.append(field)
        if fields:
            matches.append({
                "matched_fields": fields,
                "announcement": deepcopy(row),
            })
    return {
        "query": query,
        "match_mode": "literal_casefold",
        "announcements_returned": len(announcements),
        "announcements_matched": len(matches),
        "matches": matches,
    }

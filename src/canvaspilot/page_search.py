"""Find literal text in the complete returned course-page collection."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from canvaspilot.api import CanvasAPI

MAX_PAGES = 1000
MAX_COLLECTION_BYTES = 8 * 1024 * 1024


def validate_course(value: Any) -> str:
    """Admit one decimal course selector before creating a client."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError("course_id must be a positive decimal Canvas ID")
    text = str(value)
    if not re.fullmatch(r"[0-9]{1,64}", text) or not text.strip("0"):
        raise ValueError("course_id must be a positive decimal Canvas ID")
    return text.lstrip("0")


def validate_query(value: Any) -> str:
    """Keep meaningful query whitespace; do not turn an empty query into all rows."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("text must contain at least one non-whitespace character")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise ValueError("text must be valid Unicode") from error
    if size > 512:
        raise ValueError("text must be at most 512 UTF-8 bytes")
    if any(ord(char) < 32 and char not in "\t\r\n" for char in value):
        raise ValueError("text contains an unsupported control character")
    return value


def find_pages(api: CanvasAPI, course_id: int | str, query: str) -> dict[str, Any]:
    """Search returned title/body text, retaining explicit unavailable-body coverage.

    The existing paginator supplies all returned pages or raises. The limits here
    apply after that client has decoded the collection. No per-page request,
    server title filter, external resource fetch or provider mutation is added.
    """
    course = validate_course(course_id)
    query = validate_query(query)
    rows = api.client.get_paginated(
        f"/api/v1/courses/{course}/pages", params={"include[]": ["body"]},
    )
    if not isinstance(rows, list) or len(rows) > MAX_PAGES:
        raise ValueError(f"Page collection must be a list of at most {MAX_PAGES} rows")
    try:
        encoded = json.dumps(rows, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError, RecursionError) as error:
        raise ValueError("Page collection must contain valid finite JSON data") from error
    if len(encoded) > MAX_COLLECTION_BYTES:
        raise ValueError("Decoded page collection exceeds the 8 MiB search limit")

    from canvaspilot.api import strip_html

    needle = query.casefold()
    matches: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    titles_searched = 0
    bodies_searched = 0
    for position, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise TypeError(f"Page row {position} must be an object")
        for field in ("title", "body"):
            if row.get(field) is not None and not isinstance(row[field], str):
                raise ValueError(f"Page row {position} {field} must be text or null")
        if row.get("locked_for_user") is not None and type(row["locked_for_user"]) is not bool:
            raise ValueError(f"Page row {position} locked_for_user must be boolean or null")
        title = row.get("title")
        fields: list[str] = []
        if isinstance(title, str):
            titles_searched += 1
            if needle in title.casefold():
                fields.append("title")

        reason = None
        if row.get("locked_for_user") is True:
            reason = "locked_for_user"
        elif "body" not in row:
            reason = "body_not_supplied"
        elif row["body"] is None:
            reason = "body_null"
        body_text = None
        if reason is None:
            body_text = strip_html(row["body"])
            bodies_searched += 1
            if needle in body_text.casefold():
                fields.append("body_text")
        else:
            unavailable.append({
                "position": position, "reason": reason, "page": deepcopy(row),
            })
        if fields:
            matches.append({
                "position": position, "matched_fields": fields,
                "body_text": body_text, "page": deepcopy(row),
            })
    return {
        "course_id": course, "query": query, "match_mode": "literal_casefold",
        "pages_returned": len(rows), "pages_matched": len(matches),
        "titles_searched": titles_searched, "bodies_searched": bodies_searched,
        "matches": matches, "unavailable_bodies": unavailable,
        "coverage": (
            "Search covers supplied titles and available HTML bodies in the returned "
            "page collection. Missing, null and locked bodies are not searched; "
            "block-editor attributes, attachments and embedded resources are not searched. "
            "An empty match list is not a claim that unavailable content has no match."
        ),
    }

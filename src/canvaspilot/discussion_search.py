"""Find literal text in complete normalized discussion-topic openings."""

from __future__ import annotations

import json
import math
from typing import Any

MAX_COURSES = 10
MAX_QUERY_BYTES = 512
MAX_TOPICS = 1000
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_DEPTH = 32
PROJECTED_FIELDS = frozenset(
    ("id", "title", "posted_at", "published", "message_text", "html_url")
)
BOUNDARY = (
    "Searches only returned titles and complete normalized opening prompts from "
    "the existing topic-list reader; not replies, attachments, hidden/unavailable "
    "raw content or a freshness/completeness guarantee. The existing paginator is "
    "reused unchanged; pagination failure refuses the result, and its provider "
    "conventions/limits remain."
)


def _course(value: Any) -> str:
    if type(value) is int:
        if value <= 0 or value >= 10**20:
            raise ValueError("course IDs must be positive decimal values of at most 20 digits")
        return str(value)
    if (type(value) is not str or not 1 <= len(value) <= 20
            or any(char not in "0123456789" for char in value)):
        raise ValueError("course IDs must contain 1 to 20 ASCII decimal digits")
    normalized = value.lstrip("0")
    if not normalized:
        raise ValueError("course IDs must be positive")
    return normalized


def _query(query: Any) -> str:
    if type(query) is not str or not query.strip():
        raise ValueError("query must contain a non-whitespace character")
    if len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        raise ValueError("query exceeds 512 UTF-8 bytes")
    return query


def validate_selection(course_ids: Any, query: Any) -> tuple[list[str], str]:
    """Validate before client construction; repeated selections remain repeated."""
    if type(course_ids) not in (list, tuple) or not 1 <= len(course_ids) <= MAX_COURSES:
        raise ValueError("select 1 to 10 course occurrences")
    courses = [_course(value) for value in course_ids]
    return courses, _query(query)


def _json_tree(value: Any, depth: int = 0, active: set[int] | None = None) -> None:
    """Refuse lossy JSON coercions, cycles and excessive container nesting."""
    if value is None or type(value) in (bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("normalized topic metadata must contain finite JSON numbers")
        return
    if type(value) is str:
        value.encode("utf-8")
        return
    if type(value) not in (list, dict):
        raise ValueError("normalized topic metadata must contain only JSON values")
    if depth >= MAX_DEPTH:
        raise ValueError("normalized topic metadata exceeds 32 container levels")
    if active is None:
        active = set()
    identity = id(value)
    if identity in active:
        raise ValueError("normalized topic metadata contains a cycle")
    active.add(identity)
    try:
        if type(value) is dict:
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError("normalized topic object keys must be strings")
                key.encode("utf-8")
                _json_tree(item, depth + 1, active)
        else:
            for item in value:
                _json_tree(item, depth + 1, active)
    finally:
        active.remove(identity)


def _admit(selections: Any, query: Any) -> tuple[list[dict[str, Any]], str]:
    if type(selections) is not list or not 1 <= len(selections) <= MAX_COURSES:
        raise ValueError("select 1 to 10 course occurrences")
    query = _query(query)
    count = 0
    normalized = []
    for selection in selections:
        if type(selection) is not dict or set(selection) != {"course_id", "topics"}:
            raise ValueError("each selection must contain exactly course_id and topics")
        course = _course(selection["course_id"])
        rows = selection["topics"]
        if type(rows) is not list:
            raise ValueError("topics must be a complete normalized reader list")
        count += len(rows)
        if count > MAX_TOPICS:
            raise ValueError("selection exceeds 1000 normalized topics")
        for row in rows:
            if type(row) is not dict or not PROJECTED_FIELDS.issubset(row):
                raise ValueError("topic must contain all six normalized reader fields")
            if row["title"] is not None and type(row["title"]) is not str:
                raise ValueError("normalized topic title must be text or null")
            if type(row["message_text"]) is not str:
                raise ValueError("normalized topic message_text must be text")
        normalized.append({"course_id": course, "topics": rows})
    _json_tree(normalized)
    encoded = json.dumps(
        normalized, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )
    if len(encoded.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("selection exceeds 8 MiB of normalized JSON")
    # JSON round-trip both preserves admitted values and detaches all nested inputs.
    return json.loads(encoded), query


def search_discussions(selections: Any, query: Any) -> dict[str, Any]:
    """Search normalized rows without fetching details or changing input objects."""
    selections, query = _admit(selections, query)
    needle = query.casefold()
    matches = []
    summary = []
    topic_count = 0
    empty_count = 0
    for number, selection in enumerate(selections, 1):
        rows = selection["topics"]
        empty = sum(row["message_text"] == "" for row in rows)
        topic_count += len(rows)
        empty_count += empty
        summary.append({
            "selection_number": number,
            "course_id": selection["course_id"],
            "topics_returned": len(rows),
            "empty_message_text_count": empty,
        })
        for position, row in enumerate(rows, 1):
            fields = [
                field for field in ("title", "message_text")
                if type(row[field]) is str and needle in row[field].casefold()
            ]
            if fields:
                matches.append({
                    "selection_number": number,
                    "course_id": selection["course_id"],
                    "topic_position": position,
                    "matched_fields": fields,
                    "topic": row,
                })
    return {
        "schema": "canvaspilot.discussion-search.v1",
        "query": query,
        "match_mode": "literal_casefold",
        "topic_count": topic_count,
        "matched_count": len(matches),
        "empty_message_text_count": empty_count,
        "selections": summary,
        "matches": matches,
        "boundary": BOUNDARY,
    }


def collect_discussions(api: Any, course_ids: Any, query: Any) -> dict[str, Any]:
    courses, query = validate_selection(course_ids, query)
    selections = [
        {"course_id": course, "topics": api.list_discussion_topics(course)}
        for course in courses
    ]
    return search_discussions(selections, query)


def serialize_discussion_search(result: Any) -> str:
    _json_tree(result)
    text = json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    if len(text.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("search result exceeds 16 MiB of output JSON")
    return text


def _fail(error: Exception, code: int) -> None:
    import sys

    text = json.dumps({
        "ok": False, "error": type(error).__name__, "message": str(error),
    }, ensure_ascii=True) + "\n"
    try:
        if sys.stderr is not None:
            sys.stderr.write(text)
            sys.stderr.flush()
    except (OSError, ValueError):
        pass
    raise SystemExit(code) from None


def run_find_discussions(args: Any) -> None:
    """Use the existing client, prepare everything, close it, then deliver JSON."""
    import logging
    import sys
    from pathlib import Path

    try:
        courses, query = validate_selection(args.course_ids, args.text)
    except (TypeError, ValueError) as error:
        _fail(error, 2)

    import httpx

    from canvaspilot.api import CanvasAPI
    from canvaspilot.client import (
        CanvasAuthError,
        CanvasClient,
        CanvasPaginationError,
        default_base_url,
        default_profile,
    )

    logger = logging.getLogger("httpx")
    previous_level = logger.level
    client = None
    try:
        try:
            logger.setLevel(max(logger.getEffectiveLevel(), logging.WARNING))
            client = CanvasClient(
                base_url=args.base_url or default_base_url(),
                token=args.token,
                profile=Path(args.profile) if args.profile else default_profile(),
            )
            result = collect_discussions(CanvasAPI(client), courses, query)
            text = serialize_discussion_search(result)
        finally:
            try:
                if client is not None:
                    client.close()
            finally:
                logger.setLevel(previous_level)
    except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError,
            OSError, TypeError, ValueError, OverflowError) as error:
        _fail(error, 1)

    try:
        if sys.stdout is None:
            raise OSError("stdout is unavailable")
        if sys.stdout.write(text) != len(text):
            raise OSError("stdout accepted an incomplete search result")
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        _fail(error, 1)

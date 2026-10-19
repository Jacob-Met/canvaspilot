"""Find classic quizzes by literal title or their returned instruction text."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from canvaspilot.api import strip_html

MAX_COURSES = 10
MAX_QUIZZES = 1000
MAX_QUERY_BYTES = 512
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
DESCRIPTION_STATES = ("missing", "null", "empty", "no_text", "text")
QUIZ_FIELDS = (
    "id", "title", "due_at", "lock_at", "question_count", "points_possible",
    "published", "quiz_type", "html_url", "unlock_at", "locked_for_user",
)
BOUNDARY = (
    "Searches returned classic-quiz titles and descriptions using the existing "
    "HTML-to-text projection. Missing or empty text does not establish that no "
    "instructions exist. Questions, answers, submissions, attachments and New "
    "Quizzes/LTI content are not searched. Counts describe returned records; "
    "recorded dates and lock values do not establish current eligibility."
)


def _identifier(value: Any, name: str) -> str:
    if type(value) is int:
        if 0 < value < 10**20:
            return str(value)
    elif (type(value) is str and 1 <= len(value) <= 20
          and all(char in "0123456789" for char in value)):
        normalized = value.lstrip("0")
        if normalized:
            return normalized
    raise ValueError(f"{name} must be a positive ASCII decimal ID of at most 20 digits")


def validate_selection(course_ids: Any, query: Any) -> tuple[list[str], str]:
    """Validate the complete selection before constructing a client or reading."""
    if type(course_ids) not in (list, tuple) or not 1 <= len(course_ids) <= MAX_COURSES:
        raise ValueError("select 1 to 10 course occurrences")
    courses = [_identifier(value, "course ID") for value in course_ids]
    if type(query) is not str or not query.strip():
        raise ValueError("query must contain a non-whitespace character")
    if len(query.encode("utf-8")) > MAX_QUERY_BYTES:
        raise ValueError("query exceeds 512 UTF-8 bytes")
    return courses, query


def _json(value: Any, *, indent: int | None = None) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=indent)
    except RecursionError as error:
        raise ValueError("quiz data exceeds supported JSON nesting") from error


def _description(row: dict[str, Any]) -> tuple[str, str | None, str | None]:
    if "description" not in row:
        return "missing", None, None
    raw = row["description"]
    if raw is None:
        return "null", None, None
    if type(raw) is not str:
        raise ValueError("quiz description must be text or null when supplied")
    text = strip_html(raw)
    state = "empty" if raw == "" else "text" if text else "no_text"
    return state, raw, text


def search_quizzes(client: Any, course_ids: Any, query: Any) -> dict[str, Any]:
    """Read complete collections through CanvasClient and prepare one report.

    The existing paginator owns transport limits and continuation admission. The
    limits here apply after it has decoded each collection, before any output.
    """
    courses, query = validate_selection(course_ids, query)
    needle = query.casefold()
    total = 0
    input_bytes = 0
    counts = dict.fromkeys(DESCRIPTION_STATES, 0)
    selections = []
    matches = []
    for number, course in enumerate(courses, 1):
        rows = client.get_paginated(f"/api/v1/courses/{course}/quizzes")
        if type(rows) is not list:
            raise ValueError("quiz collection must be a complete list")
        total += len(rows)
        if total > MAX_QUIZZES:
            raise ValueError("selection exceeds 1000 quiz records")
        input_bytes += len(_json(rows).encode("utf-8"))
        if input_bytes > MAX_INPUT_BYTES:
            raise ValueError("quiz collections exceed 8 MiB of decoded JSON")
        matched = 0
        for position, row in enumerate(rows, 1):
            if type(row) is not dict:
                raise ValueError("each quiz record must be an object")
            _identifier(row.get("id"), "returned quiz ID")
            if "course_id" in row and _identifier(row["course_id"], "returned course ID") != course:
                raise ValueError("returned quiz course ID does not match its selected course")
            title = row.get("title")
            if title is not None and type(title) is not str:
                raise ValueError("quiz title must be text or null when supplied")
            state, raw, text = _description(row)
            counts[state] += 1
            fields = []
            if title is not None and needle in title.casefold():
                fields.append("title")
            if text is not None and needle in text.casefold():
                fields.append("description_text")
            if fields:
                matched += 1
                matches.append({
                    "selection_number": number,
                    "course_id": course,
                    "quiz_position": position,
                    "matched_fields": fields,
                    "quiz": {key: deepcopy(row.get(key)) for key in QUIZ_FIELDS},
                    "description_state": state,
                    "description_html": raw,
                    "description_text": text,
                })
        selections.append({
            "selection_number": number, "course_id": course,
            "quiz_count": len(rows), "matched_count": matched,
        })
    return {
        "schema": "canvaspilot.quiz-search.v1",
        "query": query,
        "match_mode": "literal_casefold",
        "quiz_count": total,
        "matched_count": len(matches),
        "description_counts": counts,
        "selections": selections,
        "matches": matches,
        "boundary": BOUNDARY,
    }


def serialize_quiz_search(result: Any) -> str:
    text = _json(result, indent=2) + "\n"
    if len(text.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("search result exceeds 16 MiB of output JSON")
    return text


def _fail(error: Exception, status: int) -> None:
    import sys

    try:
        if sys.stderr is not None:
            sys.stderr.write(json.dumps({
                "ok": False, "error": type(error).__name__, "message": str(error),
            }) + "\n")
            sys.stderr.flush()
    except (OSError, ValueError):
        pass
    raise SystemExit(status) from None


def run_find_quizzes(args: Any) -> None:
    """Close the ordinary read client before delivering one complete JSON result."""
    import logging
    import sys
    from pathlib import Path

    try:
        courses, query = validate_selection(args.course_ids, args.text)
    except (TypeError, ValueError) as error:
        _fail(error, 2)

    import httpx

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
            text = serialize_quiz_search(search_quizzes(client, courses, query))
        finally:
            try:
                if client is not None:
                    client.close()
            finally:
                logger.setLevel(previous_level)
    except (CanvasAuthError, CanvasPaginationError, httpx.HTTPError,
            OSError, TypeError, ValueError, OverflowError, RecursionError) as error:
        _fail(error, 1)

    try:
        if sys.stdout is None:
            raise OSError("stdout is unavailable")
        if sys.stdout.write(text) != len(text):
            raise OSError("stdout accepted an incomplete search result")
        sys.stdout.flush()
    except (OSError, ValueError) as error:
        _fail(error, 1)

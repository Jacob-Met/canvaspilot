"""Literal name search over the existing course-file metadata reader."""

from __future__ import annotations

import json
from typing import Any, Protocol

NAME_FIELDS = ("display_name", "filename")
MAX_COURSES = 10
MAX_FILES_PER_COURSE = 2000
MAX_TOTAL_FILES = 5000
MAX_SOURCE_BYTES = 8 * 1024 * 1024


class FileReader(Protocol):
    def list_files(self, course_id: str) -> list[dict[str, Any]]: ...


def _course_id(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise TypeError("course IDs must contain 1 to 20 ASCII decimal digits")
    raw = str(value)
    if not 1 <= len(raw) <= 20 or not raw.isascii() or not raw.isdecimal():
        raise ValueError("course IDs must contain 1 to 20 ASCII decimal digits")
    canonical = str(int(raw))
    if canonical == "0":
        raise ValueError("course IDs must be positive")
    return canonical


def _file_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise TypeError("course file metadata must be a list")
    return value


def validate_request(course_ids: object, text: object) -> tuple[list[str], str]:
    """Admit the complete explicit selection before a reader can be constructed."""
    if not isinstance(course_ids, (list, tuple)) or not 1 <= len(course_ids) <= MAX_COURSES:
        raise ValueError("select between 1 and 10 unique positive course IDs")
    selected: list[str] = []
    seen: set[str] = set()
    for value in course_ids:
        try:
            canonical = _course_id(value)
        except TypeError as error:
            # Public request admission has one stable ValueError boundary.
            raise ValueError(str(error)) from error
        if canonical in seen:
            raise ValueError("select each numeric course ID only once")
        selected.append(canonical)
        seen.add(canonical)
    if not isinstance(text, str) or not text.strip():
        raise ValueError("search text must contain non-whitespace characters")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeError as error:
        raise ValueError("search text must be valid UTF-8") from error
    if size > 512:
        raise ValueError("search text must be at most 512 UTF-8 bytes")
    return selected, text


def _require_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int, float)):
        return
    if isinstance(value, list):
        for item in value:
            _require_json(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("file metadata must have string JSON object keys")
            _require_json(item)
        return
    raise ValueError("file metadata must contain only JSON values")


def _source_size(row: dict[str, Any]) -> int:
    try:
        if not isinstance(row, dict):
            raise TypeError("each returned file metadata row must be an object")
        _require_json(row)
        return len(json.dumps(
            row, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        ).encode("utf-8"))
    except (TypeError, UnicodeError, RecursionError, ValueError) as error:
        raise ValueError("file metadata must be finite, valid UTF-8 JSON") from error


def find_files(api: FileReader, course_ids: object, text: object) -> dict[str, Any]:
    """Search complete returned names without changing rows or following links.

    Results refer to CanvasAPI.list_files' normalized metadata projection. An
    unavailable name is reported explicitly and cannot establish a nonmatch.
    """
    selected, query = validate_request(course_ids, text)
    folded_query = query.casefold()
    courses: list[dict[str, Any]] = []
    total_rows = 0
    total_bytes = 0
    for course_id in selected:
        returned = api.list_files(course_id)
        try:
            rows = _file_rows(returned)
        except TypeError as error:
            # Normalize response admission; transport errors still propagate.
            raise ValueError(str(error)) from error
        if len(rows) > MAX_FILES_PER_COURSE:
            raise ValueError("course file metadata exceeds 2000 returned rows")
        if total_rows + len(rows) > MAX_TOTAL_FILES:
            raise ValueError("selected file metadata exceeds 5000 returned rows")
        total_rows += len(rows)
        matches: list[dict[str, Any]] = []
        unavailable: list[dict[str, Any]] = []
        searched = 0
        for position, row in enumerate(rows, 1):
            total_bytes += _source_size(row)
            if total_bytes > MAX_SOURCE_BYTES:
                raise ValueError("selected file metadata exceeds 8 MiB of UTF-8 JSON row data")
            matched_fields: list[str] = []
            missing_fields: dict[str, str] = {}
            has_searchable_name = False
            for field in NAME_FIELDS:
                if field not in row:
                    missing_fields[field] = "missing"
                elif row[field] is None:
                    missing_fields[field] = "null"
                elif not isinstance(row[field], str):
                    missing_fields[field] = "unsupported_type"
                else:
                    has_searchable_name = True
                    if folded_query in row[field].casefold():
                        matched_fields.append(field)
            if has_searchable_name:
                searched += 1
            if missing_fields:
                unavailable.append({"source_position": position, "fields": missing_fields})
            if matched_fields:
                matches.append({
                    "source_position": position,
                    "matched_fields": matched_fields,
                    "file": row,
                })
        courses.append({
            "course_id": course_id,
            "returned_files": len(rows),
            "searched_files": searched,
            "matched_files": len(matches),
            "unavailable_names": unavailable,
            "matches": matches,
        })
    return {
        "query": query,
        "match_rule": "unicode_casefold_substring",
        "searched_fields": list(NAME_FIELDS),
        "source": "CanvasAPI.list_files",
        "content_searched": False,
        "courses": courses,
        "totals": {
            "courses": len(courses),
            "returned_files": total_rows,
            "searched_files": sum(course["searched_files"] for course in courses),
            "matched_files": sum(course["matched_files"] for course in courses),
            "rows_with_unavailable_names": sum(
                len(course["unavailable_names"]) for course in courses
            ),
        },
    }

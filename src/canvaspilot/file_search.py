"""Literal search over the existing normalized course-file metadata reader."""

from __future__ import annotations

import json
import math
import re
from typing import Any

MAX_ROWS = 5000
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
NAME_FIELDS = ("display_name", "filename")


def validate_selection(course_ids: list[int | str], query: str) -> tuple[list[str], str]:
    if type(course_ids) is not list or not 1 <= len(course_ids) <= 10:
        raise ValueError("Select 1–10 unique positive decimal course IDs")
    selected = []
    for value in course_ids:
        if type(value) not in (int, str):
            raise ValueError("Course IDs must be positive ASCII decimal integers")
        raw = str(value)
        if not re.fullmatch(r"[0-9]{1,20}", raw) or not raw.strip("0"):
            raise ValueError("Course IDs must contain 1–20 ASCII digits and be positive")
        canonical = raw.lstrip("0")
        if canonical in selected:
            raise ValueError("Select each course only once (leading-zero aliases are duplicates)")
        selected.append(canonical)
    if type(query) is not str or not query.strip():
        raise ValueError("Search text must contain a non-whitespace character")
    try:
        size = len(query.encode("utf-8"))
    except UnicodeError as error:
        raise ValueError("Search text must be valid UTF-8") from error
    if size > 512:
        raise ValueError("Search text exceeds 512 UTF-8 bytes")
    return selected, query


def _admit_json(value: Any, depth: int = 0) -> None:
    if type(value) in (dict, list):
        if depth > 16:
            raise ValueError("File metadata exceeds 16 nested containers")
        if type(value) is dict:
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError("File metadata object keys must be strings")
                key.encode("utf-8")
                _admit_json(item, depth + 1)
        else:
            for item in value:
                _admit_json(item, depth + 1)
    elif type(value) is str:
        value.encode("utf-8")
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError("File metadata numbers must be finite")
    elif value is not None and type(value) not in (bool, int):
        raise ValueError("File metadata must contain only JSON values")


def _encoded(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")


def search_course_files(api: Any, course_ids: list[int | str], query: str) -> dict[str, Any]:
    """Return complete detached observations; never fetch a file's URL or contents."""
    selected, query = validate_selection(course_ids, query)
    needle = query.casefold()
    courses = []
    totals = {"returned": 0, "matched": 0, "nonmatching": 0, "unknown": 0}
    source_bytes = 0
    for course in selected:
        rows = api.list_files(course)
        if type(rows) is not list:
            raise ValueError("The normalized file reader must return a list")
        if totals["returned"] + len(rows) > MAX_ROWS:
            raise ValueError("Selected courses exceed 5,000 normalized file rows")
        for row in rows:
            if type(row) is not dict:
                raise ValueError("Every normalized file row must be an object")
            _admit_json(row)
            for name in NAME_FIELDS:
                if name in row and row[name] is not None and type(row[name]) is not str:
                    raise ValueError(f"{name} must be a string, null or absent")
        serialized = _encoded(rows)
        source_bytes += len(serialized)
        if source_bytes > MAX_SOURCE_BYTES:
            raise ValueError("Normalized file metadata exceeds 4 MiB")
        detached = json.loads(serialized)
        observations = []
        counts = {"returned": len(rows), "matched": 0, "nonmatching": 0, "unknown": 0}
        for index, row in enumerate(detached):
            unavailable = [name for name in NAME_FIELDS if row.get(name) is None]
            matched = [
                name for name in NAME_FIELDS
                if type(row.get(name)) is str and needle in row[name].casefold()
            ]
            match = True if matched else (None if unavailable else False)
            counts["matched" if match is True else "nonmatching" if match is False else "unknown"] += 1
            observations.append({
                "source_index": index, "source": row, "matched_fields": matched,
                "unavailable_fields": unavailable, "match": match,
            })
        courses.append({"course_id": course, "counts": counts, "observations": observations})
        for key in totals:
            totals[key] += counts[key]
    result = {
        "schema": "canvaspilot.file-search.v1", "query": query,
        "course_ids": selected, "counts": totals, "courses": courses,
        "scope": (
            "Literal casefold search of display_name and filename from the existing list_files "
            "projection. It skips non-object raw rows, maps missing fields to null, and retains "
            "only its fixed metadata fields. These sequential returned observations do not "
            "establish a complete provider inventory, download permission or file contents. "
            "No file URL was followed."
        ),
    }
    if len(_encoded(result)) > MAX_OUTPUT_BYTES:
        raise ValueError("Complete search report exceeds 16 MiB")
    return result


def run_file_search(args: Any) -> None:
    """Own command lifecycle, leaving the common CLI and client policy unchanged."""
    import logging
    import sys
    from pathlib import Path

    try:
        course_ids, query = validate_selection(args.course_ids, args.text)
    except (ValueError, UnicodeError) as error:
        print(json.dumps({"ok": False, "error": type(error).__name__, "message": str(error)}),
              file=sys.stderr)
        raise SystemExit(1) from None

    from canvaspilot.api import CanvasAPI
    from canvaspilot.client import CanvasClient, default_base_url, default_profile

    http_log = logging.getLogger("httpx")
    previous_level = http_log.level
    http_log.setLevel(max(http_log.getEffectiveLevel(), logging.WARNING))
    try:
        client = CanvasClient(
            base_url=args.base_url or default_base_url(), token=args.token,
            profile=Path(args.profile) if args.profile else default_profile(),
        )
        try:
            result = search_course_files(CanvasAPI(client), course_ids, query)
            output = _encoded(result).decode("utf-8") + "\n"
        finally:
            client.close()
        sys.stdout.write(output)
        sys.stdout.flush()
    except Exception as error:  # noqa: BLE001 — structured command boundary, no automatic retry
        print(json.dumps({"ok": False, "error": type(error).__name__, "message": str(error)}),
              file=sys.stderr)
        raise SystemExit(1) from None
    finally:
        http_log.setLevel(previous_level)

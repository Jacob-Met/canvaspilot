"""Read recorded course-page revisions without modifying or reverting a page."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import quote

MAX_ID = 9223372036854775807


def positive_id(value: int | str, name: str) -> str:
    """Canonicalize a bounded positive ASCII-decimal identifier."""
    if type(value) is int:
        if not 1 <= value <= MAX_ID:
            raise ValueError(f"{name} must be between 1 and {MAX_ID}")
        return str(value)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a positive decimal integer")
    if not 1 <= len(value) <= 19 or not all("0" <= c <= "9" for c in value):
        raise ValueError(f"{name} must be 1–19 ASCII decimal digits")
    number = int(value)
    if not 1 <= number <= MAX_ID:
        raise ValueError(f"{name} must be between 1 and {MAX_ID}")
    return str(number)


def revision_selector(value: int | str) -> str:
    if value == "latest" and isinstance(value, str):
        return value
    return positive_id(value, "revision_id")


def page_path(course_id: int | str, page_url: str) -> str:
    course = positive_id(course_id, "course_id")
    if not isinstance(page_url, str):
        raise TypeError("page_url must be a literal page locator string")
    if not page_url or page_url in {".", ".."}:
        raise ValueError("page_url must be a nonempty page locator, not '.' or '..'")
    if any(ord(c) < 32 or ord(c) == 127 for c in page_url):
        raise ValueError("page_url must not contain control characters")
    try:
        encoded = page_url.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("page_url must contain Unicode scalar values") from error
    if len(encoded) > 2048:
        raise ValueError("page_url must be at most 2048 UTF-8 bytes")
    return f"/api/v1/courses/{course}/pages/{quote(page_url, safe='')}/revisions"


def _row(value: Any) -> tuple[dict[str, Any], str]:
    if not isinstance(value, dict):
        raise TypeError("page revision must be an object")
    identity = positive_id(value.get("revision_id"), "returned revision_id")
    return deepcopy(value), identity


def read_page_revisions(client: Any, course_id: int | str, page_url: str) -> list[dict[str, Any]]:
    path = page_path(course_id, page_url)
    rows = client.get_paginated(path)
    if not isinstance(rows, list):
        raise TypeError("page revision reader must return a list")
    result = []
    seen = set()
    for value in rows:
        row, identity = _row(value)
        if identity in seen:
            raise ValueError(f"duplicate returned revision_id: {identity}")
        seen.add(identity)
        result.append(row)
    return result


def read_page_revision(
    client: Any, course_id: int | str, page_url: str, revision_id: int | str,
    *, summary: bool = False,
) -> dict[str, Any]:
    path = page_path(course_id, page_url)
    selected = revision_selector(revision_id)
    if type(summary) is not bool:
        raise TypeError("summary must be a boolean")
    row, identity = _row(client.request("GET", f"{path}/{selected}", params={"summary": summary}))
    if selected != "latest" and selected != identity:
        raise ValueError("returned revision_id does not match the selected revision")
    result = {"revision": row}
    if "body" in row:
        body = row["body"]
        if body is not None and not isinstance(body, str):
            raise ValueError("revision body must be text or null when supplied")
        from canvaspilot.api import strip_html

        result["body_text"] = None if body is None else strip_html(body)
    return result

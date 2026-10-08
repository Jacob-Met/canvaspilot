"""Read a student's returned submission versions without assigning grades to them."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from canvaspilot.client import CanvasClient

_ASSIGNMENT_FIELDS = (
    "id", "course_id", "name", "html_url", "due_at", "points_possible",
)


def _numeric_id(value: int | str, name: str) -> str:
    if type(value) is int and value > 0:
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        normalized = value.lstrip("0")
        if normalized:
            return normalized
    raise ValueError(f"{name} must be a positive numeric Canvas ID")


def _records(value: Any, name: str) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(
        not isinstance(record, dict) for record in value
    ):
        raise ValueError(f"Canvas returned malformed {name}")
    return value


def build_submission_history(
    assignment: dict[str, Any], submission: dict[str, Any]
) -> dict[str, Any]:
    """Keep current data, returned versions and top-level comments distinct.

    Canvas may omit history. A returned list is preserved in response order,
    without filling gaps, choosing a duplicate attempt, or inferring coverage.
    Grades and comments stay on the records where Canvas supplied them.
    """
    if not isinstance(assignment, dict) or not isinstance(submission, dict):
        raise ValueError(  # noqa: TRY004
            "Canvas returned malformed assignment or submission history"
        )
    history = _records(submission.get("submission_history"), "submission history")
    comments = _records(submission.get("submission_comments"), "submission comments")
    return deepcopy({
        "assignment": {field: assignment.get(field) for field in _ASSIGNMENT_FIELDS},
        "current_submission": {
            key: value for key, value in submission.items()
            if key not in {"submission_history", "submission_comments"}
        },
        "history": {"returned": history is not None, "records": history},
        "submission_comments": comments,
    })


def read_submission_history(
    client: CanvasClient, course_id: int | str, assignment_id: int | str
) -> dict[str, Any]:
    """Use only caller-self GETs; do not request read_status or follow content URLs."""
    course = _numeric_id(course_id, "course_id")
    assignment = _numeric_id(assignment_id, "assignment_id")
    path = f"/api/v1/courses/{course}/assignments/{assignment}"
    assignment_data = client.request("GET", path)
    submission_data = client.request(
        "GET",
        f"{path}/submissions/self",
        params={"include[]": ["submission_history", "submission_comments"]},
    )
    return build_submission_history(assignment_data, submission_data)

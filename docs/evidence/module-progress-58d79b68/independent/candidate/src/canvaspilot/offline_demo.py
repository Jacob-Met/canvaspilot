"""A deterministic, synthetic Canvas review; no account or network required.

Run ``python -m canvaspilot.offline_demo`` after installing CanvasPilot.
This example exercises the real high-level API against an explicit fixture.
It cannot fall back to token, session-broker, or browser execution.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

FIXTURE: dict[str, Any] = {
    "profile": {"id": 1, "name": "Synthetic Learner"},
    "routes": {
        "GET /api/v1/courses": [
            {"id": 101, "name": "Synthetic Biology", "course_code": "DEMO-BIO"},
            {"id": 102, "name": "Synthetic Computing", "course_code": "DEMO-CS"},
        ],
        "GET /api/v1/courses/101/assignments": [
            {"id": 1001, "name": "Read the methods", "due_at": "2026-09-18T18:00:00Z"},
        ],
        "GET /api/v1/courses/102/assignments": [
            {"id": 1002, "name": "Review an algorithm", "due_at": None},
        ],
        "GET /api/v1/courses/101/assignments/1001": {
            "id": 1001, "name": "Read the methods", "due_at": "2026-09-18T18:00:00Z",
            "description": "<p>Identify the <b>controls</b> and limitations.</p>",
            "points_possible": 10, "submission_types": ["online_upload"],
        },
        "GET /api/v1/courses/102/assignments/1002": {
            "id": 1002, "name": "Review an algorithm", "due_at": None,
            "description": "<p>Explain the time and space requirements.</p>",
            "points_possible": 10, "submission_types": ["online_upload"],
        },
    },
}


class OfflineOnlyClient(CanvasClient):
    """Read only the exact synthetic routes; reject writes and fixture misses."""

    def __init__(self) -> None:
        super().__init__(base_url="https://example.test", token="", profile=Path("."),
                         fixture=copy.deepcopy(FIXTURE))

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        if method.upper() != "GET":
            raise ValueError("The offline demo never performs write requests")
        assert self.fixture is not None
        if f"GET {path}" not in self.fixture["routes"]:
            raise KeyError(f"No exact synthetic route: {path}")
        return super().request(method, path, **kwargs)


def build_review() -> dict[str, Any]:
    """Return the same inspectable JSON result on every invocation."""
    briefs: list[dict[str, Any]] = []
    with CanvasAPI(OfflineOnlyClient()) as api:
        courses = api.list_courses()
        for course in courses:
            for assignment in api.list_assignments(course["id"], bucket=None):
                briefs.append(api.assignment_brief(course["id"], assignment["id"]))
    return {
        "mode": "synthetic_offline_example",
        "network_required": False,
        "account_required": False,
        "model_calls": 0,
        "courses": courses,
        "assignment_briefs": briefs,
        "buyer_or_student_results": "Not measured; synthetic demonstration only",
        "unknowns": [{"assignment_id": b["assignment_id"], "reason": "due_date_not_supplied"}
                     for b in briefs if b["due_at"] is None],
        "limitations": "No live pagination, authentication, submission, or institution-policy validation.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="New JSON file; an existing file is never overwritten")
    args = parser.parse_args(argv)
    text = json.dumps(build_review(), indent=2, ensure_ascii=False) + "\n"
    if args.out is None:
        print(text, end="")
        return 0
    try:
        with args.out.open("x", encoding="utf-8", newline="\n") as output:
            output.write(text)
    except OSError as exc:
        print(f"Output not written: {exc.strerror or type(exc).__name__}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

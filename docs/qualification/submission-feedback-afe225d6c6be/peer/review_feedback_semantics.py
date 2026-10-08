# SPDX-License-Identifier: MIT
"""Independent Canvas feedback semantics; deterministic clients, no live access."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import itertools
import json
import sys
import traceback
from pathlib import Path
from typing import Any


class RecordingClient:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path, copy.deepcopy(kwargs)))
        index = len(self.calls) - 1
        if index >= len(self.responses):
            raise AssertionError("Unexpected additional Canvas request")
        result = self.responses[index]
        if isinstance(result, Exception):
            raise result
        return result


def payloads() -> tuple[dict[str, Any], dict[str, Any]]:
    assignment = {
        "id": 19,
        "course_id": 7,
        "name": "Review without guessed grades",
        "points_possible": 0,
        "rubric_settings": {"hide_points": True, "extension": {"tags": ["kept"]}},
        "use_rubric_for_grading": False,
        "rubric": [
            {"id": "unique", "description": "Criterion", "points": 0,
             "ratings": [{"id": "rating", "description": "Zero still meaningful"}]},
            {"id": "duplicate", "description": "First duplicate"},
            {"id": "duplicate", "description": "Second duplicate"},
        ],
    }
    submission = {
        "id": 41,
        "assignment_id": 19,
        "user_id": 9,
        "attempt": 2,
        "score": 0,
        "grade": "",
        "grade_matches_current_submission": False,
        "grader_id": -42,
        "rubric_assessment": {
            "unique": {"points": 0, "comments": "", "extension": {"tags": ["raw"]}},
            "duplicate": {"points": 3, "extension": {"tags": ["ambiguous"]}},
            "orphan": {"points": None, "comments": "Unmapped feedback"},
        },
        "submission_comments": [{
            "id": 81, "author_id": 13, "author": {"display_name": "Reviewer"},
            "comment": "Original feedback", "attachments": [{"id": 5, "filename": "notes.pdf"}],
            "media_comment": {"media_id": "media", "media_type": "audio"},
        }],
    }
    return assignment, submission


def duplicate_ids(build: Any, api: Any, httpx: Any, auth_error: Any) -> dict[str, Any]:
    assignment, submission = payloads()
    count = 0
    for order in itertools.permutations(assignment["rubric"]):
        current = copy.deepcopy(assignment)
        current["rubric"] = list(copy.deepcopy(order))
        before = copy.deepcopy((current, submission))
        result = build(current, submission)["rubric"]
        assert len(result["criteria"]) == 3
        for actual, criterion in zip(result["criteria"], current["rubric"], strict=True):
            assert actual["criterion"] == criterion
            expected = submission["rubric_assessment"]["unique"] if criterion["id"] == "unique" else None
            assert actual["assessment"] == expected, "Ambiguous duplicate criterion consumed feedback"
        assert result["unmatched_assessments"] == {
            name: submission["rubric_assessment"][name] for name in ("duplicate", "orphan")
        }, "Ambiguous or orphan feedback was lost"
        assert (current, submission) == before
        count += 1
    return {"criterion_orders": count, "duplicate_assessments_joined": 0}


def invalid_ids(build: Any, api: Any, httpx: Any, auth_error: Any) -> dict[str, Any]:
    ids = [None, 7, True, 7.0, ["x"], {"id": "x"}]
    assignment = {"rubric": [{"description": "No ID"}] + [
        {"id": value, "description": f"Non-string criterion {index}"}
        for index, value in enumerate(ids)
    ]}
    assessments = {key: {"comments": "Must stay unmatched: " + key} for key in (
        "", "None", "7", "True", "7.0", "['x']", "{'id': 'x'}", "undefined"
    )}
    submission = {"rubric_assessment": assessments}
    before = copy.deepcopy((assignment, submission))
    rubric = build(assignment, submission)["rubric"]
    assert len(rubric["criteria"]) == 7
    assert all(item["assessment"] is None for item in rubric["criteria"]), (
        "Missing or non-string criterion IDs must never stringify or guess an assessment"
    )
    assert rubric["unmatched_assessments"] == assessments
    assert (assignment, submission) == before
    return {"non_string_ids": len(ids), "missing_ids": 1, "unmatched_assessments": len(assessments)}


def exact_strings(build: Any, api: Any, httpx: Any, auth_error: Any) -> dict[str, Any]:
    ids = ["quality", "QUALITY", " quality ", "007", "7", "é", "e\u0301"]
    assignment = {"rubric": [{"id": value, "description": value} for value in ids]}
    assessments = {value: {"comments": f"Exact ID: {value}"} for value in ids[::2]}
    result = build(assignment, {"rubric_assessment": assessments})["rubric"]
    for index, item in enumerate(result["criteria"]):
        assert item["criterion"] == assignment["rubric"][index]
        assert item["assessment"] == assessments.get(ids[index]), "Criterion ID was normalized or coerced"
    assert result["unmatched_assessments"] == {}
    return {"distinct_string_ids": len(ids), "exact_joins": len(assessments)}


def source_and_output_isolation(build: Any, api: Any, httpx: Any, auth_error: Any) -> dict[str, Any]:
    assignment, submission = payloads()
    original_inputs = copy.deepcopy((assignment, submission))
    result = build(assignment, submission)
    original_result = copy.deepcopy(result)
    assert (assignment, submission) == original_inputs, "Transformation mutated a Canvas response"
    assert result["submission_comments"] == submission["submission_comments"]
    assert result["submission"]["score"] == 0
    assert result["submission"]["grade"] == ""
    assert result["submission"]["grade_matches_current_submission"] is False
    assert result["submission"]["grader_id"] == -42
    assert result["rubric"]["use_rubric_for_grading"] is False
    result["rubric"]["criteria"][0]["criterion"]["ratings"][0]["description"] = "changed"
    result["rubric"]["criteria"][0]["assessment"]["extension"]["tags"].append("changed")
    result["rubric"]["unmatched_assessments"]["duplicate"]["extension"]["tags"].append("changed")
    result["rubric"]["settings"]["extension"]["tags"].append("changed")
    result["submission_comments"][0]["author"]["display_name"] = "changed"
    result["submission_comments"][0]["attachments"][0]["filename"] = "changed"
    result["submission_comments"][0]["media_comment"]["media_id"] = "changed"
    assert (assignment, submission) == original_inputs, "Returned feedback aliases a mutable Canvas response"
    assert build(assignment, submission) == original_result
    client = RecordingClient([assignment, submission])
    assert api(client=client).submission_feedback(7, 19) == original_result
    assert (assignment, submission) == original_inputs, "API-level feedback transform mutated client objects"
    return {"nested_output_mutation_challenges": 7, "repeat_transform_stable": True, "api_inputs_unchanged": True}


def absent_and_empty(build: Any, api: Any, httpx: Any, auth_error: Any) -> dict[str, Any]:
    observations = []
    for submission in [{}, {"rubric_assessment": None}, {"rubric_assessment": {}, "submission_comments": []}]:
        result = build({}, submission)
        expected_returned = isinstance(submission.get("rubric_assessment"), dict)
        assert result["rubric"]["criteria"] is None
        assert result["rubric"]["assessment_returned"] is expected_returned
        assert result["rubric"]["unmatched_assessments"] == ({} if expected_returned else None)
        assert result["submission_comments"] == submission.get("submission_comments")
        assert result["submission"]["score"] is None
        observations.append({"assessment_returned": expected_returned, "comments": result["submission_comments"]})
    return {"observations": observations}


def error_propagation(build: Any, api: Any, httpx: Any, auth_error: Any) -> dict[str, Any]:
    request = httpx.Request("GET", "https://canvas.invalid/api/v1/courses/7/assignments/19")
    errors = [
        auth_error("Access denied to this feedback"),
        httpx.HTTPStatusError("Canvas HTTP 503", request=request, response=httpx.Response(503, request=request)),
        httpx.ReadTimeout("Canvas feedback read timed out", request=request),
    ]
    observations = []
    for stage in ("assignment", "submission"):
        for error in errors:
            assignment, _ = payloads()
            client = RecordingClient([error] if stage == "assignment" else [assignment, error])
            try:
                api(client=client).submission_feedback(7, 19)
            except Exception as actual:
                assert actual is error, "Read failure was replaced instead of propagated"
            else:
                raise AssertionError("Read failure masqueraded as successful or missing feedback")
            expected_paths = ["/api/v1/courses/7/assignments/19"]
            if stage == "submission":
                expected_paths.append(expected_paths[0] + "/submissions/self")
            assert [call[1] for call in client.calls] == expected_paths
            assert all(call[0] == "GET" for call in client.calls)
            observations.append({"stage": stage, "exception": type(error).__name__, "requests": len(client.calls)})
    return {"original_exception_identities_preserved": observations}


GROUPS = {
    "duplicate_ids": duplicate_ids,
    "invalid_ids": invalid_ids,
    "exact_strings": exact_strings,
    "source_and_output_isolation": source_and_output_isolation,
    "absent_and_empty": absent_and_empty,
    "error_propagation": error_propagation,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Frozen repository root")
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args()
    sys.path.insert(0, str(options.source / "src"))
    feedback = importlib.import_module("canvaspilot.feedback")
    api_module = importlib.import_module("canvaspilot.api")
    httpx = importlib.import_module("httpx")
    auth_error = importlib.import_module("canvaspilot.client").CanvasAuthError
    report: dict[str, Any] = {
        "source": str(options.source),
        "review_program_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": sys.version,
        "groups": [],
    }
    for name, check in GROUPS.items():
        entry: dict[str, Any] = {"name": name}
        try:
            entry["observations"] = check(feedback.build_submission_feedback, api_module.CanvasAPI, httpx, auth_error)
            entry["passed"] = True
        except Exception as error:
            entry.update(passed=False, error=repr(error), traceback=traceback.format_exc())
        report["groups"].append(entry)
    report["passed"] = all(entry["passed"] for entry in report["groups"])
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

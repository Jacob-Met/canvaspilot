"""Current-user assignment state through the existing native assignment reader."""

import copy

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.offline_demo import OfflineOnlyClient


@pytest.fixture(autouse=True)
def no_live_transport(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Assignment-state fixtures must not use a live transport")

    for name in ("broker_health", "broker_fetch", "default_profile", "default_base_url"):
        monkeypatch.setattr(f"canvaspilot.client.{name}", forbidden)
    monkeypatch.setattr("canvaspilot.client.httpx.Client", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


class AssignmentClient(OfflineOnlyClient):
    def __init__(self, rows, *, second_course=None):
        super().__init__()
        courses = [{"id": 41, "name": "Synthetic field methods"}]
        routes = {"GET /api/v1/courses/41/assignments": copy.deepcopy(rows)}
        if second_course is not None:
            courses.append({"id": 57, "name": "Synthetic studio"})
            routes["GET /api/v1/courses/57/assignments"] = copy.deepcopy(second_course)
        routes["GET /api/v1/courses"] = courses
        self.fixture = {"routes": routes}
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, copy.deepcopy(kwargs)))
        return super().request(method, path, **kwargs)


def assignment(identifier=901, **changes):
    return {
        "id": identifier,
        "name": f"Synthetic assignment {identifier}",
        "due_at": "2026-10-10T12:00:00+02:00",
        "points_possible": 0,
        "submission_types": ["online_upload"],
        "html_url": f"https://fixture.invalid/courses/41/assignments/{identifier}",
        "description": "<p>Retain the <b>original prompt</b>.</p>",
        "has_submitted_submissions": True,
        **changes,
    }


def get_row(raw, *, detail="compact"):
    client = AssignmentClient([raw])
    with CanvasAPI(client) as api:
        result = api.list_assignments(41, bucket=None, detail=detail)
    assert len(result) == 1
    assert client.calls == [(
        "GET", "/api/v1/courses/41/assignments",
        {"params": [("order_by", "due_at"), ("include[]", "submission")]},
    )]
    return result[0]


def test_separates_current_user_state_from_aggregate_submissions():
    reported = {
        "workflow_state": "unsubmitted", "submission_type": None,
        "submitted_at": None, "attempt": 0, "late": False,
        "missing": True, "excused": False, "late_policy_status": "missing",
    }
    raw = assignment(submission={**reported, "score": 0, "grade": "0",
                                 "body": "Private answer text", "attachments": [{"id": 6}]})
    result = get_row(raw)
    assert result["has_submitted_submissions"] is True
    assert result["submission"] == reported
    assert result["submission_warnings"] == []
    assert "description_text" not in result
    assert set(result) == {
        "id", "course_id", "name", "due_at", "points_possible", "submission_types",
        "html_url", "has_submitted_submissions", "submission", "submission_warnings",
    }


@pytest.mark.parametrize("supplied", [False, True])
@pytest.mark.parametrize("aggregate", [False, True])
def test_no_submission_does_not_mean_missing(supplied, aggregate):
    raw = assignment(has_submitted_submissions=aggregate, due_at="1900-01-01T00:00:00Z",
                     submission_types=["none"])
    if supplied:
        raw["submission"] = None
    row = get_row(raw)
    assert row["submission"] is None
    assert row["submission_warnings"] == []
    assert row["has_submitted_submissions"] is aggregate
    assert row["due_at"] == raw["due_at"]


def test_empty_and_explicit_unknown_fields_are_preserved():
    assert get_row(assignment(submission={}))['submission'] == {}
    fields = {name: None for name in (
        "workflow_state", "submission_type", "submitted_at", "late_policy_status",
        "attempt", "late", "missing", "excused",
    )}
    row = get_row(assignment(submission=fields))
    assert row["submission"] == fields
    assert row["submission_warnings"] == []


@pytest.mark.parametrize("value", [False, 4, "submitted", [], ["submitted"]])
def test_malformed_container_is_unknown_with_an_explicit_warning(value):
    row = get_row(assignment(submission=value))
    assert row["submission"] is None
    assert len(row["submission_warnings"]) == 1
    assert row["submission_warnings"][0].startswith("submission:")
    assert row["id"] == 901


def test_bad_optional_fields_do_not_coerce_truth_or_erase_usable_neighbors():
    row = get_row(assignment(submission={
        "workflow_state": "unsubmitted", "late": False, "excused": None,
        "missing": "false", "attempt": True, "submitted_at": [],
    }))
    assert row["submission"] == {
        "workflow_state": "unsubmitted", "late": False, "excused": None,
    }
    assert {warning.split(":", 1)[0] for warning in row["submission_warnings"]} == {
        "submission.missing", "submission.attempt", "submission.submitted_at",
    }


def test_every_malformed_known_field_has_its_own_diagnostic():
    bad = {"workflow_state": [], "submission_type": 5, "submitted_at": {},
           "late_policy_status": False, "attempt": -1, "late": 0,
           "missing": "true", "excused": []}
    row = get_row(assignment(submission=bad))
    assert row["submission"] == {}
    assert {warning.split(":", 1)[0] for warning in row["submission_warnings"]} == {
        "submission." + name for name in bad
    }
    assert len(row["submission_warnings"]) == len(bad)


@pytest.mark.parametrize("attempt", [0, 2, 9007199254740993])
def test_integer_attempt_is_not_rounded_or_replaced(attempt):
    row = get_row(assignment(submission={"attempt": attempt}))
    assert row["submission"] == {"attempt": attempt}
    assert row["submission_warnings"] == []


@pytest.mark.parametrize("attempt", [1.5, float("inf"), float("nan"), "2"])
def test_noninteger_attempt_is_not_reported_as_a_real_attempt(attempt):
    row = get_row(assignment(submission={"attempt": attempt, "missing": False}))
    assert row["submission"] == {"missing": False}
    assert len(row["submission_warnings"]) == 1


def test_supplied_flags_and_new_state_labels_are_not_reconciled_locally():
    reported = {"workflow_state": "future_reported_state", "late_policy_status": "extended",
                "missing": True, "excused": True, "late": False,
                "submitted_at": "2026-10-08T07:14:30-04:00"}
    row = get_row(assignment(submission=reported))
    assert row["submission"] == reported
    assert row["submission_warnings"] == []


def test_compact_full_and_existing_assignment_fields_remain_consistent():
    raw = assignment(submission={"workflow_state": "submitted", "attempt": 2})
    compact, full = get_row(raw), get_row(raw, detail="full")
    assert full.pop("description_text") == "Retain the original prompt ."
    assert compact == full
    for name in ("id", "name", "due_at", "points_possible", "submission_types",
                 "html_url", "has_submitted_submissions"):
        assert compact[name] == raw[name]


def test_changed_user_state_is_visible_without_changing_the_aggregate():
    client = AssignmentClient([assignment(submission={"workflow_state": "unsubmitted",
                                                      "missing": True})])
    original = copy.deepcopy(client.fixture)
    with CanvasAPI(client) as api:
        first = api.list_assignments(41)[0]
        first["submission"]["missing"] = False
        first["submission_warnings"].append("consumer annotation")
        assert client.fixture == original
        client.fixture["routes"]["GET /api/v1/courses/41/assignments"][0]["submission"] = {
            "workflow_state": "submitted", "attempt": 2, "missing": False,
        }
        second = api.list_assignments(41)[0]
    assert second["submission"] == {"workflow_state": "submitted", "attempt": 2, "missing": False}
    assert second["submission_warnings"] == []
    assert first["has_submitted_submissions"] is second["has_submitted_submissions"] is True
    assert len(client.calls) == 2


def test_sync_keeps_reported_state_with_existing_order_and_counts():
    client = AssignmentClient([
        assignment(901, due_at=None, submission={"excused": True}),
        assignment(902, due_at="2026-10-10T12:00:00Z", submission={"missing": True}),
    ], second_course=[assignment(903, due_at="2026-10-09T12:00:00Z",
                                submission={"workflow_state": "submitted", "missing": False})])
    with CanvasAPI(client) as api:
        result = api.sync_summary(limit_assignments_per_course=1)
    assert [row["id"] for row in result["upcoming_assignments"]] == [903, 902]
    assert [row["submission"] for row in result["upcoming_assignments"]] == [
        {"workflow_state": "submitted", "missing": False}, {"missing": True},
    ]
    assert result["course_summaries"][0] == {
        "course_id": 41, "status": "ok", "assignments_returned": 2,
        "assignments_included": 1, "assignments_omitted": 1, "unknown_due_dates": 1,
    }
    assert [path for _, path, _ in client.calls] == [
        "/api/v1/courses", "/api/v1/courses/41/assignments", "/api/v1/courses/57/assignments",
    ]
    assert all(dict(kwargs["params"])["bucket"] == "upcoming" for _, _, kwargs in client.calls[1:])


def test_raw_self_submission_remains_the_existing_unprojected_response():
    client = AssignmentClient([])
    raw = {"workflow_state": "submitted", "attempt": 2, "score": 0,
           "grade": "0", "body": "Original answer", "attachments": [{"id": 1}],
           "submission_comments": [{"comment": "Original feedback"}]}
    client.fixture["routes"]["GET /api/v1/courses/41/assignments/901/submissions/self"] = raw
    with CanvasAPI(client) as api:
        result = api.submission_status(41, 901)
    assert result == raw
    assert len(client.calls) == 1

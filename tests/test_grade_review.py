"""Grade review source contracts; all provider data is explicitly synthetic."""

from __future__ import annotations

from copy import deepcopy

import httpx
import pytest
from grade_review_fixture import grade_fixture

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.grade_review import GradeReviewError


@pytest.fixture
def subject(monkeypatch):
    data = grade_fixture()
    original = deepcopy(data)
    routes = {
        "GET /api/v1/users/self/profile": data["profile"],
        "GET /api/v1/courses/42": data["course"],
        "GET /api/v1/courses/42/assignment_groups": data["groups"],
    }
    requests = []

    def no_network(*args, **kwargs):
        raise AssertionError("grade fixture must not perform HTTP")

    monkeypatch.setattr(httpx.Client, "request", no_network)

    class RecordingClient(CanvasClient):
        def request(self, method, path, **kwargs):
            requests.append((method, path, deepcopy(kwargs)))
            return super().request(method, path, **kwargs)

    client = RecordingClient(fixture={"routes": routes})
    with CanvasAPI(client) as api:
        yield api, data, original, requests


def test_reported_totals_zero_rules_and_resubmission_are_distinct(subject):
    api, data, original, requests = subject
    result = api.grade_review("0042")
    assert data == original
    totals = result["enrollments"][0]["reported_totals"]
    assert totals["computed_current_score"] == 0
    assert totals["computed_final_score"] == 0
    assert totals["computed_current_grade"] is None
    assert totals["current_period_computed_current_score"] == 12.5
    assert totals["current_period_computed_final_score"] is None
    assert "unposted_current_score" not in totals
    assert "override_score" not in totals
    assert result["enrollments"][0]["context"]["totals_for_all_grading_periods_option"] is False
    groups = result["assignment_groups"]
    assert [group["id"] for group in groups] == [3, 4]
    assert groups[0]["group_weight"] == 40
    assert groups[0]["rules"] == original["groups"][0]["rules"]
    zero = groups[0]["assignments"][0]["submission"]["fields"]
    assert zero["score"] == 0 and zero["grade"] == "0"
    assert zero["entered_score"] == 1 and zero["points_deducted"] == 1
    assert zero["missing"] is False and zero["late"] is True
    revised = groups[0]["assignments"][2]["submission"]["fields"]
    assert revised["score"] == 85 and revised["attempt"] == 2
    assert revised["grade_matches_current_submission"] is False
    assert result["counts"]["excused_true"] == 1
    assert result["counts"]["missing_true"] == 0
    assert result["counts"]["late_true"] == 1
    assert result["counts"]["grade_matches_current_submission_false"] == 1
    assert result["counts"]["submissions_not_returned"] == 1
    assert result["collection_complete"] is None
    assert result["warnings"] == []
    assert [entry[:2] for entry in requests] == [
        ("GET", "/api/v1/users/self/profile"),
        ("GET", "/api/v1/courses/42"),
        ("GET", "/api/v1/courses/42/assignment_groups"),
    ]
    assert requests[1][2]["params"]["include[]"] == [
        "total_scores", "current_grading_period_scores", "grading_periods",
    ]
    assert requests[2][2]["params"] == {
        "include[]": ["assignments", "submission"], "override_assignment_dates": True,
    }
    groups[0]["rules"]["never_drop"].append(900)
    zero["score"] = 999
    assert data == original


def test_changed_input_is_read_fresh_without_recalculating_totals(subject):
    api, data, _, _ = subject
    first = api.grade_review(42)
    data["groups"][0]["group_weight"] = 0
    data["groups"][1]["group_weight"] = 120
    data["groups"][0]["assignments"][0]["submission"]["score"] = 19
    data["course"]["enrollments"][0]["computed_current_score"] = 7.25
    second = api.grade_review(42)
    assert first["enrollments"][0]["reported_totals"]["computed_current_score"] == 0
    assert second["enrollments"][0]["reported_totals"]["computed_current_score"] == 7.25
    assert second["assignment_groups"][0]["assignments"][0]["submission"]["fields"]["score"] == 19
    assert [group["group_weight"] for group in second["assignment_groups"]] == [0, 120]
    assert second["counts"] == first["counts"]


def test_course_hidden_totals_do_not_replace_or_hide_posted_assignment_values(subject):
    api, data, _, _ = subject
    data["course"]["hide_final_grades"] = True
    result = api.grade_review(42)
    assert result["totals_visibility"] == "hidden_by_course"
    assert result["enrollments"][0]["reported_totals"] == {}
    assert result["assignment_groups"][0]["assignments"][0]["submission"]["fields"]["score"] == 0


@pytest.mark.parametrize("reason", ["posted_at", "assignment_visible"])
def test_explicit_submission_visibility_excludes_even_inconsistent_neighbor_grades(subject, reason):
    api, data, _, _ = subject
    raw = data["groups"][0]["assignments"][0]["submission"]
    raw[reason] = None if reason == "posted_at" else False
    raw.update({"score": 99, "entered_score": 100, "grade": "A", "entered_grade": "A+"})
    result = api.grade_review(42)
    submission = result["assignment_groups"][0]["assignments"][0]["submission"]
    assert submission["grade_visibility"] == ("not_posted" if reason == "posted_at" else "assignment_not_visible")
    assert not {"score", "grade", "entered_grade", "entered_score", "points_deducted"} & submission["fields"].keys()
    assert submission["fields"]["missing"] is False


def test_absent_null_and_zero_keep_different_meanings(subject):
    api, data, _, _ = subject
    data["course"]["enrollments"][0].pop("computed_current_score")
    data["course"]["enrollments"][0]["computed_final_score"] = None
    assignments = data["groups"][0]["assignments"]
    assignments[0]["submission"].pop("posted_at")
    assignments[1]["submission"] = None
    data["groups"][1].pop("assignments")
    result = api.grade_review(42)
    totals = result["enrollments"][0]["reported_totals"]
    assert "computed_current_score" not in totals and totals["computed_final_score"] is None
    assert result["assignment_groups"][0]["assignments"][0]["submission"]["fields"]["score"] == 0
    assert result["assignment_groups"][0]["assignments"][1]["submission_state"] == "null"
    assert result["assignment_groups"][1]["assignments_state"] == "not_returned"
    assert result["assignment_groups"][1]["assignments"] is None
    assert result["counts"]["groups_without_assignment_list"] == 1
    assert result["counts"]["submissions_null"] == 1


@pytest.mark.parametrize("target", ["enrollments", "grading_periods"])
@pytest.mark.parametrize("kind", ["absent", "null", "empty"])
def test_missing_course_context_is_not_a_zero_grade(subject, target, kind):
    api, data, _, _ = subject
    if kind == "absent":
        data["course"].pop(target)
    else:
        data["course"][target] = None if kind == "null" else []
    result = api.grade_review(42)
    assert result[target] == ([] if kind == "empty" else None)
    assert result[f"{target}_state"] == {"absent": "not_returned", "null": "null", "empty": "returned"}[kind]


@pytest.mark.parametrize("value", [False, True, 0, -2, 4.2, "42/../99", "", "４２", None])
def test_invalid_course_id_refuses_before_any_source_request(subject, value):
    api, _, _, requests = subject
    with pytest.raises(GradeReviewError):
        api.grade_review(value)
    assert requests == []


@pytest.mark.parametrize("case", [
    "course", "enrollment_user", "assignment_course", "assignment_group",
    "submission_assignment", "submission_user", "duplicate_group", "duplicate_assignment",
])
def test_mismatched_or_ambiguous_identity_refuses_the_whole_report(subject, case):
    api, data, _, _ = subject
    assignment = data["groups"][0]["assignments"][0]
    if case == "course":
        data["course"]["id"] = 99
    elif case == "enrollment_user":
        data["course"]["enrollments"][0]["user_id"] = 99
    elif case == "assignment_course":
        assignment["course_id"] = 99
    elif case == "assignment_group":
        assignment["assignment_group_id"] = 99
    elif case == "submission_assignment":
        assignment["submission"]["assignment_id"] = 99
    elif case == "submission_user":
        assignment["submission"]["user_id"] = 99
    elif case == "duplicate_group":
        data["groups"].append(deepcopy(data["groups"][0]))
    else:
        data["groups"][0]["assignments"].append(deepcopy(assignment))
    before = deepcopy(data)
    with pytest.raises(GradeReviewError):
        api.grade_review(42)
    assert data == before


@pytest.mark.parametrize("case", [
    "hidden_type", "restricted_type", "restricted_true", "visible_type", "posted_type",
    "enrollments", "periods", "group", "assignments", "assignment", "submission", "rules",
])
def test_malformed_structure_or_visibility_is_not_an_empty_success(subject, case):
    api, data, _, _ = subject
    if case == "hidden_type":
        data["course"]["hide_final_grades"] = "false"
    elif case == "restricted_type":
        data["course"]["access_restricted_by_date"] = "false"
    elif case == "restricted_true":
        data["course"]["access_restricted_by_date"] = True
    elif case == "visible_type":
        data["groups"][0]["assignments"][0]["submission"]["assignment_visible"] = 1
    elif case == "posted_type":
        data["groups"][0]["assignments"][0]["submission"]["posted_at"] = False
    elif case == "enrollments":
        data["course"]["enrollments"] = {}
    elif case == "periods":
        data["course"]["grading_periods"] = "unavailable"
    elif case == "group":
        data["groups"][0] = None
    elif case == "assignments":
        data["groups"][0]["assignments"] = {}
    elif case == "assignment":
        data["groups"][0]["assignments"][0] = None
    elif case == "submission":
        data["groups"][0]["assignments"][0]["submission"] = []
    else:
        data["groups"][0]["rules"] = []
    with pytest.raises(GradeReviewError):
        api.grade_review(42)


def test_invalid_optional_fields_warn_without_creating_scores(subject):
    api, data, _, _ = subject
    data["groups"][0]["assignments"][0]["submission"].update({"score": float("nan"), "missing": 1})
    data["course"]["enrollments"][0]["computed_current_score"] = True
    data["groups"][0]["rules"]["drop_lowest"] = -1
    data["groups"][0]["assignments"][0]["points_possible"] = float("inf")
    result = api.grade_review(42)
    assert len(result["warnings"]) == 5
    assert "computed_current_score" not in result["enrollments"][0]["reported_totals"]
    row = result["assignment_groups"][0]["assignments"][0]
    assert "score" not in row["submission"]["fields"]
    assert "missing" not in row["submission"]["fields"]
    assert "points_possible" not in row["fields"]
    assert result["counts"]["missing_true"] == 0


def test_empty_assignment_groups_remain_an_observed_empty_list(subject):
    api, data, _, _ = subject
    data["groups"].clear()
    result = api.grade_review(42)
    assert result["assignment_groups"] == []
    assert result["counts"]["groups_returned"] == 0
    assert result["counts"]["assignments_returned"] == 0
    assert result["collection_complete"] is None


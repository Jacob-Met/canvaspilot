"""Read a student's Canvas-reported course grades without recalculating them."""

from __future__ import annotations

import re
from collections.abc import Callable
from math import isfinite
from typing import Any

from canvaspilot.client import CanvasClient


class GradeReviewError(ValueError):
    """The supplied Canvas data cannot be reviewed without guessing its meaning."""


_CHECKS: dict[str, Callable[[Any], bool]] = {
    "text": lambda value: isinstance(value, str),
    "bool": lambda value: type(value) is bool,
    "number": lambda value: type(value) is int or (type(value) is float and isfinite(value)),
    "count": lambda value: type(value) is int and value >= 0,
    "id": lambda value: type(value) in (int, str) and bool(re.fullmatch(r"[0-9]+", str(value)))
    and any(character != "0" for character in str(value)),
    "texts": lambda value: isinstance(value, list) and all(isinstance(item, str) for item in value),
    "ids": lambda value: isinstance(value, list) and all(_CHECKS["id"](item) for item in value),
}

_COURSE_FIELDS = {
    "id": "id", "name": "text", "course_code": "text", "workflow_state": "text",
    "hide_final_grades": "bool", "apply_assignment_group_weights": "bool",
    "has_grading_periods": "bool", "has_weighted_grading_periods": "bool",
    "grading_standard_id": "id", "time_zone": "text", "access_restricted_by_date": "bool",
}
_ENROLLMENT_FIELDS = {
    "type": "text", "role": "text", "role_id": "id", "user_id": "id",
    "enrollment_state": "text", "has_grading_periods": "bool",
    "totals_for_all_grading_periods_option": "bool",
    "current_grading_period_id": "id", "current_grading_period_title": "text",
}
_TOTAL_FIELDS = {
    "computed_current_score": "number", "computed_final_score": "number",
    "computed_current_grade": "text", "computed_final_grade": "text",
    "computed_current_letter_grade": "text",
    "current_period_computed_current_score": "number",
    "current_period_computed_final_score": "number",
    "current_period_computed_current_grade": "text",
    "current_period_computed_final_grade": "text",
}
_ASSIGNMENT_FIELDS = {
    "id": "id", "course_id": "id", "assignment_group_id": "id", "name": "text",
    "position": "count", "due_at": "text", "points_possible": "number",
    "grading_type": "text", "submission_types": "texts", "html_url": "text",
    "published": "bool", "omit_from_final_grade": "bool", "post_manually": "bool",
    "locked_for_user": "bool", "lock_explanation": "text",
}
_SUBMISSION_FIELDS = {
    "id": "id", "assignment_id": "id", "user_id": "id", "attempt": "count",
    "workflow_state": "text", "submission_type": "text", "submitted_at": "text",
    "graded_at": "text", "posted_at": "text", "cached_due_date": "text",
    "grade": "text", "score": "number", "entered_grade": "text",
    "entered_score": "number", "points_deducted": "number", "seconds_late": "number",
    "grade_matches_current_submission": "bool", "assignment_visible": "bool",
    "excused": "bool", "missing": "bool", "late": "bool", "late_policy_status": "text",
    "redo_request": "bool",
}
_GRADE_FIELDS = {"grade", "score", "entered_grade", "entered_score", "points_deducted"}


def _id(value: Any, path: str) -> str:
    if not _CHECKS["id"](value):
        raise GradeReviewError(f"{path}: expected a positive numeric Canvas ID")
    return str(value).lstrip("0")


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GradeReviewError(f"{path}: expected a Canvas object")
    return value


def _bound_id(row: dict[str, Any], key: str, expected: str, path: str) -> None:
    if key in row and row[key] is not None and _id(row[key], f"{path}.{key}") != expected:
        raise GradeReviewError(f"{path}.{key}: Canvas returned a different {key}")


def _fields(
    row: dict[str, Any], definitions: dict[str, str], path: str, warnings: list[str],
) -> dict[str, Any]:
    result = {}
    for key, kind in definitions.items():
        if key not in row:
            continue
        value = row[key]
        if value is None or _CHECKS[kind](value):
            result[key] = list(value) if isinstance(value, list) else value
        else:
            warnings.append(f"{path}.{key}: invalid value omitted; field remains unknown")
    return result


def _submission(
    assignment: dict[str, Any], assignment_id: str, user_id: str,
    path: str, warnings: list[str],
) -> tuple[str, dict[str, Any] | None]:
    if "submission" not in assignment:
        return "not_returned", None
    raw = assignment["submission"]
    if raw is None:
        return "null", None
    raw = _object(raw, path)
    _bound_id(raw, "assignment_id", assignment_id, path)
    _bound_id(raw, "user_id", user_id, path)
    for key, kind in (("assignment_visible", "bool"), ("posted_at", "text")):
        if key in raw and raw[key] is not None and not _CHECKS[kind](raw[key]):
            raise GradeReviewError(f"{path}.{key}: invalid visibility metadata")
    fields = _fields(raw, _SUBMISSION_FIELDS, path, warnings)

    # An explicit Canvas visibility boundary must not be undone by a stale or
    # inconsistent neighboring score. Missing posting metadata proves nothing.
    if fields.get("assignment_visible") is False:
        visibility = "assignment_not_visible"
    elif "posted_at" in fields and fields["posted_at"] is None:
        visibility = "not_posted"
    else:
        visibility = "reported_fields"
    if visibility != "reported_fields":
        fields = {key: value for key, value in fields.items() if key not in _GRADE_FIELDS}
    return "returned", {"grade_visibility": visibility, "fields": fields}


def grade_review(client: CanvasClient, course_id: int | str) -> dict[str, Any]:
    """Read current-user totals and returned assignment groups; never compute a grade."""
    cid = _id(course_id, "course_id")
    profile = _object(client.request("GET", "/api/v1/users/self/profile"), "profile")
    uid = _id(profile.get("id"), "profile.id")
    course = _object(client.request(
        "GET", f"/api/v1/courses/{cid}",
        params={"include[]": ["total_scores", "current_grading_period_scores", "grading_periods"]},
    ), "course")
    if _id(course.get("id"), "course.id") != cid:
        raise GradeReviewError("course.id: Canvas returned a different course")
    for key in ("hide_final_grades", "access_restricted_by_date"):
        if key in course and course[key] is not None and type(course[key]) is not bool:
            raise GradeReviewError(f"course.{key}: invalid visibility metadata")
    if course.get("access_restricted_by_date") is True:
        raise GradeReviewError("Canvas reports that this course is restricted by dates")

    warnings: list[str] = []
    course_fields = _fields(course, _COURSE_FIELDS, "course", warnings)
    hidden = course_fields.get("hide_final_grades") is True
    enrollments = None
    enrollment_state = "not_returned"
    if "enrollments" in course:
        enrollment_state = "null" if course["enrollments"] is None else "returned"
        if course["enrollments"] is not None:
            if not isinstance(course["enrollments"], list):
                raise GradeReviewError("course.enrollments: expected a list or null")
            enrollments = []
            for index, value in enumerate(course["enrollments"]):
                path = f"course.enrollments[{index}]"
                row = _object(value, path)
                _bound_id(row, "user_id", uid, path)
                context = _fields(row, _ENROLLMENT_FIELDS, path, warnings)
                # Deliberately exclude every unposted/override score. Current and
                # final values retain their original Canvas names and nulls.
                scores = {} if hidden else _fields(row, _TOTAL_FIELDS, path, warnings)
                enrollments.append({"context": context, "reported_totals": scores})
    grading_periods = None
    period_state = "not_returned"
    if "grading_periods" in course:
        period_state = "null" if course["grading_periods"] is None else "returned"
        if course["grading_periods"] is not None:
            if not isinstance(course["grading_periods"], list):
                raise GradeReviewError("course.grading_periods: expected a list or null")
            grading_periods = [
                _fields(_object(row, f"course.grading_periods[{index}]"), {
                    "id": "id", "title": "text", "start_date": "text", "end_date": "text",
                    "close_date": "text", "weight": "number", "workflow_state": "text",
                }, f"course.grading_periods[{index}]", warnings)
                for index, row in enumerate(course["grading_periods"])
            ]

    rows = client.get_paginated(
        f"/api/v1/courses/{cid}/assignment_groups",
        params={"include[]": ["assignments", "submission"], "override_assignment_dates": True},
    )
    if not isinstance(rows, list):
        raise GradeReviewError("assignment_groups: expected returned list")
    groups = []
    group_ids: set[str] = set()
    assignment_ids: set[str] = set()
    counts = {
        "groups_returned": len(rows), "assignments_returned": 0,
        "groups_without_assignment_list": 0, "submissions_not_returned": 0,
        "submissions_null": 0, "explicitly_not_posted": 0,
        "explicitly_not_visible": 0, "excused_true": 0, "missing_true": 0,
        "late_true": 0, "grade_matches_current_submission_false": 0,
    }
    for index, value in enumerate(rows):
        path = f"assignment_groups[{index}]"
        row = _object(value, path)
        gid = _id(row.get("id"), f"{path}.id")
        if gid in group_ids:
            raise GradeReviewError(f"{path}.id: duplicate assignment group")
        group_ids.add(gid)
        group = _fields(row, {
            "id": "id", "name": "text", "position": "count", "group_weight": "number",
        }, path, warnings)
        if "rules" in row:
            rules = row["rules"]
            group["rules"] = None if rules is None else _fields(
                _object(rules, f"{path}.rules"),
                {"drop_lowest": "count", "drop_highest": "count", "never_drop": "ids"},
                f"{path}.rules", warnings,
            )
        group["assignments_state"] = (
            "not_returned" if "assignments" not in row
            else "null" if row["assignments"] is None else "returned"
        )
        group["assignments"] = None
        if group["assignments_state"] != "returned":
            counts["groups_without_assignment_list"] += 1
        else:
            if not isinstance(row["assignments"], list):
                raise GradeReviewError(f"{path}.assignments: expected a list or null")
            assignments = []
            for offset, item in enumerate(row["assignments"]):
                item_path = f"{path}.assignments[{offset}]"
                item = _object(item, item_path)
                aid = _id(item.get("id"), f"{item_path}.id")
                if aid in assignment_ids:
                    raise GradeReviewError(f"{item_path}.id: duplicate assignment")
                assignment_ids.add(aid)
                _bound_id(item, "course_id", cid, item_path)
                _bound_id(item, "assignment_group_id", gid, item_path)
                fields = _fields(item, _ASSIGNMENT_FIELDS, item_path, warnings)
                state, submission = _submission(
                    item, aid, uid, f"{item_path}.submission", warnings,
                )
                assignments.append({
                    "fields": fields, "submission_state": state, "submission": submission,
                })
                counts["assignments_returned"] += 1
                if state == "not_returned":
                    counts["submissions_not_returned"] += 1
                elif state == "null":
                    counts["submissions_null"] += 1
                else:
                    assert submission is not None
                    detail = submission["fields"]
                    counts["explicitly_not_posted"] += submission["grade_visibility"] == "not_posted"
                    counts["explicitly_not_visible"] += submission["grade_visibility"] == "assignment_not_visible"
                    for flag in ("excused", "missing", "late"):
                        counts[f"{flag}_true"] += detail.get(flag) is True
                    counts["grade_matches_current_submission_false"] += (
                        detail.get("grade_matches_current_submission") is False
                    )
            group["assignments"] = assignments
        groups.append(group)

    return {
        "course": course_fields,
        "authenticated_user_id": profile["id"],
        "totals_visibility": "hidden_by_course" if hidden else "reported_fields_only",
        "enrollments_state": enrollment_state, "enrollments": enrollments,
        "grading_periods_state": period_state, "grading_periods": grading_periods,
        "assignment_scope": "all_returned_assignment_groups",
        "assignment_groups": groups,
        "counts": counts,
        "collection_complete": None,
        "reader_source": "CanvasClient.get_paginated",
        "upstream_response_shape": "not_observed",
        "warnings": warnings,
    }


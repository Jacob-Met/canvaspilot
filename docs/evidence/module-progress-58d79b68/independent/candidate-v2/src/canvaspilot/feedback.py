"""Join a student's Canvas submission feedback to its rubric without grading it."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

ASSIGNMENT_FIELDS = (
    "id",
    "course_id",
    "name",
    "html_url",
    "due_at",
    "points_possible",
)
SUBMISSION_FIELDS = (
    "id",
    "assignment_id",
    "user_id",
    "submission_type",
    "attempt",
    "workflow_state",
    "submitted_at",
    "graded_at",
    "posted_at",
    "grader_id",
    "score",
    "grade",
    "grade_matches_current_submission",
    "excused",
    "late",
    "missing",
    "redo_request",
)


def build_submission_feedback(
    assignment: dict[str, Any], submission: dict[str, Any]
) -> dict[str, Any]:
    """Preserve reported grades, attempts, rubric evidence, and comment authors.

    A false grade_matches_current_submission means grading preceded the latest
    resubmission. Neither that grade nor the rubric is reinterpreted here.
    Missing values stay unknown; an empty assessment/comment list stays empty.
    """
    if not isinstance(assignment, dict) or not isinstance(submission, dict):
        # An invalid response value retains the same error contract as its fields.
        raise ValueError(  # noqa: TRY004
            "Canvas returned malformed assignment or submission feedback"
        )

    criteria = assignment.get("rubric")
    assessments = submission.get("rubric_assessment")
    comments = submission.get("submission_comments")
    if criteria is not None and (
        not isinstance(criteria, list)
        or any(not isinstance(criterion, dict) for criterion in criteria)
    ):
        raise ValueError("Canvas returned malformed rubric criteria")
    if assessments is not None and (
        not isinstance(assessments, dict)
        or any(
            value is not None and not isinstance(value, dict)
            for value in assessments.values()
        )
    ):
        raise ValueError("Canvas returned malformed rubric assessment")
    if comments is not None and (
        not isinstance(comments, list)
        or any(not isinstance(comment, dict) for comment in comments)
    ):
        raise ValueError("Canvas returned malformed submission comments")

    # Canvas documents string criterion IDs. Array order, descriptions, and
    # duplicate IDs cannot establish which criterion an assessment belongs to.
    counts = Counter(
        criterion["id"]
        for criterion in criteria or []
        if isinstance(criterion.get("id"), str) and criterion["id"]
    )
    joined = None
    remaining = dict(assessments) if assessments is not None else None
    if criteria is not None:
        joined = []
        for criterion in criteria:
            criterion_id = criterion.get("id")
            assessment = None
            if (
                isinstance(criterion_id, str)
                and counts[criterion_id] == 1
                and remaining is not None
            ):
                assessment = remaining.pop(criterion_id, None)
            joined.append({"criterion": criterion, "assessment": assessment})

    # Retain all criterion/assessment and comment fields, including media-only
    # comments and future Canvas metadata, without sharing mutable fixture data.
    return deepcopy(
        {
            "assignment": {field: assignment.get(field) for field in ASSIGNMENT_FIELDS},
            "submission": {field: submission.get(field) for field in SUBMISSION_FIELDS},
            "rubric": {
                "use_rubric_for_grading": assignment.get("use_rubric_for_grading"),
                "settings": assignment.get("rubric_settings"),
                "assessment_returned": assessments is not None,
                "criteria": joined,
                "unmatched_assessments": remaining,
            },
            "submission_comments": comments,
        }
    )

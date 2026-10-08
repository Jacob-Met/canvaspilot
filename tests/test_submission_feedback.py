"""Feedback must preserve Canvas evidence without inventing a current grade."""

import copy
import json
from pathlib import Path

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

FIXTURE = Path(__file__).parent / "fixtures" / "submission_feedback.json"


@pytest.fixture
def source():
    return json.loads(FIXTURE.read_text())


def report(source):
    routes = {
        "GET /api/v1/courses/41/assignments/902": source["assignment"],
        "GET /api/v1/courses/41/assignments/902/submissions/self": source["submission"],
    }
    with CanvasAPI(CanvasClient(fixture={"routes": routes})) as api:
        return api.submission_feedback(41, 902)


def test_feedback_associates_by_id_and_retains_unmatched_assessment(source):
    feedback = report(source)
    criteria = feedback["rubric"]["criteria"]
    assert [row["criterion"]["id"] for row in criteria] == [
        "evidence",
        "reflection",
        "revision",
    ]
    assert criteria[0]["assessment"] == {
        "points": 3,
        "rating_id": "developing",
        "comments": "Explain the source.",
    }
    assert criteria[1]["assessment"] == {
        "points": 0,
        "rating_id": "not-yet",
        "comments": "",
    }
    assert criteria[2]["assessment"] is None
    assert feedback["rubric"]["unmatched_assessments"] == {
        "removed": {"points": 2, "comments": "Earlier rubric criterion."}
    }
    source["assignment"]["rubric"].reverse()
    reversed_report = report(source)
    assert reversed_report["rubric"]["criteria"] == list(reversed(criteria))


def test_feedback_keeps_grade_attempt_and_advisory_metadata(source):
    feedback = report(source)
    submission = feedback["submission"]
    assert submission["score"] == 0
    assert submission["grade"] == "0"
    assert submission["attempt"] == 2
    assert submission["grade_matches_current_submission"] is False
    assert submission["grader_id"] == -19
    assert submission["graded_at"] == "2026-10-07T15:00:00Z"
    assert submission["submitted_at"] == "2026-10-08T17:00:00Z"
    assert submission["posted_at"] == "2026-10-07T15:10:00Z"
    rubric = feedback["rubric"]
    assert rubric["use_rubric_for_grading"] is False
    assert rubric["settings"] == {"title": "Revision guide", "points_possible": 12}
    assert rubric["criteria"][0]["criterion"]["criterion_use_range"] is True
    assert rubric["criteria"][1]["criterion"]["ignore_for_scoring"] is True
    assert feedback["assignment"]["points_possible"] == 20
    assert "total" not in rubric


def test_feedback_keeps_all_submission_comments_and_media(source):
    feedback = report(source)
    assert (
        feedback["submission_comments"] == source["submission"]["submission_comments"]
    )
    assert feedback["submission_comments"][1]["media_comment"]["media_type"] == "audio"
    assert "instructor_comments" not in feedback


@pytest.mark.parametrize("missing", [True, False], ids=["omitted", "null"])
def test_unknown_feedback_remains_unknown(source, missing):
    source["submission"] = (
        {}
        if missing
        else {"rubric_assessment": None, "submission_comments": None, "score": None}
    )
    source["assignment"] = {} if missing else {"rubric": None}
    feedback = report(source)
    assert feedback["submission"]["score"] is None
    assert feedback["submission"]["grade_matches_current_submission"] is None
    assert feedback["submission"]["attempt"] is None
    assert feedback["rubric"]["use_rubric_for_grading"] is None
    assert feedback["rubric"]["criteria"] is None
    assert feedback["rubric"]["assessment_returned"] is False
    assert feedback["rubric"]["unmatched_assessments"] is None
    assert feedback["submission_comments"] is None


def test_explicit_empty_feedback_is_distinct_from_unknown(source):
    source["assignment"]["rubric"] = []
    source["submission"]["rubric_assessment"] = {}
    source["submission"]["submission_comments"] = []
    feedback = report(source)
    assert feedback["rubric"]["criteria"] == []
    assert feedback["rubric"]["unmatched_assessments"] == {}
    assert feedback["rubric"]["assessment_returned"] is True
    assert feedback["submission_comments"] == []


def test_comment_only_assessment_does_not_invent_points_or_grade(source):
    source["submission"] = {"rubric_assessment": {"evidence": {"comments": "Cite it."}}}
    feedback = report(source)
    assert feedback["rubric"]["criteria"][0]["assessment"] == {"comments": "Cite it."}
    assert feedback["submission"]["grade"] is None
    assert feedback["submission"]["score"] is None
    assert feedback["submission"]["grade_matches_current_submission"] is None


def test_duplicate_missing_and_wrong_type_ids_never_guess(source):
    source["assignment"]["rubric"] = [
        {"id": "same", "description": "First"},
        {"id": "same", "description": "Second"},
        {"description": "Missing ID"},
        {"id": 5, "description": "Non-string ID"},
        {"id": "0", "description": "Exact zero ID"},
    ]
    source["submission"]["rubric_assessment"] = {
        "same": {"points": 4},
        "5": {"points": 1},
        "0": {"points": 0},
    }
    feedback = report(source)
    rows = feedback["rubric"]["criteria"]
    assert [row["assessment"] for row in rows[:4]] == [None, None, None, None]
    assert rows[4]["assessment"] == {"points": 0}
    assert feedback["rubric"]["unmatched_assessments"] == {
        "same": {"points": 4},
        "5": {"points": 1},
    }


def test_assessment_without_rubric_is_retained(source):
    del source["assignment"]["rubric"]
    feedback = report(source)
    assert feedback["rubric"]["criteria"] is None
    assert (
        feedback["rubric"]["unmatched_assessments"]
        == source["submission"]["rubric_assessment"]
    )


def test_report_does_not_mutate_or_share_source_objects(source):
    original = copy.deepcopy(source)
    feedback = report(source)
    feedback["rubric"]["criteria"][0]["criterion"]["ratings"][0]["description"] = (
        "Changed"
    )
    feedback["rubric"]["criteria"][0]["assessment"]["points"] = 99
    feedback["rubric"]["unmatched_assessments"]["removed"]["points"] = 99
    feedback["submission_comments"][0]["author"]["display_name"] = "Changed"
    assert source == original


@pytest.mark.parametrize(
    ("part", "field", "value"),
    [
        ("assignment", None, []),
        ("submission", None, []),
        ("assignment", "rubric", {}),
        ("assignment", "rubric", [None]),
        ("submission", "rubric_assessment", []),
        ("submission", "submission_comments", {}),
    ],
)
def test_malformed_feedback_is_not_presented_as_empty(source, part, field, value):
    if field is None:
        source[part] = value
    else:
        source[part][field] = value
    with pytest.raises(ValueError, match="Canvas returned malformed"):
        report(source)

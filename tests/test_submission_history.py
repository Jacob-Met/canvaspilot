"""Submission-history semantics through the production projection and API."""

from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient
from canvaspilot.submission_history import build_submission_history


def authored_assignment():
    return {
        "id": 902, "course_id": 71, "name": "Vectors & <proof> λ",
        "html_url": "https://history.invalid/courses/71/assignments/902",
        "due_at": None, "points_possible": 20,
        "rubric": [{"id": "not-part-of-this-projection"}],
    }


def authored_submission():
    return {
        "id": 501, "assignment_id": 902, "user_id": 19, "attempt": 3,
        "workflow_state": "submitted", "submitted_at": "2026-10-07T14:00:00Z",
        "score": 12, "grade": "12", "grade_matches_current_submission": False,
        "future_metadata": {"original": ["do not reinterpret"]},
        "submission_comments": [
            {"id": 8, "author_id": 19, "author_name": "Student", "attempt": 3,
             "comment": "Revision ready <b>literal</b> λ"},
            {"id": 9, "author_id": 81, "author_name": "Reader", "comment": None,
             "media_comment": {"media_type": "audio", "url": "https://media.invalid/c"}},
        ],
        "submission_history": [
            {"attempt": 2, "submission_type": "online_upload", "score": 0,
             "grade": "0", "grade_matches_current_submission": True,
             "attachments": [{"id": 508, "filename": "v2-λ.pdf", "size": 42,
                              "url": "https://files.invalid/v2?opaque=retained"}],
             "submission_comments": [{"id": 6, "attempt": 2, "comment": "Earlier only"}]},
            {"attempt": 1, "submission_type": "online_text_entry", "score": None,
             "body": "<p>λ &lt;theta&gt; “quoted”\nsecond line</p>",
             "late": False, "missing": None},
            {"attempt": 2, "submission_type": "online_url",
             "url": "https://work.invalid/revision?x=1&y=2",
             "graded_at": "2026-10-06T13:00:00Z", "vendor": {"revision": "other"}},
        ],
    }


def test_current_and_each_returned_version_stay_distinct():
    assignment, submission = authored_assignment(), authored_submission()
    report = build_submission_history(assignment, submission)
    assert report["assignment"] == {
        "id": 902, "course_id": 71, "name": "Vectors & <proof> λ",
        "html_url": "https://history.invalid/courses/71/assignments/902",
        "due_at": None, "points_possible": 20,
    }
    assert report["current_submission"] == {
        "id": 501, "assignment_id": 902, "user_id": 19, "attempt": 3,
        "workflow_state": "submitted", "submitted_at": "2026-10-07T14:00:00Z",
        "score": 12, "grade": "12", "grade_matches_current_submission": False,
        "future_metadata": {"original": ["do not reinterpret"]},
    }
    assert report["history"] == {
        "returned": True, "records": submission["submission_history"],
    }
    assert [row["attempt"] for row in report["history"]["records"]] == [2, 1, 2]
    assert report["submission_comments"] == submission["submission_comments"]
    assert "grade" not in report["history"]["records"][1]
    assert "submission_comments" not in report["history"]["records"][2]


@pytest.mark.parametrize("association", [{}, {"submission_history": None}])
def test_unavailable_history_does_not_imply_no_attempts(association):
    result = build_submission_history({}, {"attempt": 900, **association})
    assert result["assignment"] == {
        "id": None, "course_id": None, "name": None,
        "html_url": None, "due_at": None, "points_possible": None,
    }
    assert result["current_submission"] == {"attempt": 900}
    assert result["history"] == {"returned": False, "records": None}
    assert result["submission_comments"] is None


def test_returned_empty_history_and_comments_remain_empty():
    result = build_submission_history(
        {}, {"attempt": 5, "submission_history": [], "submission_comments": []},
    )
    assert result["history"] == {"returned": True, "records": []}
    assert result["submission_comments"] == []
    assert result["current_submission"] == {"attempt": 5}


def test_all_nested_output_is_detached_from_inputs():
    assignment, submission = authored_assignment(), authored_submission()
    before = deepcopy((assignment, submission))
    report = build_submission_history(assignment, submission)
    report["history"]["records"][0]["attachments"][0]["filename"] = "changed"
    report["submission_comments"][1]["media_comment"]["url"] = "changed"
    report["current_submission"]["future_metadata"]["original"].append("changed")
    assert (assignment, submission) == before
    submission["submission_history"][1]["body"] = "later input mutation"
    assert report["history"]["records"][1]["body"] != "later input mutation"


@pytest.mark.parametrize("assignment,submission", [
    (None, {}), ([], {}), ({}, None), ({}, []),
    ({}, {"submission_history": {}}),
    ({}, {"submission_history": [None]}),
    ({}, {"submission_history": [{}, 2]}),
    ({}, {"submission_history": "unavailable"}),
    ({}, {"submission_comments": {}}),
    ({}, {"submission_comments": [False]}),
    ({}, {"submission_comments": [{}, []]}),
])
def test_malformed_response_structure_refuses_the_report(assignment, submission):
    with pytest.raises(ValueError, match="Canvas returned malformed"):
        build_submission_history(assignment, submission)


class ForbiddenClient:
    def request(self, *_args, **_kwargs):
        raise AssertionError("Invalid IDs must fail before any request")


@pytest.mark.parametrize("invalid", [
    None, True, False, 0, -1, 2.5, "", " ", "0", "000", "+1", "-1", "1.0",
    "1e2", "1/../../users", "1?include[]=read_status", "１２", "١٢",
])
@pytest.mark.parametrize("position", ["course", "assignment"])
def test_invalid_identifiers_do_not_reach_transport(invalid, position):
    api = CanvasAPI(ForbiddenClient())
    args = (invalid, 902) if position == "course" else (71, invalid)
    with pytest.raises(ValueError, match="positive numeric Canvas ID"):
        api.submission_history(*args)


def make_api(respond):
    client = CanvasClient(
        base_url="https://history.invalid", token="synthetic-history-token",
        profile=Path("/unused-history-fixture"),
    )
    client._http = httpx.Client(
        base_url=client.base_url, transport=httpx.MockTransport(respond),
        trust_env=False,
    )
    return CanvasAPI(client)


def test_actual_api_only_requests_the_assignment_and_self_history():
    requests = []

    def respond(request):
        requests.append(request)
        payload = authored_submission() if request.url.path.endswith("/self") else authored_assignment()
        return httpx.Response(200, json=payload)

    api = make_api(respond)
    try:
        report = api.submission_history("00071", 902)
    finally:
        api.client.close()
    assert report["history"]["records"][0]["score"] == 0
    assert [(r.method, r.url.path) for r in requests] == [
        ("GET", "/api/v1/courses/71/assignments/902"),
        ("GET", "/api/v1/courses/71/assignments/902/submissions/self"),
    ]
    assert requests[0].url.params.get_list("include[]") == []
    assert requests[1].url.params.get_list("include[]") == [
        "submission_history", "submission_comments",
    ]
    assert all(r.content == b"" for r in requests)
    assert all("read_status" not in str(r.url) for r in requests)


@pytest.mark.parametrize("failing_request,status,error", [
    (1, 403, CanvasAuthError), (1, 500, httpx.HTTPStatusError),
    (2, 403, CanvasAuthError), (2, 503, httpx.HTTPStatusError),
])
def test_request_errors_never_become_empty_history(failing_request, status, error):
    calls = []

    def respond(request):
        calls.append(request)
        if len(calls) == failing_request:
            return httpx.Response(status, json={"errors": [{"message": "authored refusal"}]})
        return httpx.Response(200, json=authored_assignment())

    api = make_api(respond)
    try:
        with pytest.raises(error):
            api.submission_history(71, 902)
    finally:
        api.client.close()
    assert len(calls) == failing_request

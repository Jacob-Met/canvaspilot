"""Exercise Canvas parameter encoding through the real loopback broker handler."""

from __future__ import annotations

import copy
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from canvaspilot import client as client_mod
from canvaspilot import session_broker
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient, broker_fetch


@pytest.fixture
def broker(monkeypatch):
    # The proxy-env defect has its own fix; these tests isolate serialization.
    for name in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    ):
        monkeypatch.delenv(name, raising=False)

    jobs = []

    def echo(job):
        jobs.append(job)
        return {"ok": True, "response": {"status": 200, "json": job}}

    # Only the browser worker is replaced. Client requests still cross HTTP and
    # JSON encoding before the production Handler dispatches their Canvas job.
    monkeypatch.setattr(session_broker, "_call", echo)
    monkeypatch.setattr(session_broker.STATE, "read_only", False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), session_broker.Handler)
    monkeypatch.setattr(client_mod, "BROKER_PORT", server.server_address[1])
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True,
    )
    thread.start()
    try:
        yield jobs
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def query(job):
    return parse_qs(urlsplit(job["path"]).query, keep_blank_values=True)


def test_assignment_submission_include_reaches_canvas(broker, monkeypatch):
    submission = {"id": 81, "workflow_state": "submitted", "score": 9}

    def assignment(job):
        broker.append(job)
        response = {"id": 7, "name": "Assignment"}
        if "submission" in query(job).get("include[]", []):
            response["submission"] = submission
        return {"ok": True, "response": {"status": 200, "json": response}}

    monkeypatch.setattr(session_broker, "_call", assignment)
    with CanvasAPI(CanvasClient(token="")) as api:
        result = api.get_assignment(1, 7)

    assert result["submission"] == submission
    assert query(broker[0])["include[]"] == ["submission"]


def test_course_keeps_each_requested_include(broker):
    with CanvasAPI(CanvasClient(token="")) as api:
        api.get_course(1)

    assert query(broker[0])["include[]"] == [
        "syllabus_body", "term", "total_scores",
    ]


def test_session_includes_survive_malformed_proxy_environment(broker, monkeypatch):
    # The merged proxy correction and list encoder must work in one request.
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "[::1]")
    with CanvasClient(token="") as client:
        job = client.request(
            "GET", "/api/v1/courses/1/modules", params={"include[]": ["items"]},
        )

    assert query(job) == {"include[]": ["items"], "per_page": ["50"]}


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        (
            {"include[]": ["submission", "rubric"]},
            {"include[]": ["submission", "rubric"]},
        ),
        (
            [("include[]", "term"), ("active_only", True), ("include[]", "scores")],
            {"include[]": ["term", "scores"], "active_only": ["true"]},
        ),
        (
            {"active_only": True, "only_announcements": False, "optional": None, "zero": 0},
            {"active_only": ["true"], "only_announcements": ["false"], "optional": [""], "zero": ["0"]},
        ),
        (
            {"search_term": "café + math & science?", "include[]": ("a", "b"), "empty[]": []},
            {"search_term": ["café + math & science?"], "include[]": ["a", "b"]},
        ),
    ],
)
def test_query_values_match_token_mode(broker, params, expected):
    original = copy.deepcopy(params)
    job = broker_fetch("GET", "/api/v1/courses", params=params)
    token_request = httpx.Request(
        "GET", "https://canvas.example.test/api/v1/courses", params=params,
    )

    assert query(job) == expected
    assert query(job) == parse_qs(token_request.url.query.decode(), keep_blank_values=True)
    assert params == original


def test_existing_query_and_repeated_values_survive(broker):
    job = broker_fetch(
        "GET", "/api/v1/courses?search_term=A%26B",
        params=[("include[]", "term"), ("include[]", "total_scores")],
    )

    assert query(job) == {
        "search_term": ["A&B"], "include[]": ["term", "total_scores"],
    }


@pytest.mark.parametrize("params", [None, {}, [], {"include[]": []}])
def test_empty_query_parameters_keep_path(broker, params):
    job = broker_fetch("GET", "/api/v1/courses", params=params)
    assert job["path"] == "/api/v1/courses"


def test_paginated_includes_survive_every_page(broker, monkeypatch):
    rows = [{"id": 1}, {"id": 2}, {"id": 3}]
    params = {"include[]": ["items"], "per_page": 2}

    def page(job):
        broker.append(job)
        number = int(query(job)["page"][0])
        start = (number - 1) * 2
        return {"ok": True, "response": {"status": 200, "json": rows[start:start + 2]}}

    monkeypatch.setattr(session_broker, "_call", page)
    with CanvasClient(token="") as client:
        result = client.get_paginated("/api/v1/courses/1/modules", params=params)

    assert result == rows
    assert [query(job) for job in broker] == [
        {"include[]": ["items"], "per_page": ["2"], "page": ["1"]},
        {"include[]": ["items"], "per_page": ["2"], "page": ["2"]},
    ]
    assert params == {"include[]": ["items"], "per_page": 2}


def test_form_arrays_and_primitives_match_token_mode(broker):
    form = {
        "recipients[]": [4, 8], "body": "Hello + café & team",
        "force_new": True, "group_conversation": False, "optional": None,
        "empty[]": [], "zero": 0,
    }
    original = copy.deepcopy(form)
    with CanvasClient(token="") as client:
        job = client.request("POST", "/api/v1/conversations", data=form)
    token_request = httpx.Request(
        "POST", "https://canvas.example.test/api/v1/conversations", data=form,
    )
    expected = {
        "recipients[]": ["4", "8"], "body": ["Hello + café & team"],
        "force_new": ["true"], "group_conversation": ["false"],
        "optional": [""], "zero": ["0"],
    }

    assert job["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert parse_qs(job["body"], keep_blank_values=True) == expected
    assert job["body"] == token_request.read().decode()
    assert form == original


@pytest.mark.parametrize("body", [{}, {"include": ["submission"], "published": False}])
def test_json_body_keeps_priority_over_form(broker, body):
    job = broker_fetch("POST", "/api/v1/courses", json_body=body, data={"ignored": [1, 2]})

    assert job["headers"]["Content-Type"] == "application/json"
    assert job["body"] == body

"""Independent receiving tests for CanvasAPI through the real HTTP broker.

These use the production Handler, queue dispatch, broker_fetch and public API.
Only the browser worker is replaced with authored Canvas response envelopes;
no real Canvas account, profile, or school data is opened.
"""

from __future__ import annotations

import queue
import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

import httpx
import pytest

from canvaspilot import client as client_module
from canvaspilot import session_broker as broker_module
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient, broker_fetch

ORIGIN = "https://receiving-fixture.instructure.com"
ASSIGNMENTS = "/api/v1/courses/17/assignments"


def assignment_rows(start, stop):
    return [{"id": number, "name": f"Fictional assignment {number}"}
            for number in range(start, stop)]


def envelope(rows, link=None, status=200):
    return {"status": status, "json": rows, "text": None, "link": link}


@contextmanager
def running_broker(monkeypatch, respond):
    """Run the unchanged HTTP handler and dispatch queue on a private port."""
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy",
                 "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    state = broker_module._BrokerState()
    state.base_url = ORIGIN
    state.ready.set()
    monkeypatch.setattr(broker_module, "STATE", state)
    requests = []
    stopped = threading.Event()

    def worker():
        while not stopped.is_set():
            try:
                job, reply = state.jobs.get(timeout=0.05)
            except queue.Empty:
                continue
            requests.append(job)
            try:
                result = respond(job, len(requests))
                reply.put({"ok": True, "response": result})
            except Exception as exc:
                reply.put({"ok": False, "error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", 0), broker_module.Handler)
    monkeypatch.setattr(client_module, "BROKER_PORT", server.server_port)
    dispatch = threading.Thread(target=worker, daemon=True)
    http = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05),
                            daemon=True)
    dispatch.start()
    http.start()
    try:
        with CanvasClient(base_url=ORIGIN, token="", timeout=3) as client:
            yield CanvasAPI(client), requests
    finally:
        stopped.set()
        server.shutdown()
        server.server_close()
        dispatch.join(timeout=2)
        http.join(timeout=2)
        assert not dispatch.is_alive()
        assert not http.is_alive()


def test_public_assignments_keep_opaque_cursor_and_empty_intermediate_page(monkeypatch):
    second = ASSIGNMENTS + "?cursor=rows%3A10%2fA%2B&include[]=submission&include[]=overrides"
    third = ASSIGNMENTS + "?cursor=rows%3A10%2fB%2B&include[]=submission&include[]=overrides"

    def respond(job, index):
        assert job["method"] == "GET"
        assert job["body"] is None
        if index == 1:
            return envelope(assignment_rows(1, 11),
                            f'<{ORIGIN}{second}>; rel="next"; title="Assignments, continued"')
        if job["path"] == second:
            return envelope([], f'<{ORIGIN}{third}>; rel="next"')
        if job["path"] == third:
            return envelope(assignment_rows(11, 26))
        raise AssertionError("The continuation URL was rebuilt or an extra page was guessed.")

    with running_broker(monkeypatch, respond) as (api, requests):
        rows = api.list_assignments(17)
        assert [row["id"] for row in rows] == list(range(1, 26))
        assert [job["path"] for job in requests[1:]] == [second, third]
        initial = parse_qsl(urlsplit(requests[0]["path"]).query)
        assert initial == [("order_by", "due_at"), ("include[]", "submission"),
                           ("bucket", "upcoming"), ("per_page", "50")]


def test_a_full_terminal_page_does_not_invent_another_request(monkeypatch):
    def respond(_job, index):
        if index != 1:
            raise AssertionError("The broker guessed another page after a terminal Link.")
        return envelope(assignment_rows(1, 51))

    with running_broker(monkeypatch, respond) as (api, requests):
        assert len(api.list_assignments(17)) == 50
        assert len(requests) == 1


@pytest.mark.parametrize("link", [
    '<https://other-fixture.invalid/api/v1/items?cursor=private-value>; rel="next"',
    '<//other-fixture.invalid/api/v1/items>; rel="next"',
    f'<{ORIGIN}//other-fixture.invalid/api/v1/items>; rel="next"',
    f'<{ORIGIN}/api/v1/items?cursor=private-value>; rel="next", <{ORIGIN}/api/v1/other>; rel="next"',
])
def test_unsafe_or_ambiguous_next_is_refused_before_another_fetch(monkeypatch, link):
    with running_broker(monkeypatch, lambda _job, _index: envelope([{"id": 1}], link)) as (api, requests):
        with pytest.raises(RuntimeError) as caught:
            api.client.get_paginated("/api/v1/items")
        assert "private-value" not in str(caught.value)
        assert len(requests) == 1


def test_cycle_refuses_a_partial_list_and_never_fetches_the_same_url_twice(monkeypatch):
    same = "/api/v1/items?per_page=50"
    with running_broker(monkeypatch, lambda _job, _index: envelope([{"id": 1}],
                        f'<{ORIGIN}{same}>; rel="next"')) as (api, requests):
        with pytest.raises(RuntimeError, match="repeated|incomplete"):
            api.client.get_paginated("/api/v1/items")
        assert len(requests) == 1


def test_old_broker_metadata_is_an_actionable_error_not_a_partial_collection(monkeypatch):
    old = {"status": 200, "json": [{"id": 1}], "text": None}
    with running_broker(monkeypatch, lambda _job, _index: old) as (api, requests):
        with pytest.raises(RuntimeError, match="[Rr]estart"):
            api.client.get_paginated("/api/v1/items")
        assert len(requests) == 1


@pytest.mark.parametrize("status", [401, 403, 429])
def test_error_on_later_page_never_becomes_successful_partial_data(monkeypatch, status):
    def respond(_job, index):
        if index == 1:
            return envelope([{"id": 1}], f'<{ORIGIN}/api/v1/items?cursor=second>; rel="next"')
        return envelope({"errors": [{"message": "authored failure"}]}, status=status)

    expected_error = httpx.HTTPStatusError if status == 429 else CanvasAuthError
    with running_broker(monkeypatch, respond) as (api, requests):
        with pytest.raises(expected_error):
            api.client.get_paginated("/api/v1/items")
        assert len(requests) == 2


def test_default_broker_fetch_keeps_its_existing_decoded_payload_contract(monkeypatch):
    wanted = {"id": 17, "name": "Fictional profile"}
    with running_broker(monkeypatch, lambda _job, _index: envelope(wanted)) as (_api, requests):
        assert broker_fetch("GET", "/api/v1/users/self") == wanted
        assert len(requests) == 1

"""Complete broker collections follow Canvas's opaque Link continuation URLs."""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from canvaspilot import client as client_mod
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.pagination import CanvasPaginationError

BASE = "https://canvas.example.test"
DATASET = [{"id": i, "name": f"Course {i}"} for i in range(1, 236)]


def _client():
    return CanvasClient(base_url=BASE, token="")


def _mock_broker(monkeypatch, page_for_path):
    """Exercise real broker_fetch decoding, not a replacement pagination helper."""
    calls = []
    monkeypatch.setattr(client_mod, "broker_health", lambda: {"ok": True})

    def request(method, url, *, json, **kwargs):
        assert method == "POST"
        assert url == f"{client_mod.broker_base()}/fetch"
        assert json["method"] == "GET"
        calls.append(json)
        response = page_for_path(json["path"])
        return httpx.Response(200, json={"ok": True, "response": response})

    monkeypatch.setattr(client_mod, "_broker_request", request)
    return calls


def _collection(rows, *, cap=50):
    def page_for_path(path):
        params = parse_qs(urlsplit(path).query)
        offset = int(params.get("cursor", ["0"])[0])
        chunk = rows[offset:offset + cap]
        following = offset + cap
        link = (
            f'<{BASE}{urlsplit(path).path}?cursor={following}>; rel="next"'
            if following < len(rows) else None
        )
        return {"status": 200, "json": chunk, "link": link}
    return page_for_path


def test_broker_path_collects_all_pages(monkeypatch):
    calls = _mock_broker(monkeypatch, _collection(DATASET))
    assert _client().get_paginated("/api/v1/courses") == DATASET
    assert len(calls) == 5


def test_broker_path_exact_multiple_stops_at_no_next_link(monkeypatch):
    calls = _mock_broker(monkeypatch, _collection(DATASET[:100]))
    assert _client().get_paginated("/api/v1/courses") == DATASET[:100]
    assert len(calls) == 2


def test_broker_path_list_params_only_on_first_request(monkeypatch):
    calls = _mock_broker(monkeypatch, _collection(DATASET))
    params = [("enrollment_state", "active"), ("include[]", "term"), ("include[]", "scores")]
    assert _client().get_paginated("/api/v1/courses", params=params) == DATASET
    assert calls[0]["path"] == (
        "/api/v1/courses?enrollment_state=active&include%5B%5D=term"
        "&include%5B%5D=scores&per_page=50"
    )
    assert calls[1]["path"] == "/api/v1/courses?cursor=50"
    assert params == [("enrollment_state", "active"), ("include[]", "term"), ("include[]", "scores")]


def test_broker_path_non_list_response(monkeypatch):
    single = {"id": 7, "name": "Single"}
    _mock_broker(monkeypatch, lambda path: {"status": 200, "json": single, "link": None})
    assert _client().get_paginated("/api/v1/users/self") == [single]


def test_broker_path_non_list_continuation_refuses_collection(monkeypatch):
    first = {"status": 200, "json": DATASET[:100], "link": f'<{BASE}/api/v1/courses?cursor=tail>; rel="next"'}
    single = {"id": 999, "name": "Trailing single"}
    calls = _mock_broker(monkeypatch, lambda path: (
        {"status": 200, "json": single, "link": None} if "cursor=tail" in path else first
    ))
    with pytest.raises(CanvasPaginationError, match="non-list later page"):
        _client().get_paginated("/api/v1/courses")
    assert len(calls) == 2


def test_broker_path_40_page_cap_raises_instead_of_returning_partial_collection(monkeypatch):
    calls = _mock_broker(monkeypatch, _collection(list(range(41)), cap=1))
    with pytest.raises(CanvasPaginationError, match="40-page cap"):
        _client().get_paginated("/api/v1/courses")
    assert len(calls) == 40


def test_complete_40_page_collection_succeeds(monkeypatch):
    calls = _mock_broker(monkeypatch, _collection(list(range(40)), cap=1))
    assert _client().get_paginated("/api/v1/courses") == list(range(40))
    assert len(calls) == 40


def test_actual_assignment_api_reads_server_capped_short_pages(monkeypatch):
    """The original public API returned 10/25 rows, trusting requested per_page=50."""
    calls = _mock_broker(monkeypatch, _collection(DATASET[:25], cap=10))
    result = CanvasAPI(_client()).list_assignments(7)
    assert [row["id"] for row in result] == list(range(1, 26))
    assert len(calls) == 3
    assert "page=1" not in calls[0]["path"]


def test_empty_page_with_next_and_opaque_cursor_are_followed_verbatim(monkeypatch):
    next_path = "/api/v1/courses?after=a%2Fb%2Bc&filter[]=one&filter[]=two&opaque=1,2"
    pages = {
        "/api/v1/courses?per_page=50": {
            "status": 200, "json": [], "link": f'<{BASE}{next_path}>; rel="next"'
        },
        next_path: {"status": 200, "json": [{"id": 3}], "link": None},
    }
    calls = _mock_broker(monkeypatch, pages.__getitem__)
    assert _client().get_paginated("/api/v1/courses") == [{"id": 3}]
    assert [call["path"] for call in calls] == list(pages)


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_later_page_http_failure_does_not_return_partial_success(monkeypatch, status):
    calls = _mock_broker(monkeypatch, lambda path: (
        {"status": status, "json": {"error": "fixture failure"}, "link": None}
        if "cursor=next" in path else
        {"status": 200, "json": [{"id": 1}], "link": f'<{BASE}/api/v1/courses?cursor=next>; rel="next"'}
    ))
    error = client_mod.CanvasAuthError if status in (401, 403) else httpx.HTTPStatusError
    with pytest.raises(error):
        _client().get_paginated("/api/v1/courses")
    assert len(calls) == 2


def test_cycle_rejected_before_repeating_a_request(monkeypatch):
    calls = _mock_broker(monkeypatch, lambda path: {
        "status": 200, "json": [{"id": 1}], "link": f'<{BASE}/api/v1/courses?per_page=50>; rel="next"'
    })
    with pytest.raises(CanvasPaginationError, match="repeated"):
        _client().get_paginated("/api/v1/courses")
    assert len(calls) == 1


@pytest.mark.parametrize("response, message", [
    ({"status": 200, "json": []}, "Restart"),
    ({"status": 200, "json": [], "link": 12}, "Malformed"),
    ({"status": 200, "text": "<html>Log in</html>", "link": None}, "JSON"),
    ({"status": 200, "json": {"id": 1}, "link": '<https://canvas.example.test/next>; rel="next"'}, "non-list"),
])
def test_unverifiable_collection_is_an_actionable_error(monkeypatch, response, message):
    calls = _mock_broker(monkeypatch, lambda path: response)
    with pytest.raises(CanvasPaginationError, match=message):
        _client().get_paginated("/api/v1/courses")
    assert len(calls) == 1


@pytest.mark.parametrize("target", [
    "https://foreign.example.test/api/v1/courses?private=secret-marker",
    "http://canvas.example.test/api/v1/courses",
    "https://canvas.example.test:444/api/v1/courses",
    "https://user:secret-marker@canvas.example.test/api/v1/courses",
    "//foreign.example.test/api/v1/courses",
    "https://canvas.example.test//foreign.example.test/api/v1/courses",
    "https://canvas.example.test/api/v1/courses#fragment",
    "https://canvas.example.test\\@foreign.example.test/api/v1/courses",
])
def test_rejected_continuation_never_reaches_broker(monkeypatch, target):
    calls = _mock_broker(monkeypatch, lambda path: {
        "status": 200, "json": [1], "link": f'<{target}>; rel="next"'
    })
    with pytest.raises(CanvasPaginationError) as error:
        _client().get_paginated("/api/v1/courses")
    assert len(calls) == 1
    assert "secret-marker" not in str(error.value)


def test_default_broker_fetch_result_is_unchanged(monkeypatch):
    _mock_broker(monkeypatch, lambda path: {"status": 200, "json": [1], "link": ""})
    assert client_mod.broker_fetch("GET", "/api/v1/courses") == [1]


def test_token_and_fixture_modes_do_not_call_the_broker(monkeypatch):
    monkeypatch.setattr(client_mod, "broker_health", lambda: pytest.fail("broker probe"))
    fixture = CanvasClient(fixture={"routes": {"GET /api/v1/courses": [1]}})
    assert fixture.get_paginated("/api/v1/courses") == [1]
    with CanvasClient(base_url=BASE, token="fixture-token") as client:
        client._http = httpx.Client(base_url=BASE, transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=[2])
        ))
        assert client.get_paginated("/api/v1/courses") == [2]

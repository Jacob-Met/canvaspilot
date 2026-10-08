"""Complete coursework retrieval through the actual client and API decoders.

The provider responses are authored; neither auth mode contacts a school.
"""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
import pytest

from canvaspilot import client as client_mod
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

BASE = "https://school.instructure.com"
ASSIGNMENTS = "/api/v1/courses/7/assignments"


@pytest.fixture(params=["broker", "token"])
def collection(request, monkeypatch):
    mode = request.param
    monkeypatch.delenv("CANVAS_API_TOKEN", raising=False)
    client = CanvasClient(base_url=BASE, token="synthetic-token" if mode == "token" else "")
    replies = []
    calls = []

    def respond(req):
        index = len(calls)
        calls.append(req)
        assert index < len(replies), "pagination made an unrequested extra read"
        reply = replies[index]
        if mode == "token":
            headers = {"LiNk": reply["link"]} if reply.get("link") else {}
            return httpx.Response(reply.get("status", 200), json=reply["json"], headers=headers)
        envelope = {"status": 200, "text": None, "url": str(req.url), **reply}
        if envelope.pop("legacy", False):
            envelope.pop("link", None)
            envelope.pop("url", None)
        return httpx.Response(200, json={"ok": True, "response": envelope})

    if mode == "token":
        client._http = httpx.Client(base_url=BASE, transport=httpx.MockTransport(respond))
    else:
        monkeypatch.setattr(client_mod, "broker_health", lambda: {"ok": True})

        def post(url, *, json, **kwargs):
            assert url == client_mod.broker_base() + "/fetch"
            assert json["method"] == "GET"
            return respond(httpx.Request("GET", urljoin(BASE + "/", json["path"])))

        def broker_request(method, url, **kwargs):
            assert method == "POST"
            return post(url, **kwargs)

        monkeypatch.setattr(client_mod.httpx, "post", post)
        monkeypatch.setattr(client_mod.httpx, "request", broker_request)
    try:
        yield client, replies, calls, mode
    finally:
        client.close()


def test_short_page_follows_opaque_link_in_actual_assignment_api(collection):
    client, replies, calls, _ = collection
    next_url = BASE + ASSIGNMENTS + "?cursor=after%3A2&include%5B%5D=submission"
    replies.extend([
        {"json": [{"id": 1}, {"id": 2}], "link": f'<{next_url}>; rel="next"'},
        {"json": [{"id": 3, "name": "Final coursework"}], "link": None},
    ])
    rows = CanvasAPI(client).list_assignments(7)
    assert [row["id"] for row in rows] == [1, 2, 3]
    assert rows[-1]["name"] == "Final coursework"
    assert str(calls[1].url) == next_url
    assert calls[0].url.params.get_list("include[]") == ["submission"]
    assert "page" not in calls[0].url.params


def test_empty_intermediate_page_and_opaque_punctuation_are_preserved(collection):
    client, replies, calls, _ = collection
    next_url = BASE + ASSIGNMENTS + "?cursor=a,b;c%2Fd&include%5B%5D=one&include%5B%5D=two"
    final_url = BASE + ASSIGNMENTS + "?cursor=end%3D3"
    replies.extend([
        {"json": [], "link": f'<{next_url}>; title="Page, two"; rel="next"'},
        {"json": [{"id": 1}], "link": f'<{final_url}>; rel="next alternate"'},
        {"json": [{"id": 2}], "link": None},
    ])
    assert client.get_paginated(ASSIGNMENTS) == [{"id": 1}, {"id": 2}]
    assert [str(req.url) for req in calls[1:]] == [next_url, final_url]


def test_full_last_page_stops_without_empty_probe(collection):
    client, replies, calls, _ = collection
    rows = [{"id": n} for n in range(50)]
    replies.append({"json": rows, "link": None})
    assert client.get_paginated(ASSIGNMENTS) == rows
    assert len(calls) == 1


def test_first_filters_and_caller_values_survive(collection):
    client, replies, calls, _ = collection
    replies.append({"json": [{"id": 1}], "link": None})
    params = [("include[]", "submission"), ("include[]", "rubric"), ("per_page", 100)]
    original = params.copy()
    client.get_paginated(ASSIGNMENTS, params=params)
    assert calls[0].url.params.get_list("include[]") == ["submission", "rubric"]
    assert calls[0].url.params["per_page"] == "100"
    assert params == original


def test_initial_absolute_url_keeps_its_existing_cursor(collection):
    client, replies, calls, _ = collection
    replies.append({"json": [{"id": 1}], "link": None})
    client.get_paginated(BASE + ASSIGNMENTS + "?cursor=starting%2Fpoint")
    assert calls[0].url.params["cursor"] == "starting/point"


@pytest.mark.parametrize("next_url", [
    "https://elsewhere.example/api/v1/assignments?page=2",
    "https://school.instructure.com.evil.example/api/v1/assignments?page=2",
    "http://school.instructure.com/api/v1/assignments?page=2",
    "https://school.instructure.com:444/api/v1/assignments?page=2",
    "https://school.instructure.com:0/api/v1/assignments?page=2",
    "https://user:secret@school.instructure.com/api/v1/assignments?page=2",
    "https://school.instructure.com\\@elsewhere.example/api/v1/assignments?page=2",
])
def test_next_link_cannot_leave_the_response_origin(collection, next_url):
    client, replies, calls, _ = collection
    replies.append({"json": [{"id": 1}], "link": f'<{next_url}>; rel="next"'})
    with pytest.raises(RuntimeError, match="pagination.*(origin|URL)"):
        client.get_paginated(ASSIGNMENTS)
    assert len(calls) == 1


def test_repeated_next_link_refuses_partial_list_without_duplicate_read(collection):
    client, replies, calls, _ = collection
    next_url = BASE + ASSIGNMENTS + "?cursor=second"
    replies.extend([
        {"json": [{"id": 1}], "link": f'<{next_url}>; rel="next"'},
        {"json": [{"id": 2}], "link": f'<{next_url}>; rel="next"'},
    ])
    with pytest.raises(RuntimeError, match="pagination.*repeat"):
        client.get_paginated(ASSIGNMENTS)
    assert len(calls) == 2


@pytest.mark.parametrize("header", [
    'not-a-link; rel="next"',
    '<https://school.instructure.com/api/v1/courses?page=2>; rel',
    '<https://school.instructure.com/api/v1/courses?page=2>; rel=""',
    '<https://school.instructure.com/api/v1/courses?page=2>; rel="next"; rel="prev"',
    '<https://school.instructure.com/api/v1/courses?page=2>; rel="next", broken',
    ('<https://school.instructure.com/api/v1/courses?a>; rel="next", '
     '<https://school.instructure.com/api/v1/courses?b>; rel="next"'),
])
def test_malformed_or_ambiguous_links_do_not_assert_completion(collection, header):
    client, replies, calls, _ = collection
    replies.append({"json": [{"id": 1}], "link": header})
    with pytest.raises(RuntimeError, match="pagination.*Link"):
        client.get_paginated(ASSIGNMENTS)
    assert len(calls) == 1


def test_existing_page_ceiling_refuses_incomplete_success(collection):
    client, replies, calls, _ = collection
    replies.extend({"json": [{"id": n}], "link": f'<{BASE}{ASSIGNMENTS}?cursor={n + 1}>; rel="next"'}
                   for n in range(40))
    with pytest.raises(RuntimeError, match="40-page.*incomplete"):
        client.get_paginated(ASSIGNMENTS, params={"per_page": 1})
    assert len(calls) == 40


def test_same_origin_relative_next_link_is_resolved_without_reusing_filters(collection):
    client, replies, calls, _ = collection
    replies.extend([
        {"json": [{"id": 1}], "link": '<?cursor=next%2Fone>; rel="next"'},
        {"json": [{"id": 2}], "link": None},
    ])
    assert client.get_paginated(ASSIGNMENTS, params={"per_page": 25}) == [{"id": 1}, {"id": 2}]
    assert str(calls[1].url) == BASE + ASSIGNMENTS + "?cursor=next%2Fone"


def test_exactly_forty_pages_can_complete(collection):
    client, replies, calls, _ = collection
    replies.extend({"json": [{"id": n}], "link": f'<{BASE}{ASSIGNMENTS}?cursor={n + 1}>; rel="next"'}
                   for n in range(39))
    replies.append({"json": [{"id": 39}], "link": None})
    assert len(client.get_paginated(ASSIGNMENTS)) == 40
    assert len(calls) == 40


def test_later_auth_failure_is_not_a_partial_success(collection):
    client, replies, calls, _ = collection
    replies.extend([
        {"json": [{"id": 1}], "link": f'<{BASE}{ASSIGNMENTS}?cursor=2>; rel="next"'},
        {"json": {"message": "login required"}, "status": 401, "link": None},
    ])
    with pytest.raises(client_mod.CanvasAuthError):
        client.get_paginated(ASSIGNMENTS)
    assert len(calls) == 2


def test_legacy_running_broker_requires_restart(collection):
    client, replies, calls, mode = collection
    if mode != "broker":
        pytest.skip("running broker compatibility only")
    replies.append({"json": [{"id": 1}], "link": None, "legacy": True})
    with pytest.raises(RuntimeError, match="[Rr]estart.*broker"):
        client.get_paginated(ASSIGNMENTS)
    assert len(calls) == 1


def test_ordinary_broker_fetch_keeps_legacy_body_contract(collection):
    _, replies, _, mode = collection
    if mode != "broker":
        pytest.skip("broker_fetch public API only")
    replies.append({"json": [{"id": 1}], "link": None, "legacy": True})
    assert client_mod.broker_fetch("GET", ASSIGNMENTS) == [{"id": 1}]

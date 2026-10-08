"""Token collection reads keep opaque next links on the configured Canvas origin.

Every HTTP exchange uses MockTransport and an explicitly synthetic token. No
network endpoint, user credential, browser session or school account is used.
"""

from __future__ import annotations

from urllib.parse import parse_qsl

import httpx
import pytest

from canvaspilot import client as client_module
from canvaspilot.client import CanvasAuthError, CanvasClient, CanvasPaginationError

BASE = "https://token-pagination-fixture.instructure.com"
SYNTHETIC_TOKEN = "fixture-token-not-a-credential"


def token_client(monkeypatch, handler):
    """Keep production token/header setup and substitute only its HTTP transport."""
    original_client = httpx.Client
    requests = []

    def receive(request):
        requests.append(request)
        return handler(request, len(requests))

    def construct(**kwargs):
        return original_client(**kwargs, transport=httpx.MockTransport(receive), trust_env=False)

    monkeypatch.setattr(client_module.httpx, "Client", construct)
    monkeypatch.setattr(client_module, "broker_health", lambda: pytest.fail("Token read probed broker"))
    return CanvasClient(base_url=BASE, token=SYNTHETIC_TOKEN), requests


def test_opaque_next_query_survives_short_and_empty_intermediate_pages(monkeypatch):
    second = "/api/v1/items?after=a%2fb%2Bc&include[]=one&include[]=two"
    third = "/api/v1/items?after=tail%3Dopaque"

    def respond(request, number):
        assert request.headers["authorization"] == f"Bearer {SYNTHETIC_TOKEN}"
        if number == 1:
            return httpx.Response(200, json=[{"id": 1}], headers={"Link": f'<{BASE}{second}>; rel="next"'})
        if number == 2:
            assert request.url.query.decode() == second.split("?", 1)[1]
            return httpx.Response(200, json=[], headers={"Link": f'<{BASE}{third}>; rel="next"'})
        assert number == 3
        assert request.url.query.decode() == third.split("?", 1)[1]
        return httpx.Response(200, json=[{"id": 2}])

    client, requests = token_client(monkeypatch, respond)
    with client:
        assert client.get_paginated("/api/v1/items", params=[("include[]", "source")]) == [{"id": 1}, {"id": 2}]
    assert len(requests) == 3


@pytest.mark.parametrize("target", [
    "https://foreign-pagination-fixture.invalid/api/v1/items?cursor=private-marker",
    "http://token-pagination-fixture.instructure.com/api/v1/items",
    "https://token-pagination-fixture.instructure.com:444/api/v1/items",
    "https://user:private-marker@token-pagination-fixture.instructure.com/api/v1/items",
    "//foreign-pagination-fixture.invalid/api/v1/items",
    f"{BASE}//foreign-pagination-fixture.invalid/api/v1/items",
    f"{BASE}/api/v1/items#fragment",
    f"{BASE}\\@foreign-pagination-fixture.invalid/api/v1/items",
])
def test_invalid_next_never_receives_the_configured_authorization_header(monkeypatch, target):
    def respond(_request, number):
        if number == 1:
            return httpx.Response(200, json=[1], headers={"Link": f'<{target}>; rel="next"'})
        return httpx.Response(200, json=[2])

    client, requests = token_client(monkeypatch, respond)
    with client, pytest.raises(CanvasPaginationError) as error:
        client.get_paginated("/api/v1/items")
    assert len(requests) == 1
    assert SYNTHETIC_TOKEN not in str(error.value)
    assert "private-marker" not in str(error.value)


def test_foreign_initial_url_is_refused_before_any_request(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(200, json=[]))
    with client, pytest.raises(CanvasPaginationError):
        client.get_paginated("https://foreign-pagination-fixture.invalid/api/v1/items")
    assert requests == []


def test_same_origin_absolute_initial_url_keeps_initial_parameters(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(200, json=[]))
    with client:
        assert client.get_paginated(f"{BASE}/api/v1/items", params={"include[]": ["one", "two"]}) == []
    assert parse_qsl(requests[0].url.query.decode()) == [
        ("include[]", "one"), ("include[]", "two"), ("per_page", "50")
    ]


def test_initial_path_query_and_native_httpx_parameter_types_are_preserved(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(200, json=[]))
    params = {"include[]": ["one", "two"], "published": True, "optional": None}
    with client:
        assert client.get_paginated("/api/v1/items?starting_cursor=given%2fopaque", params=params) == []
    assert parse_qsl(requests[0].url.query.decode(), keep_blank_values=True) == [
        ("starting_cursor", "given/opaque"), ("include[]", "one"),
        ("include[]", "two"), ("published", "true"), ("optional", ""),
        ("per_page", "50"),
    ]
    assert params == {"include[]": ["one", "two"], "published": True, "optional": None}


def test_full_terminal_page_stops_without_an_extra_request(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(200, json=list(range(50))))
    with client:
        assert client.get_paginated("/api/v1/items") == list(range(50))
    assert len(requests) == 1


def test_cycle_refuses_partial_output_before_a_repeated_fetch(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(
        200, json=[1], headers={"Link": f'<{BASE}/api/v1/items?per_page=50>; rel="next"'}
    ))
    with client, pytest.raises(CanvasPaginationError, match="repeated"):
        client.get_paginated("/api/v1/items")
    assert len(requests) == 1


@pytest.mark.parametrize("complete", [False, True])
def test_exact_forty_page_boundary_distinguishes_complete_and_truncated(monkeypatch, complete):
    def respond(_request, number):
        headers = {} if complete and number == 40 else {"Link": f'<{BASE}/api/v1/items?cursor={number + 1}>; rel="next"'}
        return httpx.Response(200, json=[number], headers=headers)
    client, requests = token_client(monkeypatch, respond)
    with client:
        if complete:
            assert client.get_paginated("/api/v1/items") == list(range(1, 41))
        else:
            with pytest.raises(CanvasPaginationError, match="40-page cap"):
                client.get_paginated("/api/v1/items")
    assert len(requests) == 40


@pytest.mark.parametrize("link", [
    f'<{BASE}/api/v1/items?cursor=a>; rel="next", <{BASE}/api/v1/items?cursor=b>; rel="next"',
    f'<{BASE}/api/v1/items?cursor=a>; rel="next',
    f'{BASE}/api/v1/items?cursor=a; rel="next"',
])
def test_ambiguous_or_malformed_link_refuses_a_complete_result(monkeypatch, link):
    client, requests = token_client(monkeypatch, lambda _request, number: httpx.Response(
        200, json=[number], headers={"Link": link} if number == 1 else {}
    ))
    with client, pytest.raises(CanvasPaginationError):
        client.get_paginated("/api/v1/items")
    assert len(requests) == 1


def test_non_next_relation_is_terminal(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, number: httpx.Response(
        200, json=[number], headers={"Link": f'<{BASE}/api/v1/items?cursor=wrong>; rel="nextish"'} if number == 1 else {}
    ))
    with client:
        assert client.get_paginated("/api/v1/items") == [1]
    assert len(requests) == 1


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_later_http_error_propagates_without_partial_output(monkeypatch, status):
    client, requests = token_client(monkeypatch, lambda _request, number: (
        httpx.Response(200, json=[1], headers={"Link": f'<{BASE}/api/v1/items?cursor=next>; rel="next"'})
        if number == 1 else httpx.Response(status, json={"error": "fictional failure"})
    ))
    error = CanvasAuthError if status in (401, 403) else httpx.HTTPStatusError
    with client, pytest.raises(error):
        client.get_paginated("/api/v1/items")
    assert len(requests) == 2


def test_terminal_single_object_keeps_existing_contract(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(200, json={"id": 1}))
    with client:
        assert client.get_paginated("/api/v1/users/self") == [{"id": 1}]
    assert len(requests) == 1


def test_non_list_with_next_refuses_partial_collection(monkeypatch):
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(
        200, json={"id": 1}, headers={"Link": f'<{BASE}/api/v1/items?cursor=next>; rel="next"'}
    ))
    with client, pytest.raises(CanvasPaginationError, match="non-list"):
        client.get_paginated("/api/v1/items")
    assert len(requests) == 1

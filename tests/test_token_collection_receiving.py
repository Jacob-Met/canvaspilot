"""Receiving boundaries when the qualified PAT loop meets the e208 contract.

All exchanges use the donor's native HTTPX MockTransport fixture and a synthetic
token. These cases exercise public collection results and emitted request URLs.
"""

import json

import httpx
import pytest
from test_token_pagination import BASE, token_client

from canvaspilot.client import CanvasPaginationError


@pytest.mark.parametrize("chunk", [{"id": 2}, None, 17, False, "error"])
def test_later_terminal_json_scalar_or_object_cannot_complete_a_collection(monkeypatch, chunk):
    client, requests = token_client(monkeypatch, lambda _request, number: (
        httpx.Response(200, json=[{"id": 1}], headers={
            "Link": f'<{BASE}/api/v1/items?after=second>; rel="next"'
        }) if number == 1 else httpx.Response(200, content=json.dumps(chunk),
                                            headers={"Content-Type": "application/json"})
    ))
    with client, pytest.raises(CanvasPaginationError, match="non-list"):
        client.get_paginated("/api/v1/items")
    assert len(requests) == 2


@pytest.mark.parametrize("payload", [b"", b"<html>Authored error</html>", b"{"])
def test_later_non_json_body_is_an_incomplete_collection_error(monkeypatch, payload):
    client, requests = token_client(monkeypatch, lambda _request, number: (
        httpx.Response(200, json=[{"id": 1}], headers={
            "Link": f'<{BASE}/api/v1/items?after=second>; rel="next"'
        }) if number == 1 else httpx.Response(200, content=payload)
    ))
    with client, pytest.raises(CanvasPaginationError, match="JSON|incomplete"):
        client.get_paginated("/api/v1/items")
    assert len(requests) == 2


@pytest.mark.parametrize("applicable", [False, True])
def test_pat_ignores_an_entire_anchored_link_without_hiding_applicable_next(monkeypatch, applicable):
    other = f'{BASE}/api/v1/other?after=wrong'
    good = f'{BASE}/api/v1/items?after=right%2Fopaque'
    header = f'<{other}>; rel="NEXT"; anchor="{BASE}/api/v1/other"'
    if applicable:
        header += f', <{good}>; rel="next"'
    client, requests = token_client(monkeypatch, lambda _request, number: (
        httpx.Response(200, json=[{"id": 1}], headers={"Link": header})
        if number == 1 else httpx.Response(200, json=[{"id": 2}])
    ))
    with client:
        assert client.get_paginated("/api/v1/items") == (
            [{"id": 1}, {"id": 2}] if applicable else [{"id": 1}]
        )
    assert len(requests) == (2 if applicable else 1)
    if applicable:
        assert str(requests[1].url) == good


def test_pat_initial_opaque_query_is_retained_before_the_added_filters(monkeypatch):
    authored = "cursor=a%2fb%2Bc%3D&include[]=first&include[]=second&empty=&literal=+"
    client, requests = token_client(monkeypatch, lambda _request, _number: httpx.Response(200, json=[]))
    with client:
        assert client.get_paginated(f"{BASE}/api/v1/items?{authored}",
                                    params=[("include[]", "third"), ("published", True)]) == []
    assert requests[0].url.query.decode() == (
        authored + "&include%5B%5D=third&published=true&per_page=50"
    )

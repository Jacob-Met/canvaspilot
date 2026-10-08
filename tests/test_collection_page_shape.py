"""Receive the later-page object finding from PR35 review 5454974316.

Broker controls use the production HTTP Handler and dispatch queue; token
controls keep production client/header setup with a synthetic-token transport.
Only authored response bodies are supplied. No Canvas account is contacted.
"""

from __future__ import annotations

from contextlib import contextmanager

import httpx
import pytest
from test_broker_http_receiving import ORIGIN, envelope, running_broker
from test_token_pagination import BASE, SYNTHETIC_TOKEN, token_client

from canvaspilot.pagination import CanvasPaginationError

PATH = "/api/v1/items"


@contextmanager
def collection_client(monkeypatch, mode, pages):
    def page(index, origin):
        assert 1 <= index <= len(pages), "An extra page was requested."
        link = (
            f'<{origin}{PATH}?cursor=page-{index + 1}>; rel="next"'
            if index < len(pages) else None
        )
        return pages[index - 1], link

    if mode == "broker":
        def respond(_job, index):
            body, link = page(index, ORIGIN)
            return envelope(body, link)

        with running_broker(monkeypatch, respond) as (api, requests):
            yield api.client, requests
        return

    def respond(request, index):
        assert request.headers["authorization"] == f"Bearer {SYNTHETIC_TOKEN}"
        body, link = page(index, BASE)
        return httpx.Response(200, json=body, headers={"Link": link} if link else {})

    client, requests = token_client(monkeypatch, respond)
    with client:
        yield client, requests


@pytest.mark.parametrize("mode", ["broker", "token"])
@pytest.mark.parametrize("first_page", [
    pytest.param([{"id": 1}], id="populated-first-list"),
    pytest.param([], id="empty-first-list"),
])
def test_terminal_object_on_a_later_page_refuses_collection(monkeypatch, mode, first_page):
    pages = [first_page, {"message": "Fictional unexpected object"}]
    with collection_client(monkeypatch, mode, pages) as (client, requests):
        with pytest.raises(CanvasPaginationError, match="non-list"):
            client.get_paginated(PATH)
        assert len(requests) == 2


@pytest.mark.parametrize("mode", ["broker", "token"])
@pytest.mark.parametrize("body", [{"id": 17}, {}], ids=["object", "empty-object"])
def test_first_page_terminal_object_keeps_singleton_compatibility(monkeypatch, mode, body):
    with collection_client(monkeypatch, mode, [body]) as (client, requests):
        assert client.get_paginated(PATH) == [body]
        assert len(requests) == 1


@pytest.mark.parametrize("mode", ["broker", "token"])
def test_empty_first_list_can_continue_to_a_terminal_list(monkeypatch, mode):
    with collection_client(monkeypatch, mode, [[], [{"id": 17}]]) as (client, requests):
        assert client.get_paginated(PATH) == [{"id": 17}]
        assert len(requests) == 2

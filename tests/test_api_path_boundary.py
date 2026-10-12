"""The generic API boundary must refuse non-REST targets before dispatch."""

import asyncio

import httpx
import pytest

from canvaspilot import CanvasAPI, CanvasClient, assert_canvas_api_path, mcp_server

INVALID_PATHS = [
    "/api/v10/courses",
    "/api/v1evil",
    "/api/v1;courses",
    "/api/v1#fragment",
    "/api/v1/courses#fragment",
    "/api/v1/../login",
    "/api/v1/%2e%2e/login",
    "/api/v1/%2E%2E/%2e%2e/login",
    "/api/v1/.%2e/login",
    "/api/v1/%2E./login",
    "/api/v1/%2e%2e%2flogin",
    "/api/v1/%2e%2e%5clogin",
    "/api/v1\\courses",
    "/api/v1/%5ccourses",
    "/api/v1/cour\nses",
    "/api/v1/cour\tses",
    "/api/v1/courses%00",
    "/api/v1/courses%0a",
    "/api/v1/courses%7f",
    "https://canvas.example/api/v1/courses",
    "//canvas.example/api/v1/courses",
]

VALID_PATHS = [
    "/api/v1",
    "/api/v1/",
    "/api/v1?per_page=10",
    "/api/v1/courses",
    "/api/v1/courses?include[]=term&include[]=total_scores",
    "/api/v1/courses/7/pages/chapter%2Eone?include[]=body",
    "/api/v1/courses/7/pages/caf%C3%A9",
    "/api/v1/courses?search_term=%2e%2e&cursor=%2F%25%3F%23",
]


class RecordingClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append(("request", method, path, kwargs))
        return {"accepted": True}

    def get_paginated(self, path, **kwargs):
        self.calls.append(("paginated", path, kwargs))
        return [{"accepted": True}]


@pytest.mark.parametrize("path", INVALID_PATHS)
@pytest.mark.parametrize("operation", ["request", "paginated"])
def test_api_refuses_unsafe_path_without_dispatch(path, operation):
    client = RecordingClient()
    api = CanvasAPI(client)
    with pytest.raises(ValueError):
        if operation == "request":
            api.api_request("POST", path, json_body={"must_not_be_sent": True})
        else:
            api.api_paginated(path)
    assert client.calls == []


@pytest.mark.parametrize("path", VALID_PATHS)
def test_valid_path_query_and_request_payload_are_preserved(path):
    client = RecordingClient()
    api = CanvasAPI(client)
    params = [("include[]", "term"), ("include[]", "total_scores")]
    body = {"message": "/api/v10 and ../ are ordinary body text"}
    data = {"literal": "%2e%2e"}
    assert api.api_request("post", path, params=params, json_body=body, data=data) == {
        "accepted": True,
    }
    assert api.api_paginated(path, params=params) == [{"accepted": True}]
    assert client.calls == [
        ("request", "POST", path, {"params": params, "json_body": body, "data": data}),
        ("paginated", path, {"params": params}),
    ]


def test_existing_outer_whitespace_convenience_is_preserved():
    assert assert_canvas_api_path("  /api/v1/courses  ") == "/api/v1/courses"


@pytest.mark.parametrize("operation", ["request", "paginated"])
def test_mcp_uses_the_same_guard_before_dispatch(monkeypatch, operation):
    client = RecordingClient()
    monkeypatch.setattr(mcp_server, "_get_api", lambda: CanvasAPI(client))
    for path in ["/api/v10/courses", "/api/v1/%2e%2e/%2e%2e/login"]:
        with pytest.raises(ValueError):
            if operation == "request":
                asyncio.run(mcp_server.canvas_api_request("POST", path, body_json='{"x":1}'))
            else:
                asyncio.run(mcp_server.canvas_api_paginated(path))
    assert client.calls == []


def test_real_token_transport_receives_only_admitted_target():
    requests = []

    def receive(request):
        requests.append(request)
        return httpx.Response(200, json=[{"id": 7}])

    with CanvasClient(base_url="https://canvas.example", token="offline-placeholder") as client:
        client._http = httpx.Client(
            base_url=client.base_url,
            transport=httpx.MockTransport(receive),
        )
        api = CanvasAPI(client)
        for path in ["/api/v1evil", "/api/v1/%2e%2e/%2e%2e/login"]:
            with pytest.raises(ValueError):
                api.api_request("POST", path, json_body={"x": 1})
        assert requests == []
        assert api.api_request("GET", "/api/v1/courses?owned=1") == [{"id": 7}]
        assert len(requests) == 1
        assert requests[0].url.path == "/api/v1/courses"

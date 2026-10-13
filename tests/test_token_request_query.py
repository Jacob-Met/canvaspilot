"""Receive ordinary token requests at a real, fictional loopback HTTP endpoint."""

from __future__ import annotations

import asyncio
import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import httpx
import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient


@pytest.fixture
def endpoint(monkeypatch):
    # Keep authored numeric-loopback HTTP independent of this host's proxy setup.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("no_proxy", "*")
    observed = []
    response = {"status": 200, "body": b'{"received":true}', "type": "application/json"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def receive(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            observed.append({"method": self.command, "target": self.path,
                             "body": body, "content_type": self.headers.get("Content-Type"),
                             "authorization": self.headers.get("Authorization")})
            self.send_response(response["status"])
            self.send_header("Content-Type", response["type"])
            self.send_header("Content-Length", str(len(response["body"])))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response["body"])

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = receive

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
    thread.start()
    try:
        with CanvasClient(base_url=f"http://127.0.0.1:{server.server_port}",
                          token="synthetic-query-136") as client:
            yield CanvasAPI(client), observed, response
        assert client._http is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


@pytest.mark.parametrize("params", [None, {}, []])
def test_embedded_repeated_blank_and_opaque_values_reach_http(endpoint, params):
    api, seen, _ = endpoint
    path = "/api/v1/courses?include%5B%5D=term&include%5B%5D=teachers&opaque=a%2Bb%26c%3Dd&blank=&flag"
    before = copy.deepcopy(params)
    assert api.api_request("GET", path, params=params) == {"received": True}
    assert seen[0]["target"] == path + "&per_page=50"
    assert seen[0]["authorization"] == "Bearer synthetic-query-136"
    assert len(seen) == 1
    assert params == before


def test_explicit_array_boolean_null_and_unicode_encoding(endpoint):
    api, seen, _ = endpoint
    params = {"include[]": ["syllabus", "teachers"], "active": True, "missing": None,
              "search_term": "α + β", "per_page": 7}
    before = copy.deepcopy(params)
    api.api_request("GET", "/api/v1/courses?source=keep", params=params)
    assert seen[0]["target"] == (
        "/api/v1/courses?source=keep&include%5B%5D=syllabus&include%5B%5D=teachers"
        "&active=true&missing=&search_term=%CE%B1+%2B+%CE%B2&per_page=7"
    )
    assert params == before


def test_colliding_names_append_without_discarding_embedded_occurrences(endpoint):
    api, seen, _ = endpoint
    params = [("x", "second"), ("x", "third"), ("per_page", 7)]
    api.api_request("GET", "/api/v1/courses?x=first&per_page=3", params=params)
    assert seen[0]["target"] == "/api/v1/courses?x=first&per_page=3&x=second&x=third&per_page=7"
    assert params == [("x", "second"), ("x", "third"), ("per_page", 7)]


def test_embedded_page_size_retains_existing_append_default_contract(endpoint):
    api, seen, _ = endpoint
    api.api_request("GET", "/api/v1/courses?per_page=3")
    assert seen[0]["target"] == "/api/v1/courses?per_page=3&per_page=50"


@pytest.mark.parametrize("params", [{"per_page": []}, {"per_page": (), "filter": []}])
@pytest.mark.parametrize("path,expected", [
    ("/api/v1/example?cursor=%2f%2F&&flag&blank=", "/api/v1/example?cursor=%2f%2F&&flag&blank="),
    ("/api/v1/example", "/api/v1/example?"),
])
def test_empty_encoding_preserves_query_and_existing_empty_marker(endpoint, params, path, expected):
    api, seen, _ = endpoint
    before = copy.deepcopy(params)
    api.api_request("GET", path, params=params)
    assert seen[0]["target"] == expected
    assert params == before


@pytest.mark.parametrize("path,expected", [
    ("/api/v1/courses?cursor=%2f%2F%2526&name=one+two", "/api/v1/courses?cursor=%2f%2F%2526&name=one+two&per_page=50"),
    ("/api/v1/courses?word=雪&literal=%23", "/api/v1/courses?word=%E9%9B%AA&literal=%23&per_page=50"),
    ("/api/v1/courses?first=1&&last=2&", "/api/v1/courses?first=1&&last=2&&per_page=50"),
    ("/api/v1/courses?", "/api/v1/courses?per_page=50"),
    ("/api/v1/courses", "/api/v1/courses?per_page=50"),
])
def test_httpx_url_spelling_and_empty_query_controls(endpoint, path, expected):
    api, seen, _ = endpoint
    api.api_request("GET", path)
    assert seen[0]["target"] == expected


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_method_json_body_and_query_are_received_together(endpoint, method):
    api, seen, _ = endpoint
    body = {"literal": "<tag> 雪", "zero": 0, "false": False, "null": None}
    before = copy.deepcopy(body)
    api.api_request(method.lower(), "/api/v1/example?option=retain", json_body=body,
                    params={"per_page": 9})
    assert seen[0]["method"] == method
    assert seen[0]["target"] == "/api/v1/example?option=retain&per_page=9"
    assert json.loads(seen[0]["body"]) == body
    assert seen[0]["content_type"] == "application/json"
    assert body == before


def test_form_body_and_no_query_control(endpoint):
    api, seen, _ = endpoint
    data = {"answer": "a & b", "include[]": ["first", "second"]}
    api.api_request("POST", "/api/v1/example", data=data, params={"per_page": 8})
    assert seen[0]["target"] == "/api/v1/example?per_page=8"
    assert seen[0]["body"] == b"answer=a+%26+b&include%5B%5D=first&include%5B%5D=second"
    assert seen[0]["content_type"] == "application/x-www-form-urlencoded"


@pytest.mark.parametrize("status,body,ctype,expected", [
    (204, b"", "application/json", None),
    (200, b"plain reply", "text/plain", "plain reply"),
    (200, b"null", "application/json; charset=utf-8", None),
])
def test_terminal_response_contracts(endpoint, status, body, ctype, expected):
    api, seen, response = endpoint
    response.update(status=status, body=body, type=ctype)
    assert api.api_request("GET", "/api/v1/example?requested=one") == expected
    assert seen[0]["target"] == "/api/v1/example?requested=one&per_page=50"


@pytest.mark.parametrize("status,error", [(401, CanvasAuthError), (403, CanvasAuthError),
                                         (404, httpx.HTTPStatusError), (503, httpx.HTTPStatusError)])
def test_error_class_and_single_dispatch_are_preserved(endpoint, status, error):
    api, seen, response = endpoint
    response.update(status=status, body=b'{"error":"synthetic refusal"}')
    with pytest.raises(error):
        api.api_request("GET", "/api/v1/example?filter=keep")
    assert len(seen) == 1
    assert seen[0]["target"] == "/api/v1/example?filter=keep&per_page=50"


def test_existing_mcp_request_tool_reaches_the_same_filtered_read(endpoint, monkeypatch):
    from canvaspilot import mcp_server

    api, seen, _ = endpoint
    monkeypatch.setattr(mcp_server, "_api", api)
    result = asyncio.run(mcp_server.canvas_api_request(
        "GET", "/api/v1/courses?state%5B%5D=available",
        params_json='{"search_term":"biology"}',
    ))
    assert json.loads(result) == {"received": True}
    assert urlsplit(seen[0]["target"]).query == "state%5B%5D=available&search_term=biology&per_page=50"

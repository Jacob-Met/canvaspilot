"""Receiving checks written separately from the CanvasPilot candidate author.

Only local fixture/MockTransport inputs are used; no Canvas or broker calls.
Malformed responses may be explicitly refused, but may not become success with
missing module contents.  Tests intentionally exercise the real API/client/MCP.
"""

import asyncio
import json
from copy import deepcopy

import httpx
import pytest

from canvaspilot import mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient


BASE = "/api/v1/courses/42/modules"
ITEMS = [
    {"id": 71, "module_id": 7, "title": "Read the lesson", "type": "Page"},
    {"id": 72, "module_id": 7, "title": "Submit the quiz", "type": "Quiz"},
]


def http_client(respond):
    client = CanvasClient(base_url="https://canvas.invalid", token="synthetic-receiving-token")
    client._http = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(respond))
    return client


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("inline", [[None], [{}], [ITEMS[0], None]])
def test_malformed_inline_must_fetch_or_explicitly_refuse(detail, inline):
    module = {"id": 7, "items_count": len(inline), "items": deepcopy(inline)}
    expected = deepcopy(ITEMS[:len(inline)])
    fixture = {"routes": {f"GET {BASE}": [module], f"GET {BASE}/7/items": expected}}
    before = deepcopy(fixture)
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        try:
            result = api.list_modules(42, detail=detail)
        except (ValueError, CanvasAuthError):
            assert fixture == before
            return
    assert fixture == before
    assert result[0]["items"] and all(isinstance(item, dict) for item in result[0]["items"])
    assert [item.get("id") for item in result[0]["items"]] == [item["id"] for item in expected]


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_boolean_count_cannot_prove_omitted_contents_are_empty(detail):
    fixture = {"routes": {
        f"GET {BASE}": [{"id": 7, "items_count": False}],
        f"GET {BASE}/7/items": [ITEMS[0]],
    }}
    before = deepcopy(fixture)
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        try:
            result = api.list_modules(42, detail=detail)
        except (ValueError, CanvasAuthError):
            assert fixture == before
            return
    assert fixture == before
    assert [item["id"] for item in result[0]["items"]] == [71]


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("payload", [None, [None], {"error": "synthetic upstream shape failure"}])
def test_malformed_secondary_payload_is_refused_by_actual_client(detail, payload):
    calls = []

    def respond(request):
        calls.append(request.url.path)
        assert request.method == "GET"
        assert request.url.host == "canvas.invalid"
        if request.url.path == BASE:
            return httpx.Response(200, json=[{"id": 7, "items_count": 1}])
        assert request.url.path == f"{BASE}/7/items"
        return httpx.Response(200, content=json.dumps(payload), headers={"Content-Type": "application/json"})

    with CanvasAPI(http_client(respond)) as api:
        with pytest.raises((ValueError, CanvasAuthError)):
            api.list_modules(42, detail=detail)
    assert calls == [BASE, f"{BASE}/7/items"]


def test_mcp_compact_cannot_serialize_malformed_inline_as_a_healthy_empty_module(monkeypatch):
    fixture = {"routes": {
        f"GET {BASE}": [{"id": 7, "items_count": 1, "items": [None]}],
        f"GET {BASE}/7/items": [ITEMS[0]],
    }}
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        monkeypatch.setattr(mcp_server, "_api", api)
        try:
            result = json.loads(asyncio.run(mcp_server.canvas_list_modules("42")))
        except (ValueError, CanvasAuthError):
            return
    assert [item["id"] for item in result[0]["items"]] == [71]


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_course_page_order_identity_and_metadata_survive_mixed_module_shapes(detail):
    modules = [
        {"id": 9, "position": 5, "name": "Inline", "items_count": 1, "items": [{"id": 91, "type": "Page"}], "state": "locked"},
        {"id": "007", "position": 2, "name": "Fetched", "items_count": 2, "items_url": "https://unrelated.invalid/ignore", "prerequisite_module_ids": [9], "require_sequential_progress": True},
        {"id": 3, "position": 1, "name": "Empty", "items_count": 0},
    ]
    item_rows = deepcopy(ITEMS)
    item_rows[0]["completion_requirement"] = {"type": "must_view", "completed": False}
    before = deepcopy((modules, item_rows))
    calls = []

    def respond(request):
        calls.append((request.url.path, request.url.params.get("page")))
        assert request.method == "GET"
        assert request.url.host == "canvas.invalid"
        if request.url.path == BASE:
            if request.url.params.get("page") == "2":
                return httpx.Response(200, json=modules[2:])
            assert request.url.params.get_list("include[]") == ["items"]
            return httpx.Response(200, json=modules[:2], headers={
                "Link": f'<https://canvas.invalid{BASE}?page=2>; rel="next"',
            })
        assert request.url.path == f"{BASE}/007/items"
        return httpx.Response(200, json=item_rows)

    with CanvasAPI(http_client(respond)) as api:
        result = api.list_modules("42", detail=detail)
    assert [module["id"] for module in result] == [9, "007", 3]
    assert [module["position"] for module in result] == [5, 2, 1]
    assert [item["id"] for item in result[1]["items"]] == [71, 72]
    assert result[2]["items"] == []
    if detail == "full":
        assert result == [modules[0], {**modules[1], "items": item_rows}, {**modules[2], "items": []}]
    assert calls == [(BASE, None), (BASE, "2"), (f"{BASE}/007/items", None)]
    assert (modules, item_rows) == before


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("status", [403, 500])
def test_later_items_page_refusal_never_returns_partial_course(detail, status):
    calls = []

    def respond(request):
        calls.append((request.url.path, request.url.params.get("page")))
        assert request.method == "GET"
        if request.url.path == BASE:
            return httpx.Response(200, json=[{"id": 7, "items_count": 2}])
        assert request.url.path == f"{BASE}/7/items"
        if request.url.params.get("page") == "2":
            return httpx.Response(status, json={"error": "synthetic later-page refusal"})
        return httpx.Response(200, json=[ITEMS[0]], headers={
            "Link": f'<https://canvas.invalid{BASE}/7/items?page=2>; rel="next"',
        })

    expected_exception = CanvasAuthError if status == 403 else httpx.HTTPStatusError
    with CanvasAPI(http_client(respond)) as api:
        with pytest.raises(expected_exception):
            api.list_modules(42, detail=detail)
    assert calls == [(BASE, None), (f"{BASE}/7/items", None), (f"{BASE}/7/items", "2")]


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_full_and_compact_fixture_resolution_leave_all_original_responses_untouched(detail):
    modules = [
        {"id": 7, "items_count": 2, "items": [ITEMS[0]], "prerequisite_module_ids": [2]},
        {"id": 9, "items_count": 0},
    ]
    fixture = {"routes": {f"GET {BASE}": modules, f"GET {BASE}/7/items": deepcopy(ITEMS)}}
    before = deepcopy(fixture)
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        result = api.list_modules(42, detail=detail)
    assert [item["id"] for item in result[0]["items"]] == [71, 72]
    assert fixture == before

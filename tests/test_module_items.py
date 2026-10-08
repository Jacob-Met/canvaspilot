"""Independent native checks for Canvas's optional inline module contents."""
import asyncio
import json
from copy import deepcopy

import httpx
import pytest

from canvaspilot import client as client_module
from canvaspilot import mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("inline", ["omitted", None, [{"id": 71, "title": "Old inline item"}]])
def test_optional_or_partial_inline_items_do_not_hide_course_content(detail, inline):
    module = {"id": 7, "name": "Synthetic course module", "items_count": 2}
    if inline != "omitted":
        module["items"] = inline
    items = [
        {"id": 71, "title": "Read the required instructions", "type": "Page"},
        {"id": 72, "title": "Complete the preparation quiz", "type": "Quiz"},
    ]
    fixture = {"routes": {
        "GET /api/v1/courses/42/modules": [module],
        "GET /api/v1/courses/42/modules/7/items": items,
    }}
    before = deepcopy(fixture)
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        result = api.list_modules(42, detail=detail)
    assert [item["id"] for item in result[0]["items"]] == [71, 72]
    assert result[0]["items"][0]["title"] == "Read the required instructions"
    assert fixture == before


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_existing_complete_inline_contents_need_no_secondary_route(detail):
    items = [{"id": 71, "title": "Available inline", "type": "Page"}]
    module = {"id": 7, "name": "Synthetic module", "items_count": 1, "items": items}
    fixture = {"routes": {"GET /api/v1/courses/42/modules": [module]}}
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        result = api.list_modules(42, detail=detail)
    assert [item["id"] for item in result[0]["items"]] == [71]


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_unavailable_secondary_route_cannot_be_reported_as_empty_module(detail):
    class RefusingClient(CanvasClient):
        def get_paginated(self, path, *, params=None):
            if path.endswith("/7/items"):
                raise CanvasAuthError("Synthetic module-item access failure")
            return super().get_paginated(path, params=params)

    fixture = {"routes": {"GET /api/v1/courses/42/modules": [
        {"id": 7, "name": "Synthetic module", "items_count": 2},
    ]}}
    before = deepcopy(fixture)
    with (
        CanvasAPI(RefusingClient(token="", fixture=fixture)) as api,
        pytest.raises(CanvasAuthError, match="module-item access failure"),
    ):
        api.list_modules(42, detail=detail)
    assert fixture == before


def test_token_module_fallback_receives_multiple_pages_through_actual_client():
    requests = []
    items = [{"id": i, "title": f"Synthetic item {i}", "type": "Page"} for i in range(1, 52)]

    def respond(request):
        requests.append((request.method, str(request.url)))
        assert request.method == "GET"
        assert request.url.host == "canvas.invalid"
        if request.url.path == "/api/v1/courses/42/modules":
            return httpx.Response(200, json=[{
                "id": 7, "items_count": 51,
                "items_url": "https://unrelated.invalid/must-not-be-followed",
            }])
        assert request.url.path == "/api/v1/courses/42/modules/7/items"
        if request.url.params.get("page") == "2":
            return httpx.Response(200, json=items[50:])
        return httpx.Response(200, json=items[:50], headers={
            "Link": '<https://canvas.invalid/api/v1/courses/42/modules/7/items?page=2>; rel="next"',
        })

    client = CanvasClient(token="synthetic-fixture-token", base_url="https://canvas.invalid")
    client._http = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(respond))
    with CanvasAPI(client) as api:
        result = api.list_modules(42)
    assert [item["id"] for item in result[0]["items"]] == list(range(1, 52))
    assert len(requests) == 3


def test_broker_module_fallback_receives_multiple_pages_through_actual_client(monkeypatch):
    requests = []
    items = [{"id": i, "title": f"Synthetic item {i}", "type": "Page"} for i in range(1, 52)]

    def broker_transport(method, url, **kwargs):
        if method == "GET":
            assert url == f"{client_module.broker_base()}/health"
            return httpx.Response(200, json={
                "ok": True, "base_url": "https://canvas.invalid", "link_pagination": True,
            })
        assert method == "POST"
        assert url == f"{client_module.broker_base()}/fetch"
        envelope = kwargs["json"]
        assert envelope["method"] == "GET"
        path = envelope["path"]
        parsed = httpx.URL(path if path.startswith("https://") else "https://canvas.invalid" + path)
        assert parsed.host == "canvas.invalid"
        assert parsed.path.startswith("/api/v1/courses/42/modules")
        requests.append((parsed.path, parsed.params.get("after")))
        link = ""
        if parsed.path == "/api/v1/courses/42/modules":
            data = [{"id": 7, "items_count": 51}]
        else:
            assert parsed.path == "/api/v1/courses/42/modules/7/items"
            assert parsed.params.get("per_page") == "50"
            if parsed.params.get("after") == "items/second":
                data = items[50:]
            else:
                data = items[:50]
                link = ('<https://canvas.invalid/api/v1/courses/42/modules/7/items'
                        '?after=items%2Fsecond&per_page=50>; rel="next"')
        return httpx.Response(200, json={"ok": True, "response": {
            "status": 200, "json": data, "headers": {"link": link},
        }})

    monkeypatch.setattr(client_module, "_broker_request", broker_transport)
    with CanvasAPI(CanvasClient(token="", base_url="https://canvas.invalid")) as api:
        result = api.list_modules(42)
    assert [item["id"] for item in result[0]["items"]] == list(range(1, 52))
    assert requests == [
        ("/api/v1/courses/42/modules", None),
        ("/api/v1/courses/42/modules/7/items", None),
        ("/api/v1/courses/42/modules/7/items", "items/second"),
    ]


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_reported_empty_module_needs_no_secondary_request(detail):
    fixture = {"routes": {"GET /api/v1/courses/42/modules": [
        {"id": 7, "items_count": 0},
    ]}}
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        result = api.list_modules(42, detail=detail)
    assert result[0]["items"] == []


@pytest.mark.parametrize("module_id", [None, "7/../../other"])
def test_missing_items_with_unusable_module_identity_are_not_silently_empty(module_id):
    fixture = {"routes": {"GET /api/v1/courses/42/modules": [
        {"id": module_id, "items_count": 2},
    ]}}
    with (
        CanvasAPI(CanvasClient(token="", fixture=fixture)) as api,
        pytest.raises(ValueError, match="valid module ID"),
    ):
        api.list_modules(42)


def test_existing_mcp_tool_returns_fetched_items_and_keeps_full_metadata(monkeypatch):
    module = {"id": 7, "items_count": 1, "state": "locked", "prerequisite_module_ids": [3]}
    item = {"id": 71, "type": "Page", "page_url": "orientation", "completion_requirement": {"type": "must_view"}}
    fixture = {"routes": {
        "GET /api/v1/courses/42/modules": [module],
        "GET /api/v1/courses/42/modules/7/items": [item],
    }}
    before = deepcopy(fixture)
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        monkeypatch.setattr(mcp_server, "_api", api)
        result = json.loads(asyncio.run(mcp_server.canvas_list_modules("42", detail="full")))
    assert result == [{**module, "items": [item]}]
    assert fixture == before


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("inline", [[None], [{}], [{"id": 71}, None]])
def test_malformed_inline_rows_are_replaced_by_valid_secondary_items(detail, inline):
    items = [{"id": 71, "type": "Page"}, {"id": 72, "type": "Quiz"}][:len(inline)]
    fixture = {"routes": {
        "GET /api/v1/courses/42/modules": [{"id": 7, "items_count": len(inline), "items": inline}],
        "GET /api/v1/courses/42/modules/7/items": items,
    }}
    before = deepcopy(fixture)
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        result = api.list_modules(42, detail=detail)
    assert [item["id"] for item in result[0]["items"]] == [item["id"] for item in items]
    assert fixture == before


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("count", [False, 0.0])
def test_only_integer_zero_proves_omitted_module_items_are_empty(detail, count):
    fixture = {"routes": {
        "GET /api/v1/courses/42/modules": [{"id": 7, "items_count": count}],
        "GET /api/v1/courses/42/modules/7/items": [{"id": 71, "type": "Page"}],
    }}
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        result = api.list_modules(42, detail=detail)
    assert [item["id"] for item in result[0]["items"]] == [71]


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("payload", [None, [None], {}, {"error": "synthetic failure"}, [{"id": 71}, None]])
def test_actual_client_malformed_secondary_payload_does_not_become_empty_success(detail, payload):
    paths = []

    def respond(request):
        assert request.method == "GET"
        assert request.url.host == "canvas.invalid"
        paths.append(request.url.path)
        if request.url.path == "/api/v1/courses/42/modules":
            return httpx.Response(200, json=[{"id": 7, "items_count": 1}])
        assert request.url.path == "/api/v1/courses/42/modules/7/items"
        return httpx.Response(200, content=json.dumps(payload), headers={"Content-Type": "application/json"})

    client = CanvasClient(token="synthetic-fixture-token", base_url="https://canvas.invalid")
    client._http = httpx.Client(base_url=client.base_url, transport=httpx.MockTransport(respond))
    with CanvasAPI(client) as api, pytest.raises(ValueError, match="malformed module items"):
        api.list_modules(42, detail=detail)
    assert paths == ["/api/v1/courses/42/modules", "/api/v1/courses/42/modules/7/items"]

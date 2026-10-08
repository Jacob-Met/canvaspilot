"""Course file listings must never become a successful root-folder subset."""

import asyncio
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from canvaspilot import mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient, CanvasPaginationError

BASE = "https://canvas.invalid"
COURSE_FILES = "/api/v1/courses/7/files"
NEXT = BASE + COURSE_FILES + "?cursor=next%2Bopaque&per_page=3"
ROOT_LOOKUP = "/api/v1/courses/7/folders/by_path"
ROOT_FILES = "/api/v1/folders/80/files"
DECOY = {"id": 99, "display_name": "Root-only decoy"}


def make_api(respond):
    client = CanvasClient(
        base_url=BASE, token="authored-fixture-token", profile=Path("unused-profile"),
    )
    client._http = httpx.Client(
        base_url=BASE, transport=httpx.MockTransport(respond), trust_env=False,
    )
    return CanvasAPI(client)


def failed_listing(failure, *, later):
    requests = []

    def respond(request):
        requests.append(request)
        # Keep both old fallback routes successful: the regression must expose
        # silently changed collection scope, not an unavailable fallback.
        if request.url.path == ROOT_LOOKUP:
            return httpx.Response(200, json=[{"id": 80}])
        if request.url.path == ROOT_FILES:
            return httpx.Response(200, json=[DECOY])
        assert request.method == "GET" and request.url.path == COURSE_FILES
        if later and len(requests) == 1:
            return httpx.Response(200, json=[{"id": 1}], headers={
                "Link": f'<{NEXT}>; rel="next"',
            })
        return failure(request)

    return make_api(respond), requests


@pytest.mark.parametrize("later", [False, True], ids=["first-page", "later-page"])
@pytest.mark.parametrize("status", [403, 404, 500])
def test_http_failure_keeps_course_scope_and_original_error(status, later):
    api, requests = failed_listing(
        lambda _request: httpx.Response(status, json={"error": "authored refusal"}),
        later=later,
    )
    error = CanvasAuthError if status == 403 else httpx.HTTPStatusError
    with api, pytest.raises(error) as caught:
        api.list_files(7)
    assert len(requests) == (2 if later else 1)
    assert all(request.url.path == COURSE_FILES for request in requests)
    if status != 403:
        assert caught.value.response.status_code == status
        assert caught.value.request.url.path == COURSE_FILES


@pytest.mark.parametrize("later", [False, True], ids=["first-page", "later-page"])
def test_transport_failure_is_not_replaced_by_root_files(later):
    original = None

    def fail(request):
        nonlocal original
        original = httpx.ReadTimeout("authored unavailable file page", request=request)
        raise original

    api, requests = failed_listing(fail, later=later)
    with api, pytest.raises(httpx.ReadTimeout) as caught:
        api.list_files("7")
    assert caught.value is original
    assert len(requests) == (2 if later else 1)
    assert all(request.url.path == COURSE_FILES for request in requests)


@pytest.mark.parametrize("failure", [
    lambda _request: httpx.Response(200, content=b"{not-json"),
    lambda _request: httpx.Response(200, json={"not": "a continuing list"}),
    lambda _request: httpx.Response(200, json=[], headers={
        "Link": '<https://foreign.invalid/files>; rel="next"',
    }),
])
def test_invalid_continuation_cannot_return_root_decoy(failure):
    api, requests = failed_listing(failure, later=True)
    with api, pytest.raises(CanvasPaginationError):
        api.list_files(7)
    assert len(requests) == 2
    assert all(request.url.path == COURSE_FILES for request in requests)


def test_complete_pages_keep_order_projection_and_literal_values():
    rows = [
        {"id": 1, "display_name": "Root 雪", "filename": "empty.txt", "size": 0,
         "updated_at": None, "url": BASE + "/file/1", "content-type": "text/plain",
         "folder_id": 80},
        {"id": 2, "display_name": "Nested <notes>", "filename": "lesson.pdf", "size": None,
         "updated_at": "2026-10-08T00:00:00Z", "url": None,
         "content_type": "application/pdf", "folder_id": 81},
    ]
    before = deepcopy(rows)
    requests = []

    def respond(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            assert request.url.params.multi_items() == [("per_page", "50")]
            return httpx.Response(200, json=rows[:1], headers={"Link": f'<{NEXT}>; rel="next"'})
        assert str(request.url) == NEXT
        return httpx.Response(200, json=rows[1:])

    with make_api(respond) as api:
        result = api.list_files(7)
    assert result == [
        {"id": 1, "display_name": "Root 雪", "filename": "empty.txt", "size": 0,
         "updated_at": None, "url": BASE + "/file/1", "content_type": "text/plain"},
        {"id": 2, "display_name": "Nested <notes>", "filename": "lesson.pdf", "size": None,
         "updated_at": "2026-10-08T00:00:00Z", "url": None,
         "content_type": "application/pdf"},
    ]
    assert len(requests) == 2 and rows == before


def test_empty_course_result_is_empty_without_folder_lookup():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    with make_api(respond) as api:
        assert api.list_files(7) == []
    assert len(requests) == 1 and requests[0].url.path == COURSE_FILES


def test_mcp_propagates_file_read_failure_without_successful_json(monkeypatch):
    api, requests = failed_listing(
        lambda _request: httpx.Response(500, json={"error": "authored failure"}), later=True,
    )
    with api, pytest.raises(httpx.HTTPStatusError):
        monkeypatch.setattr(mcp_server, "_api", api)
        asyncio.run(mcp_server.canvas_list_files("7"))
    assert len(requests) == 2
    assert all(request.url.path == COURSE_FILES for request in requests)


def test_mcp_keeps_fixture_projection_and_input_unchanged(monkeypatch):
    fixture = {"routes": {f"GET {COURSE_FILES}": [
        {"id": 1, "display_name": "A & B", "size": 0}, None, {"id": 2},
    ]}}
    before = deepcopy(fixture)
    client = CanvasClient(base_url=BASE, token="", fixture=fixture, profile=Path("unused-profile"))
    with CanvasAPI(client) as api:
        monkeypatch.setattr(mcp_server, "_api", api)
        output = json.loads(asyncio.run(mcp_server.canvas_list_files("7")))
    assert [row["id"] for row in output] == [1, 2]
    assert output[0]["size"] == 0 and output[1]["size"] is None
    assert fixture == before

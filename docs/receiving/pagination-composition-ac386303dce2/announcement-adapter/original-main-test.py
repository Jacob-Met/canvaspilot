"""Announcement completeness through the existing native HTTP client and MCP tool."""

import asyncio
import json
from copy import deepcopy
from pathlib import Path

import httpx
import pytest

from canvaspilot import mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient

BASE = "https://canvas.invalid"
ROUTE = "/api/v1/announcements"
NEXT = BASE + ROUTE + "?cursor=after%2B50%2Fkeep%3D&per_page=11&view=first&view=second"
MESSAGE = "Read & check " + "x" * 420


def announcement(item_id, course_id=7):
    return {
        "id": item_id,
        "title": f"Announcement {item_id}",
        "posted_at": "2026-10-01T12:00:00Z",
        "context_code": f"course_{course_id}",
        "message": "<p>Read &amp; check <b>" + "x" * 420 + "</b></p>",
        "html_url": f"{BASE}/courses/{course_id}/discussion_topics/{item_id}",
        "attachments": [{"id": item_id + 1000}],
    }


def http_api(respond):
    client = CanvasClient(
        base_url=BASE, token="synthetic-fixture-token", profile=Path("unused-profile"),
    )
    client._http = httpx.Client(base_url=BASE, transport=httpx.MockTransport(respond))
    return CanvasAPI(client)


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_all_pages_keep_filters_order_projection_and_opaque_continuation(detail):
    rows = [announcement(i, 7 if i % 2 else 9) for i in range(1, 62)]
    before = deepcopy(rows)
    requests = []
    course_ids = [7, "9"]

    def respond(request):
        requests.append(request)
        assert request.method == "GET" and request.url.path == ROUTE
        if len(requests) == 1:
            assert request.url.params.multi_items() == [
                ("active_only", "true"), ("per_page", "50"),
                ("context_codes[]", "course_7"), ("context_codes[]", "course_9"),
                ("start_date", "2026-10-01"),
            ]
            return httpx.Response(200, json=rows[:50], headers={"Link": f'<{NEXT}>; rel="next"'})
        assert str(request.url) == NEXT
        return httpx.Response(200, json=rows[50:])

    with http_api(respond) as api:
        result = api.list_announcements(course_ids, start_date="2026-10-01", detail=detail)

    assert len(requests) == 2
    assert [row["id"] for row in result] == list(range(1, 62))
    text = MESSAGE if detail == "full" else MESSAGE[:400] + "…"
    for actual, original in zip(result, rows, strict=True):
        assert actual == {
            "id": original["id"], "title": original["title"],
            "posted_at": original["posted_at"], "context_code": original["context_code"],
            "message_text": text, "html_url": original["html_url"],
        }
    assert rows == before and course_ids == [7, "9"]


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("first_count", [0, 1])
def test_short_or_empty_page_with_next_link_does_not_end_listing(detail, first_count):
    requests = []

    def respond(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            return httpx.Response(200, json=[announcement(1)][:first_count], headers={
                "Link": f'<{NEXT}>; rel="next"',
            })
        assert str(request.url) == NEXT
        return httpx.Response(200, json=[announcement(2)])

    with http_api(respond) as api:
        result = api.list_announcements([7], detail=detail)
    assert [row["id"] for row in result] == ([1, 2] if first_count else [2])
    assert len(requests) == 2


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_terminal_empty_response_is_empty_without_an_extra_request(detail):
    requests = []

    def respond(request):
        requests.append(request)
        assert request.url.params.get_list("context_codes[]") == ["course_7"]
        assert "start_date" not in request.url.params
        return httpx.Response(200, json=[])

    with http_api(respond) as api:
        assert api.list_announcements([7], detail=detail) == []
    assert len(requests) == 1


@pytest.mark.parametrize("detail", ["compact", "full"])
@pytest.mark.parametrize("failure, error", [
    ("forbidden", CanvasAuthError),
    ("server", httpx.HTTPStatusError),
    ("invalid_json", json.JSONDecodeError),
])
def test_later_page_failure_raises_without_returning_a_partial_listing(detail, failure, error):
    requests = []

    def respond(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            return httpx.Response(200, json=[announcement(1)], headers={
                "Link": f'<{NEXT}>; rel="next"',
            })
        assert str(request.url) == NEXT
        if failure == "invalid_json":
            return httpx.Response(200, content=b"{invalid", headers={"Content-Type": "application/json"})
        return httpx.Response(403 if failure == "forbidden" else 500, json={"error": failure})

    with http_api(respond) as api, pytest.raises(error):
        api.list_announcements([7], detail=detail)
    assert len(requests) == 2


def test_repeated_calls_receive_fresh_pages_without_reusing_rows_or_course_filters():
    requests = []
    pages = {"course_7": [announcement(71), announcement(72)],
             "course_9": [announcement(91, 9), announcement(92, 9)]}
    before = deepcopy(pages)

    def respond(request):
        requests.append(request)
        cursor = request.url.params.get("cursor")
        if cursor:
            assert list(request.url.params) == ["cursor"]
            return httpx.Response(200, json=pages[cursor][1:])
        context = request.url.params.get_list("context_codes[]")
        assert len(context) == 1
        return httpx.Response(200, json=pages[context[0]][:1], headers={
            "Link": f'<{BASE}{ROUTE}?cursor={context[0]}>; rel="next"',
        })

    with http_api(respond) as api:
        first = api.list_announcements([7])
        assert [row["id"] for row in first] == [71, 72]
        first[0]["title"] = "Caller changed its own result"
        second = api.list_announcements([9], detail="full")
        assert [row["id"] for row in second] == [91, 92]
        assert second[0]["title"] == "Announcement 91"
        assert second[0]["message_text"] == MESSAGE
    assert len(requests) == 4
    assert pages == before


@pytest.mark.parametrize("detail", ["compact", "full"])
def test_mcp_keeps_metadata_and_fixture_rows_unchanged(detail, monkeypatch):
    fixture = {"routes": {f"GET {ROUTE}": [announcement(7), None, "ignored", {"id": 9}]}}
    before = deepcopy(fixture)
    with CanvasAPI(CanvasClient(base_url=BASE, token="", profile=Path("unused-profile"), fixture=fixture)) as api:
        monkeypatch.setattr(mcp_server, "_api", api)
        result = json.loads(asyncio.run(mcp_server.canvas_list_announcements(" 7, 9 ", detail=detail)))
        assert [row["id"] for row in result] == [7, 9]
        assert result[0]["message_text"] == (MESSAGE if detail == "full" else MESSAGE[:400] + "…")
        assert result[1] == {
            "id": 9, "title": None, "posted_at": None, "context_code": None,
            "message_text": "", "html_url": None,
        }
        result[0]["title"] = "Caller changed its own result"
    assert fixture == before

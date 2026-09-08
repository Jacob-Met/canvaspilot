from canvaspilot.bundle import CURATED_MCP_TOOLS, make_api, tool_inventory
from canvaspilot import mcp_server
import pytest


def test_assert_canvas_api_path_rejects_unsafe():
    from canvaspilot.api import assert_canvas_api_path

    with pytest.raises(ValueError):
        assert_canvas_api_path("https://evil.example/api/v1/users/self")
    with pytest.raises(ValueError):
        assert_canvas_api_path("/api/v1/../admin")
    with pytest.raises(ValueError):
        assert_canvas_api_path("/v1/users/self")
    assert assert_canvas_api_path("/api/v1/users/self") == "/api/v1/users/self"


def test_api_request_escape_hatch_fixture():
    fixture = {
        "profile": {"id": 1, "name": "Fixture"},
        "routes": {
            "GET /api/v1/users/self/todo": [{"assignment": {"name": "HW"}}],
            "GET /api/v1/users/self/enrollments": [{"course_id": 7, "type": "StudentEnrollment"}],
        },
    }
    api = make_api(fixture=fixture)
    todo = api.api_paginated("/api/v1/users/self/todo")
    assert todo[0]["assignment"]["name"] == "HW"
    enroll = api.list_enrollments()
    assert enroll[0]["course_id"] == 7
    raw = api.api_request("GET", "/api/v1/users/self/todo")
    assert isinstance(raw, list)
    api.close()


def test_bundle_inventory():
    inv = tool_inventory()
    assert "canvas_api_request" in inv["escape_hatches"]
    assert "canvas_list_courses" in CURATED_MCP_TOOLS


def test_curated_tools_match_mcp_server():
    registered = sorted(
        name
        for name, fn in vars(mcp_server).items()
        if callable(fn) and name.startswith("canvas_")
    )
    assert registered == sorted(CURATED_MCP_TOOLS)

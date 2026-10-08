"""Read-only deadline overview through the native API, CLI, and MCP tool."""

import asyncio
import copy
import json
from unittest.mock import patch

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from canvaspilot import cli, mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.offline_demo import OfflineOnlyClient


@pytest.fixture(autouse=True)
def no_account_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("This sync test must use only explicit offline fixtures")

    for name in ("broker_health", "broker_fetch", "default_profile", "default_base_url"):
        monkeypatch.setattr(f"canvaspilot.client.{name}", forbidden)
    monkeypatch.setattr("canvaspilot.client.httpx.Client", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


class SyncFixtureClient(OfflineOnlyClient):
    def __init__(self, courses, assignments, *, failures=()):
        super().__init__()
        self.fixture = {"routes": {"GET /api/v1/courses": copy.deepcopy(courses)}}
        for course_id, rows in assignments.items():
            self.fixture["routes"][f"GET /api/v1/courses/{course_id}/assignments"] = copy.deepcopy(rows)
        self.calls = []
        self.failures = set(failures)

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, copy.deepcopy(kwargs)))
        if path in self.failures:
            raise RuntimeError("Synthetic read failure")
        return super().request(method, path, **kwargs)


def course(course_id):
    return {"id": course_id, "name": f"Synthetic course {course_id}"}


def assignment(assignment_id, due_at):
    return {"id": assignment_id, "name": f"Synthetic assignment {assignment_id}", "due_at": due_at}


def assignment_ids(result):
    return [row["id"] for row in result["upcoming_assignments"] if "id" in row]


def test_default_selection_takes_nearest_before_course_cap_and_orders_globally():
    client = SyncFixtureClient(
        [course(1), course(2)],
        {
            1: [assignment(n, f"2026-10-{20 + n:02d}T12:00:00Z") for n in range(1, 7)]
            + [assignment(7, "2026-10-10T12:00:00Z")],
            2: [assignment(8, "2026-10-09T12:00:00Z")],
        },
    )
    with CanvasAPI(client) as api:
        result = api.sync_summary()
    assert assignment_ids(result) == [8, 7, 1, 2, 3, 4]
    assert result["limits"] == {"courses": 10, "assignments_per_course": 5}
    assert result["course_summaries"][0]["assignments_omitted"] == 2


def test_offsets_same_instant_ties_and_original_values_are_preserved():
    rows = {
        1: [assignment(11, "2026-10-10T00:30:00+02:00"),
            assignment(12, "2026-10-09T23:00:00Z")],
        2: [assignment(21, "2026-10-09T18:30:00-04:00"),
            assignment(22, "2026-10-09T22:00:00+00:00")],
    }
    client = SyncFixtureClient([course(1), course(2)], rows)
    before = copy.deepcopy(client.fixture)
    with CanvasAPI(client) as api:
        result = api.sync_summary()
    assert assignment_ids(result) == [22, 11, 21, 12]
    originals = {row["id"]: row["due_at"] for values in rows.values() for row in values}
    assert {row["id"]: row["due_at"] for row in result["upcoming_assignments"]} == originals
    assert client.fixture == before


def test_unknown_dates_are_stable_after_known_dates_and_remain_unmodified():
    unknown = [None, "not-a-date", "2026-10-09", "2026-10-09T12:00:00", 0, {}, ""]
    rows = [assignment(i + 1, value) for i, value in enumerate(unknown)]
    rows.insert(2, assignment(99, "2026-10-09T12:00:00Z"))
    client = SyncFixtureClient([course(1)], {1: rows})
    with CanvasAPI(client) as api:
        result = api.sync_summary(limit_assignments_per_course=20)
    assert assignment_ids(result) == [99, 1, 2, 3, 4, 5, 6, 7]
    assert [row["due_at"] for row in result["upcoming_assignments"][1:]] == unknown
    assert result["course_summaries"][0]["unknown_due_dates"] == 7


def test_extreme_aware_dates_do_not_require_representable_utc_datetime():
    client = SyncFixtureClient([course(1)], {1: [
        assignment(1, "9999-12-31T23:59:59-12:00"),
        assignment(2, "0001-01-01T00:00:00+14:00"),
        assignment(3, "2026-10-09T12:00:00Z"),
    ]})
    with CanvasAPI(client) as api:
        result = api.sync_summary()
    assert assignment_ids(result) == [2, 3, 1]
    assert result["course_summaries"][0]["unknown_due_dates"] == 0


def test_counts_cover_returned_rows_including_omitted_unknowns_and_courses():
    client = SyncFixtureClient([course(1), course(2), course(3)], {
        1: [assignment(1, None), assignment(2, "2026-10-10T00:00:00Z"),
            assignment(3, "bad-date"), assignment(4, "2026-10-09T00:00:00Z")],
        2: [],
    })
    with CanvasAPI(client) as api:
        result = api.sync_summary(limit_courses=2, limit_assignments_per_course=3)
    assert result["course_count"] == 2
    assert result["courses_returned"] == 3
    assert result["courses_omitted"] == 1
    assert [row["id"] for row in result["courses"]] == [1, 2]
    assert assignment_ids(result) == [4, 2, 1]
    assert result["course_summaries"] == [
        {"course_id": 1, "status": "ok", "assignments_returned": 4,
         "assignments_included": 3, "assignments_omitted": 1, "unknown_due_dates": 2},
        {"course_id": 2, "status": "ok", "assignments_returned": 0,
         "assignments_included": 0, "assignments_omitted": 0, "unknown_due_dates": 0},
    ]
    assert [(method, path) for method, path, _ in client.calls] == [
        ("GET", "/api/v1/courses"),
        ("GET", "/api/v1/courses/1/assignments"),
        ("GET", "/api/v1/courses/2/assignments"),
    ]
    assert all(dict(kwargs["params"])["bucket"] == "upcoming" for _, _, kwargs in client.calls[1:])


def test_course_read_failure_remains_visible_with_unknown_counts():
    client = SyncFixtureClient([course(1), course(2)], {
        2: [assignment(2, "2026-10-09T00:00:00Z")],
    }, failures=["/api/v1/courses/1/assignments"])
    with CanvasAPI(client) as api:
        result = api.sync_summary()
    assert result["upcoming_assignments"][-1] == {"course_id": 1, "error": "Synthetic read failure"}
    assert assignment_ids(result) == [2]
    assert result["course_summaries"][0] == {
        "course_id": 1, "status": "error", "assignments_returned": None,
        "assignments_included": None, "assignments_omitted": None, "unknown_due_dates": None,
    }
    assert result["course_summaries"][1]["status"] == "ok"


def test_empty_course_result_has_explicit_zero_counts():
    with CanvasAPI(SyncFixtureClient([], {})) as api:
        result = api.sync_summary()
    assert result["course_count"] == result["courses_returned"] == result["courses_omitted"] == 0
    assert result["courses"] == result["upcoming_assignments"] == result["course_summaries"] == []


def test_course_list_read_failure_propagates():
    client = SyncFixtureClient([], {}, failures=["/api/v1/courses"])
    with CanvasAPI(client) as api, pytest.raises(RuntimeError, match="Synthetic read failure"):
        api.sync_summary()


@pytest.mark.parametrize("name", ["limit_courses", "limit_assignments_per_course"])
@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "2", None])
def test_api_rejects_invalid_limits_before_any_read(name, value):
    client = SyncFixtureClient([], {})
    with CanvasAPI(client) as api, pytest.raises(ValueError, match=f"{name} must be a positive integer"):
        api.sync_summary(**{name: value})
    assert client.calls == []


@pytest.mark.parametrize("explicit", [False, True])
def test_cli_returns_native_summary_and_forwards_limits(explicit, capsys):
    client = SyncFixtureClient([course(1), course(2)], {
        1: [assignment(1, "2026-10-10T00:00:00Z"), assignment(2, "2026-10-09T00:00:00Z")],
        2: [],
    })
    args = ["sync", "--base-url", "https://fixture.invalid", "--profile", ".", "--token", ""]
    if explicit:
        args += ["--limit-courses", "1", "--limit-assignments-per-course", "1"]
    with patch("canvaspilot.client.CanvasClient", return_value=client) as factory:
        cli.main(args)
    result = json.loads(capsys.readouterr().out)
    assert result["mode"] == "fixture"
    assert result["limits"] == {"courses": 1 if explicit else 10, "assignments_per_course": 1 if explicit else 5}
    assert assignment_ids(result) == ([2] if explicit else [2, 1])
    factory.assert_called_once()


@pytest.mark.parametrize("flag", ["--limit-courses", "--limit-assignments-per-course"])
@pytest.mark.parametrize("value", ["0", "-1", "1.5", "true"])
def test_cli_rejects_invalid_limits_before_client_creation(flag, value, capsys):
    with patch("canvaspilot.client.CanvasClient") as factory, pytest.raises(SystemExit) as exc:
        cli.main(["sync", flag, value])
    assert exc.value.code == 2
    assert "positive integer" in capsys.readouterr().err
    factory.assert_not_called()


def test_registered_mcp_tool_returns_same_native_summary(monkeypatch):
    client = SyncFixtureClient([course(1)], {
        1: [assignment(1, None), assignment(2, "2026-10-09T00:00:00Z")],
    })
    with CanvasAPI(client) as api:
        monkeypatch.setattr(mcp_server, "_api", api)
        result = asyncio.run(mcp_server.mcp.call_tool("canvas_sync_summary", {
            "limit_courses": 1, "limit_assignments_per_course": 1,
        }))
    assert result.is_error is False
    summary = json.loads(result.content[0].text)
    assert assignment_ids(summary) == [2]
    assert summary["course_summaries"][0]["assignments_omitted"] == 1
    assert summary["course_summaries"][0]["unknown_due_dates"] == 1


@pytest.mark.parametrize("name", ["limit_courses", "limit_assignments_per_course"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5, "2", None])
def test_mcp_rejects_invalid_limits_before_api_factory(name, value):
    with patch("canvaspilot.mcp_server._get_api") as factory, pytest.raises(ToolError):
        asyncio.run(mcp_server.mcp.call_tool("canvas_sync_summary", {name: value}))
    factory.assert_not_called()


@pytest.mark.parametrize("name", ["limit_courses", "limit_assignments_per_course"])
def test_direct_mcp_entry_rejects_invalid_limit_before_api_factory(name):
    with patch("canvaspilot.mcp_server._get_api") as factory, pytest.raises(ValueError, match="positive integer"):
        asyncio.run(mcp_server.canvas_sync_summary(**{name: True}))
    factory.assert_not_called()

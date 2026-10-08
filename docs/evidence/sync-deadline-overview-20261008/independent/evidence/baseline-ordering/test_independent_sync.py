"""Independent receiving controls; authored fixture data only, no Canvas account."""

from __future__ import annotations

import asyncio
import contextlib
import copy
import io
import json
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

from canvaspilot import cli, client as client_module, mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient


class FixtureClient(CanvasClient):
    """Exercise the real fixture transport and retain every attempted request."""

    def __init__(self, courses, assignments, *, failures=()):
        fixture = {"routes": {"GET /api/v1/courses": copy.deepcopy(courses)}}
        fixture["routes"].update(
            {
                f"GET /api/v1/courses/{course_id}/assignments": copy.deepcopy(rows)
                for course_id, rows in assignments.items()
            }
        )
        super().__init__(
            base_url="https://canvas-review.invalid",
            token="",
            profile=Path("/canvaspilot-independent-unused-profile"),
            fixture=fixture,
        )
        self.calls = []
        self.failures = {
            f"/api/v1/courses/{course_id}/assignments" for course_id in failures
        }
        self.closed = False

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, copy.deepcopy(kwargs)))
        if method != "GET" or kwargs.get("json_body") is not None or kwargs.get("data") is not None:
            raise AssertionError("sync attempted a write")
        if path in self.failures:
            raise OSError("authored assignment lookup failure")
        return super().request(method, path, **kwargs)

    def close(self):
        self.closed = True
        return super().close()


def course(course_id):
    return {"id": course_id, "name": f"Fixture course {course_id}", "course_code": f"C{course_id}"}


def assignment(assignment_id, due_at):
    return {"id": assignment_id, "name": str(assignment_id), "due_at": due_at}


def ids(summary):
    return [row["id"] for row in summary["upcoming_assignments"] if "id" in row]


def mcp_json(result):
    if getattr(result, "is_error", False) or getattr(result, "isError", False):
        raise AssertionError(f"MCP returned an error: {result}")
    texts = [block.text for block in result.content if getattr(block, "type", None) == "text"]
    if len(texts) != 1:
        raise AssertionError(f"expected one JSON text result, got {len(texts)}")
    return json.loads(texts[0])


class IndependentSyncReview(unittest.TestCase):
    def setUp(self):
        self.guards = contextlib.ExitStack()
        self.addCleanup(self.guards.close)
        for name in ("broker_health", "broker_fetch", "default_profile", "default_base_url"):
            self.guards.enter_context(
                patch.object(client_module, name, side_effect=AssertionError(f"unexpected {name} lookup"))
            )
        self.guards.enter_context(
            patch.object(socket.socket, "connect", side_effect=AssertionError("network is forbidden"))
        )
        self.guards.enter_context(
            patch.object(socket.socket, "connect_ex", side_effect=AssertionError("network is forbidden"))
        )

    def make_api(self, courses, assignments, **kwargs):
        fixture_client = FixtureClient(courses, assignments, **kwargs)
        self.addCleanup(fixture_client.close)
        return CanvasAPI(fixture_client), fixture_client

    def test_default_limits_choose_earliest_then_merge_courses(self):
        courses = [course(i) for i in range(1, 12)]
        assignments = {
            i: [assignment(f"{i}-{day}", f"2026-10-{day:02d}T12:00:00Z") for day in (20, 19, 18, 17, 16, 8)]
            for i in range(1, 12)
        }
        api, fixture_client = self.make_api(courses, assignments)
        summary = api.sync_summary()
        expected = [f"{i}-{day}" for day in (8, 16, 17, 18, 19) for i in range(1, 11)]
        self.assertEqual(ids(summary), expected)
        self.assertEqual(summary["mode"], "fixture")
        self.assertEqual(summary["course_count"], 10)
        self.assertEqual([row["id"] for row in summary["courses"]], list(range(1, 11)))
        self.assertEqual(len(fixture_client.calls), 11)
        self.assertNotIn("/api/v1/courses/11/assignments", [call[1] for call in fixture_client.calls])
        for _, _, kwargs in fixture_client.calls[1:]:
            self.assertIn(("bucket", "upcoming"), kwargs["params"])

    def test_offsets_same_instant_and_source_values_are_stable(self):
        rows = {
            1: [
                assignment("a-late", "2026-10-08T12:00:01Z"),
                assignment("a-east", "2026-10-08T14:00:00+02:00"),
                assignment("a-west", "2026-10-08T07:00:00-05:00"),
                assignment("a-first", "2026-10-08T14:00:00+03:00"),
            ],
            2: [
                assignment("b-tie", "2026-10-08T12:00:00Z"),
                assignment("b-later", "2026-10-08T11:30:00-01:00"),
            ],
        }
        api, fixture_client = self.make_api([course(1), course(2)], rows)
        snapshot = copy.deepcopy(fixture_client.fixture)
        first = api.sync_summary()
        second = api.sync_summary()
        self.assertEqual(ids(first), ["a-first", "a-east", "a-west", "b-tie", "a-late", "b-later"])
        self.assertEqual(first, second)
        self.assertEqual(fixture_client.fixture, snapshot)
        originals = {row["id"]: row["due_at"] for items in rows.values() for row in items}
        self.assertEqual({row["id"]: row["due_at"] for row in first["upcoming_assignments"]}, originals)

    def test_unknown_due_values_remain_after_known_dates(self):
        unknowns = [None, "", "2026-10-08", "2026-10-08T12:00:00", "bad-date", False, 0, [], {"date": "2026-10-08"}]
        rows = [assignment(f"unknown-{i}", value) for i, value in enumerate(unknowns)]
        rows.insert(3, assignment("known", "2026-10-09T12:00:00Z"))
        api, _ = self.make_api([course(1)], {1: rows})
        summary = api.sync_summary(limit_assignments_per_course=20)
        self.assertEqual(ids(summary), ["known"] + [f"unknown-{i}" for i in range(len(unknowns))])
        self.assertEqual([row["due_at"] for row in summary["upcoming_assignments"]][1:], unknowns)

    def test_extreme_valid_dates_and_microseconds_sort_without_float_loss(self):
        values = [
            ("last-outside-utc", "9999-12-31T23:59:59.999999-23:59"),
            ("last-plus", "9999-12-31T23:59:59.999999Z"),
            ("last", "9999-12-31T23:59:59.999998Z"),
            ("first", "0001-01-01T00:00:00Z"),
            ("first-outside-utc", "0001-01-01T00:00:00+23:59"),
        ]
        api, _ = self.make_api([course(1)], {1: [assignment(*item) for item in values]})
        summary = api.sync_summary()
        self.assertEqual(ids(summary), ["first-outside-utc", "first", "last", "last-plus", "last-outside-utc"])
        self.assertEqual({row["id"]: row["due_at"] for row in summary["upcoming_assignments"]}, dict(values))

    def test_invalid_api_limits_reject_before_lookup(self):
        for key in ("limit_courses", "limit_assignments_per_course"):
            for value in (0, -1, True, False, None, 1.0, 1.5, "2", [], {}):
                with self.subTest(key=key, value=value):
                    api, fixture_client = self.make_api([course(1)], {1: []})
                    with self.assertRaises((TypeError, ValueError)):
                        api.sync_summary(**{key: value})
                    self.assertEqual(fixture_client.calls, [])

    def test_cli_positive_limits_delegate_to_real_fixture_and_close(self):
        api, fixture_client = self.make_api(
            [course(1), course(2)],
            {1: [assignment("late", "2026-10-11T00:00:00Z"), assignment("early", "2026-10-08T00:00:00Z")], 2: []},
        )
        output = io.StringIO()
        with patch.object(client_module, "CanvasClient", return_value=fixture_client) as constructor:
            with contextlib.redirect_stdout(output):
                cli.main([
                    "sync", "--base-url", "https://canvas-review.invalid", "--profile", "/canvaspilot-independent-unused-profile",
                    "--token", "", "--limit-courses", "1", "--limit-assignments-per-course", "1",
                ])
        summary = json.loads(output.getvalue())
        self.assertEqual(ids(summary), ["early"])
        self.assertEqual(summary["course_count"], 1)
        self.assertEqual(len(fixture_client.calls), 2)
        self.assertTrue(fixture_client.closed)
        self.assertEqual(constructor.call_count, 1)

    def test_cli_invalid_limits_do_not_construct_client(self):
        for flag in ("--limit-courses", "--limit-assignments-per-course"):
            for value in ("0", "-1", "1.5", "true"):
                with self.subTest(flag=flag, value=value):
                    with patch.object(client_module, "CanvasClient", side_effect=AssertionError("client construction before validation")) as constructor:
                        with contextlib.redirect_stderr(io.StringIO()):
                            with self.assertRaises(SystemExit) as error:
                                cli.main(["sync", flag, value])
                        self.assertEqual(error.exception.code, 2)
                        constructor.assert_not_called()

    def test_registered_mcp_schema_and_explicit_limits(self):
        schemas = asyncio.run(mcp_server.mcp.list_tools())
        schema = next(tool.input_schema for tool in schemas if tool.name == "canvas_sync_summary")
        for key, default in (("limit_courses", 10), ("limit_assignments_per_course", 5)):
            item = schema["properties"][key]
            self.assertEqual(item["type"], "integer")
            self.assertEqual(item["default"], default)
            self.assertTrue(item.get("minimum", 0) >= 1 or item.get("exclusiveMinimum", -1) >= 0)
        api, fixture_client = self.make_api(
            [course(1), course(2)],
            {1: [assignment("late", "2026-10-11T00:00:00Z"), assignment("early", "2026-10-08T00:00:00Z")], 2: []},
        )
        with patch.object(mcp_server, "_get_api", return_value=api):
            result = asyncio.run(mcp_server.mcp.call_tool("canvas_sync_summary", {"limit_courses": 1, "limit_assignments_per_course": 1}))
        summary = mcp_json(result)
        self.assertEqual(ids(summary), ["early"])
        self.assertEqual(len(fixture_client.calls), 2)

    def test_registered_mcp_invalid_limits_reject_before_api_lookup(self):
        for key in ("limit_courses", "limit_assignments_per_course"):
            for value in (0, -1, True, False, None, 1.0, 1.5, "2", [], {}):
                with self.subTest(key=key, value=value):
                    with patch.object(mcp_server, "_get_api", side_effect=AssertionError("API lookup before validation")) as get_api:
                        with self.assertRaises(Exception):
                            asyncio.run(mcp_server.mcp.call_tool("canvas_sync_summary", {key: value}))
                        get_api.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

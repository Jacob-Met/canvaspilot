"""Actual CLI/MCP paths through native HTTPX; synthetic terminal Canvas responses."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys

import pytest
from grade_review_fixture import GradeReviewHTTPFixture

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient


@pytest.fixture
def receiving(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.lower().endswith("_proxy"):
            monkeypatch.delenv(name)
    fixture = GradeReviewHTTPFixture()
    env = {name: os.environ[name] for name in (
        "PATH", "SYSTEMROOT", "LANG", "TMPDIR", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
    ) if name in os.environ}
    env.update({
        "CANVAS_BASE_URL": fixture.base_url,
        "CANVAS_API_TOKEN": "grade-review-synthetic-token",
        "CANVAS_PROFILE": str(tmp_path / "unused-profile"),
        "NO_PROXY": "127.0.0.1,localhost",
    })
    try:
        yield fixture, env, tmp_path
    finally:
        fixture.close()


def test_native_http_pagination_and_cli_changed_grade_then_denial(receiving):
    fixture, env, directory = receiving
    records = []

    def cli(value="42"):
        process = subprocess.run(
            [sys.executable, "-B", "-m", "canvaspilot.cli", "grade-review", value],
            env=env, capture_output=True, text=True, timeout=15, check=False,
        )
        records.append({"exit": process.returncode, "stdout": process.stdout, "stderr": process.stderr})
        (directory / "cli-observations.json").write_text(json.dumps({
            "records": records, "requests": fixture.requests,
        }, indent=2))
        return process

    with CanvasAPI(CanvasClient(base_url=fixture.base_url, token="grade-review-synthetic-token")) as api:
        direct = api.grade_review(42)
    first = cli()
    assert first.returncode == 0 and "Traceback" not in first.stderr
    assert json.loads(first.stdout) == direct
    assert [group["id"] for group in direct["assignment_groups"]] == [3, 4]
    assert direct["collection_complete"] is None
    assert fixture.requests[2]["query"]["include[]"] == ["assignments", "submission"]
    assert fixture.requests[3]["query"] == {"cursor": ["last-page"]}

    fixture.data["groups"][1]["assignments"][0]["submission"] = {
        "assignment_id": 201, "user_id": 7, "grade": "17", "score": 17,
        "posted_at": "2026-10-08T10:00:00Z", "missing": False,
    }
    changed = cli()
    assert changed.returncode == 0
    assert json.loads(changed.stdout)["assignment_groups"][1]["assignments"][0]["submission"]["fields"]["score"] == 17
    fixture.overrides[("/api/v1/courses/42/assignment_groups", "last-page")] = (
        403, {"error": "authored later-page denial"}, {},
    )
    denied = cli()
    assert denied.returncode == 1 and denied.stdout == ""
    assert json.loads(denied.stderr.splitlines()[-1])["ok"] is False
    assert "Traceback" not in denied.stderr
    before = len(fixture.requests)
    invalid = cli("42/../99")
    assert invalid.returncode == 1 and invalid.stdout == ""
    assert len(fixture.requests) == before
    assert {request["method"] for request in fixture.requests} == {"GET"}
    assert not (directory / "unused-profile").exists()
    (directory / "cli-receiving.json").write_text(json.dumps({
        "records": records, "requests": fixture.requests,
    }, indent=2))


def test_registered_mcp_stdio_review_and_hidden_grade(receiving):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    fixture, env, directory = receiving
    records = []

    async def run():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-B", "-m", "canvaspilot.cli", "mcp"], env=env,
        )
        with (directory / "mcp-stderr.log").open("w") as error_log:
            async with (
                stdio_client(parameters, errlog=error_log) as (read, write),
                ClientSession(read, write, read_timeout_seconds=10) as session,
            ):
                await session.initialize()
                catalog = await session.list_tools()
                tool = next(item for item in catalog.tools if item.name == "canvas_grade_review")
                tool_wire = tool.model_dump(by_alias=True)
                assert tool_wire["annotations"]["readOnlyHint"] is True
                assert tool_wire["annotations"]["destructiveHint"] is False
                assert tool_wire["inputSchema"]["required"] == ["course_id"]
                assert tool_wire["inputSchema"]["properties"]["course_id"]["type"] == "string"

                async def call(arguments):
                    response = await session.call_tool("canvas_grade_review", arguments)
                    wire = response.model_dump(by_alias=True)
                    records.append(wire)
                    return wire

                wire = await call({"course_id": "42"})
                assert not wire.get("isError", False)
                result = json.loads(wire["content"][0]["text"])
                assert result["enrollments"][0]["reported_totals"]["computed_current_score"] == 0
                fixture.data["course"]["hide_final_grades"] = True
                wire = await call({"course_id": "42"})
                assert not wire.get("isError", False)
                hidden = json.loads(wire["content"][0]["text"])
                assert hidden["enrollments"][0]["reported_totals"] == {}
                assert hidden["totals_visibility"] == "hidden_by_course"
                before = len(fixture.requests)
                wire = await call({"course_id": True})
                assert wire["isError"] is True
                assert len(fixture.requests) == before

    asyncio.run(run())
    assert {request["method"] for request in fixture.requests} == {"GET"}
    assert not (directory / "unused-profile").exists()
    (directory / "mcp-receiving.json").write_text(json.dumps({
        "records": records, "requests": fixture.requests,
    }, indent=2))


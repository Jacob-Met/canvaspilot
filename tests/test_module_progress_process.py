"""Native HTTP, CLI and MCP receiving for the module-progress learner workflow."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from copy import deepcopy

import pytest
from module_progress_fixture import ModuleProgressHTTPFixture

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient


@pytest.fixture
def receiving(monkeypatch, tmp_path):
    fixture = ModuleProgressHTTPFixture()
    for name in list(os.environ):
        if name.lower().endswith("_proxy"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("CANVAS_BASE_URL", fixture.base_url)
    monkeypatch.setenv("CANVAS_API_TOKEN", "synthetic-module-progress-token")
    monkeypatch.setenv("CANVAS_PROFILE", str(tmp_path / "unused-profile"))
    try:
        yield fixture
    finally:
        fixture.close()


def cli(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "canvaspilot.cli", "module-progress", *arguments],
        capture_output=True, text=True, timeout=15, check=False,
    )


def test_native_client_preserves_module_and_item_pages_with_changed_completion(receiving, tmp_path):
    fixture = receiving
    before = deepcopy(fixture.fixture)
    with CanvasAPI(CanvasClient(base_url=fixture.base_url, token="synthetic")) as api:
        result = api.module_progress(42)
        assert [module["id"] for module in result["modules"]] == [7, 8, 9, 10]
        assert [item["id"] for item in result["modules"][0]["items"]] == [71, 72, 73]
        assert fixture.fixture == before
        assert [(r["path"], r["query"].get("page", ["1"])[0]) for r in fixture.requests] == [
            ("/api/v1/courses/42/modules", "1"),
            ("/api/v1/courses/42/modules", "2"),
            ("/api/v1/courses/42/modules/7/items", "1"),
            ("/api/v1/courses/42/modules/7/items", "2"),
        ]
        assert fixture.requests[0]["query"]["include[]"] == ["items"]
        fixture.fixture["routes"]["GET /api/v1/courses/42/modules/7/items"][1]["completion_requirement"]["completed"] = True
        changed = api.module_progress(42, module_id=7)
        assert changed["modules"][0]["remaining_work"]["incomplete_item_ids"] == []
        assert changed["modules"][0]["state"] == "started"
    assert {request["method"] for request in fixture.requests} == {"GET"}
    (tmp_path / "native-http.json").write_text(json.dumps({
        "initial": result, "changed": changed, "requests": fixture.requests,
    }, indent=2))


def test_real_cli_course_selection_empty_and_failure(receiving, tmp_path):
    fixture = receiving
    records = []

    def run(*arguments):
        process = cli(*arguments)
        records.append({"arguments": arguments, "exit": process.returncode,
                        "stdout": process.stdout, "stderr": process.stderr})
        return process

    full = run("42")
    assert full.returncode == 0
    report = json.loads(full.stdout)
    assert report["module_state_counts"]["locked"] == 1
    assert report["collection_complete"] is None
    selected = run("42", "--module-id", "8")
    assert selected.returncode == 0
    selected_report = json.loads(selected.stdout)
    assert selected_report["modules_included"] == 1
    assert selected_report["modules"][0]["remaining_work"]["rule"] == "module_completed"
    assert selected_report["modules"][0]["remaining_work"]["incomplete_item_ids"] == []

    before = len(fixture.requests)
    invalid = run("42/../99")
    assert invalid.returncode == 1 and invalid.stdout == ""
    assert json.loads(invalid.stderr)["ok"] is False
    assert len(fixture.requests) == before
    missing = run("42", "--module-id", "999")
    assert missing.returncode == 1 and missing.stdout == ""
    fixture.overrides[("/api/v1/courses/42/modules", "2")] = (403, {"error": "authored denial"}, {})
    denied = run("42")
    assert denied.returncode == 1 and denied.stdout == ""
    assert json.loads(denied.stderr.splitlines()[-1])["ok"] is False
    fixture.overrides.clear()
    fixture.fixture["routes"]["GET /api/v1/courses/42/modules"] = []
    empty = run("42")
    assert empty.returncode == 0 and json.loads(empty.stdout)["modules_returned"] == 0
    assert json.loads(empty.stdout)["collection_complete"] is None
    assert {request["method"] for request in fixture.requests} == {"GET"}
    (tmp_path / "cli-receiving.json").write_text(json.dumps({
        "records": records, "requests": fixture.requests,
    }, indent=2))


def test_real_cli_short_fallback_and_foreign_identity(receiving):
    fixture = receiving
    fixture.overrides[("/api/v1/courses/42/modules/7/items", "2")] = (200, [], {})
    short = cli("42")
    assert short.returncode == 0
    module = json.loads(short.stdout)["modules"][0]
    assert module["item_coverage"] == {
        "reported_count": 3, "returned_count": 2, "status": "shorter_than_reported_count",
    }
    assert json.loads(short.stdout)["collection_complete"] is None
    fixture.overrides.clear()
    fixture.fixture["routes"]["GET /api/v1/courses/42/modules/7/items"][0]["module_id"] = 900
    foreign = cli("42")
    assert foreign.returncode == 1 and foreign.stdout == ""
    assert "different module" in json.loads(foreign.stderr.splitlines()[-1])["message"]


def test_registered_mcp_stdio_progress_journey_and_refusals(receiving, tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    fixture = receiving
    records = []

    async def run():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "canvaspilot.cli", "mcp"], env=dict(os.environ),
        )
        with (tmp_path / "mcp-stderr.log").open("w") as errlog:
            async with (
                stdio_client(parameters, errlog=errlog) as (read, write),
                ClientSession(read, write, read_timeout_seconds=10) as session,
            ):
                await session.initialize()
                catalog = await session.list_tools()
                tool = next(tool for tool in catalog.tools if tool.name == "canvas_module_progress")
                wire = tool.model_dump(by_alias=True)
                assert wire["annotations"]["readOnlyHint"] is True
                assert wire["annotations"]["destructiveHint"] is False
                assert wire["inputSchema"]["properties"]["course_id"]["type"] == "string"
                assert set(wire["inputSchema"]["required"]) == {"course_id"}

                async def call(arguments):
                    result = await session.call_tool("canvas_module_progress", arguments)
                    wire_result = result.model_dump(by_alias=True)
                    records.append({"arguments": arguments, "result": wire_result})
                    text = "".join(row["text"] for row in wire_result["content"] if row["type"] == "text")
                    return wire_result.get("isError", False), text

                failed, text = await call({"course_id": "42"})
                assert not failed
                report = json.loads(text)
                assert report["modules_returned"] == 4
                assert report["modules"][0]["remaining_work"]["incomplete_item_ids"] == [72]
                failed, text = await call({"course_id": "42", "module_id": "9"})
                assert not failed and json.loads(text)["modules"][0]["state"] == "locked"
                assert json.loads(text)["modules"][0]["prerequisite_module_ids"] == [7]
                fixture.fixture["routes"]["GET /api/v1/courses/42/modules/7/items"][1]["completion_requirement"]["completed"] = True
                failed, text = await call({"course_id": "42", "module_id": "7"})
                assert not failed and json.loads(text)["modules"][0]["remaining_work"]["incomplete_item_ids"] == []
                assert json.loads(text)["modules"][0]["state"] == "started"

                before = len(fixture.requests)
                for arguments in (
                    {"course_id": "42/../99"}, {"course_id": True},
                    {"course_id": "42", "module_id": "invalid"},
                    {"course_id": "42", "module_id": False},
                ):
                    failed, _ = await call(arguments)
                    assert failed
                assert len(fixture.requests) == before
                failed, _ = await call({"course_id": "42", "module_id": "999"})
                assert failed
                fixture.overrides[("/api/v1/courses/42/modules", "2")] = (403, {"error": "authored denial"}, {})
                failed, _ = await call({"course_id": "42"})
                assert failed

    asyncio.run(run())
    assert {request["method"] for request in fixture.requests} == {"GET"}
    (tmp_path / "mcp-receiving.json").write_text(json.dumps({
        "records": records, "requests": fixture.requests,
    }, indent=2))


@pytest.mark.parametrize("case", [
    "singleton_module", "singleton_fallback_item", "replaced_inline_items",
])
def test_real_cli_and_mcp_report_the_normalized_reader_boundary(receiving, tmp_path, case):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    fixture = receiving
    modules_route = "GET /api/v1/courses/42/modules"
    items_route = "GET /api/v1/courses/42/modules/7/items"
    module = deepcopy(fixture.fixture["routes"][modules_route][0])
    item = deepcopy(fixture.fixture["routes"][items_route][0])
    module["items_count"] = 1
    if case == "singleton_module":
        module["items"] = [item]
        fixture.fixture["routes"][modules_route] = module
    else:
        fixture.fixture["routes"][modules_route] = [module]
        if case == "replaced_inline_items":
            module["items"] = [{"id": "invalid-inline-id", "module_id": 7}]
        fixture.fixture["routes"][items_route] = item if case == "singleton_fallback_item" else [item]
    original = deepcopy(fixture.fixture)
    process = cli("42")
    assert process.returncode == 0
    cli_report = json.loads(process.stdout)
    records = {"case": case, "upstream_fixture": original,
               "cli": {"exit": process.returncode, "stdout": process.stdout, "stderr": process.stderr}}

    async def call_mcp():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-m", "canvaspilot.cli", "mcp"], env=dict(os.environ),
        )
        with (tmp_path / "mcp-boundary-stderr.log").open("w") as errlog:
            async with (
                stdio_client(parameters, errlog=errlog) as (read, write),
                ClientSession(read, write, read_timeout_seconds=10) as session,
            ):
                await session.initialize()
                response = await session.call_tool("canvas_module_progress", {"course_id": "42"})
                wire = response.model_dump(by_alias=True)
                assert not wire.get("isError", False)
                records["mcp"] = wire
                return json.loads("".join(row["text"] for row in wire["content"] if row["type"] == "text"))

    mcp_report = asyncio.run(call_mcp())
    assert cli_report == mcp_report
    assert cli_report["reader_source"] == "CanvasAPI.list_modules(detail=full)"
    assert cli_report["upstream_response_shape"] == "not_observed"
    assert cli_report["collection_complete"] is None
    assert [row["id"] for row in cli_report["modules"]] == [7]
    module_report = cli_report["modules"][0]
    assert [row["id"] for row in module_report["items"]] == [71]
    assert module_report["state"] == "started"
    assert module_report["item_coverage"]["returned_count"] == 1
    assert module_report["remaining_work"]["incomplete_item_ids"] == []
    assert fixture.fixture == original
    assert {request["method"] for request in fixture.requests} == {"GET"}
    expected_paths = ["/api/v1/courses/42/modules"]
    if case != "singleton_module":
        expected_paths.append("/api/v1/courses/42/modules/7/items")
    assert [request["path"] for request in fixture.requests] == expected_paths * 2
    records["requests"] = fixture.requests
    (tmp_path / "normalized-reader-boundary.json").write_text(json.dumps(records, indent=2))

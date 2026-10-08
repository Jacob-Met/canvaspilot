"""Receiving at the real API/client, CLI subprocess and MCP stdio boundaries."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from folder_http_fixture import FolderBrokerFixture, FolderHTTPFixture, file, folder

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient
from canvaspilot.folder_browser import FolderBrowseError


@pytest.fixture
def receiving(tmp_path, monkeypatch):
    for name in (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    ):
        monkeypatch.delenv(name, raising=False)
    fixture = FolderHTTPFixture()
    monkeypatch.setenv("CANVAS_BASE_URL", fixture.url)
    monkeypatch.setenv("CANVAS_API_TOKEN", "authored-fixture-value")
    monkeypatch.setenv("CANVAS_PROFILE", str(tmp_path / "unused-profile"))
    monkeypatch.setenv("CANVAS_SESSION_PORT", str(fixture.server.server_port))
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    try:
        with CanvasAPI(CanvasClient()) as api:
            yield fixture, api
    finally:
        fixture.close()
        assert not (tmp_path / "unused-profile").exists()
        assert all(request["method"] == "GET" for request in fixture.requests)


def _ids(page):
    return [item["id"] for item in page["items"]]


def _cli(*arguments):
    return subprocess.run(
        [sys.executable, "-m", "canvaspilot.cli", "browse-files", *arguments],
        capture_output=True, text=True, timeout=15, env=dict(os.environ), check=False,
    )


def test_real_client_root_chosen_folder_next_pages_and_nested_file(receiving):
    fixture, api = receiving
    root = api.browse_files(42, per_page=2)
    assert root["course_id"] == "42" and root["folder"]["id"] == 100
    assert _ids(root["folders"]) == [110, 120]
    assert _ids(root["files"]) == [1001]
    assert root["folders"]["next_page_to_try"] == 2
    assert root["files"]["has_more"] is None
    second_folders = api.browse_files(42, folders_page=2, per_page=2)
    assert _ids(second_folders["folders"]) == [130]
    chosen = api.browse_files("42", "110", files_page=2, per_page=2)
    assert chosen["folder"]["name"] == "Unit 1 — 雪"
    assert _ids(chosen["folders"]) == [111]
    assert _ids(chosen["files"]) == [2003]
    nested = api.browse_files(42, 111)
    assert _ids(nested["files"]) == [3001]
    assert nested["files"]["items"][0]["filename"] == "Lab <notes>.pdf"
    assert nested["scope"] == "direct_children"
    assert len(fixture.requests) == 12
    assert fixture.requests[6]["path"] == "/api/v1/courses/42/folders/110"
    assert fixture.requests[7]["query"] == {"page": ["1"], "per_page": ["2"]}
    assert fixture.requests[8]["query"] == {"page": ["2"], "per_page": ["2"]}
    for result in (root, second_folders, chosen, nested):
        serialized = json.dumps(result)
        assert "must-not-" not in serialized and "authored body" not in serialized
        assert result["folders"]["has_more"] is None
        assert result["files"]["has_more"] is None


def test_empty_folder_is_scoped_without_a_false_completeness_claim(receiving):
    fixture, api = receiving
    result = api.browse_files(42, 120)
    assert result["folder"]["id"] == 120
    for kind in ("folders", "files"):
        assert result[kind]["items"] == []
        assert result[kind]["returned_count"] == 0
        assert result[kind]["has_more"] is None
    assert len(fixture.requests) == 3


@pytest.mark.parametrize("selected,exception", [
    (900, CanvasAuthError), (901, FolderBrowseError), (902, FolderBrowseError),
])
def test_foreign_or_mismatched_folder_stops_before_child_requests(receiving, selected, exception):
    fixture, api = receiving
    with pytest.raises(exception):
        api.browse_files(42, selected)
    assert len(fixture.requests) == 1
    assert fixture.requests[0]["path"] == f"/api/v1/courses/42/folders/{selected}"


@pytest.mark.parametrize("path,body", [
    ("/api/v1/folders/100/folders", [folder(900, 100, "Foreign", course=77)]),
    ("/api/v1/folders/100/folders", [folder(110, 999, "Wrong parent")]),
    ("/api/v1/folders/100/files", [file(1001, 999, "Wrong folder.pdf")]),
    ("/api/v1/folders/100/files", {"error": "not an array"}),
    ("/api/v1/folders/100/files", [file(1001, 100, "A"), file(1001, 100, "B")]),
])
def test_malformed_or_foreign_children_cannot_produce_a_browse_result(receiving, path, body):
    fixture, api = receiving
    fixture.overrides[path] = (200, body)
    with pytest.raises(FolderBrowseError):
        api.browse_files(42)


def test_server_cannot_exceed_requested_output_page_bound(receiving):
    fixture, api = receiving
    fixture.overrides["/api/v1/folders/100/files"] = (
        200, [file(1001, 100, "A"), file(1002, 100, "B")],
    )
    with pytest.raises(FolderBrowseError, match="page bound"):
        api.browse_files(42, per_page=1)


def test_files_permission_failure_remains_an_error(receiving):
    fixture, api = receiving
    with pytest.raises(CanvasAuthError, match="403"):
        api.browse_files(42, 130)
    assert len(fixture.requests) == 3


@pytest.mark.parametrize("arguments", [
    {"course_id": "42/../77"}, {"course_id": "42?other=77"}, {"course_id": True},
    {"course_id": "٤٢"}, {"folder_id": "root/../900"}, {"folder_id": "media"},
    {"folder_id": 0}, {"folder_id": None}, {"folders_page": 0},
    {"folders_page": 10001}, {"files_page": -1}, {"files_page": True},
    {"files_page": 1.5}, {"per_page": "2"}, {"per_page": 101}, {"per_page": 0},
])
def test_query_validation_precedes_any_client_call(arguments):
    class NoRequests:
        def request(self, *_args, **_kwargs):
            raise AssertionError("invalid query reached client")

    from canvaspilot.folder_browser import browse_course_folder

    with pytest.raises(ValueError):
        browse_course_folder(NoRequests(), **{"course_id": 42, **arguments})


def test_explicit_maximum_page_is_bounded_and_remains_unknown(receiving):
    _, api = receiving
    result = api.browse_files(42, files_page=10_000)
    assert result["files"]["page_limit_reached"] is True
    assert result["files"]["next_page_to_try"] is None
    assert result["files"]["has_more"] is None


def test_public_cli_root_selection_next_page_and_empty_folder(receiving):
    fixture, _ = receiving
    root = _cli("42", "--per-page", "2")
    assert root.returncode == 0, root.stderr
    assert _ids(json.loads(root.stdout)["folders"]) == [110, 120]
    selected = _cli("42", "--folder-id", "110", "--files-page", "2", "--per-page", "2")
    assert selected.returncode == 0, selected.stderr
    assert _ids(json.loads(selected.stdout)["files"]) == [2003]
    empty = _cli("42", "--folder-id", "120")
    assert empty.returncode == 0, empty.stderr
    assert json.loads(empty.stdout)["files"]["items"] == []
    assert len(fixture.requests) == 9


def test_public_cli_foreign_forbidden_and_invalid_queries_return_no_data(receiving):
    fixture, _ = receiving
    for selected in ("900", "901", "902", "130", "404"):
        result = _cli("42", "--folder-id", selected)
        assert result.returncode == 1 and result.stdout == ""
        # httpx's normal informational logs may precede the final structured error.
        error = json.loads(result.stderr.strip().splitlines()[-1])
        assert error["ok"] is False
        assert "Foreign private name" not in result.stderr
    before = len(fixture.requests)
    for args in (("42/../77",), ("42", "--folder-id", "media"), ("42", "--per-page", "101")):
        result = _cli(*args)
        assert result.returncode == 1 and result.stdout == ""
    assert len(fixture.requests) == before


def test_public_api_and_cli_through_actual_read_only_broker_handler(receiving, monkeypatch):
    metadata, _ = receiving
    broker = FolderBrokerFixture(metadata)
    monkeypatch.delenv("CANVAS_API_TOKEN")
    monkeypatch.setenv("CANVAS_SESSION_PORT", str(broker.server.server_port))
    monkeypatch.setattr("canvaspilot.client.BROKER_PORT", broker.server.server_port)
    try:
        with CanvasAPI(CanvasClient()) as api:
            result = api.browse_files(42, 110, files_page=2, per_page=2)
        assert _ids(result["files"]) == [2003]
        assert len(broker.jobs) == 3
        assert broker.jobs[0]["path"] == "/api/v1/courses/42/folders/110?per_page=50"
        assert broker.jobs[1]["path"] == "/api/v1/folders/110/folders?page=1&per_page=2"
        assert broker.jobs[2]["path"] == "/api/v1/folders/110/files?page=2&per_page=2"
        child = _cli("42", "--folder-id", "111")
        assert child.returncode == 0, child.stderr
        assert _ids(json.loads(child.stdout)["files"]) == [3001]
        foreign = _cli("42", "--folder-id", "900")
        assert foreign.returncode == 1 and foreign.stdout == ""
        assert len(broker.jobs) == 7
        assert all(job["method"] == "GET" and job["body"] is None for job in broker.jobs)
        assert metadata.requests == []
    finally:
        broker.close()


def test_public_mcp_stdio_browse_journey_and_refusals(receiving, tmp_path):
    fixture, _ = receiving
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

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
                tool = next(item for item in catalog.tools if item.name == "canvas_browse_files")
                wire_tool = tool.model_dump(by_alias=True)
                assert wire_tool["inputSchema"]["properties"]["per_page"]["type"] == "integer"
                assert wire_tool["annotations"]["readOnlyHint"] is True

                async def call(arguments):
                    result = await session.call_tool("canvas_browse_files", arguments)
                    wire_result = result.model_dump(by_alias=True)
                    text = "".join(item["text"] for item in wire_result["content"] if item["type"] == "text")
                    return wire_result.get("isError", False), text

                failed, text = await call({"course_id": "42", "per_page": 2})
                assert not failed and _ids(json.loads(text)["folders"]) == [110, 120]
                failed, text = await call({
                    "course_id": "42", "folder_id": "110", "files_page": 2, "per_page": 2,
                })
                chosen = json.loads(text)
                assert not failed and _ids(chosen["files"]) == [2003]
                assert chosen["files"]["has_more"] is None
                failed, text = await call({"course_id": "42", "folder_id": "120"})
                assert not failed and json.loads(text)["folders"]["items"] == []
                for selected in ("900", "901", "130"):
                    failed, text = await call({"course_id": "42", "folder_id": selected})
                    assert failed and "Foreign private name" not in text
                before = len(fixture.requests)
                for arguments in (
                    {"course_id": "42", "per_page": True},
                    {"course_id": "42", "per_page": 101},
                    {"course_id": "42", "files_page": 0},
                    {"course_id": "42/../77"},
                    {"course_id": "42", "folder_id": "media"},
                ):
                    failed, _ = await call(arguments)
                    assert failed
                assert len(fixture.requests) == before

    asyncio.run(run())

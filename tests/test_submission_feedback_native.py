"""Exercise actual HTTP, CLI subprocesses, and MCP stdio with synthetic feedback."""

import asyncio
import copy
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasAuthError, CanvasClient

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "submission_feedback.json"
ASSIGNMENT = "/api/v1/courses/41/assignments/902"
SUBMISSION = f"{ASSIGNMENT}/submissions/self"
TOKEN = "canvaspilot-disposable-fixture"


@pytest.fixture
def loopback(monkeypatch, tmp_path):
    source = json.loads(FIXTURE.read_text())
    state = {"requests": [], "source": source, "submission_status": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            request = urlsplit(self.path)
            query = parse_qs(request.query)
            state["requests"].append(
                {
                    "method": self.command,
                    "path": request.path,
                    "query": query,
                    "authorization": self.headers.get("Authorization"),
                }
            )
            status = 200
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                status, body = 401, {"error": "Synthetic token required"}
            elif request.path == ASSIGNMENT and query == {"per_page": ["50"]}:
                body = state["source"]["assignment"]
            elif request.path == SUBMISSION and query == {
                "per_page": ["50"],
                "include[]": ["submission_comments", "rubric_assessment"],
            }:
                status = state["submission_status"]
                body = (
                    state["source"]["submission"]
                    if status == 200
                    else {"error": "Synthetic refusal"}
                )
            else:
                status, body = 404, {"error": "Unrecognized fixture request"}
            encoded = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    monkeypatch.setenv("CANVAS_BASE_URL", base)
    monkeypatch.setenv("CANVAS_API_TOKEN", TOKEN)
    monkeypatch.setenv("CANVAS_PROFILE", str(tmp_path / "unused-profile"))
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    # These requests stay on the disposable loopback server. Avoid constructing
    # unrelated proxy transports (including optional SOCKS dependencies).
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    # Source checkouts and installed packages both work; the subprocess uses the
    # same interpreter and any explicitly supplied dependency path as pytest.
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join([str(ROOT / "src"), os.environ.get("PYTHONPATH", "")]),
    )
    try:
        yield state, base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def assert_wire(state, calls=1):
    assert [r["path"] for r in state["requests"]] == [ASSIGNMENT, SUBMISSION] * calls
    assert all(r["method"] == "GET" for r in state["requests"])
    assert all(r["authorization"] == f"Bearer {TOKEN}" for r in state["requests"])


def assert_report(feedback, source):
    assert feedback["assignment"]["name"] == "Synthetic research reflection"
    assert feedback["submission"]["score"] == 0
    assert feedback["submission"]["attempt"] == 2
    assert feedback["submission"]["grade_matches_current_submission"] is False
    assert feedback["rubric"]["criteria"][0]["assessment"]["points"] == 3
    assert feedback["rubric"]["criteria"][1]["assessment"]["points"] == 0
    assert (
        feedback["submission_comments"] == source["submission"]["submission_comments"]
    )


def test_api_feedback_through_actual_http(loopback):
    state, base = loopback
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        feedback = api.submission_feedback(41, 902)
    assert_report(feedback, state["source"])
    assert_wire(state)


def cli_feedback(base):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "canvaspilot.cli",
            "feedback",
            "41",
            "902",
            "--base-url",
            base,
            "--token",
            TOKEN,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_cli_feedback_through_actual_http(loopback):
    state, base = loopback
    completed = cli_feedback(base)
    assert completed.returncode == 0, completed.stderr
    assert_report(json.loads(completed.stdout), state["source"])
    assert_wire(state)


async def mcp_feedback():
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "canvaspilot.cli", "mcp"],
        cwd=ROOT,
        env={
            name: os.environ[name]
            for name in (
                "CANVAS_BASE_URL",
                "CANVAS_API_TOKEN",
                "CANVAS_PROFILE",
                "NO_PROXY",
                "no_proxy",
                "PYTHONPATH",
                "PYTHONDONTWRITEBYTECODE",
            )
        },
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            inventory = await session.list_tools()
            tool = next(
                (t for t in inventory.tools if t.name == "canvas_submission_feedback"),
                None,
            )
            assert tool is not None, (
                "Feedback tool must be available to actual MCP clients"
            )
            assert set(tool.model_dump(by_alias=True)["inputSchema"]["required"]) == {
                "course_id",
                "assignment_id",
            }
            result = await session.call_tool(
                "canvas_submission_feedback",
                {"course_id": "41", "assignment_id": "902"},
            )
            return result.model_dump(by_alias=True)


def test_mcp_feedback_through_actual_stdio_and_http(loopback):
    state, _ = loopback
    result = asyncio.run(asyncio.wait_for(mcp_feedback(), timeout=25))
    assert not result.get("isError")
    feedback = json.loads(
        "".join(item["text"] for item in result["content"] if item["type"] == "text")
    )
    assert_report(feedback, state["source"])
    assert_wire(state)


def test_actual_api_reacts_to_changed_assessment_and_attempt(loopback):
    state, base = loopback
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        first = api.submission_feedback(41, 902)
        changed = copy.deepcopy(state["source"])
        changed["submission"]["attempt"] = 3
        changed["submission"]["grade_matches_current_submission"] = True
        changed["submission"]["rubric_assessment"]["evidence"]["points"] = 6
        changed["submission"]["submission_comments"] = []
        state["source"] = changed
        second = api.submission_feedback(41, 902)
    assert first["rubric"]["criteria"][0]["assessment"]["points"] == 3
    assert second["rubric"]["criteria"][0]["assessment"]["points"] == 6
    assert second["submission"]["attempt"] == 3
    assert second["submission"]["grade_matches_current_submission"] is True
    assert second["submission_comments"] == []
    assert_wire(state, calls=2)


@pytest.mark.parametrize("status", [403, 404, 500])
def test_api_refusal_is_not_empty_feedback(loopback, status):
    state, base = loopback
    state["submission_status"] = status
    error = CanvasAuthError if status == 403 else httpx.HTTPStatusError
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        with pytest.raises(error):
            api.submission_feedback(41, 902)
    assert_wire(state)


def test_cli_refusal_does_not_print_a_success_report(loopback):
    state, base = loopback
    state["submission_status"] = 404
    completed = cli_feedback(base)
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "404" in completed.stderr
    assert_wire(state)


def test_mcp_refusal_is_a_tool_error(loopback):
    state, _ = loopback
    state["submission_status"] = 404
    result = asyncio.run(asyncio.wait_for(mcp_feedback(), timeout=25))
    assert result["isError"]
    # MCP may hide unexpected exception details. Its error flag must still
    # distinguish the failed Canvas read from a successful empty report.
    assert result["content"]
    assert_wire(state)

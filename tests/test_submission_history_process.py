"""Actual CLI processes and registered MCP stdio over authored loopback HTTP."""

import asyncio
import json
import os
import subprocess
import sys
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from test_submission_history import authored_assignment, authored_submission

TOKEN = "synthetic-submission-history-process-token"


class HistoryHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        self.server.calls.append({
            "method": self.command, "path": url.path,
            "query": parse_qs(url.query, keep_blank_values=True),
            "authorization": self.headers.get("Authorization"),
        })
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            status, payload = 401, {"error": "synthetic authorization required"}
        elif url.path == "/api/v1/courses/71/assignments/902":
            status, payload = self.server.assignment_status, self.server.assignment
        elif url.path == "/api/v1/courses/71/assignments/902/submissions/self":
            status, payload = self.server.submission_status, self.server.submission
        else:
            status, payload = 404, {"error": "unexpected fixture path"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def unexpected_write(self):
        self.server.calls.append({"method": self.command, "path": self.path})
        self.send_error(405)

    do_POST = unexpected_write
    do_PUT = unexpected_write
    do_PATCH = unexpected_write
    do_DELETE = unexpected_write
    do_HEAD = unexpected_write


@pytest.fixture
def history_http(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), HistoryHandler)
    server.daemon_threads = True
    server.assignment = authored_assignment()
    server.submission = authored_submission()
    server.assignment_status = server.submission_status = 200
    server.calls = []
    server.profile = tmp_path / "unused-profile"
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def process_env(server):
    env = os.environ.copy()
    env.update({
        "CANVAS_BASE_URL": server.base_url,
        "CANVAS_API_TOKEN": TOKEN,
        "CANVAS_PROFILE": str(server.profile),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_PROXY": "127.0.0.1,localhost",
    })
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    return env


def record(name, payload):
    destination = os.environ.get("CANVAS_HISTORY_RECEIPTS_DIR")
    if destination:
        root = Path(destination)
        root.mkdir(parents=True, exist_ok=True)
        with (root / f"{name}.json").open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


def assert_read_pair(calls):
    assert [row["method"] for row in calls] == ["GET", "GET"]
    assert [row["path"] for row in calls] == [
        "/api/v1/courses/71/assignments/902",
        "/api/v1/courses/71/assignments/902/submissions/self",
    ]
    assert calls[0]["query"].get("include[]", []) == []
    assert calls[1]["query"]["include[]"] == [
        "submission_history", "submission_comments",
    ]
    assert all(row["authorization"] == f"Bearer {TOKEN}" for row in calls)
    assert all("read_status" not in json.dumps(row) for row in calls)


@pytest.mark.parametrize("variant,exit_code", [
    ("rich", 0), ("empty", 0), ("unavailable", 0),
    ("bad_history", 1), ("bad_comments", 1),
    ("bad_submission", 1), ("auth_refused", 1), ("read_refused", 1),
])
def test_actual_cli_report_and_refusals(history_http, variant, exit_code):
    server = history_http
    if variant == "empty":
        server.submission = {"attempt": 5, "submission_history": [], "submission_comments": []}
    elif variant == "unavailable":
        server.submission = {"attempt": 5}
    elif variant == "bad_history":
        server.submission["submission_history"] = [{}, None]
    elif variant == "bad_comments":
        server.submission["submission_comments"] = "not a list"
    elif variant == "bad_submission":
        server.submission = []
    elif variant == "auth_refused":
        server.assignment_status = 403
    elif variant == "read_refused":
        server.submission_status = 503
    original = deepcopy((server.assignment, server.submission))
    process = subprocess.run(
        [sys.executable, "-B", "-m", "canvaspilot.cli",
         "submission-history", "00071", "0902"],
        env=process_env(server), text=True, capture_output=True, timeout=30,
        check=False,
    )
    record(f"cli-{variant}", {
        "returncode": process.returncode, "stdout": process.stdout,
        "stderr": process.stderr, "requests": server.calls,
    })
    assert process.returncode == exit_code
    assert not server.profile.exists()
    assert (server.assignment, server.submission) == original
    if exit_code:
        assert process.stdout == ""
        error = json.loads(process.stderr)
        assert error["ok"] is False
        assert error["error"] in {"ValueError", "CanvasAuthError", "HTTPStatusError"}
        if variant == "auth_refused":
            assert len(server.calls) == 1
        else:
            assert_read_pair(server.calls)
        return
    assert process.stderr == ""
    report = json.loads(process.stdout)
    assert_read_pair(server.calls)
    if variant == "rich":
        assert report["current_submission"]["attempt"] == 3
        assert report["current_submission"]["grade_matches_current_submission"] is False
        assert report["history"]["records"] == server.submission["submission_history"]
        assert report["submission_comments"] == server.submission["submission_comments"]
        assert "submission_comments" not in report["current_submission"]
        assert report["history"]["records"][0]["score"] == 0
        assert report["history"]["records"][1]["score"] is None
    elif variant == "empty":
        assert report["history"] == {"returned": True, "records": []}
        assert report["submission_comments"] == []
    else:
        assert report["history"] == {"returned": False, "records": None}
        assert report["submission_comments"] is None


def test_actual_cli_invalid_id_fails_without_a_request(history_http):
    process = subprocess.run(
        [sys.executable, "-B", "-m", "canvaspilot.cli",
         "submission-history", "71/other", "902"],
        env=process_env(history_http), text=True, capture_output=True, timeout=30,
        check=False,
    )
    record("cli-invalid-id", {
        "returncode": process.returncode, "stdout": process.stdout,
        "stderr": process.stderr, "requests": history_http.calls,
    })
    assert process.returncode == 1
    assert process.stdout == ""
    assert json.loads(process.stderr)["error"] == "ValueError"
    assert history_http.calls == []
    assert not history_http.profile.exists()


def test_registered_mcp_stdio_history_unknowns_and_errors(history_http):
    async def exercise():
        server = history_http
        params = StdioServerParameters(
            command=sys.executable,
            args=["-B", "-m", "canvaspilot.mcp_server"],
            env=process_env(server),
        )
        observations = []
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            catalog = await session.list_tools()
            tool = next(t for t in catalog.tools if t.name == "canvas_submission_history")
            assert tool.annotations.model_dump(by_alias=True)["readOnlyHint"] is True
            assert tool.annotations.model_dump(by_alias=True)["destructiveHint"] is False
            arguments = {"course_id": "71", "assignment_id": "902"}
            result = await session.call_tool(tool.name, arguments)
            observations.append(result.model_dump(mode="json", by_alias=True))
            assert not result.model_dump(by_alias=True)["isError"]
            report = json.loads(result.content[0].text)
            assert report["history"]["records"] == server.submission["submission_history"]
            assert report["current_submission"]["score"] == 12
            assert_read_pair(server.calls[-2:])

            server.submission = {"attempt": 4, "submission_history": None}
            result = await session.call_tool(tool.name, arguments)
            observations.append(result.model_dump(mode="json", by_alias=True))
            assert not result.model_dump(by_alias=True)["isError"]
            report = json.loads(result.content[0].text)
            assert report["history"] == {"returned": False, "records": None}
            assert report["current_submission"] == {"attempt": 4}
            assert_read_pair(server.calls[-2:])

            server.submission = {"submission_history": [42]}
            result = await session.call_tool(tool.name, arguments)
            observations.append(result.model_dump(mode="json", by_alias=True))
            assert result.model_dump(by_alias=True)["isError"]
            assert "malformed submission history" in result.content[0].text
            assert_read_pair(server.calls[-2:])

            count = len(server.calls)
            result = await session.call_tool(
                tool.name, {"course_id": "71", "assignment_id": "not-an-id"},
            )
            observations.append(result.model_dump(mode="json", by_alias=True))
            assert result.model_dump(by_alias=True)["isError"]
            assert len(server.calls) == count

            server.submission_status = 503
            result = await session.call_tool(tool.name, arguments)
            observations.append(result.model_dump(mode="json", by_alias=True))
            assert result.model_dump(by_alias=True)["isError"]
            assert_read_pair(server.calls[-2:])
        record("mcp-stdio", {"responses": observations, "requests": server.calls})
        assert not server.profile.exists()

    asyncio.run(exercise())

"""Receive current-user assignment facts through actual HTTP, CLI and MCP."""

import asyncio
import copy
import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

ROOT = Path(os.environ.get("CANVAS_SUBMISSION_SOURCE", Path(__file__).resolve().parents[1]))
TOKEN = "canvaspilot-synthetic-assignment-reader"
COURSES = "/api/v1/courses"
ASSIGNMENTS = f"{COURSES}/41/assignments"
SECOND_COURSE = f"{COURSES}/57/assignments"


def synthetic_rows():
    def row(identifier, due_at, **extra):
        return {
            "id": identifier, "name": f"Synthetic assignment {identifier}",
            "due_at": due_at, "points_possible": 0, "submission_types": ["online_upload"],
            "html_url": f"https://fixture.invalid/assignments/{identifier}",
            "has_submitted_submissions": True, **extra,
        }

    return [
        row(901, "2026-10-10T12:00:00+02:00", submission={
            "workflow_state": "unsubmitted", "attempt": 0, "missing": True,
            "late": False, "excused": False, "submitted_at": None,
            "body": "Synthetic private answer excluded from a list",
            "score": 0, "attachments": [{"id": 3}],
        }),
        row(902, "2026-10-09T14:00:00Z", submission={
            "workflow_state": "submitted", "attempt": 2, "late": True,
            "missing": False, "excused": False, "submitted_at": "2026-10-08T07:14:30-04:00",
        }),
        row(903, None, submission=[]),
        row(904, "1900-01-01T00:00:00Z"),
        row(905, "2026-10-11T00:00:00Z", submission={
            "workflow_state": "future_reported_state", "missing": "false",
            "attempt": True, "late": False, "excused": None,
        }),
    ]


@pytest.fixture
def loopback(monkeypatch, tmp_path, request):
    state = {"requests": [], "rows": synthetic_rows(), "later_status": 200, "outputs": []}
    state["second_rows"] = [{
        "id": 906, "name": "Synthetic studio review", "due_at": "2026-10-08T12:00:00Z",
        "has_submitted_submissions": False, "submission": {"excused": True, "missing": False},
    }]

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            state["requests"].append({
                "method": self.command, "path": parsed.path, "query": query,
                "synthetic_token_matched": self.headers.get("Authorization") == f"Bearer {TOKEN}",
            })
            status, body, next_link = 200, None, None
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                status, body = 401, {"error": "Synthetic token required"}
            elif parsed.path == COURSES and query == {
                "per_page": ["50"], "enrollment_state": ["active"],
                "include[]": ["term", "total_scores"],
            }:
                body = [{"id": 41, "name": "Synthetic field methods"},
                        {"id": 57, "name": "Synthetic studio"}]
            elif parsed.path in (ASSIGNMENTS, SECOND_COURSE):
                expected = {"per_page": ["50"], "order_by": ["due_at"],
                            "include[]": ["submission"]}
                if "bucket" in query:
                    expected["bucket"] = ["upcoming"]
                page = query.get("page", ["1"])
                if page == ["2"]:
                    expected["page"] = ["2"]
                if query != expected or page not in (["1"], ["2"]):
                    status, body = 400, {"error": "Unrecognized assignment query"}
                elif parsed.path == SECOND_COURSE:
                    body = state["second_rows"]
                elif page == ["1"]:
                    body = state["rows"][:2]
                    expected["page"] = ["2"]
                    next_link = (f"http://127.0.0.1:{server.server_port}{ASSIGNMENTS}?"
                                 + urlencode(expected, doseq=True))
                else:
                    status = state["later_status"]
                    body = state["rows"][2:] if status == 200 else {"error": "Synthetic later-page refusal"}
            else:
                status, body = 404, {"error": "Unrecognized fixture request"}
            encoded = json.dumps(body, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            if next_link is not None:
                self.send_header("Link", f'<{next_link}>; rel="next"')
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
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")

    # Restrict both the API caller and real child processes to this disposable
    # endpoint. AF_UNIX socket pairs used for process plumbing remain available.
    guard = tmp_path / "guard"
    guard.mkdir()
    guard_source = (
        "import socket\n"
        f"_allowed = ('127.0.0.1', {server.server_port})\n"
        "_connect, _connect_ex = socket.socket.connect, socket.socket.connect_ex\n"
        "def _check(address):\n"
        "    if isinstance(address, tuple) and address != _allowed:\n"
        "        raise AssertionError('Only the disposable Canvas fixture is allowed')\n"
        "def _guarded(self, address):\n"
        "    _check(address)\n"
        "    return _connect(self, address)\n"
        "def _guarded_ex(self, address):\n"
        "    _check(address)\n"
        "    return _connect_ex(self, address)\n"
        "socket.socket.connect = _guarded\n"
        "socket.socket.connect_ex = _guarded_ex\n"
    )
    (guard / "sitecustomize.py").write_text(guard_source)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([
        str(guard), str(ROOT / "src"), os.environ.get("PYTHONPATH", ""),
    ]))
    connect = socket.socket.connect

    def guarded_connect(connection, address):
        if isinstance(address, tuple) and address != ("127.0.0.1", server.server_port):
            raise AssertionError("Only the disposable Canvas fixture is allowed")
        return connect(connection, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    try:
        yield state, base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        if destination := os.environ.get("CANVAS_SUBMISSION_EVIDENCE"):
            directory = Path(destination)
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{request.node.name}.json").write_text(
                json.dumps(state, indent=2, allow_nan=False) + "\n"
            )


def assert_wire(state, expected_paths):
    assert [entry["path"] for entry in state["requests"]] == expected_paths
    assert all(entry["method"] == "GET" and entry["synthetic_token_matched"]
               for entry in state["requests"])


def assert_state(rows):
    assert [row["id"] for row in rows] == [901, 902, 903, 904, 905]
    by_id = {row["id"]: row for row in rows}
    assert by_id[901]["submission"] == {
        "workflow_state": "unsubmitted", "attempt": 0, "missing": True,
        "late": False, "excused": False, "submitted_at": None,
    }
    assert by_id[902]["submission"]["attempt"] == 2
    assert by_id[902]["submission"]["late"] is True
    assert by_id[902]["submission"]["submitted_at"] == "2026-10-08T07:14:30-04:00"
    assert by_id[903]["submission"] is None
    assert len(by_id[903]["submission_warnings"]) == 1
    assert by_id[904]["submission"] is None
    assert by_id[904]["submission_warnings"] == []
    assert by_id[904]["has_submitted_submissions"] is True
    assert by_id[904]["due_at"] == "1900-01-01T00:00:00Z"
    assert by_id[905]["submission"] == {
        "workflow_state": "future_reported_state", "late": False, "excused": None,
    }
    assert {warning.split(":")[0] for warning in by_id[905]["submission_warnings"]} == {
        "submission.attempt", "submission.missing",
    }


def run_cli(state, base, *args):
    command = [sys.executable, "-B", "-m", "canvaspilot.cli", *args,
               "--base-url", base, "--token", TOKEN]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                               timeout=20, check=False)
    state["outputs"].append({"boundary": "cli", "arguments": list(args),
                             "exit_code": completed.returncode,
                             "stdout": completed.stdout, "stderr": completed.stderr})
    return completed


async def run_mcp(state, calls):
    parameters = StdioServerParameters(
        command=sys.executable, args=["-B", "-m", "canvaspilot.cli", "mcp"], cwd=ROOT,
        env={name: os.environ[name] for name in (
            "CANVAS_BASE_URL", "CANVAS_API_TOKEN", "CANVAS_PROFILE",
            "NO_PROXY", "no_proxy", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE",
        )},
    )
    async with (
        stdio_client(parameters) as (read, write),
        ClientSession(read, write) as session,
    ):
        initialized = await session.initialize()
        inventory = await session.list_tools()
        state["outputs"].append({
            "boundary": "mcp_initialize", "result": initialized.model_dump(by_alias=True),
            "tool_names": [tool.name for tool in inventory.tools],
        })
        assert {"canvas_list_assignments", "canvas_sync_summary"} <= {
            tool.name for tool in inventory.tools
        }
        results = []
        for name, arguments in calls:
            result = (await session.call_tool(name, arguments)).model_dump(by_alias=True)
            state["outputs"].append({"boundary": "mcp", "tool": name,
                                     "arguments": arguments, "result": result})
            results.append(result)
        return results


def decoded_tool(result):
    assert not result.get("isError"), result
    return json.loads("".join(item["text"] for item in result["content"] if item["type"] == "text"))


def test_real_http_and_cli_keep_current_user_facts_across_pages(loopback):
    state, base = loopback
    with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
        rows = api.list_assignments("41", bucket=None)
    state["outputs"].append({"boundary": "api", "result": rows})
    completed = run_cli(state, base, "assignments", "41", "--bucket", "")
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == rows
    assert_wire(state, [ASSIGNMENTS, ASSIGNMENTS] * 2)
    assert_state(rows)


def test_cli_reports_changed_current_user_state_with_unchanged_aggregate(loopback):
    state, base = loopback
    before = run_cli(state, base, "assignments", "41", "--bucket", "")
    assert before.returncode == 0, before.stderr
    state["rows"] = copy.deepcopy(state["rows"])
    state["rows"][0]["submission"] = {
        "workflow_state": "submitted", "attempt": 1, "missing": False, "late": False,
    }
    after = run_cli(state, base, "assignments", "41", "--bucket", "")
    assert after.returncode == 0, after.stderr
    first, second = json.loads(before.stdout)[0], json.loads(after.stdout)[0]
    assert first["has_submitted_submissions"] is second["has_submitted_submissions"] is True
    assert first["submission"]["missing"] is True
    assert second["submission"] == state["rows"][0]["submission"]
    assert_wire(state, [ASSIGNMENTS, ASSIGNMENTS] * 2)


def assert_summary(summary):
    assert summary["course_count"] == summary["courses_returned"] == 2
    assert summary["courses_omitted"] == 0
    assert [row["id"] for row in summary["upcoming_assignments"]] == [904, 906, 902, 901, 905, 903]
    selected = {row["id"]: row for row in summary["upcoming_assignments"]}
    assert_state([selected[identifier] for identifier in (901, 902, 903, 904, 905)])
    assert selected[906]["submission"] == {"excused": True, "missing": False}
    assert summary["course_summaries"][0] == {
        "course_id": 41, "status": "ok", "assignments_returned": 5,
        "assignments_included": 5, "assignments_omitted": 0, "unknown_due_dates": 1,
    }
    assert summary["limits"] == {"courses": 2, "assignments_per_course": 10}


def test_cli_sync_propagates_state_without_extra_per_assignment_reads(loopback):
    state, base = loopback
    completed = run_cli(state, base, "sync", "--limit-courses", "2",
                        "--limit-assignments-per-course", "10")
    assert completed.returncode == 0, completed.stderr
    assert_wire(state, [COURSES, ASSIGNMENTS, ASSIGNMENTS, SECOND_COURSE])
    assert_summary(json.loads(completed.stdout))


def test_registered_mcp_assignment_and_sync_tools_propagate_the_same_facts(loopback):
    state, _ = loopback
    results = asyncio.run(asyncio.wait_for(run_mcp(state, [
        ("canvas_list_assignments", {"course_id": "41", "bucket": ""}),
        ("canvas_sync_summary", {"limit_courses": 2, "limit_assignments_per_course": 10}),
    ]), timeout=25))
    assert_wire(state, [ASSIGNMENTS, ASSIGNMENTS, COURSES, ASSIGNMENTS, ASSIGNMENTS, SECOND_COURSE])
    assert_state(decoded_tool(results[0]))
    assert_summary(decoded_tool(results[1]))


def test_cli_later_page_failure_does_not_emit_a_partial_success_list(loopback):
    state, base = loopback
    state["later_status"] = 500
    completed = run_cli(state, base, "assignments", "41", "--bucket", "")
    assert completed.returncode != 0
    assert completed.stdout == ""
    assert "500" in completed.stderr
    assert_wire(state, [ASSIGNMENTS, ASSIGNMENTS])


@pytest.mark.parametrize("status", [403, 500])
def test_mcp_later_page_refusal_remains_a_tool_error(loopback, status):
    state, _ = loopback
    state["later_status"] = status
    result, = asyncio.run(asyncio.wait_for(run_mcp(state, [
        ("canvas_list_assignments", {"course_id": "41", "bucket": ""}),
    ]), timeout=25))
    assert result["isError"]
    assert result["content"]
    assert_wire(state, [ASSIGNMENTS, ASSIGNMENTS])


def test_cli_sync_preserves_course_failure_and_another_courses_reported_state(loopback):
    state, base = loopback
    state["later_status"] = 500
    completed = run_cli(state, base, "sync", "--limit-courses", "2",
                        "--limit-assignments-per-course", "10")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["course_summaries"][0] == {
        "course_id": 41, "status": "error", "assignments_returned": None,
        "assignments_included": None, "assignments_omitted": None, "unknown_due_dates": None,
    }
    rows = result["upcoming_assignments"]
    assert len(rows) == 2
    assert rows[0]["id"] == 906
    assert rows[1]["course_id"] == 41 and "500" in rows[1]["error"]
    assert "submission" not in rows[1]
    assert_wire(state, [COURSES, ASSIGNMENTS, ASSIGNMENTS, SECOND_COURSE])
    assert rows[0]["submission"] == {"excused": True, "missing": False}

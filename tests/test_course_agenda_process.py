"""Real CLI and registered MCP processes over paginated authored HTTP data."""

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
from course_agenda_fixture import END, START, TOKEN, calendar_records
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import canvaspilot


class AgendaHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query, keep_blank_values=True)
        self.server.calls.append({"method": self.command, "path": url.path, "query": query})
        status, headers, payload = 200, {}, []
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            status, payload = 401, {"error": "authored token required"}
        elif url.path != "/api/v1/calendar_events":
            status, payload = 404, {"error": "unexpected path"}
        else:
            cursor = query.get("cursor", [None])[0]
            kind = cursor.split("-", 1)[0] if cursor else query.get("type", [None])[0]
            if kind not in self.server.records:
                status, payload = 400, {"error": "missing collection type"}
            else:
                rows = self.server.records[kind]
                split = 2 if kind == "event" else 1
                payload = deepcopy(rows[split:] if cursor else rows[:split])
                if not cursor:
                    headers["Link"] = f'<{self.server.base_url}{url.path}?cursor={kind}-2>; rel="next"'
                elif kind == "assignment":
                    variant = self.server.variant
                    if variant == "denied":
                        status, payload = 403, {"error": "authored permission refusal"}
                    elif variant == "nonlist":
                        payload = {"id": 8, "context_code": "course_42"}
                    elif variant == "cycle":
                        headers["Link"] = f'<{self.server.base_url}{url.path}?cursor={kind}-2>; rel="next"'
                    elif variant == "foreign":
                        payload[0]["context_code"] = "course_900"
                    elif variant == "invalid_json":
                        payload = b"not valid JSON"
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def refuse_write(self):
        self.server.calls.append({"method": self.command, "path": self.path})
        self.send_error(405)

    do_POST = refuse_write
    do_PUT = refuse_write
    do_PATCH = refuse_write
    do_DELETE = refuse_write


@pytest.fixture
def agenda_http(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), AgendaHandler)
    server.daemon_threads = True
    server.records = calendar_records()
    server.calls, server.variant = [], "healthy"
    server.profile = tmp_path / "unused-agenda-profile"
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
    source = str(Path(canvaspilot.__file__).resolve().parent.parent)
    env.update({
        "CANVAS_BASE_URL": server.base_url,
        "CANVAS_API_TOKEN": TOKEN,
        "CANVAS_PROFILE": str(server.profile),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": os.pathsep.join(filter(None, (source, env.get("PYTHONPATH")))),
        "NO_PROXY": "127.0.0.1,localhost",
    })
    # Authored loopback traffic stays local; no shared proxy setting is changed.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    return env


def record(name, value):
    destination = os.environ.get("CANVAS_AGENDA_RECEIPTS_DIR")
    if destination:
        path = Path(destination)
        path.mkdir(parents=True, exist_ok=True)
        with (path / f"{name}.json").open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


def run_cli(server, course_ids=("42", "00077")):
    return subprocess.run(
        [sys.executable, "-B", "-m", "canvaspilot.cli", "agenda", *course_ids,
         "--start", START, "--end", END],
        env=process_env(server), text=True, capture_output=True, timeout=25, check=False,
    )


def assert_complete_reads(calls):
    assert len(calls) == 4
    assert all(call["method"] == "GET" and call["path"] == "/api/v1/calendar_events" for call in calls)
    for index, kind in ((0, "event"), (2, "assignment")):
        first, continuation = calls[index:index + 2]
        assert first["query"] == {
            "type": [kind], "start_date": [START], "end_date": [END],
            "context_codes[]": ["course_42", "course_77"], "per_page": ["50"],
        }
        assert continuation["query"] == {"cursor": [f"{kind}-2"]}


def assert_native_report(report, records):
    assert report["counts"] == {"total": 6, "timed": 4, "all_day": 1, "timing_unavailable": 1}
    assert [entry["record"]["title"] for entry in report["timed"]] == [
        "Seminar — 水", "Reading response", "Measured example", "Section-specific activity",
    ]
    all_entries = report["timed"] + report["all_day"] + report["timing_unavailable"]
    assert len(all_entries) == 6
    for entry in all_entries:
        assert entry["record"] == records[entry["source"]["collection"]][entry["source"]["index"]]
    assert report["all_day"][0]["record"]["all_day_date"] == "2026-10-10"
    assert report["timed"][-1]["course_id"] == "42"


def test_actual_cli_combines_both_paginated_calendar_types(agenda_http):
    server = agenda_http
    original = deepcopy(server.records)
    result = run_cli(server)
    record("cli-success", {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "requests": server.calls})
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert_native_report(json.loads(result.stdout), original)
    assert_complete_reads(server.calls)
    assert server.records == original and not server.profile.exists()


@pytest.mark.parametrize("variant", ["denied", "nonlist", "cycle", "foreign", "invalid_json"])
def test_actual_cli_refuses_late_failure_without_partial_report(agenda_http, variant):
    server = agenda_http
    original = deepcopy(server.records)
    server.variant = variant
    result = run_cli(server)
    record(f"cli-{variant}", {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "requests": server.calls})
    assert result.returncode == 1
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["ok"] is False
    assert error["error"] in {"ValueError", "CanvasPaginationError", "CanvasAuthError"}
    assert_complete_reads(server.calls)
    assert server.records == original and not server.profile.exists()


def test_actual_cli_rejects_duplicate_selection_before_read(agenda_http):
    result = run_cli(agenda_http, ("42", "0042"))
    record("cli-duplicate", {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "requests": agenda_http.calls})
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "ValueError"
    assert agenda_http.calls == [] and not agenda_http.profile.exists()


def test_registered_mcp_tool_reads_refuses_and_recovers(agenda_http, tmp_path):
    async def exercise():
        server = agenda_http
        original = deepcopy(server.records)
        observations = []
        params = StdioServerParameters(
            command=sys.executable, args=["-B", "-m", "canvaspilot.mcp_server"],
            env=process_env(server),
        )
        with (tmp_path / "mcp.stderr").open("w+") as error_log:
            async with stdio_client(params, errlog=error_log) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                catalog = await session.list_tools()
                tool = next(t for t in catalog.tools if t.name == "canvas_course_agenda")
                assert tool.annotations.model_dump(by_alias=True)["readOnlyHint"] is True
                assert tool.annotations.model_dump(by_alias=True)["destructiveHint"] is False
                arguments = {"course_ids": [42, "00077"], "start_date": START, "end_date": END}
                first = await session.call_tool(tool.name, arguments)
                observations.append(first.model_dump(mode="json", by_alias=True))
                assert not first.model_dump(by_alias=True)["isError"]
                report = json.loads(first.content[0].text)
                assert_native_report(report, original)
                assert_complete_reads(server.calls[-4:])
                server.variant = "denied"
                refused = await session.call_tool(tool.name, arguments)
                observations.append(refused.model_dump(mode="json", by_alias=True))
                assert refused.model_dump(by_alias=True)["isError"] and "403" in refused.content[0].text
                assert_complete_reads(server.calls[-4:])
                count = len(server.calls)
                invalid = await session.call_tool(tool.name, {**arguments, "course_ids": [True]})
                observations.append(invalid.model_dump(mode="json", by_alias=True))
                assert invalid.model_dump(by_alias=True)["isError"] and len(server.calls) == count
                server.variant = "healthy"
                recovered = await session.call_tool(tool.name, arguments)
                observations.append(recovered.model_dump(mode="json", by_alias=True))
                assert not recovered.model_dump(by_alias=True)["isError"]
                assert json.loads(recovered.content[0].text) == report
                assert_complete_reads(server.calls[-4:])
            error_log.seek(0)
            stderr = error_log.read()
        record("mcp-stdio", {"responses": observations, "requests": server.calls, "stderr": stderr})
        assert server.records == original and not server.profile.exists()

    asyncio.run(asyncio.wait_for(exercise(), timeout=35))

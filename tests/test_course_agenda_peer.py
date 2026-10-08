"""Independent real-process receiving for the selected-course agenda.

All data is authored. Calls use the real CanvasClient/HTTPX paginator and the
registered MCP stdio server, directed only at the owned loopback fixture.
"""
from __future__ import annotations

import asyncio
import hashlib
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

ROOT = Path(os.environ.get("CANVAS_AGENDA_SOURCE", Path(__file__).resolve().parents[1]))
TOKEN = "synthetic-e827-agenda-peer-only"

DATA = json.loads("{\"selection\":{\"course_ids\":[\"00023\",\"61\"],\"canonical_course_ids\":[\"23\",\"61\"],\"context_codes\":[\"course_23\",\"course_61\"],\"start_date\":\"2026-10-08\",\"end_date\":\"2026-10-11\"},\"event_pages\":[[{\"id\":701,\"title\":\"Offset studio\",\"context_code\":\"course_23\",\"all_day\":false,\"start_at\":\"2026-10-09T10:30:00+05:30\",\"end_at\":\"2026-10-09T11:00:00+05:30\",\"description\":\"<b>Preserve & explain</b>\\nsecond line\",\"hidden\":true,\"workflow_state\":\"active\"},{\"id\":702,\"title\":\"Section observance\",\"context_code\":\"course_section_91\",\"effective_context_code\":\"course_61\",\"all_day\":true,\"all_day_date\":\"2026-10-08\",\"start_at\":\"2026-10-08T00:00:00+02:00\",\"end_at\":null,\"child_events\":[],\"all_context_codes\":\"course_61,course_section_91\"},{\"id\":703,\"title\":\"Later fractional event\",\"context_code\":\"course_61\",\"all_day\":false,\"start_at\":\"2026-10-09T04:00:00.0000000002Z\",\"end_at\":null}],[{\"id\":704,\"title\":\"Saved time unavailable\",\"context_code\":\"course_23\",\"all_day\":false,\"start_at\":null,\"all_day_date\":\"2026-10-09\",\"description\":\"<script>literal only</script>\"},{\"id\":705,\"title\":\"Flag has wrong type\",\"context_code\":\"course_61\",\"all_day\":\"false\",\"start_at\":\"2026-10-09T05:10:00Z\"},{\"id\":706,\"title\":\"Negative half-hour offset\",\"context_code\":\"course_23\",\"all_day\":false,\"start_at\":\"2026-10-10T00:00:00-03:30\"}]],\"assignment_pages\":[[{\"id\":\"assignment_801\",\"title\":\"Earlier fractional override\",\"context_code\":\"course_61\",\"all_day\":false,\"start_at\":\"2026-10-09T00:00:00.0000000001-04:00\",\"end_at\":\"2026-10-09T00:00:00.0000000001-04:00\",\"assignment\":{\"id\":801,\"course_id\":61,\"due_at\":\"2026-10-11T23:59:00Z\",\"points_possible\":0},\"assignment_overrides\":[{\"id\":11,\"course_section_id\":91,\"due_at\":\"2026-10-09T00:00:00.0000000001-04:00\"}]},{\"id\":\"assignment_802\",\"title\":\"Declared all-day assignment\",\"context_code\":\"course_23\",\"all_day\":true,\"all_day_date\":\"2026-10-09\",\"start_at\":\"2026-10-09T23:59:00-04:00\",\"assignment\":{\"id\":802,\"course_id\":\"23\",\"due_at\":null},\"assignment_overrides\":[]}],[{\"id\":\"assignment_801\",\"title\":\"Same ID, separate returned override\",\"context_code\":\"course_61\",\"all_day\":false,\"start_at\":\"2026-10-09T04:00:00Z\",\"assignment\":{\"id\":801,\"course_id\":61},\"assignment_overrides\":[{\"id\":12,\"student_ids\":[9001,9002]}]},{\"id\":\"assignment_804\",\"title\":\"No offset supplied\",\"context_code\":\"course_23\",\"all_day\":false,\"start_at\":\"2026-10-09T10:00:00\",\"assignment\":{\"id\":804,\"course_id\":23}}]]}")
EXPECTED = json.loads("{\"schema\":\"canvaspilot.course-agenda.v1\",\"collection_counts\":{\"event\":6,\"assignment\":4},\"counts\":{\"total\":10,\"timed\":5,\"all_day\":2,\"timing_unavailable\":3},\"timed_sources\":[[\"assignment\",2],[\"assignment\",0],[\"event\",2],[\"event\",0],[\"event\",5]],\"all_day_sources\":[[\"event\",1],[\"assignment\",1]],\"unavailable_sources\":[[\"event\",3],[\"event\",4],[\"assignment\",3]],\"record_rule\":\"Every full record equals its source JSON value, including identities/types, nested overrides, literal text, unknown flags and original timestamps. Course binding resolves section91 to selected course61. Duplicate assignment_801 records stay distinct by source index. No fallback to nested assignment.due_at, midnight, host time zone or local date refiltering.\",\"page_rule\":\"Two real HTTP pages per collection. First requests carry exact normalized context filters and inclusive date strings. Next links contain only opaque percent-encoded cursor queries; original filters must not be appended to the continuation. GET only, synthetic bearer only, loopback only.\"}")


def source_hashes():
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((ROOT / "src" / "canvaspilot").glob("*.py"))
    }


def keep(name, value):
    target = os.environ.get("CANVAS_AGENDA_PEER_RECEIPTS")
    if target:
        directory = Path(target)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / f"{name}.json").open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")


class AgendaHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        query = parse_qs(url.query, keep_blank_values=True)
        self.server.calls.append({
            "method": self.command, "path": url.path, "raw_query": url.query,
            "query": query,
            "synthetic_authorization": self.headers.get("Authorization") == f"Bearer {TOKEN}",
        })
        status, body, link = 200, [], None
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            status, body = 401, {"error": "synthetic bearer required"}
        elif url.path != "/api/v1/calendar_events":
            status, body = 404, {"error": "unexpected fixture endpoint"}
        else:
            cursor = query.get("cursor", [None])[0]
            if cursor in ("event+next", "assignment+next"):
                kind, page = cursor.split("+")[0], 1
            elif query.get("type") in (["event"], ["assignment"]):
                kind, page = query["type"][0], 0
            else:
                status, body, kind, page = 400, {"error": "missing collection selection"}, None, None
            if kind:
                body = self.server.pages[kind][page]
                if page == 0:
                    link = f'<{self.server.base_url}/api/v1/calendar_events?cursor={kind}%2Bnext>; rel="next"'
                elif self.server.mode == "repeated_link" and kind == "event":
                    link = f'<{self.server.base_url}/api/v1/calendar_events?cursor=event%2Bnext>; rel="next"'
                elif self.server.mode == "late_denial" and kind == "assignment":
                    status, body = 403, {"error": "authored late refusal"}
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if link:
            self.send_header("Link", link)
        self.end_headers()
        self.wfile.write(encoded)

    def reject_write(self):
        self.server.calls.append({"method": self.command, "path": self.path})
        self.send_error(405)

    do_POST = reject_write
    do_PUT = reject_write
    do_PATCH = reject_write
    do_DELETE = reject_write


@pytest.fixture
def agenda_server(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), AgendaHandler)
    server.daemon_threads = True
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    server.profile = tmp_path / "no-browser-profile"
    server.pages = {"event": deepcopy(DATA["event_pages"]), "assignment": deepcopy(DATA["assignment_pages"])}
    server.calls = []
    server.mode = "normal"
    original_source = source_hashes()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not server.profile.exists()
        assert source_hashes() == original_source, "native source changed during receiving"


def child_env(server):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("CANVAS_"):
            env.pop(key)
    previous_pythonpath = os.environ.get("PYTHONPATH", "")
    env.update({
        "CANVAS_BASE_URL": server.base_url,
        "CANVAS_API_TOKEN": TOKEN,
        "CANVAS_PROFILE": str(server.profile),
        "PYTHONPATH": str(ROOT / "src") + (os.pathsep + previous_pythonpath if previous_pythonpath else ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_PROXY": "127.0.0.1,localhost",
    })
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(name, None)
    return env


def cli(server, name, courses=None, start=None, end=None):
    selection = DATA["selection"]
    arguments = [
        sys.executable, "-B", "-m", "canvaspilot.cli", "agenda",
        *(selection["course_ids"] if courses is None else courses),
        "--start", selection["start_date"] if start is None else start,
        "--end", selection["end_date"] if end is None else end,
    ]
    before = deepcopy(server.pages)
    result = subprocess.run(
        arguments, env=child_env(server), cwd=ROOT,
        capture_output=True, text=True, timeout=30, check=False,
    )
    keep(name, {
        "args": arguments, "returncode": result.returncode,
        "stdout": result.stdout, "stderr": result.stderr,
        "calls": server.calls, "source": source_hashes(),
    })
    assert server.pages == before
    assert not server.profile.exists()
    return result


def assert_collection_requests(calls):
    assert len(calls) == 4
    assert all(call["method"] == "GET" and call["path"] == "/api/v1/calendar_events"
               and call["synthetic_authorization"] for call in calls)
    first = [call for call in calls if "type" in call["query"]]
    following = [call for call in calls if "cursor" in call["query"]]
    assert sorted(call["query"]["type"][0] for call in first) == ["assignment", "event"]
    for call in first:
        assert call["query"] == {
            "type": call["query"]["type"],
            "context_codes[]": ["course_23", "course_61"],
            "start_date": ["2026-10-08"], "end_date": ["2026-10-11"],
            "per_page": ["50"],
        }
    assert sorted(call["raw_query"] for call in following) == [
        "cursor=assignment%2Bnext", "cursor=event%2Bnext",
    ]
    assert sorted(call["query"]["cursor"][0] for call in following) == [
        "assignment+next", "event+next",
    ]


def sources(entries):
    return [[entry["source"]["collection"], entry["source"]["index"]] for entry in entries]


def assert_complete(report, server):
    assert report["schema"] == EXPECTED["schema"]
    assert report["selection"] == {
        "course_ids": ["23", "61"], "context_codes": ["course_23", "course_61"],
        "start_date": "2026-10-08", "end_date": "2026-10-11",
    }
    assert report["collection_counts"] == EXPECTED["collection_counts"]
    assert report["counts"] == EXPECTED["counts"]
    assert sources(report["timed"]) == EXPECTED["timed_sources"]
    assert sources(report["all_day"]) == EXPECTED["all_day_sources"]
    assert sorted(sources(report["timing_unavailable"])) == sorted(EXPECTED["unavailable_sources"])
    all_entries = report["timed"] + report["all_day"] + report["timing_unavailable"]
    assert len(all_entries) == 10
    seen = set()
    flat = {kind: [row for page in pages for row in page] for kind, pages in server.pages.items()}
    for entry in all_entries:
        kind, index = entry["source"]["collection"], entry["source"]["index"]
        assert (kind, index) not in seen
        seen.add((kind, index))
        assert entry["kind"] == kind
        original = flat[kind][index]
        assert entry["record"] == original
        expected_course = "61" if original.get("effective_context_code") == "course_61" else original["context_code"].split("_")[-1]
        assert entry["course_id"] == expected_course
    assert seen == {(kind, index) for kind, records in flat.items() for index in range(len(records))}
    issues = {tuple(sources([entry])[0]): entry["timing_issue"] for entry in report["timing_unavailable"]}
    assert issues[("event", 3)]["field"] == "start_at"
    assert issues[("event", 4)]["field"] == "all_day"
    assert issues[("assignment", 3)]["field"] == "start_at"
    assert all(isinstance(issue["reason"], str) and issue["reason"] for issue in issues.values())


def test_peer_actual_cli_preserves_complete_agenda_and_empty_result(agenda_server):
    server = agenda_server
    result = cli(server, "cli-complete")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert_complete(json.loads(result.stdout), server)
    assert_collection_requests(server.calls)

    server.calls.clear()
    server.pages = {"event": [[], []], "assignment": [[], []]}
    result = cli(server, "cli-empty")
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert report["counts"] == {"total": 0, "timed": 0, "all_day": 0, "timing_unavailable": 0}
    assert report["collection_counts"] == {"event": 0, "assignment": 0}
    assert report["timed"] == report["all_day"] == report["timing_unavailable"] == []
    assert_collection_requests(server.calls)


@pytest.mark.parametrize("variant", ["foreign", "conflicting", "malformed", "late_denial", "repeated_link"])
def test_peer_actual_cli_refuses_partial_or_conflicting_collection(agenda_server, variant):
    server = agenda_server
    if variant == "foreign":
        server.pages["assignment"][1][-1]["context_code"] = "course_999"
    elif variant == "conflicting":
        server.pages["assignment"][1][-1]["assignment"]["course_id"] = 61
    elif variant == "malformed":
        server.pages["assignment"][1].append(None)
    else:
        server.mode = variant
    result = cli(server, "cli-" + variant)
    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["ok"] is False
    assert error["error"] in {"ValueError", "CanvasAuthError", "CanvasPaginationError"}
    assert all(call["method"] == "GET" for call in server.calls)
    if variant == "repeated_link":
        assert len(server.calls) == 2, "repeated opaque page must not be fetched again"
    else:
        assert_collection_requests(server.calls)


@pytest.mark.parametrize("variant,courses,start,end", [
    ("duplicate", ["23", "00023"], None, None),
    ("too_many", [str(value) for value in range(1, 12)], None, None),
    ("non_ascii", ["٢٣"], None, None),
    ("bad_date", None, "2026-1-08", None),
    ("reversed", None, "2026-10-12", "2026-10-11"),
])
def test_peer_actual_cli_invalid_selection_makes_no_request(agenda_server, variant, courses, start, end):
    result = cli(agenda_server, "cli-invalid-" + variant, courses, start, end)
    assert result.returncode == 1, result.stderr
    assert result.stdout == ""
    assert json.loads(result.stderr)["ok"] is False
    assert agenda_server.calls == []


def test_peer_registered_mcp_stdio_refusal_and_recovery(agenda_server):
    server = agenda_server

    async def receive():
        params = StdioServerParameters(
            command=sys.executable, args=["-B", "-m", "canvaspilot.mcp_server"],
            env=child_env(server), cwd=str(ROOT),
        )
        observations = []
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            catalog = await session.list_tools()
            names = [tool.name for tool in catalog.tools]
            assert "canvas_course_agenda" in names
            tool = next(tool for tool in catalog.tools if tool.name == "canvas_course_agenda")
            annotations = tool.annotations.model_dump(by_alias=True)
            assert annotations["readOnlyHint"] is True
            assert annotations["destructiveHint"] is False
            assert annotations["idempotentHint"] is True
            arguments = {
                "course_ids": ["00023", 61],
                "start_date": "2026-10-08", "end_date": "2026-10-11",
            }

            async def invoke(args):
                result = await session.call_tool(tool.name, args)
                observations.append(result.model_dump(mode="json", by_alias=True))
                return result

            result = await invoke(arguments)
            assert result.model_dump(by_alias=True)["isError"] is False
            assert_complete(json.loads(result.content[0].text), server)
            assert_collection_requests(server.calls)

            server.calls.clear()
            server.mode = "late_denial"
            result = await invoke(arguments)
            assert result.model_dump(by_alias=True)["isError"] is True
            assert_collection_requests(server.calls)

            server.calls.clear()
            result = await invoke({**arguments, "course_ids": [True]})
            assert result.model_dump(by_alias=True)["isError"] is True
            assert server.calls == []

            server.mode = "normal"
            result = await invoke(arguments)
            assert result.model_dump(by_alias=True)["isError"] is False
            assert_complete(json.loads(result.content[0].text), server)
            assert_collection_requests(server.calls)
        keep("mcp-recovery", {
            "responses": observations, "final_calls": server.calls,
            "source": source_hashes(),
        })

    asyncio.run(receive())

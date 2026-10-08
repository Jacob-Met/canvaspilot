"""Independent contract receiving for issue 49; only synthetic loopback traffic."""
from __future__ import annotations

import asyncio
import copy
import importlib
import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import pytest

RECEIVER = Path(__file__).resolve().parent
SOURCE = Path(os.environ["INBOX_REVIEW_SOURCE"]).resolve()
RESULTS = Path(os.environ["INBOX_REVIEW_RESULT_DIR"]).resolve()
sys.path.insert(0, str(SOURCE))
for key in list(os.environ):
    if key.startswith("CANVAS_") or key.lower().endswith("_proxy"):
        del os.environ[key]
os.environ["CANVAS_PROFILE"] = str(RECEIVER / "unused-profile")
os.environ["CANVAS_API_TOKEN"] = ""
os.environ["CANVAS_BASE_URL"] = "http://127.0.0.1:1"
from canvaspilot.api import CanvasAPI  # noqa: E402
from canvaspilot.client import CanvasAuthError, CanvasClient, CanvasPaginationError  # noqa: E402

client_module = importlib.import_module("canvaspilot.client")
assert Path(client_module.__file__).resolve().is_relative_to(SOURCE)

def authored_conversations():
    rows = []
    for conversation_id, state in [(501, "unread"), (303, "read"), (88, "archived")]:
        rows.append({
            "id": conversation_id, "subject": "明日の予定 — Åsa 🧭",
            "workflow_state": state, "last_message": "e\u0301, שלום; <p>kept</p>",
            "last_message_at": "2026-10-08T12:00:00Z", "message_count": 2,
            "subscribed": state != "archived", "private": True,
            "starred": conversation_id == 303,
            "properties": ["attachments", "last_author"] if conversation_id == 303 else ["attachments"],
            "audience": [17, 6], "audience_contexts": {"courses": {"42": ["StudentEnrollment"]}, "groups": {}},
            "avatar_url": "https://media.example.invalid/avatars/17",
            "participants": [
                {"id": 17, "name": "Åsa 🧭", "full_name": "Åsa Example", "uuid": "fixture-17", "extension": {"roles": [None, False]}},
                {"id": 6, "name": "李", "full_name": "李 Example", "avatar_url": "https://media.example.invalid/avatars/6"},
            ],
            "visible": state != "archived", "context_name": "Synthetic seminar",
            "messages": [
                {"id": conversation_id * 10 + 9, "created_at": "2026-10-08T12:00:00Z",
                 "body": "<p>明日 09:00 — e\u0301 / שלום 🧭</p>\n\"quoted\" & unchanged",
                 "author_id": 17, "generated": False,
                 "media_comment": {"display_name": "音声", "content-type": "audio/ogg", "media_id": "m1",
                                   "media_type": "audio", "url": "https://media.example.invalid/audio"},
                 "forwarded_messages": [
                     {"id": 4, "body": "forwarded 👩🏽‍💻", "author_id": 6, "generated": False,
                      "forwarded_messages": [{"id": 2, "body": "deeply forwarded", "forwarded_messages": [], "attachments": []}],
                      "attachments": [{"id": 71, "display_name": "résumé.pdf", "content-type": "application/pdf",
                                       "filename": "資料.pdf", "url": "https://files.example.invalid/71?download=1"}]},
                 ],
                 "attachments": [{"id": 72, "display_name": "notes.txt", "filename": "notes.txt",
                                  "url": "https://files.example.invalid/72", "extension": {"retained": [0, False, None]}}],
                 "future_field": {"preserve": ["z", "a"]}},
                {"id": conversation_id * 10 + 1, "created_at": "2026-10-07T09:00:00Z",
                 "body": "", "author_id": 6, "generated": True, "media_comment": None,
                 "forwarded_messages": [], "attachments": []},
            ],
            "submissions": [], "extension": {"opaque": {"b": 2, "a": 1}, "missing_is_not_false": None},
        })
    return rows

def summaries(rows):
    return [{key: copy.deepcopy(value) for key, value in row.items() if key != "messages"} for row in rows]

class Provider:
    """A contract fixture, not a Canvas emulator or a real school receiver."""
    def __init__(self):
        self.rows = authored_conversations()
        self.before = copy.deepcopy(self.rows)
        self.requests = []
        self.processes = []
        self.continuations = {}
        self.fail_next = None
        self.counter = 0
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def reply(self, status, payload, headers=None):
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path == "/health":
                    fixture.requests.append({"transport": "health", "method": "GET", "path": "/health"})
                    return self.reply(200, {"ok": True, "base_url": fixture.base_url, "link_pagination": True})
                status, payload, headers = fixture.canvas(
                    "GET", self.path, "token", self.headers.get("Authorization") == "Bearer synthetic-inbox-peer"
                )
                self.reply(status, payload, headers)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                if self.path != "/fetch" or not 0 <= length <= 65536:
                    fixture.requests.append({"transport": "unexpected", "method": "POST", "path": self.path})
                    return self.reply(400, {"error": "fixture rejected unexpected route"})
                envelope = json.loads(self.rfile.read(length))
                fixture.requests.append({"transport": "broker-envelope", "method": "POST", "path": "/fetch",
                                         "envelope": envelope})
                assert envelope["op"] == "fetch" and envelope["body"] is None
                assert "Authorization" not in envelope["headers"]
                status, payload, headers = fixture.canvas(envelope["method"], envelope["path"], "session", True)
                self.reply(200, {"ok": True, "response": {
                    "status": status, "json": payload, "text": json.dumps(payload),
                    "headers": {"link": headers.get("Link", "")},
                }})

            def do_PUT(self):
                fixture.requests.append({"transport": "unexpected", "method": "PUT", "path": self.path})
                self.reply(405, {"error": "writes are not fixture operations"})

            do_DELETE = do_PUT
            do_PATCH = do_PUT

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def canvas(self, method, target, mode, auth_ok):
        parsed = urlsplit(target)
        assert not parsed.netloc or parsed.netloc == f"127.0.0.1:{self.port}"
        query = parse_qs(parsed.query, keep_blank_values=True)
        self.requests.append({"transport": "canvas", "mode": mode, "method": method,
                              "path": parsed.path, "raw_query": parsed.query, "query": query,
                              "synthetic_auth_ok": auth_ok})
        if method != "GET" or not auth_ok:
            return 403, {"errors": [{"message": "fixture admission refused"}]}, {}
        if parsed.path == "/api/v1/conversations":
            if "cursor" in query:
                assert set(query) == {"cursor", "view"} and query["view"] == ["a", "b"]
                key = query["cursor"][0]
                tail, link = self.continuations[key]
                if self.fail_next == "denied":
                    return 403, {"errors": [{"message": "synthetic second-page denial"}]}, {}
                if self.fail_next == "shape":
                    return 200, {"error": "not a conversation array"}, {}
                if self.fail_next == "cycle":
                    return 200, copy.deepcopy(tail), {"Link": f'<{link}>; rel="next"'}
                return 200, copy.deepcopy(tail), {}
            scope = query.get("scope", [None])[0]
            if scope not in (None, "unread", "starred", "archived", "sent"):
                return 400, {"errors": [{"message": "undocumented list scope"}]}, {}
            selected = self.selected(scope)
            values = summaries(selected)
            if len(values) < 2:
                return 200, values, {}
            self.counter += 1
            cursor = f"cursor+/{self.counter}/☃"
            link = self.base_url + "/api/v1/conversations?" + urlencode(
                [("cursor", cursor), ("view", "a"), ("view", "b")]
            )
            self.continuations[cursor] = (values[1:], link)
            return 200, values[:1], {"Link": f'<{link}>; rel="next"'}
        prefix = "/api/v1/conversations/"
        if parsed.path.startswith(prefix):
            conversation_id = parsed.path[len(prefix):]
            if conversation_id == "999":
                return 403, {"errors": [{"message": "synthetic inaccessible conversation"}]}, {}
            row = next((item for item in self.rows if str(item["id"]) == conversation_id), None)
            if row is None:
                return 404, {"errors": [{"message": "synthetic missing conversation"}]}, {}
            # Official show behavior: omission defaults to true.
            if query.get("auto_mark_as_read", ["true"]) != ["false"] and row["workflow_state"] == "unread":
                row["workflow_state"] = "read"
            return 200, copy.deepcopy(row), {}
        return 404, {"errors": [{"message": "fixture has no such endpoint"}]}, {}

    def selected(self, scope):
        if scope == "unread":
            return [row for row in self.rows if row["workflow_state"] == "unread"]
        if scope == "archived":
            return [row for row in self.rows if row["workflow_state"] == "archived"]
        if scope == "starred":
            return [row for row in self.rows if row["starred"]]
        if scope == "sent":
            return [row for row in self.rows if "last_author" in row["properties"]]
        return [row for row in self.rows if row["workflow_state"] != "archived"]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

@pytest.fixture(params=["token", "session"])
def receiving(request, monkeypatch):
    fixture = Provider()
    mode = request.param
    monkeypatch.setattr(client_module, "BROKER_PORT", fixture.port)
    monkeypatch.setenv("CANVAS_SESSION_PORT", str(fixture.port))
    monkeypatch.setenv("CANVAS_BASE_URL", fixture.base_url)
    monkeypatch.setenv("CANVAS_API_TOKEN", "synthetic-inbox-peer" if mode == "token" else "")
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def admission(address):
        if not isinstance(address, tuple) or address[:2] != ("127.0.0.1", fixture.port):
            raise RuntimeError("independent receiver refused a non-fixture connection")

    def connect(sock, address):
        admission(address)
        return original_connect(sock, address)

    def connect_ex(sock, address):
        admission(address)
        return original_connect_ex(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    try:
        yield fixture, mode
    finally:
        fixture.close()
        assert not (RECEIVER / "unused-profile").exists()
        RESULTS.mkdir(parents=True, exist_ok=True)
        (RESULTS / (request.node.name.replace("/", "_") + ".json")).write_text(json.dumps({
            "case": request.node.name, "mode": mode, "state_before": fixture.before, "state_after": fixture.rows,
            "requests": fixture.requests, "processes": fixture.processes,
        }, ensure_ascii=False, indent=2) + "\n")

def api_for(fixture, mode):
    return CanvasAPI(CanvasClient(
        base_url=fixture.base_url, token="synthetic-inbox-peer" if mode == "token" else "",
        profile=RECEIVER / "unused-profile",
    ))

def canvas_requests(fixture):
    return [row for row in fixture.requests if row["transport"] == "canvas"]

def test_details_preserve_all_states_nested_fields_and_order(receiving):
    fixture, mode = receiving
    before = copy.deepcopy(fixture.rows)
    with api_for(fixture, mode) as api:
        observed = [api.get_conversation(row["id"]) for row in before]
        repeated = api.get_conversation("501")
    assert observed == before and repeated == before[0]
    assert fixture.rows == before
    calls = canvas_requests(fixture)
    assert [row["query"]["auto_mark_as_read"] for row in calls] == [["false"]] * 4
    assert all(row["method"] == "GET" and row["synthetic_auth_ok"] for row in calls)

def test_scope_mapping_ordered_opaque_pages_and_empty_list(receiving):
    fixture, mode = receiving
    with api_for(fixture, mode) as api:
        for scope in [None, "inbox", "unread", "starred", "archived", "sent"]:
            start = len(canvas_requests(fixture))
            result = api.list_conversations() if scope is None else api.list_conversations(scope=scope)
            assert result == summaries(fixture.selected(None if scope == "inbox" else scope))
            first = canvas_requests(fixture)[start]
            assert first["query"].get("scope") == (None if scope in (None, "inbox") else [scope])
            continuation = canvas_requests(fixture)[start + 1:]
            assert all(set(row["query"]) == {"cursor", "view"} for row in continuation)
        assert fixture.rows == fixture.before
        fixture.rows = []
        assert api.list_conversations() == []

def test_incomplete_list_and_auth_failure_never_return_partial_success(receiving):
    fixture, mode = receiving
    with api_for(fixture, mode) as api:
        for failure, expected in [("denied", CanvasAuthError), ("shape", CanvasPaginationError), ("cycle", CanvasPaginationError)]:
            fixture.fail_next = failure
            with pytest.raises(expected):
                api.list_conversations()
        fixture.fail_next = None
        with pytest.raises(CanvasAuthError):
            api.get_conversation("999")
    assert fixture.rows == fixture.before
    assert {row["method"] for row in canvas_requests(fixture)} == {"GET"}

def child_arguments(fixture, *arguments):
    return [sys.executable, "-B", str(RECEIVER / "loopback_guard.py"),
            str(fixture.port), str(SOURCE), *arguments]

def cli(fixture, *arguments):
    result = subprocess.run(
        child_arguments(fixture, *arguments), cwd=RECEIVER, env=dict(os.environ),
        capture_output=True, text=True, timeout=20, check=False,
    )
    fixture.processes.append({"kind": "CLI", "arguments": list(arguments), "exit": result.returncode,
                              "stdout": result.stdout, "stderr": result.stderr})
    return result

def test_actual_cli_json_state_and_partial_failure_receiving(receiving):
    fixture, _mode = receiving
    full = cli(fixture, "inbox")
    detail = cli(fixture, "conversation", "501")
    archived = cli(fixture, "inbox", "--scope", "archived")
    fixture.fail_next = "denied"
    failed = cli(fixture, "inbox")
    assert full.returncode == detail.returncode == archived.returncode == 0
    assert json.loads(full.stdout) == summaries([fixture.before[0], fixture.before[1]])
    assert json.loads(detail.stdout) == fixture.before[0]
    assert json.loads(archived.stdout) == summaries([fixture.before[2]])
    assert failed.returncode != 0 and failed.stdout == ""
    assert fixture.rows == fixture.before
    assert {row["method"] for row in canvas_requests(fixture)} == {"GET"}

def test_actual_mcp_registered_tools_preserve_messages_and_refuse_failure(receiving):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    fixture, _mode = receiving

    async def run():
        args = child_arguments(fixture, "mcp")
        parameters = StdioServerParameters(command=args[0], args=args[1:], env=dict(os.environ), cwd=str(RECEIVER))
        RESULTS.mkdir(parents=True, exist_ok=True)
        with (RESULTS / f"mcp-{_mode}-stderr.log").open("w") as stderr:
            async with (
                stdio_client(parameters, errlog=stderr) as (read, write),
                ClientSession(read, write, read_timeout_seconds=15) as session,
            ):
                await session.initialize()
                catalog = await session.list_tools()
                wires = {tool.name: tool.model_dump(by_alias=True) for tool in catalog.tools}
                fixture.processes.append({"kind": "MCP catalog", "tools": wires})

                async def call(name, arguments):
                    response = await session.call_tool(name, arguments)
                    wire = response.model_dump(by_alias=True)
                    fixture.processes.append({"kind": "MCP call", "name": name, "arguments": arguments, "result": wire})
                    return wire, "".join(row["text"] for row in wire["content"] if row["type"] == "text")

                detail, text = await call("canvas_get_conversation", {"conversation_id": "501"})
                listed, list_text = await call("canvas_list_conversations", {"scope": "archived"})
                fixture.fail_next = "denied"
                failed, _text = await call("canvas_list_conversations", {})
                assert not detail.get("isError", False) and json.loads(text) == fixture.before[0]
                assert not listed.get("isError", False) and json.loads(list_text) == summaries([fixture.before[2]])
                assert failed.get("isError") is True
                expected_names = json.loads((RECEIVER / "base-tool-names.json").read_text())
                assert set(wires) == set(expected_names)
                for name in ["canvas_list_conversations", "canvas_get_conversation"]:
                    annotations = wires[name]["annotations"]
                    assert annotations["readOnlyHint"] is True
                    assert annotations["destructiveHint"] is False
                    assert annotations["idempotentHint"] is True
                assert wires["canvas_get_conversation"]["inputSchema"]["properties"]["conversation_id"]["type"] == "string"

    asyncio.run(run())
    assert fixture.rows == fixture.before
    assert {row["method"] for row in canvas_requests(fixture)} == {"GET"}

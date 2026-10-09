"""Actual loopback HTTP, CLI and MCP receiving; no school credentials."""

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

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
ROWS = [
    {"revision_id": "009", "latest": True, "updated_at": "2026-10-08T10:20:00-07:00",
     "edited_by": {"id": 5, "name": "Fictional editor"}, "extra": {"zero": 0}},
    {"revision_id": 2, "latest": False, "updated_at": None, "edited_by": None},
]
HISTORIC = {"revision_id": "002", "latest": False, "url": "former-name",
            "title": "Old instructions — 研究", "body": "<p>Bring A &amp; B.</p>",
            "body_text": "server field stays nested", "unknown": [False, None]}


@pytest.fixture
def history_http(tmp_path):
    state = {"requests": [], "late_denial": False, "denial": False}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = urlsplit(self.path)
            query = parse_qs(parts.query)
            state["requests"].append({"method": self.command, "path": parts.path, "query": query})
            headers = {}
            if state["denial"] or (state["late_denial"] and query.get("cursor") == ["last"]):
                code, value = 403, {"error": "synthetic page editor permission denied"}
            elif parts.path.endswith("/revisions"):
                code = 200
                if query.get("cursor") == ["last"]:
                    value = ROWS[1:]
                else:
                    value = ROWS[:1]
                    headers["Link"] = (f'<http://127.0.0.1:{self.server.server_port}'
                                       f'{parts.path}?cursor=last>; rel="next"')
            elif parts.path.endswith("/revisions/2"):
                code, value = 200, copy.deepcopy(HISTORIC)
                if query.get("summary") == ["true"]:
                    for key in ("url", "title", "body"):
                        value.pop(key)
            elif parts.path.endswith("/revisions/latest"):
                code, value = 200, {"revision_id": 9, "latest": True, "body": ""}
            elif parts.path == "/api/v1/courses/42/pages/current":
                code, value = 200, {"url": "current", "title": "Today", "body": "<p>Current</p>"}
            else:
                code, value = 404, {"error": "unknown fictional route"}
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = {k: v for k, v in os.environ.items() if not k.startswith("CANVAS_")}
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    env.update(CANVAS_BASE_URL=f"http://127.0.0.1:{server.server_port}",
               CANVAS_API_TOKEN="synthetic-history-only", CANVAS_PROFILE=str(tmp_path / "unused"),
               PYTHONPATH=str(SRC), PYTHONDONTWRITEBYTECODE="1",
               NO_PROXY="127.0.0.1", no_proxy="127.0.0.1")
    try:
        yield state, env
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def cli(env, *args):
    return subprocess.run([sys.executable, "-B", "-m", "canvaspilot.cli", *args],
                          env=env, capture_output=True, text=True, timeout=20, check=False)


def test_cli_actual_two_pages_and_literal_locator(history_http, tmp_path):
    state, env = history_http
    result = cli(env, "page-revisions", "00042", "café?100%#first")
    assert result.returncode == 0 and result.stderr == ""
    assert json.loads(result.stdout) == ROWS
    assert len(state["requests"]) == 2
    assert state["requests"][0]["path"] == (
        "/api/v1/courses/42/pages/caf%C3%A9%3F100%25%23first/revisions")
    assert state["requests"][1]["query"] == {"cursor": ["last"]}
    (tmp_path / "cli-list.stdout").write_text(result.stdout)


def test_cli_historical_summary_latest_and_current_are_distinct(history_http, tmp_path):
    state, env = history_http
    captured = []
    for args, expected in [
        (["page-revision", "42", "current", "002"],
         {"revision": HISTORIC, "body_text": "Bring A & B."}),
        (["page-revision", "42", "current", "2", "--summary"],
         {"revision": {k: v for k, v in HISTORIC.items() if k not in {"url", "title", "body"}}}),
        (["page-revision", "42", "current", "latest"],
         {"revision": {"revision_id": 9, "latest": True, "body": ""}, "body_text": ""}),
        (["page", "42", "current"],
         {"url": "current", "title": "Today", "body_html": "<p>Current</p>",
          "body_text": "Current", "published": None}),
    ]:
        result = cli(env, *args)
        assert result.returncode == 0 and result.stderr == "", result.stderr
        assert json.loads(result.stdout) == expected
        captured.append({"args": args, "stdout": result.stdout, "stderr": result.stderr})
    assert state["requests"][0]["query"]["summary"] == ["false"]
    assert state["requests"][1]["query"]["summary"] == ["true"]
    assert all(r["method"] == "GET" for r in state["requests"])
    (tmp_path / "cli-show.json").write_text(json.dumps(captured, indent=2))


@pytest.mark.parametrize("later", [False, True])
def test_cli_denied_history_is_not_partial_success(history_http, later):
    state, env = history_http
    state["late_denial" if later else "denial"] = True
    result = cli(env, "page-revisions", "42", "current")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "CanvasAuthError"
    assert len(state["requests"]) == (2 if later else 1)


def test_actual_registered_mcp_success_schema_and_errors(history_http, tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    state, env = history_http
    captured = []
    async def run():
        parameters = StdioServerParameters(
            command=sys.executable, args=["-B", "-m", "canvaspilot.cli", "mcp"], env=env)
        with (tmp_path / "mcp.stderr").open("w") as stderr:
            async with (
                stdio_client(parameters, errlog=stderr) as (read, write),
                ClientSession(read, write, read_timeout_seconds=10) as session,
            ):
                await session.initialize()
                catalog = await session.list_tools()
                selected = {t.name: t.model_dump(by_alias=True) for t in catalog.tools
                            if t.name in {"canvas_list_page_revisions", "canvas_get_page_revision"}}
                assert len(selected) == 2
                for tool in selected.values():
                    assert tool["annotations"]["readOnlyHint"] is True
                    assert tool["annotations"]["destructiveHint"] is False
                assert selected["canvas_get_page_revision"]["inputSchema"]["properties"]["summary"]["type"] == "boolean"

                async def call(name, arguments):
                    result = await session.call_tool(name, arguments)
                    wire = result.model_dump(by_alias=True)
                    captured.append({"name": name, "arguments": arguments, "result": wire})
                    text = "".join(x["text"] for x in wire["content"] if x["type"] == "text")
                    return wire.get("isError", False), text
                failed, text = await call("canvas_list_page_revisions", {"course_id": "42", "page_url": "current"})
                assert not failed and json.loads(text) == ROWS
                failed, text = await call("canvas_get_page_revision", {
                    "course_id": "42", "page_url": "current", "revision_id": "2"})
                assert not failed and json.loads(text) == {"revision": HISTORIC, "body_text": "Bring A & B."}
                before = len(state["requests"])
                for args in [
                    {"course_id": "0", "page_url": "current", "revision_id": "2"},
                    {"course_id": "42", "page_url": "..", "revision_id": "2"},
                    {"course_id": "42", "page_url": "current", "revision_id": "LATEST"},
                    {"course_id": "42", "page_url": "current", "revision_id": "2", "summary": "false"},
                ]:
                    failed, _ = await call("canvas_get_page_revision", args)
                    assert failed
                assert len(state["requests"]) == before
                state["late_denial"] = True
                failed, text = await call("canvas_list_page_revisions", {"course_id": "42", "page_url": "current"})
                assert failed and '"revision_id"' not in text
    asyncio.run(run())
    assert {r["method"] for r in state["requests"]} == {"GET"}
    (tmp_path / "mcp-receiving.json").write_text(json.dumps({
        "calls": captured, "requests": state["requests"],
    }, indent=2))

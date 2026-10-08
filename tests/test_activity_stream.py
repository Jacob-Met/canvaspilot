"""Read the activity feed through the native API, transport and CLI.

All credentials and content below are synthetic. The HTTP server belongs to
each test; token requests and the optional synthetic broker stay on loopback.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from canvaspilot import client as client_module
from canvaspilot.api import CanvasAPI
from canvaspilot.cli import main
from canvaspilot.client import CanvasClient

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY = "/api/v1/users/self/activity_stream"
TOKEN = "synthetic-activity-token"
ROW = {
    "id": 9, "type": "Announcement", "read_state": False, "course_id": 0,
    "title": "  Literal <b>読書</b> & e\u0301\n",
    "message": "First line\n\tsecond line",
    "unknown": [0, None, False, {"nested": "🪶"}],
}


class ActivityServer:
    def __init__(self, work: Path):
        self.work = work
        self.calls = []
        self.pages = []
        self.responder = None
        self.broker_mode = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def send_payload(self, status, body, headers=None):
                data = body if isinstance(body, bytes) else json.dumps(
                    body, ensure_ascii=False,
                ).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for key, value in (headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                owner.calls.append({
                    "method": "GET", "path": self.path,
                    "authorization": self.headers.get("Authorization"),
                })
                if owner.broker_mode and self.path == "/health":
                    self.send_payload(200, {
                        "link_pagination": True,
                        "base_url": "https://synthetic-activity.invalid",
                    })
                    return
                self.send_payload(*owner.next_page())

            def do_POST(self):
                if owner.broker_mode and self.path == "/fetch":
                    payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    owner.calls.append({"method": "POST", "path": self.path, "payload": payload})
                    status, body, headers = owner.next_page()
                    self.send_payload(200, {"ok": True, "response": {
                        "status": status, "json": body, "text": None,
                        "headers": {"link": headers.get("Link", "")},
                    }})
                    return
                owner.calls.append({"method": self.command, "path": self.path})
                self.send_payload(405, {"error": "synthetic read-only receiver"})

            do_PUT = do_POST
            do_PATCH = do_POST
            do_DELETE = do_POST

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True,
        )
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.profile = work / "unused-activity-profile"

    def next_page(self):
        if self.responder is not None:
            return self.responder(len(self.calls))
        return self.pages.pop(0) if self.pages else (
            500, {"error": "unexpected activity read"}, {},
        )

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive()

    def api(self):
        return CanvasAPI(CanvasClient(
            base_url=self.base, token=TOKEN, profile=self.profile,
        ))

    def cli(self, *options):
        env = {
            "PATH": os.defpath, "PYTHONPATH": str(ROOT / "src"),
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
            "LANG": "C.UTF-8", "TMPDIR": str(self.work),
        }
        return subprocess.run(
            [sys.executable, "-B", "-m", "canvaspilot.cli", "activity", *options,
             "--base-url", self.base, "--token", TOKEN, "--profile", str(self.profile)],
            cwd=self.work, env=env, capture_output=True, timeout=30, check=False,
        )

    def assert_reads(self, count):
        assert len(self.calls) == count
        assert all(call["method"] == "GET" for call in self.calls)
        assert all(call["authorization"] == f"Bearer {TOKEN}" for call in self.calls)
        assert not self.profile.exists()
        first = urlsplit(self.calls[0]["path"])
        assert first.path == ACTIVITY
        assert parse_qs(first.query) == {"per_page": ["50"]}

    def chain(self):
        middle = ACTIVITY + "?after=first%2Fopaque&include%5B%5D=one&include%5B%5D=two"
        last = ACTIVITY + "?after=last%3Dopaque"
        second = {"id": 0, "type": "FutureType", "read_state": None, "nested": {"empty": []}}
        self.pages = [
            (200, [ROW], {"Link": f'<{self.base}{middle}>; rel="next"'}),
            (200, [], {"Link": f'<{self.base}{last}>; rel="next"'}),
            (200, [second, ROW], {}),
        ]
        return [ROW, second, ROW], [middle, last]


@pytest.fixture
def activity_server(tmp_path, monkeypatch):
    for name in tuple(os.environ):
        if name.lower().endswith("_proxy") or name.startswith("CANVAS_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    server = ActivityServer(tmp_path)
    try:
        yield server
    finally:
        server.close()


def test_api_follows_short_and_empty_pages_without_rewriting_rows(activity_server):
    server = activity_server
    expected, continuations = server.chain()
    api = server.api()
    try:
        assert api.activity_stream() == expected
    finally:
        api.close()
    server.assert_reads(3)
    assert [row["path"] for row in server.calls[1:]] == continuations
    assert server.pages == []


def test_real_cli_prints_one_complete_document_with_literal_nested_values(activity_server):
    server = activity_server
    expected, continuations = server.chain()
    result = server.cli()
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    assert result.stdout == (json.dumps(expected, indent=2, default=str) + "\n").encode()
    server.assert_reads(3)
    assert [row["path"] for row in server.calls[1:]] == continuations


@pytest.mark.parametrize("body,expected", [
    ([], []),
    ({"unknown": None, "id": 0}, [{"unknown": None, "id": 0}]),
    (None, [None]),
    ([0, False, None, "untyped row"], [0, False, None, "untyped row"]),
])
def test_terminal_response_keeps_client_compatibility_without_extra_probe(
    activity_server, body, expected,
):
    server = activity_server
    server.pages = [(200, body, {})]
    api = server.api()
    try:
        assert api.activity_stream() == expected
    finally:
        api.close()
    server.assert_reads(1)
    assert server.pages == []


@pytest.mark.parametrize("later", [False, True], ids=["first-page", "later-page"])
@pytest.mark.parametrize("status,body,error_name", [
    (401, {"error": "synthetic expiry"}, "CanvasAuthError"),
    (403, {"error": "synthetic refusal"}, "CanvasAuthError"),
    (429, {"error": "synthetic rate limit"}, "HTTPStatusError"),
    (503, {"error": "synthetic service failure"}, "HTTPStatusError"),
    (200, b"{invalid authored JSON", "CanvasPaginationError"),
])
def test_cli_read_errors_are_one_json_error_with_no_partial_stdout(
    activity_server, later, status, body, error_name,
):
    server = activity_server
    server.pages = [(status, body, {})]
    if later:
        server.pages.insert(0, (
            200, [ROW], {"Link": f'<{server.base}{ACTIVITY}?cursor=later>; rel="next"'},
        ))
    result = server.cli()
    assert result.returncode == 1
    assert result.stdout == b""
    error = json.loads(result.stderr)
    assert set(error) == {"ok", "error", "message"}
    assert error["ok"] is False
    assert error["error"] == error_name
    assert isinstance(error["message"], str) and error["message"]
    server.assert_reads(2 if later else 1)


@pytest.mark.parametrize("kind", ["foreign", "cycle", "ambiguous", "malformed", "later-object"])
def test_cli_invalid_continuation_never_publishes_an_early_page(activity_server, kind):
    server = activity_server
    second = f"{server.base}{ACTIVITY}?cursor=next"
    links = {
        "foreign": f'<http://foreign.synthetic.invalid{ACTIVITY}>; rel="next"',
        "cycle": f'<{server.base}{ACTIVITY}?per_page=50>; rel="next"',
        "ambiguous": f'<{second}>; rel="next", <{second}2>; rel="next"',
        "malformed": f'<{second}>; rel="next',
        "later-object": f'<{second}>; rel="next"',
    }
    server.pages = [(200, [ROW], {"Link": links[kind]})]
    if kind == "later-object":
        server.pages.append((200, {"unexpected": "later object"}, {}))
    result = server.cli()
    assert result.returncode == 1
    assert result.stdout == b""
    assert json.loads(result.stderr)["error"] == "CanvasPaginationError"
    server.assert_reads(2 if kind == "later-object" else 1)


@pytest.mark.parametrize("terminal", [True, False], ids=["complete-40", "continuing-40"])
def test_cli_distinguishes_exact_terminal_cap_from_incomplete_feed(activity_server, terminal):
    server = activity_server

    def respond(number):
        headers = {} if terminal and number == 40 else {
            "Link": f'<{server.base}{ACTIVITY}?cursor={number + 1}>; rel="next"',
        }
        return 200, [{"id": number}], headers

    server.responder = respond
    result = server.cli()
    server.assert_reads(40)
    if terminal:
        assert result.returncode == 0, result.stderr
        assert result.stderr == b""
        assert json.loads(result.stdout) == [{"id": number} for number in range(1, 41)]
    else:
        assert result.returncode == 1
        assert result.stdout == b""
        assert json.loads(result.stderr)["error"] == "CanvasPaginationError"
        assert b"40-page cap" in result.stderr


@pytest.mark.parametrize("body", [[], [ROW, ROW], {"unknown": [0, None]}])
def test_fixture_route_keeps_original_client_list_wrapper(body, tmp_path, monkeypatch):
    def forbid(*_args, **_kwargs):
        pytest.fail("Fixture activity touched a live transport")
    monkeypatch.setattr(client_module, "broker_health", forbid)
    monkeypatch.setattr(client_module.httpx, "Client", forbid)
    client = CanvasClient(
        token="", profile=tmp_path / "unused-fixture-profile",
        fixture={"routes": {f"GET {ACTIVITY}": body}},
    )
    api = CanvasAPI(client)
    try:
        assert api.activity_stream() == (body if isinstance(body, list) else [body])
    finally:
        api.close()
    assert not client.profile.exists()


def test_existing_broker_transport_collects_synthetic_link_metadata(activity_server, monkeypatch):
    server = activity_server
    server.broker_mode = True
    next_url = f"https://synthetic-activity.invalid{ACTIVITY}?after=opaque%2Ftwo"
    server.pages = [
        (200, [ROW], {"Link": f'<{next_url}>; rel="next"'}),
        (200, [ROW], {}),
    ]
    monkeypatch.setattr(client_module, "BROKER_PORT", server.server.server_port)
    api = CanvasAPI(CanvasClient(
        base_url="https://synthetic-activity.invalid", token="", profile=server.profile,
    ))
    try:
        assert api.activity_stream() == [ROW, ROW]
    finally:
        api.close()
    assert [call["path"] for call in server.calls] == ["/health", "/fetch", "/fetch"]
    jobs = [call["payload"] for call in server.calls[1:]]
    assert all(job["method"] == "GET" and job["body"] is None for job in jobs)
    assert jobs[0]["path"] == ACTIVITY + "?per_page=50"
    assert jobs[1]["path"] == next_url
    assert not server.profile.exists()


@pytest.mark.parametrize("fail", [False, True], ids=["success", "failure"])
def test_cli_restores_explicit_httpx_level_and_closes_original_client(
    activity_server, monkeypatch, capsys, fail,
):
    server = activity_server
    server.pages = [(403, {"error": "synthetic expiry"}, {})] if fail else [(200, [ROW], {})]
    closed = []
    original_close = CanvasClient.close

    def close(client):
        native_http = client._http
        original_close(client)
        closed.append((client._http is None, native_http is not None and native_http.is_closed))

    monkeypatch.setattr(CanvasClient, "close", close)
    logger = logging.getLogger("httpx")
    prior_level = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        args = ["activity", "--base-url", server.base, "--token", TOKEN,
                "--profile", str(server.profile)]
        if fail:
            with pytest.raises(SystemExit) as error:
                main(args)
            assert error.value.code == 1
        else:
            main(args)
        assert logger.level == logging.DEBUG
    finally:
        logger.setLevel(prior_level)
    captured = capsys.readouterr()
    assert closed == [(True, True)]
    if fail:
        assert captured.out == ""
        assert json.loads(captured.err)["error"] == "CanvasAuthError"
    else:
        assert json.loads(captured.out) == [ROW]
        assert captured.err == ""
    server.assert_reads(1)


def test_activity_help_and_unknown_options_do_not_construct_a_client(
    activity_server, monkeypatch, capsys,
):
    server = activity_server
    help_result = server.cli("--help")
    assert help_result.returncode == 0
    assert b"--base-url" in help_result.stdout and b"--token" in help_result.stdout
    assert help_result.stderr == b""

    def forbid(*_args, **_kwargs):
        pytest.fail("Invalid arguments constructed a CanvasClient")
    monkeypatch.setattr(CanvasClient, "__init__", forbid)
    for arguments in [["activity", "--course", "42"], ["activity", "--unread"], ["activity", "42"]]:
        with pytest.raises(SystemExit) as error:
            main(arguments)
        assert error.value.code == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "error:" in captured.err
    assert server.calls == []
    assert not server.profile.exists()

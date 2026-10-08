"""Actual CLI/client receiving for the additive announcement reader."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "synthetic-announcements-token"
LONG_TEXT = ("Intro & details: " + ("λ漢字🧭 " * 100)).rstrip()
ROWS = [
    {
        "id": 601,
        "title": 'Lab <review> & "questions"',
        "posted_at": "2026-10-01T23:30:00-04:00",
        "context_code": "course_77",
        "message": "<p>" + LONG_TEXT.replace("&", "&amp;") + "</p>",
        "html_url": "https://canvas.invalid/courses/77/discussion_topics/601",
        "unrelated": "The maintained API does not project this field.",
    },
    {
        "id": 0,
        "title": "",
        "posted_at": None,
        "context_code": "course_42",
        "message": None,
        "html_url": None,
    },
    {
        "id": 603,
        "title": "Second page",
        "posted_at": "2026-10-01T03:30:00Z",
        "context_code": "course_77",
        "message": "<p>Read &amp; compare.</p>",
        "html_url": "https://canvas.invalid/courses/77/discussion_topics/603",
    },
]


@pytest.fixture(autouse=True)
def local_fixture_environment(monkeypatch):
    # These requests target only the authored loopback server, never a proxy.
    for name in tuple(os.environ):
        if name.upper() in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"}:
            monkeypatch.delenv(name)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost,::1")


@contextmanager
def canvas_server(mode="pages"):
    """Only synthetic GETs; a real opaque next link exercises the client."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = urlsplit(self.path)
            query = dict(parse_qsl(parts.query))
            requests.append({
                "method": "GET",
                "path": parts.path,
                "query": parse_qsl(parts.query),
                "authorized": self.headers.get("Authorization") == "Bearer " + TOKEN,
            })
            if parts.path == "/api/v1/users/self/profile":
                self.send_json(200, {"id": 42, "name": "Fictional learner"})
                return
            if parts.path != "/api/v1/announcements":
                self.send_json(404, {"error": "unexpected fixture route"})
                return
            if not requests[-1]["authorized"]:
                self.send_json(401, {"error": "fixture token missing"})
                return
            continued = "cursor" in query
            if mode == "unauthorized":
                self.send_json(401, {"error": "synthetic expired access"})
            elif mode == "unavailable":
                self.send_json(503, {"error": "synthetic unavailable source"})
            elif mode == "empty":
                self.send_json(200, [])
            elif continued:
                if mode == "late-failure":
                    self.send_json(503, {"error": "synthetic later page failure"})
                elif mode == "late-object":
                    self.send_json(200, {"not": "a collection"})
                else:
                    self.send_json(200, ROWS[2:])
            else:
                self.send_json(
                    200, ROWS[:2],
                    "<" + self.server.base + "/api/v1/announcements?cursor=opaque%2Bnext"
                    + '>; rel="next"',
                )

        def send_json(self, status, value, link=None):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            if link:
                self.send_header("Link", link)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.base = "http://127.0.0.1:" + str(server.server_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.base, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def invoke(base, *args, ascii_console=False):
    env = {key: value for key, value in os.environ.items() if not key.startswith("CANVAS")}
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if ascii_console:
        env["PYTHONIOENCODING"] = "ascii:strict"
    return subprocess.run(
        [sys.executable, "-B", "-m", "canvaspilot.cli", *args,
         "--base-url", base, "--token", TOKEN],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=10, check=False,
    )


def expected_rows(full=False):
    return [
        {
            "id": 601,
            "title": ROWS[0]["title"],
            "posted_at": ROWS[0]["posted_at"],
            "context_code": "course_77",
            "message_text": LONG_TEXT if full else LONG_TEXT[:400] + "…",
            "html_url": ROWS[0]["html_url"],
        },
        {
            "id": 0,
            "title": "",
            "posted_at": None,
            "context_code": "course_42",
            "message_text": "",
            "html_url": None,
        },
        {
            "id": 603,
            "title": "Second page",
            "posted_at": "2026-10-01T03:30:00Z",
            "context_code": "course_77",
            "message_text": "Read & compare.",
            "html_url": ROWS[2]["html_url"],
        },
    ]


def test_existing_api_projection_control():
    with canvas_server() as (base, requests):
        with CanvasAPI(CanvasClient(base_url=base, token=TOKEN)) as api:
            actual = api.list_announcements([42, 77], detail="full")
        assert actual == expected_rows(full=True)
        assert len(requests) == 2


def test_existing_identity_command_control():
    with canvas_server() as (base, requests):
        result = invoke(base, "whoami")
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == {
            "mode": "token", "base_url": base,
            "profile": {"id": 42, "name": "Fictional learner"},
        }
        assert len(requests) == 1


def test_compact_multi_course_page_order_and_exact_filters():
    with canvas_server() as (base, requests):
        result = invoke(base, "announcements", "42", "77")
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == expected_rows()
        assert all(row["authorized"] for row in requests)
        assert requests[0]["query"] == [
            ("active_only", "true"), ("per_page", "50"),
            ("context_codes[]", "course_42"), ("context_codes[]", "course_77"),
        ]
        assert requests[1]["query"] == [("cursor", "opaque+next")]
        assert len(requests) == 2


def test_full_text_start_date_and_narrow_console_preserve_values():
    with canvas_server() as (base, requests):
        result = invoke(
            base, "announcements", "77", "42", "--detail", "full",
            "--start-date", "2026-10-01T00:00:00Z", ascii_console=True,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == expected_rows(full=True)
        assert ("start_date", "2026-10-01T00:00:00Z") in requests[0]["query"]
        assert [value for key, value in requests[0]["query"]
                if key == "context_codes[]"] == ["course_77", "course_42"]
        assert requests[1]["query"] == [("cursor", "opaque+next")]


def test_empty_collection_is_a_successful_empty_list():
    with canvas_server("empty") as (base, requests):
        result = invoke(base, "announcements", "42")
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == []
        assert len(requests) == 1


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ([], "course_ids"),
        (["0"], "must be a positive integer"),
        (["42", "-3"], "must be a positive integer"),
        (["1.5"], "must be a positive integer"),
        (["no-course"], "must be a positive integer"),
        (["42", "--detail", "raw"], "invalid choice: 'raw'"),
        (["42", "--start-date"], "expected one argument"),
    ],
)
def test_cli_refusal_precedes_any_request(args, message):
    with canvas_server() as (base, requests):
        result = invoke(base, "announcements", *args)
        assert result.returncode == 2
        assert not result.stdout
        assert message in result.stderr
        assert not requests


@pytest.mark.parametrize(
    ("mode", "expected_requests", "error_name"),
    [
        ("unauthorized", 1, "CanvasAuthError"),
        ("unavailable", 1, "HTTPStatusError"),
        ("late-failure", 2, "HTTPStatusError"),
        ("late-object", 2, "CanvasPaginationError"),
    ],
)
def test_native_read_failure_emits_no_partial_success(mode, expected_requests, error_name):
    with canvas_server(mode) as (base, requests):
        result = invoke(base, "announcements", "42", "77")
        assert result.returncode == 1
        assert not result.stdout
        error = json.loads(result.stderr)
        assert error["ok"] is False
        assert error["error"] == error_name
        assert error["message"]
        assert len(requests) == expected_requests

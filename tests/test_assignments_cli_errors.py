"""Keep assignment-list success bytes and expected read diagnostics at the CLI."""
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

ROOT = Path(__file__).resolve().parents[1]
ROUTE = "/api/v1/courses/0042/assignments"
NEXT = ROUTE + "?cursor=authored%2Fnext"
TOKEN = "synthetic-assignments-token"
ROWS = [
    {"id": 7, "name": "Literal <b>read</b> \u0394", "due_at": None, "points_possible": 0,
     "submission_types": ["online_text_entry"], "html_url": "https://example.invalid/assignment/7",
     "has_submitted_submissions": False, "description": "Compact mode excludes this body",
     "future_field": {"zero": 0}, "submission": {"attempt": 0, "late": False, "missing": False,
     "excused": False, "workflow_state": "submitted", "submitted_at": None, "future_field": "omitted"}},
    {"id": 7, "name": "Repeated identity, second occurrence", "due_at": "", "points_possible": None,
     "submission_types": [], "html_url": None, "has_submitted_submissions": True,
     "submission": {"attempt": True, "late": "not a boolean", "missing": False, "excused": None}},
]
EXPECTED = [
    {"id": 7, "course_id": "0042", "name": "Literal <b>read</b> \u0394", "due_at": None,
     "points_possible": 0, "submission_types": ["online_text_entry"],
     "html_url": "https://example.invalid/assignment/7", "has_submitted_submissions": False,
     "submission": {"workflow_state": "submitted", "submitted_at": None, "attempt": 0,
                    "late": False, "missing": False, "excused": False}, "submission_warnings": []},
    {"id": 7, "course_id": "0042", "name": "Repeated identity, second occurrence", "due_at": "",
     "points_possible": None, "submission_types": [], "html_url": None,
     "has_submitted_submissions": True, "submission": {"missing": False, "excused": None},
     "submission_warnings": ["submission.attempt: expected nonnegative integer or null",
                             "submission.late: expected boolean or null"]},
]


@pytest.fixture
def provider():
    state = {"case": "success", "requests": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            state["requests"].append({
                "path": parsed.path, "target": self.path, "query": query,
                "token": self.headers.get("Authorization"),
            })
            case = state["case"]
            status, body, link = 200, [], None
            if parsed.path != ROUTE:
                status = 404
            elif case == "closed_response":
                self.close_connection = True
                return
            elif case in {"auth_401", "auth_403", "http_503"}:
                status = {"auth_401": 401, "auth_403": 403, "http_503": 503}[case]
            elif case == "invalid_json":
                body = b"not valid JSON"
            elif case in {"success", "later_http_503", "later_nonlist"}:
                if "cursor" not in query:
                    body = ROWS[:1]
                    link = f'<http://127.0.0.1:{self.server.server_port}{NEXT}>; rel="next"'
                elif case == "later_http_503":
                    status = 503
                elif case == "later_nonlist":
                    body = {"synthetic": "not an assignment collection"}
                else:
                    body = ROWS[1:]
            payload = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            if link:
                self.send_header("Link", link)
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True,
    )
    thread.start()
    try:
        yield server.server_port, state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def _run(port, tmp_path, case):
    env = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith("CANVAS_")
        and key.upper() not in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}
    }
    env.update({
        "CANVAS_SESSION_PORT": str(port), "NO_PROXY": "127.0.0.1,localhost",
        "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1",
    })
    profile = tmp_path / "uncreated-profile"
    command = [
        sys.executable, "-B", "-m", "canvaspilot.cli", "assignments", "0042",
        "--base-url", f"http://127.0.0.1:{port}", "--profile", str(profile),
    ]
    if case != "missing_setup":
        command += ["--token", TOKEN]
    if case == "no_bucket":
        command += ["--bucket="]
    elif case == "custom_bucket":
        command += ["--bucket", "custom state"]
    result = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, check=False, timeout=30,
    )
    assert not profile.exists()
    return result


def _assert_requests(state, case):
    requests = state["requests"]
    if case == "missing_setup":
        assert requests == [{"path": "/health", "target": "/health", "query": {}, "token": None}]
        return
    expected = {"order_by": ["due_at"], "include[]": ["submission"], "per_page": ["50"]}
    if case != "no_bucket":
        expected["bucket"] = ["custom state" if case == "custom_bucket" else "upcoming"]
    assert requests[0]["path"] == ROUTE
    assert requests[0]["query"] == expected
    assert all(row["token"] == f"Bearer {TOKEN}" for row in requests)
    assert len(requests) == (2 if case in {"success", "later_http_503", "later_nonlist"} else 1)
    if len(requests) == 2:
        assert requests[1]["target"] == NEXT


@pytest.mark.parametrize(
    ("case", "error_type", "message"),
    [
        ("missing_setup", "CanvasAuthError", "Start: canvaspilot session start"),
        ("auth_401", "CanvasAuthError", "Canvas auth failed (401)"),
        ("auth_403", "CanvasAuthError", "Canvas auth failed (403)"),
        ("http_503", "HTTPStatusError", "503 Service Unavailable"),
        ("later_http_503", "HTTPStatusError", "503 Service Unavailable"),
        ("invalid_json", "CanvasPaginationError", "expected a JSON page"),
        ("later_nonlist", "CanvasPaginationError", "non-list continuing page"),
        ("closed_response", "RemoteProtocolError", "Server disconnected"),
    ],
)
def test_expected_assignment_errors_are_one_json_diagnostic(
    provider, tmp_path, case, error_type, message,
):
    port, state = provider
    state["case"] = case

    result = _run(port, tmp_path, case)

    assert result.returncode == 1
    assert result.stdout == b""
    diagnostic = json.loads(result.stderr)
    assert set(diagnostic) == {"ok", "error", "message"}
    assert diagnostic["ok"] is False
    assert diagnostic["error"] == error_type
    assert message in diagnostic["message"]
    assert b"Traceback" not in result.stderr
    _assert_requests(state, case)


@pytest.mark.parametrize("case", ["success", "empty_success", "no_bucket", "custom_bucket"])
def test_assignment_success_preserves_projection_order_filters_and_bytes(provider, tmp_path, case):
    port, state = provider
    state["case"] = case

    result = _run(port, tmp_path, case)

    expected = EXPECTED if case == "success" else []
    assert result.returncode == 0
    assert result.stdout == (json.dumps(expected, indent=2) + "\n").replace("\n", os.linesep).encode()
    assert result.stderr == b""
    _assert_requests(state, case)


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO, logging.ERROR])
@pytest.mark.parametrize("outcome", ["success", "auth", "pagination", "http", "value", "type", "runtime"])
def test_assignments_restore_logger_close_client_and_preserve_unrelated_errors(
    monkeypatch, capsys, tmp_path, level, outcome,
):
    import httpx

    from canvaspilot import api, cli
    from canvaspilot.client import CanvasAuthError, CanvasPaginationError

    errors = {
        "auth": CanvasAuthError("synthetic auth refusal"),
        "pagination": CanvasPaginationError("synthetic incomplete page"),
        "http": httpx.RemoteProtocolError("synthetic disconnected read"),
        "value": ValueError("synthetic unrelated value"),
        "type": TypeError("synthetic projection error"),
        "runtime": RuntimeError("synthetic programming error"),
    }
    closed = []

    class Reader:
        def __init__(self, client):
            self.client = client

        def list_assignments(self, course_id, *, bucket):
            assert course_id == "0042" and bucket == "custom state"
            if outcome != "success":
                raise errors[outcome]
            return []

        def close(self):
            self.client.close()
            closed.append(True)

    monkeypatch.setattr(api, "CanvasAPI", Reader)
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(level)
    profile = tmp_path / "uncreated-profile"
    command = [
        "assignments", "0042", "--bucket", "custom state",
        "--token", TOKEN, "--profile", str(profile),
    ]
    try:
        if outcome == "success":
            cli.main(command)
            assert capsys.readouterr().out == "[]\n"
        elif outcome in {"auth", "pagination", "http"}:
            with pytest.raises(SystemExit) as caught:
                cli.main(command)
            assert caught.value.code == 1
            captured = capsys.readouterr()
            assert captured.out == ""
            assert json.loads(captured.err) == {
                "ok": False, "error": type(errors[outcome]).__name__, "message": str(errors[outcome]),
            }
        else:
            with pytest.raises(type(errors[outcome])) as caught:
                cli.main(command)
            assert caught.value is errors[outcome]
        assert logger.level == level
        assert closed == [True]
        assert not profile.exists()
    finally:
        logger.setLevel(previous)

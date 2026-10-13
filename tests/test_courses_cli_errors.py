"""Expected course-read failures remain actionable at the actual CLI boundary."""
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
ROWS = [
    {"id": 42, "name": "Synthetic course one", "course_code": "SYN-1",
     "enrollment_term_id": 0, "term": {"name": "Synthetic term"}},
    {"id": 43, "name": "Synthetic course two", "course_code": "",
     "enrollment_term_id": None, "term": None},
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
            state["requests"].append((parsed.path, query))
            status, link, body = 200, None, []
            case = state["case"]
            if parsed.path != "/api/v1/courses":
                status = 404
            elif case in {"auth_401", "auth_403", "http_503"}:
                status = {"auth_401": 401, "auth_403": 403, "http_503": 503}[case]
            elif case == "empty":
                body = []
            elif case == "invalid_json":
                body = b"not a JSON page"
            elif query.get("page") == ["2"]:
                if case == "late_http_503":
                    status = 503
                elif case == "later_nonlist":
                    body = {"unexpected": "continuation object"}
                else:
                    body = [ROWS[1]]
            else:
                body = [ROWS[0]]
                link = (f"<http://127.0.0.1:{self.server.server_port}"
                        '/api/v1/courses?page=2>; rel="next"')
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


def _run(port, tmp_path, *, token=True):
    env = os.environ.copy()
    for key in list(env):
        if key.upper() in {
            "CANVAS_API_TOKEN", "CANVAS_BASE_URL", "CANVAS_PROFILE",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        }:
            env.pop(key)
    env.update({
        "CANVAS_SESSION_PORT": str(port),
        "NO_PROXY": "127.0.0.1,localhost",
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    profile = tmp_path / "uncreated-profile"
    command = [
        sys.executable, "-B", "-m", "canvaspilot.cli", "courses",
        "--base-url", f"http://127.0.0.1:{port}", "--profile", str(profile),
    ]
    if token:
        command += ["--token", "synthetic-offline-token"]
    result = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, check=False, timeout=15,
    )
    assert not profile.exists()
    return result


@pytest.mark.parametrize(
    ("case", "error_type", "message"),
    [
        ("missing_setup", "CanvasAuthError", "Start: canvaspilot session start"),
        ("auth_401", "CanvasAuthError", "Canvas auth failed (401)"),
        ("auth_403", "CanvasAuthError", "Canvas auth failed (403)"),
        ("http_503", "HTTPStatusError", "503 Service Unavailable"),
        ("late_http_503", "HTTPStatusError", "503 Service Unavailable"),
        ("invalid_json", "CanvasPaginationError", "expected a JSON page"),
        ("later_nonlist", "CanvasPaginationError", "non-list continuing page"),
    ],
)
def test_expected_course_errors_are_one_json_diagnostic(provider, tmp_path, case, error_type, message):
    port, state = provider
    state["case"] = case

    result = _run(port, tmp_path, token=case != "missing_setup")

    assert result.returncode == 1
    assert result.stdout == b""
    diagnostic = json.loads(result.stderr)
    assert set(diagnostic) == {"ok", "error", "message"}
    assert diagnostic["ok"] is False
    assert diagnostic["error"] == error_type
    assert message in diagnostic["message"]
    assert b"Traceback" not in result.stderr
    expected_requests = 2 if case in {"late_http_503", "later_nonlist"} else 1
    assert len(state["requests"]) == expected_requests
    if case == "missing_setup":
        assert state["requests"] == [("/health", {})]


@pytest.mark.parametrize("case", ["success", "empty"])
def test_course_success_preserves_projection_order_and_bytes(provider, tmp_path, case):
    port, state = provider
    state["case"] = case

    result = _run(port, tmp_path)

    expected = [] if case == "empty" else [
        {"id": 42, "name": "Synthetic course one", "course_code": "SYN-1",
         "enrollment_term_id": 0, "term": "Synthetic term"},
        {"id": 43, "name": "Synthetic course two", "course_code": "",
         "enrollment_term_id": None, "term": None},
    ]
    assert result.returncode == 0
    assert result.stdout == (json.dumps(expected, indent=2) + "\n").replace("\n", os.linesep).encode()
    first_path, first_query = state["requests"][0]
    assert first_path == "/api/v1/courses"
    assert first_query == {
        "enrollment_state": ["active"], "include[]": ["term", "total_scores"], "per_page": ["50"],
    }
    assert len(state["requests"]) == (1 if case == "empty" else 2)


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO, logging.ERROR])
@pytest.mark.parametrize("outcome", ["success", "expected_error", "unexpected_error"])
def test_courses_restore_logging_and_close_the_client(monkeypatch, capsys, level, outcome):
    from canvaspilot import api, cli
    from canvaspilot.client import CanvasAuthError

    closed = []

    class Reader:
        def __init__(self, client):
            self.client = client

        def list_courses(self):
            if outcome == "expected_error":
                raise CanvasAuthError("synthetic expected failure")
            if outcome == "unexpected_error":
                raise RuntimeError("synthetic programming failure")
            return []

        def close(self):
            self.client.close()
            closed.append(True)

    monkeypatch.setattr(api, "CanvasAPI", Reader)
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(level)
    try:
        if outcome == "success":
            cli.main(["courses", "--token", "synthetic-offline-token"])
            assert capsys.readouterr().out == "[]\n"
        elif outcome == "expected_error":
            with pytest.raises(SystemExit) as caught:
                cli.main(["courses", "--token", "synthetic-offline-token"])
            assert caught.value.code == 1
            assert json.loads(capsys.readouterr().err)["message"] == "synthetic expected failure"
        else:
            with pytest.raises(RuntimeError, match="synthetic programming failure"):
                cli.main(["courses", "--token", "synthetic-offline-token"])
        assert logger.level == level
        assert closed == [True]
    finally:
        logger.setLevel(previous)

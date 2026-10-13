"""Expected identity-read errors remain actionable at the actual CLI boundary."""
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
PROFILE = {
    "id": 7, "name": "Synthetic Reviewer", "short_name": "", "primary_email": None,
    "opaque": {"zero": 0, "false": False, "unicode": "\u0394"},
}


@pytest.fixture
def provider():
    state = {"case": "success", "requests": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            state["requests"].append((parsed.path, parse_qs(parsed.query)))
            status, content_type, body = 200, "application/json", PROFILE
            case = state["case"]
            if parsed.path != "/api/v1/users/self/profile":
                status, body = 404, {}
            elif case == "closed_response":
                self.close_connection = True
                return
            elif case in {"auth_401", "auth_403", "http_503"}:
                status = {"auth_401": 401, "auth_403": 403, "http_503": 503}[case]
                body = {"synthetic": "refused"}
            elif case == "plain_text":
                body, content_type = b"synthetic non-JSON profile", "text/plain"
            elif case == "empty_body":
                body = b""
            elif case == "invalid_json":
                body = b"not a JSON profile"
            payload = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
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
        "CANVAS_SESSION_PORT": str(port), "NO_PROXY": "127.0.0.1,localhost",
        "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1",
    })
    profile = tmp_path / "uncreated-profile"
    command = [
        sys.executable, "-B", "-m", "canvaspilot.cli", "whoami",
        "--base-url", f"http://127.0.0.1:{port}", "--profile", str(profile),
    ]
    if token:
        command += ["--token", "synthetic-identity-token"]
    result = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, check=False, timeout=15,
    )
    assert not profile.exists()
    return result


@pytest.mark.parametrize(
    ("case", "error_type", "message"),
    [
        ("missing_setup", "CanvasAuthError", "Start: canvaspilot session start"),
        ("auth_401", "CanvasAuthError", "Canvas auth failed (401) for GET /api/v1/users/self/profile"),
        ("auth_403", "CanvasAuthError", "Canvas auth failed (403) for GET /api/v1/users/self/profile"),
        ("http_503", "HTTPStatusError", "503 Service Unavailable"),
        ("closed_response", "RemoteProtocolError", "Server disconnected without sending a response"),
        ("invalid_json", "JSONDecodeError", "Expecting value: line 1 column 1"),
    ],
)
def test_expected_identity_errors_are_one_json_diagnostic(
    provider, tmp_path, case, error_type, message,
):
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
    assert state["requests"] == (
        [("/health", {})] if case == "missing_setup"
        else [("/api/v1/users/self/profile", {"per_page": ["50"]})]
    )


@pytest.mark.parametrize("case", ["success", "plain_text", "empty_body"])
def test_identity_success_preserves_native_profile_shape_and_bytes(provider, tmp_path, case):
    port, state = provider
    state["case"] = case

    result = _run(port, tmp_path)

    profile = PROFILE if case == "success" else (
        "synthetic non-JSON profile" if case == "plain_text" else None
    )
    expected = {"mode": "token", "base_url": f"http://127.0.0.1:{port}", "profile": profile}
    assert result.returncode == 0
    assert result.stdout == (json.dumps(expected, indent=2) + "\n").replace("\n", os.linesep).encode()
    assert result.stderr == b""
    assert state["requests"] == [("/api/v1/users/self/profile", {"per_page": ["50"]})]


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO, logging.ERROR])
@pytest.mark.parametrize(
    "outcome", ["success", "auth_error", "json_error", "value_error", "unicode_error", "runtime_error"],
)
def test_identity_restores_logging_and_closes_client(monkeypatch, capsys, level, outcome):
    from canvaspilot import api, cli
    from canvaspilot.client import CanvasAuthError

    closed = []
    errors = {
        "auth_error": CanvasAuthError("synthetic expected setup failure"),
        "json_error": json.JSONDecodeError("synthetic malformed payload", "?", 0),
        "value_error": ValueError("synthetic unrelated validation failure"),
        "unicode_error": UnicodeDecodeError("utf-8", b"\xff", 0, 1, "synthetic invalid bytes"),
        "runtime_error": RuntimeError("synthetic programming failure"),
    }

    class Reader:
        def __init__(self, client):
            self.client = client

        def whoami(self):
            if outcome in errors:
                raise errors[outcome]
            return {"mode": "token", "base_url": "synthetic", "profile": None}

        def close(self):
            self.client.close()
            closed.append(True)

    monkeypatch.setattr(api, "CanvasAPI", Reader)
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(level)
    try:
        if outcome == "success":
            cli.main(["whoami", "--token", "synthetic-identity-token"])
            assert json.loads(capsys.readouterr().out)["profile"] is None
        elif outcome in {"auth_error", "json_error"}:
            with pytest.raises(SystemExit) as caught:
                cli.main(["whoami", "--token", "synthetic-identity-token"])
            assert caught.value.code == 1
            captured = capsys.readouterr()
            assert captured.out == ""
            assert json.loads(captured.err) == {
                "ok": False, "error": type(errors[outcome]).__name__,
                "message": str(errors[outcome]),
            }
        else:
            with pytest.raises(type(errors[outcome])) as caught:
                cli.main(["whoami", "--token", "synthetic-identity-token"])
            assert caught.value is errors[outcome]
        assert logger.level == level
        assert closed == [True]
    finally:
        logger.setLevel(previous)

"""Actual comparison CLI and inherited API/client against authored loopback HTTP."""

import base64
import json
import os
import re
import subprocess
import sys
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "submission_comparison.json"
TOKEN = "synthetic-comparison-process-token"


class ComparisonHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        self.server.calls.append({
            "method": self.command, "path": url.path,
            "query": parse_qs(url.query, keep_blank_values=True),
            "authorization": self.headers.get("Authorization"),
        })
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            status, payload = 401, {"error": "authored token required"}
        elif url.path == "/api/v1/courses/71/assignments/902":
            status, payload = self.server.assignment_status, self.server.payload["assignment"]
        elif url.path == "/api/v1/courses/71/assignments/902/submissions/self":
            status, payload = self.server.submission_status, self.server.payload["submission"]
        else:
            status, payload = 404, {"error": "unexpected fixture path"}
        data = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def unexpected_write(self):
        self.server.calls.append({"method": self.command, "path": self.path})
        self.send_error(405)

    do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = unexpected_write


@pytest.fixture
def comparison_http(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), ComparisonHandler)
    server.daemon_threads = True
    server.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    server.assignment_status = server.submission_status = 200
    server.calls = []
    server.profile = tmp_path / "unused-profile"
    server.base_url = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def process(server, args):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("CANVAS_", "CANVASPILOT_"))
           and key not in {"PYTHONPATH", "PYTHONHOME", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                          "http_proxy", "https_proxy", "all_proxy"}}
    env.update({
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "cp1252:strict", "NO_PROXY": "127.0.0.1,localhost",
    })
    return subprocess.run(
        [sys.executable, "-B", "-m", "canvaspilot.cli", "compare-submissions",
         *args, "--base-url", server.base_url, "--token", TOKEN,
         "--profile", str(server.profile)],
        env=env, text=True, capture_output=True, timeout=30, check=False,
    )


def record(name, payload):
    destination = os.environ.get("CANVAS_COMPARISON_RECEIPTS_DIR")
    if destination:
        target = Path(destination)
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
                                           encoding="utf-8")


def assert_read_pair(calls):
    assert [row["method"] for row in calls] == ["GET", "GET"]
    assert [row["path"] for row in calls] == [
        "/api/v1/courses/71/assignments/902",
        "/api/v1/courses/71/assignments/902/submissions/self",
    ]
    assert calls[0]["query"] == {"per_page": ["50"]}
    assert calls[1]["query"] == {
        "include[]": ["submission_history", "submission_comments"], "per_page": ["50"],
    }
    assert all(row["authorization"] == f"Bearer {TOKEN}" for row in calls)


@pytest.mark.parametrize("before,after", [
    ("history:1", "current"),
    ("history:2", "history:1"),
    ("history:3", "history:2"),
    ("current", "history:1"),
])
def test_actual_cli_produces_exact_offline_comparison(comparison_http, tmp_path, before, after):
    server = comparison_http
    untouched = deepcopy(server.payload)
    out = tmp_path / "比較 · café.html"
    result = process(server, ["00071", "0902", "--before", before, "--after", after, "--out", str(out)])
    record(f"cli-{before.replace(':', '-')}-{after.replace(':', '-')}", {
        "exit_code": result.returncode, "stdout": result.stdout,
        "stderr": result.stderr, "requests": server.calls,
        "output": str(out), "console_encoding": "cp1252:strict",
    })
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "ok": True, "output": str(out), "before": before, "after": after,
        "history_records_returned": 3,
    }
    assert_read_pair(server.calls)
    assert not server.profile.exists()
    assert server.payload == untouched
    html = out.read_text(encoding="utf-8")
    encoded = re.search(r'href="data:application/json;base64,([^"]+)"', html)[1]
    packet = json.loads(base64.b64decode(encoded, validate=True))
    current = {key: value for key, value in server.payload["submission"].items()
               if key not in {"submission_history", "submission_comments"}}
    expected = {"current": current, **{
        f"history:{index}": value
        for index, value in enumerate(server.payload["submission"]["submission_history"], 1)
    }}
    assert packet["before"] == {"selector": before, "record": expected[before]}
    assert packet["after"] == {"selector": after, "record": expected[after]}
    assert packet["request"] == {"course_id": "71", "assignment_id": "902"}
    assert html.endswith("</html>")
    assert "Current-only feedback, not a historical join" not in html
    assert list(tmp_path.iterdir()) == [out]


@pytest.mark.parametrize("variant,reads", [
    ("invalid_selector", 0), ("invalid_id", 0), ("existing_output", 0),
    ("unavailable_history", 2), ("malformed_history", 2),
    ("wrong_assignment", 2), ("read_refused", 2), ("auth_refused", 1),
])
def test_actual_cli_refusal_has_no_partial_report(comparison_http, tmp_path, variant, reads):
    server = comparison_http
    out = tmp_path / "refused.html"
    course, before = "71", "history:1"
    if variant == "invalid_selector":
        before = "history:01"
    elif variant == "invalid_id":
        course = "71/not-an-id"
    elif variant == "existing_output":
        out.write_bytes(b"existing-owner-data")
    elif variant == "unavailable_history":
        server.payload["submission"].pop("submission_history")
    elif variant == "malformed_history":
        server.payload["submission"]["submission_history"] = [None]
    elif variant == "wrong_assignment":
        server.payload["submission"]["submission_history"][0]["assignment_id"] = 999
    elif variant == "read_refused":
        server.submission_status = 503
    elif variant == "auth_refused":
        server.assignment_status = 403
    result = process(server, [course, "902", "--before", before, "--after", "current", "--out", str(out)])
    record(f"cli-{variant}", {
        "exit_code": result.returncode, "stdout": result.stdout,
        "stderr": result.stderr, "requests": server.calls, "output": str(out),
    })
    assert result.returncode == 1
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["ok"] is False
    assert error["error"] in {"ValueError", "FileExistsError", "HTTPStatusError", "CanvasAuthError"}
    assert "Traceback" not in result.stderr
    assert len(server.calls) == reads
    if reads == 2:
        assert_read_pair(server.calls)
    assert not server.profile.exists()
    if variant == "existing_output":
        assert out.read_bytes() == b"existing-owner-data"
        assert list(tmp_path.iterdir()) == [out]
    else:
        assert list(tmp_path.iterdir()) == []


def test_actual_cli_help_is_available_without_a_read(comparison_http):
    result = process(comparison_http, ["--help"])
    assert result.returncode == 0
    assert "--before" in result.stdout and "--after" in result.stdout and "--out" in result.stdout
    assert "chronology inference" in result.stdout
    assert comparison_http.calls == []

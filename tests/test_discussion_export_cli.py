"""Actual discussion export CLI against a synthetic read-only HTTP source."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
from test_discussion_export import Document
from test_discussion_thread import fixture

ROOT = Path(__file__).resolve().parents[1]
TOPIC = "/api/v1/courses/42/discussion_topics/7"


@pytest.fixture
def server():
    topic, view = fixture()
    state = SimpleNamespace(topic=topic, view=view, requests=[], status=200, on_view=lambda: None)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state.requests.append(("GET", self.path))
            status = 200
            path = urlsplit(self.path).path
            if path == TOPIC:
                value = state.topic
            elif path == TOPIC + "/view":
                state.on_view()
                status = state.status
                value = state.view if status == 200 else {"error": "Synthetic unavailable cache"}
            else:
                status, value = 404, {"error": "Unexpected fixture path"}
            body = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            state.requests.append(("POST", self.path))
            self.send_error(405)

        def log_message(self, *args):
            pass

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    state.base_url = f"http://127.0.0.1:{http.server_port}"
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=3)


def run(server, tmp_path, *arguments, out=None):
    destination = out if out is not None else tmp_path / "discussion.html"
    env = {
        "PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(ROOT / "src"),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "ascii",
        "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1",
    }
    command = [
        sys.executable, "-B", "-m", "canvaspilot.cli", "export-discussion",
        *arguments, "--out", str(destination), "--base-url", server.base_url,
        "--token", "synthetic-discussion-export", "--profile", str(tmp_path / "unused"),
    ]
    return subprocess.run(command, env=env, capture_output=True, text=True, timeout=20, check=False)


def test_cli_full_and_unread_reports_use_exact_two_gets_and_ascii_receipts(server, tmp_path):
    full = tmp_path / "Café-雪.html"
    result = run(server, tmp_path, "42", "7", out=full)
    assert result.returncode == 0 and result.stderr == ""
    receipt = json.loads(result.stdout)
    assert result.stdout.isascii() and receipt["output"] == str(full)
    assert receipt["entries_included"] == 6
    assert server.requests == [("GET", TOPIC + "?per_page=50"), ("GET", TOPIC + "/view?per_page=50")]
    focused = run(server, tmp_path, "42", "7", "--unread-only")
    assert focused.returncode == 0 and focused.stderr == ""
    report = json.loads(Document((tmp_path / "discussion.html").read_bytes()).payload())
    assert [row["entry"]["id"] for row in report["entries"]] == [1, 2, 3, 5]
    assert server.requests == [("GET", TOPIC + "?per_page=50"), ("GET", TOPIC + "/view?per_page=50")] * 2
    assert sorted(path.name for path in tmp_path.iterdir()) == ["Café-雪.html", "discussion.html"]


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling"])
def test_existing_destination_is_unchanged_and_refused_before_reads(server, tmp_path, kind):
    out = tmp_path / "discussion.html"
    target = tmp_path / "target"
    if kind == "file":
        out.write_bytes(b"existing discussion")
    elif kind == "directory":
        out.mkdir()
    else:
        if kind == "symlink":
            target.write_bytes(b"existing linked content")
        out.symlink_to(target)
    before = out.lstat()
    names = sorted(path.name for path in tmp_path.iterdir())
    result = run(server, tmp_path, "42", "7")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert out.lstat() == before and server.requests == []
    assert sorted(path.name for path in tmp_path.iterdir()) == names
    if kind == "file":
        assert out.read_bytes() == b"existing discussion"
    elif kind == "symlink":
        assert target.read_bytes() == b"existing linked content"


def test_unavailable_second_response_never_creates_partial_output(server, tmp_path):
    server.status = 503
    result = run(server, tmp_path, "42", "7")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "HTTPStatusError"
    assert server.requests == [("GET", TOPIC + "?per_page=50"), ("GET", TOPIC + "/view?per_page=50")]
    assert list(tmp_path.iterdir()) == []


def test_unknown_unread_selection_is_an_error_without_a_file(server, tmp_path):
    del server.view["unread_entries"]
    result = run(server, tmp_path, "42", "7", "--unread-only")
    assert result.returncode == 1 and result.stdout == ""
    assert "did not supply unread_entries" in json.loads(result.stderr)["message"]
    assert list(tmp_path.iterdir()) == []


def test_competing_destination_created_during_read_wins(server, tmp_path):
    destination = tmp_path / "discussion.html"
    server.on_view = lambda: destination.write_bytes(b"another creator won")
    result = run(server, tmp_path, "42", "7")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert destination.read_bytes() == b"another creator won"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["discussion.html"]


@pytest.mark.parametrize("ids", [("0", "7"), ("42", "-1"), ("../42", "7")])
def test_invalid_cli_ids_refuse_before_any_read(server, tmp_path, ids):
    result = run(server, tmp_path, *ids)
    assert result.returncode == 2 and result.stdout == ""
    assert server.requests == [] and list(tmp_path.iterdir()) == []

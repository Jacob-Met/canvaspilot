"""Actual CLI, HTTPX and filesystem receiving with fictional course data."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest


@pytest.fixture
def server():
    rows = {}
    calls = []
    hooks = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = urlsplit(self.path)
            calls.append({
                "method": "GET", "path": parts.path, "query": parse_qs(parts.query),
                "authorization": self.headers.get("Authorization"),
            })
            course_id = int(parts.path.rsplit("/", 1)[1])
            if course_id in hooks:
                hooks[course_id]()
            status, row = rows[course_id]
            body = json.dumps(row).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield rows, calls, hooks, f"http://127.0.0.1:{http.server_port}"
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)


def invoke(tmp_path, base, ids, output=None, extra=()):
    output = output or tmp_path / "syllabi.html"
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("CANVAS_") and not key.lower().endswith("_proxy")
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    command = [
        sys.executable, "-m", "canvaspilot.cli", "export-syllabus", *map(str, ids),
        "--out", str(output), "--base-url", base,
        "--token", "fictional-syllabus-test-token", "--profile", str(tmp_path / "unused-profile"),
        *extra,
    ]
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30, check=False)
    return result, output


def row(course_id, body):
    return {"id": course_id, "name": f"Fictional course {course_id}", "syllabus_body": body}


def test_actual_course_gets_and_success_json_follow_selected_order(server, tmp_path):
    rows, calls, _, base = server
    rows.update({43: (200, row(43, "<h2>Studio</h2>")), 42: (200, row(42, ""))})
    result, output = invoke(tmp_path, base, [43, 42])
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["ok"] is True and report["output"] == str(output)
    assert report["course_ids"] == [43, 42]
    assert report["syllabus_statuses"] == [
        {"course_id": 43, "status": "supplied"}, {"course_id": 42, "status": "empty"},
    ]
    assert output.read_text().index('id="course-43"') < output.read_text().index('id="course-42"')
    assert [c["path"] for c in calls] == ["/api/v1/courses/43", "/api/v1/courses/42"]
    for call in calls:
        assert call["method"] == "GET"
        assert call["query"] == {"include[]": ["syllabus_body", "term", "total_scores"], "per_page": ["50"]}
        assert call["authorization"] == "Bearer fictional-syllabus-test-token"
    assert not (tmp_path / "unused-profile").exists()


@pytest.mark.parametrize("ids,expected_exit", [
    ([42, 42], 1), ([0], 2), ([-2], 2), (["42/x"], 2), (list(range(1, 12)), 1),
])
def test_invalid_selection_never_requests_or_publishes(server, tmp_path, ids, expected_exit):
    _, calls, _, base = server
    result, output = invoke(tmp_path, base, ids)
    assert result.returncode == expected_exit
    assert result.stdout == ""
    assert not output.exists()
    assert calls == []
    if expected_exit == 1:
        assert json.loads(result.stderr)["ok"] is False


@pytest.mark.parametrize("status,body", [
    (401, {"error": "auth"}), (403, {"error": "forbidden"}), (500, {"error": "upstream"}),
    (200, {"id": 99, "syllabus_body": "foreign"}),
    (200, {"id": 43, "syllabus_body": False}),
    (200, None),
])
def test_later_course_failure_refuses_the_whole_file(server, tmp_path, status, body):
    rows, calls, _, base = server
    rows.update({42: (200, row(42, "<p>First valid course.</p>")), 43: (status, body)})
    result, output = invoke(tmp_path, base, [42, 43])
    assert result.returncode == 1
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["ok"] is False and error["message"]
    assert not output.exists()
    assert [c["path"] for c in calls] == ["/api/v1/courses/42", "/api/v1/courses/43"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling"])
def test_existing_output_refuses_before_http(server, tmp_path, kind):
    _, calls, _, base = server
    output = tmp_path / "syllabi.html"
    if kind == "file":
        output.write_bytes(b"existing")
    elif kind == "directory":
        output.mkdir()
    else:
        target = tmp_path / "target"
        if kind == "symlink":
            target.write_bytes(b"existing")
        output.symlink_to(target)
    before = set(tmp_path.iterdir())
    result, _ = invoke(tmp_path, base, [42], output)
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert calls == [] and set(tmp_path.iterdir()) == before
    if kind in {"file", "symlink"}:
        assert output.read_bytes() == b"existing"
    if kind in {"symlink", "dangling"}:
        assert output.is_symlink()


def test_concurrent_output_after_first_read_is_preserved(server, tmp_path):
    rows, calls, hooks, base = server
    output = tmp_path / "syllabi.html"
    rows.update({42: (200, row(42, "One")), 43: (200, row(43, "Two"))})
    hooks[43] = lambda: output.write_bytes(b"concurrent destination")
    result, _ = invoke(tmp_path, base, [42, 43], output)
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert len(calls) == 2 and output.read_bytes() == b"concurrent destination"
    assert list(tmp_path.iterdir()) == [output]


def test_native_recovery_reads_a_changed_body_into_a_different_new_file(server, tmp_path):
    rows, calls, _, base = server
    rows[42] = (403, {"error": "not available"})
    failed, output = invoke(tmp_path, base, [42])
    assert failed.returncode == 1 and not output.exists()
    rows[42] = (200, row(42, "<p>Accepted revision two.</p>"))
    accepted, output = invoke(tmp_path, base, [42])
    assert accepted.returncode == 0 and "Accepted revision two." in output.read_text()
    assert len(calls) == 2


def test_httpx_logging_level_is_restored_in_the_callers_process(tmp_path, monkeypatch, capsys):
    import logging

    from canvaspilot import cli
    from canvaspilot.client import CanvasClient

    original = CanvasClient.__init__

    def fixture_client(self, **kwargs):
        original(self, **kwargs, fixture={"routes": {"GET /api/v1/courses/42": row(42, "Source")}})

    monkeypatch.setattr(CanvasClient, "__init__", fixture_client)
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        cli.main(["export-syllabus", "42", "--out", str(tmp_path / "packet.html"),
                  "--base-url", "https://canvas.example.test", "--token", "fictional"])
        assert logger.level == logging.DEBUG
        assert json.loads(capsys.readouterr().out)["ok"] is True
    finally:
        logger.setLevel(previous)

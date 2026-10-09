"""Actual native CLI, HTTP pagination, complete output and lifecycle checks."""

import json
import logging
import os
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from canvaspilot import cli
from canvaspilot.client import CanvasClient

SOURCE = Path(__file__).resolve().parents[1] / "src"


@contextmanager
def server(respond):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append({"method": "GET", "path": self.path})
            status, body, headers = respond(self.path, self.server.server_address[1])
            payload = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            requests.append({"method": "POST", "path": self.path})
            self.send_error(405)

        def log_message(self, *_args):
            pass

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: http.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http.server_address[1]}", requests
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def invoke(tmp_path, origin, args):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("CANVAS_") or key.upper().endswith("_PROXY"):
            env.pop(key)
    env.update({
        "PYTHONPATH": str(SOURCE), "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": str(tmp_path / "home"), "NO_PROXY": "127.0.0.1",
    })
    return subprocess.run([
        sys.executable, "-B", "-m", "canvaspilot.cli", *args,
        "--base-url", origin, "--token", "synthetic-file-search-only",
        "--profile", str(tmp_path / "unused-profile"),
    ], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=15, check=False)


def test_real_cli_uses_complete_pages_selected_order_and_literal_metadata(tmp_path):
    rows = [
        {"id": 7, "display_name": "Straße.pdf", "filename": "unrelated.pdf",
         "size": 0, "url": "https://foreign.invalid/never-fetch", "folder_id": 99},
        {"id": 7, "display_name": None, "filename": "STRASSE.pdf",
         "content-type": "application/pdf", "url": "javascript:literal-only"},
    ]

    def respond(path, port):
        parsed = urlsplit(path)
        if parsed.path == "/api/v1/courses/77/files":
            return 200, [], {}
        assert parsed.path == "/api/v1/courses/42/files"
        if "cursor" not in parse_qs(parsed.query):
            assert parse_qs(parsed.query) == {"per_page": ["50"]}
            return 200, rows[:1], {
                "Link": f'<http://127.0.0.1:{port}/api/v1/courses/42/files?cursor=second%2Bpage>; rel="next"',
            }
        assert parsed.query == "cursor=second%2Bpage"
        return 200, rows[1:], {}

    with server(respond) as (origin, requests):
        first = invoke(tmp_path, origin, ["find-files", "0042", "77", "--text", "strasse"])
        second = invoke(tmp_path, origin, ["find-files", "0042", "77", "--text", "strasse"])
        existing = invoke(tmp_path, origin, ["files", "42"])
    assert first.returncode == second.returncode == existing.returncode == 0
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    report = json.loads(first.stdout)
    assert [c["course_id"] for c in report["courses"]] == ["42", "77"]
    matches = report["courses"][0]["matches"]
    assert [m["source_position"] for m in matches] == [1, 2]
    assert [m["matched_fields"] for m in matches] == [["display_name"], ["filename"]]
    assert [m["file"] for m in matches] == json.loads(existing.stdout)
    assert "folder_id" not in matches[0]["file"]
    assert matches[0]["file"]["size"] == 0
    assert report["courses"][1]["matches"] == []
    assert len(requests) == 8
    assert all(r["method"] == "GET" and "/courses/" in r["path"] and "/files" in r["path"] for r in requests)
    assert not (tmp_path / "unused-profile").exists()


@pytest.mark.parametrize("failure", ["http", "auth", "json", "shape", "foreign-next"])
def test_later_page_failure_has_no_partial_stdout_or_next_course(tmp_path, failure):
    def respond(path, port):
        parsed = urlsplit(path)
        assert parsed.path == "/api/v1/courses/42/files"
        if "cursor" not in parse_qs(parsed.query):
            return 200, [{"id": 1, "filename": "lab.pdf"}], {
                "Link": f'<http://127.0.0.1:{port}/api/v1/courses/42/files?cursor=next>; rel="next"',
            }
        if failure == "http":
            return 503, {"error": "authored unavailable"}, {}
        if failure == "auth":
            return 403, {"error": "authored refusal"}, {}
        if failure == "json":
            return 200, b"{not-json", {}
        if failure == "shape":
            return 200, {"not": "a collection"}, {}
        return 200, [], {"Link": '<https://foreign.invalid/never>; rel="next"'}

    with server(respond) as (origin, requests):
        result = invoke(tmp_path, origin, ["find-files", "42", "77", "--text", "lab"])
    assert result.returncode == 1 and result.stdout == ""
    error = json.loads(result.stderr)
    assert error["ok"] is False and error["error"] and error["message"]
    assert len(requests) == 2


def test_second_course_failure_does_not_publish_first_course(tmp_path):
    def respond(path, _port):
        if "/courses/42/" in path:
            return 200, [{"filename": "lab.pdf"}], {}
        assert "/courses/77/" in path
        return 500, {"error": "second selected course unavailable"}, {}

    with server(respond) as (origin, requests):
        result = invoke(tmp_path, origin, ["find-files", "42", "77", "--text", "lab"])
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["ok"] is False
    assert len(requests) == 2


@pytest.mark.parametrize("args", [
    ["find-files", "42", "0", "--text", "lab"],
    ["find-files", "42", "042", "--text", "lab"],
    ["find-files", "42", "--text", "   "],
    ["find-files", "42", "--text", "雪" * 171],
])
def test_cli_preflight_refuses_before_constructing_client(monkeypatch, capsys, args):
    constructed = []

    def forbidden(**kwargs):
        constructed.append(kwargs)
        raise AssertionError("client must not be constructed")

    monkeypatch.setattr("canvaspilot.client.CanvasClient", forbidden)
    with pytest.raises(SystemExit) as caught:
        cli.main(args)
    captured = capsys.readouterr()
    assert caught.value.code == 2 and captured.out == ""
    assert "error:" in captured.err and constructed == []


@pytest.mark.parametrize("status", [200, 500])
def test_existing_client_close_and_http_logger_level_are_preserved(monkeypatch, capsys, status):
    def respond(_path, _port):
        return status, [{"display_name": "lab", "filename": "lab.pdf"}], {}

    with server(respond) as (origin, requests):
        client = CanvasClient(base_url=origin, token="synthetic-file-search-only", profile=Path("unused"))
        original_close = client.close
        closes = []

        def close():
            closes.append(True)
            original_close()

        monkeypatch.setattr(client, "close", close)
        monkeypatch.setattr("canvaspilot.client.CanvasClient", lambda **_kwargs: client)
        logger = logging.getLogger("httpx")
        previous = logger.level
        logger.setLevel(23)
        try:
            if status == 200:
                cli.main(["find-files", "42", "--text", "lab"])
            else:
                with pytest.raises(SystemExit) as caught:
                    cli.main(["find-files", "42", "--text", "lab"])
                assert caught.value.code == 1
            assert logger.level == 23
        finally:
            logger.setLevel(previous)
    captured = capsys.readouterr()
    assert closes == [True] and client._http is None and len(requests) == 1
    if status == 200:
        assert json.loads(captured.out)["totals"]["matched_files"] == 1
        assert captured.err == ""
    else:
        assert captured.out == "" and json.loads(captured.err)["ok"] is False

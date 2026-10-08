"""Real loopback HTTP, production parser/client and output receiving."""
import json
import logging
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import pytest

from canvaspilot import cli


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            self.server.seen.append((parsed.path, parse_qs(parsed.query)))
            mode = self.server.mode
            if parsed.path == "/api/v1/users/self/profile":
                payload = {"id": 123, "name": "Fictional learner"}
            elif parsed.path != "/api/v1/courses/42/pages":
                self.send_error(404)
                return
            elif mode == "empty":
                payload = []
            elif "cursor" in parse_qs(parsed.query):
                if mode == "later-failure":
                    self.send_error(500)
                    return
                payload = [{"page_id": 2, "url": "two", "title": "FIELD JOURNAL", "body": None, "unknown": False}]
                if mode == "malformed":
                    payload.append({"page_id": 3, "body": 7})
            else:
                payload = [{"page_id": 1, "url": "one", "title": "Notes", "body": "<p>field <i>journal</i></p>"}]
            data = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            if parsed.path.endswith("/pages") and mode != "empty" and not parsed.query.startswith("cursor="):
                self.send_header("Link", f'<http://127.0.0.1:{self.server.server_port}/api/v1/courses/42/pages?cursor=second%2Bopaque>; rel="next"')
            self.end_headers()
            self.wfile.write(data)
    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    http.mode = "success"
    http.seen = []
    thread = Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield http
    finally:
        http.shutdown()
        thread.join(timeout=5)
        http.server_close()


def invoke(server, tmp_path, args):
    stdout, stderr = StringIO(), StringIO()
    logger = logging.getLogger("httpx")
    prior = logger.level
    logger.setLevel(logging.INFO)
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                cli.main([*args, "--base-url", f"http://127.0.0.1:{server.server_port}",
                          "--token", "fictional-local-fixture", "--profile", str(tmp_path / "unused-profile")])
                exit_code = 0
            except SystemExit as error:
                exit_code = error.code
        assert logger.level == logging.INFO
    finally:
        logger.setLevel(prior)
    assert not (tmp_path / "unused-profile").exists()
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_actual_cli_complete_collection_and_original_command(server, tmp_path):
    status, out, err = invoke(server, tmp_path, ["find-pages", "0042", "--text", "field journal"])
    assert status == 0 and err == ""
    result = json.loads(out)
    assert result["pages_returned"] == result["pages_matched"] == 2
    assert result["bodies_searched"] == 1
    assert [m["page"]["page_id"] for m in result["matches"]] == [1, 2]
    assert result["matches"][1]["page"]["unknown"] is False
    assert server.seen == [
        ("/api/v1/courses/42/pages", {"include[]": ["body"], "per_page": ["50"]}),
        ("/api/v1/courses/42/pages", {"cursor": ["second+opaque"]}),
    ]
    status, out, err = invoke(server, tmp_path, ["whoami"])
    assert status == 0 and json.loads(out)["profile"]["id"] == 123 and err == ""


@pytest.mark.parametrize("mode", ["later-failure", "malformed"])
def test_actual_cli_refuses_after_earlier_match(server, tmp_path, mode):
    server.mode = mode
    status, out, err = invoke(server, tmp_path, ["find-pages", "42", "--text", "field journal"])
    assert status == 1 and out == ""
    assert json.loads(err)["ok"] is False
    assert len(server.seen) == 2


def test_actual_cli_empty_collection(server, tmp_path):
    server.mode = "empty"
    status, out, err = invoke(server, tmp_path, ["find-pages", "42", "--text", "x"])
    assert status == 0 and err == ""
    assert json.loads(out)["pages_returned"] == 0


def test_actual_cli_invalid_query_stops_before_client(server, tmp_path, monkeypatch):
    def no_client(*a, **kw):
        pytest.fail("invalid argument initialized client")
    monkeypatch.setattr("canvaspilot.client.CanvasClient", no_client)
    status, out, err = invoke(server, tmp_path, ["find-pages", "42", "--text", " \t"])
    assert status == 2 and out == "" and "non-whitespace" in err
    assert server.seen == []

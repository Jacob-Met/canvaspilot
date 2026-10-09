"""Native CLI page discovery through synthetic loopback Canvas responses."""
from __future__ import annotations

import contextlib
import io
import json
import logging
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import pytest

from canvaspilot.cli import main
from canvaspilot.client import CanvasClient

SRC = Path(__file__).resolve().parents[1] / "src"


@contextlib.contextmanager
def canvas(routes):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append({"method": "GET", "path": self.path})
            response = routes(self.path, self.server.server_port)
            code, value, headers = response
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def command(base, *args, stdout=subprocess.PIPE):
    env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, "-B", "-m", "canvaspilot.cli", *args,
         "--base-url", base, "--token", "synthetic-pages-only"],
        env=env, stdout=stdout, stderr=subprocess.PIPE, text=True, timeout=20, check=False,
    )


def test_pages_keeps_order_null_false_and_follows_opaque_link():
    rows = [
        {"url": "week-one", "title": "Week one", "published": False,
         "updated_at": None, "front_page": True, "unprojected": "native API omits"},
        {"url": "café", "title": "研究", "published": True},
        {"url": "week-one", "title": "Repeated ID stays a separate row", "front_page": False},
    ]

    def route(path, port):
        parsed = urlsplit(path)
        assert parsed.path == "/api/v1/courses/42/pages"
        if parse_qs(parsed.query).get("cursor") == ["last"]:
            return 200, rows[2:], {}
        return 200, rows[:2], {
            "Link": f'<http://127.0.0.1:{port}/api/v1/courses/42/pages?cursor=last>; rel="next"',
        }

    with canvas(route) as (base, requests):
        result = command(base, "pages", "42")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    keys = ("url", "title", "published", "updated_at", "front_page")
    assert json.loads(result.stdout) == [{k: row.get(k) for k in keys} for row in rows]
    assert len(requests) == 2
    assert urlsplit(requests[1]["path"]).query == "cursor=last"


def test_empty_collection_and_existing_nonobject_filtering():
    for payload, expected in [([], []), ([None, 0, {"url": "kept"}], [
        {"url": "kept", "title": None, "published": None, "updated_at": None, "front_page": None},
    ])]:
        with canvas(lambda *_, value=payload: (200, value, {})) as (base, requests):
            result = command(base, "pages", "42")
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout) == expected
        assert len(requests) == 1


def test_page_preserves_original_html_and_existing_text_projection():
    body = "<h2>Reading &amp; practice</h2><p>Bring your notes.</p>"
    row = {"url": "reading", "title": "Today's reading", "body": body,
           "published": False, "front_page": True}
    with canvas(lambda *_: (200, row, {})) as (base, requests):
        result = command(base, "page", "42", "reading")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "url": "reading", "title": "Today's reading", "body_html": body,
        "body_text": "Reading & practice Bring your notes.", "published": False,
    }
    assert requests == [{"method": "GET", "path": "/api/v1/courses/42/pages/reading?per_page=50"}]


@pytest.mark.parametrize("payload,html", [({}, None), ({"body": None}, None), ({"body": ""}, "")])
def test_absent_null_empty_page_body(payload, html):
    with canvas(lambda *_: (200, payload, {})) as (base, _):
        result = command(base, "page", "42", "reading")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "url": None, "title": None, "body_html": html, "body_text": "", "published": None,
    }


@pytest.mark.parametrize("locator,encoded", [
    ("café 100%?draft#one", "caf%C3%A9%20100%25%3Fdraft%23one"),
    ("page_id:00170", "page_id%3A170"),
    ("170", "170"),
])
def test_locator_is_admitted_then_encoded_as_one_literal_segment(locator, encoded):
    with canvas(lambda *_: (200, {"body": "ok"}, {})) as (base, requests):
        result = command(base, "page", "00042", locator)
    assert result.returncode == 0, result.stderr
    assert requests == [{"method": "GET", "path": "/api/v1/courses/42/pages/" + encoded + "?per_page=50"}]


def test_invalid_arguments_and_help_do_not_create_client():
    invalid = [
        ["pages", "0"], ["pages", "-1"], ["pages", "abc"], ["pages"],
        ["page", "42"], ["page", "42", ""], ["page", "42", " x"],
        ["page", "42", "x "], ["page", "42", "."], ["page", "42", ".."],
        ["page", "42", "week/one"], ["page", "42", "week\\one"],
        ["page", "42", "line\nfeed"], ["page", "42", "control\x01"],
        ["page", "42", "x" * 513], ["page", "42", "é" * 257],
        ["page", "42", "page_id:0"], ["page", "42", "page_id:x"],
        ["page", "42", "https://example.test/a"], ["page", "42", "\ud800"],
    ]
    with mock.patch("canvaspilot.client.CanvasClient") as constructor:
        for args in invalid:
            with (
                contextlib.redirect_stdout(io.StringIO()) as out,
                contextlib.redirect_stderr(io.StringIO()),
                pytest.raises(SystemExit) as error,
            ):
                main(args)
            assert error.value.code == 2
            assert out.getvalue() == ""
        for args in (["pages", "--help"], ["page", "--help"]):
            with (
                contextlib.redirect_stdout(io.StringIO()) as out,
                pytest.raises(SystemExit) as error,
            ):
                main(args)
            assert error.value.code == 0
            assert "course_id" in out.getvalue()
        constructor.assert_not_called()


def test_later_page_failure_is_not_partial_success():
    def route(path, port):
        if "cursor=bad" in path:
            return 503, {"error": "synthetic second-page failure"}, {}
        return 200, [{"url": "first"}], {
            "Link": f'<http://127.0.0.1:{port}/api/v1/courses/42/pages?cursor=bad>; rel="next"',
        }

    with canvas(route) as (base, requests):
        result = command(base, "pages", "42")
    assert result.returncode == 1
    assert result.stdout == ""
    assert json.loads(result.stderr)["ok"] is False
    assert len(requests) == 2


@pytest.mark.parametrize("args,payload,status", [
    (["page", "42", "reading"], [], 200),
    (["page", "42", "reading"], None, 200),
    (["page", "42", "reading"], {"error": "denied"}, 403),
    (["pages", "42"], {"error": "denied"}, 403),
])
def test_read_failures_are_structured(args, payload, status):
    with canvas(lambda *_: (status, payload, {})) as (base, _):
        result = command(base, *args)
    assert result.returncode == 1
    assert result.stdout == ""
    report = json.loads(result.stderr)
    assert report["ok"] is False
    assert report["error"] and report["message"]


def test_same_process_error_then_success_restores_logger_and_closes_http_client():
    logger = logging.getLogger("httpx")
    previous = logger.level
    logger.setLevel(logging.INFO)
    try:
        with canvas(lambda path, _: (403, {}, {}) if "denied" in path else (200, {"body": "ok"}, {})) as (base, _):
            for locator, expected_exit in [("denied", 1), ("allowed", None)]:
                client = CanvasClient(base_url=base, token="synthetic-pages-only")
                real_close = client.close
                with (
                    mock.patch.object(client, "close", wraps=real_close) as close,
                    mock.patch("canvaspilot.client.CanvasClient", return_value=client),
                    contextlib.redirect_stdout(io.StringIO()) as out,
                    contextlib.redirect_stderr(io.StringIO()) as err,
                ):
                    if expected_exit:
                        with pytest.raises(SystemExit) as error:
                            main(["page", "42", locator])
                        assert error.value.code == expected_exit
                    else:
                        main(["page", "42", locator])
                    assert logger.level == logging.INFO
                    close.assert_called_once()
                    if expected_exit:
                        assert out.getvalue() == ""
                        assert json.loads(err.getvalue())["ok"] is False
                    else:
                        assert json.loads(out.getvalue())["body_text"] == "ok"
                        assert err.getvalue() == ""
    finally:
        logger.setLevel(previous)


@pytest.mark.skipif(not Path("/dev/full").exists(), reason="native /dev/full unavailable")
def test_failed_stdout_is_nonzero_and_client_read_remains_get_only():
    with (
        canvas(lambda *_: (200, [], {})) as (base, requests),
        open("/dev/full", "w") as sink,
    ):
        result = command(base, "pages", "42", stdout=sink)
    assert result.returncode != 0
    assert '"ok": false' in result.stderr
    assert all(row["method"] == "GET" for row in requests)


def test_existing_quiz_command_remains_unchanged():
    row = {"id": 9, "title": "Existing quiz", "published": False, "extra": {"kept": True}}
    with canvas(lambda *_: (200, row, {})) as (base, requests):
        result = command(base, "quiz", "42", "9")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == row
    assert requests == [{"method": "GET", "path": "/api/v1/courses/42/quizzes/9?per_page=50"}]

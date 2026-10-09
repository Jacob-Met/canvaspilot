"""Actual CLI, HTTPX, pagination, publication and refusal checks."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from test_module_study_packet import Document

SOURCE = Path(__file__).resolve().parents[1] / "src"


def items():
    return [
        {"id": 1, "module_id": 7, "position": 1, "type": "SubHeader", "title": "Reading unit"},
        {"id": 2, "module_id": 7, "position": 2, "type": "Page", "page_url": "reading", "title": "Read first"},
        {"id": 3, "module_id": 7, "position": 3, "type": "Assignment", "content_id": 1001, "title": "Explain"},
        {"id": 4, "module_id": 7, "position": 4, "type": "File", "content_id": 44, "title": "Attachment"},
        {"id": 5, "module_id": 7, "position": 4, "type": "Page", "page_url": "reading", "title": "Read again"},
        {"id": 6, "module_id": 7, "position": 6, "type": "Quiz", "content_id": 55, "title": "Later quiz"},
    ]


@contextmanager
def provider(tmp_path, *, fail=None, count=6, inline=None, page_extra=None, publish_race=None):
    requests = []
    source_items = items() if inline is None else inline
    selected = {"id": 7, "course_id": 42, "name": "Fictional module",
                "items_count": count, "state": "started", "requirement_type": "all"}
    if inline is not None:
        selected["items"] = inline
    page = {"page_id": 201, "url": "reading", "title": "Read", "body": "<p>Original reading.</p>",
            "locked_for_user": False, **(page_extra or {})}
    assignment = {"id": 1001, "name": "Explain", "description": "<p>Your own explanation.</p>",
                  "points_possible": 0, "due_at": None, "submission_types": [],
                  "rubric": [], "rubric_settings": None, "use_rubric_for_grading": False}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            path = parsed.path
            requests.append({"method": "GET", "path": path, "query": query,
                             "synthetic_auth": self.headers.get("Authorization") == "Bearer module-test"})
            if path.endswith("/assignments/1001") and fail == "assignment":
                self.send_response(503)
                self.end_headers()
                return
            if path.endswith("/modules") and fail == "modules":
                self.send_response(403)
                self.end_headers()
                return
            link = None
            if path.endswith("/modules"):
                if "cursor" not in query:
                    value = [selected]
                    link = f'<http://127.0.0.1:{self.server.server_port}{path}?cursor=next-modules>; rel="next"'
                else:
                    value = [{"id": 8, "items_count": 0, "items": []}]
            elif path.endswith("/modules/7/items"):
                if "cursor" not in query:
                    value = source_items[:2]
                    link = f'<http://127.0.0.1:{self.server.server_port}{path}?cursor=rest-items>; rel="next"'
                else:
                    if fail == "later-items":
                        self.send_response(500)
                        self.end_headers()
                        return
                    value = source_items[2:]
            elif path.endswith("/pages/reading"):
                if publish_race is not None:
                    publish_race.write_text("other-writer", encoding="utf-8")
                value = page
            elif path.endswith("/assignments/1001"):
                value = assignment
            elif path == "/api/v1/users/self/profile":
                value = {"id": 100, "name": "Synthetic user"}
            else:
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            if link:
                self.send_header("Link", link)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            requests.append({"method": "POST", "path": self.path})
            self.send_response(405)
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests, selected, page
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def run(tmp_path, base, command=None):
    env = dict(os.environ)
    env.update({"PYTHONPATH": str(SOURCE), "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONIOENCODING": "utf-8", "CANVAS_API_TOKEN": "module-test",
                "CANVAS_BASE_URL": base, "CANVAS_PROFILE": str(tmp_path / "unused-profile")})
    args = command or ["export-module", "42", "7", "--out", str(tmp_path / "packet.html")]
    return subprocess.run([sys.executable, "-B", "-m", "canvaspilot.cli", *args],
                          env=env, cwd=tmp_path, capture_output=True, timeout=45, check=False)


def test_real_cli_collects_paginated_module_and_items_then_exact_readings_once(tmp_path):
    with provider(tmp_path) as (base, requests, selected, page):
        result = run(tmp_path, base)
    assert result.returncode == 0, result.stderr.decode()
    assert result.stderr == b""
    receipt = json.loads(result.stdout)
    packet = (tmp_path / "packet.html").read_bytes()
    raw = json.loads(Document(packet).source)
    assert receipt["ok"] is True and receipt["items"] == 6 and receipt["unique_resources"] == 2
    assert raw["module"] == {**selected, "items": items()}
    assert raw["resources"][0]["page"] == page
    assert raw["resources"][1]["brief"]["points_possible"] == 0
    assert raw["resources"][1]["brief"]["use_rubric_for_grading"] is False
    assert raw["item_resources"] == [None, 0, 1, None, 0, None]
    assert [r["path"] for r in requests] == [
        "/api/v1/courses/42/modules", "/api/v1/courses/42/modules",
        "/api/v1/courses/42/modules/7/items", "/api/v1/courses/42/modules/7/items",
        "/api/v1/courses/42/pages/reading", "/api/v1/courses/42/assignments/1001",
    ]
    assert requests[0]["query"]["include[]"] == ["items"]
    assert requests[1]["query"] == {"cursor": ["next-modules"]}
    assert requests[3]["query"] == {"cursor": ["rest-items"]}
    assert all(r["method"] == "GET" and r["synthetic_auth"] for r in requests)
    assert not (tmp_path / "unused-profile").exists()


@pytest.mark.parametrize("failure", ["modules", "later-items", "assignment"])
def test_read_failure_never_publishes_partial_html_or_success(tmp_path, failure):
    with provider(tmp_path, fail=failure) as (base, requests, *_):
        result = run(tmp_path, base)
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert not (tmp_path / "packet.html").exists()
    assert all(r["method"] == "GET" for r in requests)


@pytest.mark.parametrize("count", [None, 0, 5, 7, True, "6"])
def test_reported_count_uncertainty_or_mismatch_refuses_before_content(tmp_path, count):
    with provider(tmp_path, count=count, inline=items() if count == 0 else None) as (base, requests, *_):
        result = run(tmp_path, base)
    assert result.returncode == 1 and result.stdout == b""
    assert "items_count" in json.loads(result.stderr)["message"]
    assert all("/pages/" not in r["path"] and "/assignments/" not in r["path"] for r in requests)
    assert not (tmp_path / "packet.html").exists()


@pytest.mark.parametrize("size,kind", [(101, "File"), (21, "Page")])
def test_complete_preflight_refuses_item_and_unique_resource_excess(tmp_path, size, kind):
    rows = [{"id": i + 1, "module_id": 7, "type": kind, "title": f"Item {i}",
             "page_url": f"page-{i}", "content_id": i + 1} for i in range(size)]
    with provider(tmp_path, count=size, inline=rows) as (base, requests, *_):
        result = run(tmp_path, base)
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert len(requests) == 2
    assert all(r["path"].endswith("/modules") for r in requests)
    assert not (tmp_path / "packet.html").exists()


@pytest.mark.parametrize("entry", ["file", "directory", "symlink", "dangling"])
def test_existing_destination_is_refused_before_any_request(tmp_path, entry):
    output = tmp_path / "packet.html"
    if entry == "file":
        output.write_bytes(b"keep original")
    elif entry == "directory":
        output.mkdir()
    else:
        target = tmp_path / "target"
        if entry == "symlink":
            target.write_bytes(b"keep target")
        try:
            output.symlink_to(target)
        except OSError as error:
            pytest.skip(f"Native symlink creation unavailable: {error}")
    with provider(tmp_path) as (base, requests, *_):
        result = run(tmp_path, base)
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert requests == []
    if entry == "file":
        assert output.read_bytes() == b"keep original"
    if entry in {"symlink", "dangling"}:
        assert output.is_symlink()


def test_destination_appearing_during_reads_is_preserved(tmp_path):
    output = tmp_path / "packet.html"
    with provider(tmp_path, publish_race=output) as (base, requests, *_):
        result = run(tmp_path, base)
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert output.read_text() == "other-writer"
    assert len(requests) == 6
    assert not list(tmp_path.glob(".canvaspilot-pages-*"))


def test_wrong_page_identity_refuses_without_successful_output(tmp_path):
    with provider(tmp_path, page_extra={"url": "different-page"}) as (base, requests, *_):
        result = run(tmp_path, base)
    assert result.returncode == 1 and result.stdout == b""
    assert "locator" in json.loads(result.stderr)["message"]
    assert not (tmp_path / "packet.html").exists()
    assert len(requests) == 5


@pytest.mark.parametrize("identity", ["0", "-7", "bad", "ä¸ƒ"])
def test_invalid_module_selection_has_no_request_or_profile(tmp_path, identity):
    with provider(tmp_path) as (base, requests, *_):
        result = run(tmp_path, base, ["export-module", "42", identity, "--out", str(tmp_path / "packet.html")])
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert requests == [] and not (tmp_path / "unused-profile").exists()


def test_help_and_existing_identity_command_retain_their_behavior(tmp_path):
    with provider(tmp_path) as (base, requests, *_):
        help_result = run(tmp_path, base, ["export-module", "--help"])
        assert help_result.returncode == 0 and b"MODULE_ID" in help_result.stdout.upper()
        assert requests == []
        identity = run(tmp_path, base, ["whoami"])
    assert identity.returncode == 0, identity.stderr.decode()
    assert json.loads(identity.stdout) == {
        "base_url": base, "mode": "token", "profile": {"id": 100, "name": "Synthetic user"},
    }
    assert [r["path"] for r in requests] == ["/api/v1/users/self/profile"]


def test_json_download_is_literal_complete_source_without_script_execution(tmp_path):
    with provider(tmp_path, page_extra={"body": '<script>window.bad=1</script><p>Read &amp; keep.</p>'}) as (base, *_):
        result = run(tmp_path, base)
    assert result.returncode == 0
    doc = Document((tmp_path / "packet.html").read_bytes())
    raw = json.loads(doc.source)
    assert raw["resources"][0]["page"]["body"].startswith("<script>")
    assert "script" not in doc.tags
    href = next(a["href"] for tag, a in doc.attrs if tag == "a" and a.get("download"))
    assert base64.b64decode(href.split(",", 1)[1]) == doc.source


def test_existing_reader_zero_count_normalization_is_an_explicit_empty_packet(tmp_path):
    with provider(tmp_path, count=0) as (base, requests, selected, _):
        result = run(tmp_path, base)
    assert result.returncode == 0, result.stderr.decode()
    receipt = json.loads(result.stdout)
    assert receipt["items"] == 0 and receipt["unique_resources"] == 0
    raw = json.loads(Document((tmp_path / "packet.html").read_bytes()).source)
    assert raw["module"] == {**selected, "items": []}
    assert all(r["path"] == "/api/v1/courses/42/modules" for r in requests)
    assert len(requests) == 2

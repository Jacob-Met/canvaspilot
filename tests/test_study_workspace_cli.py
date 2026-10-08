"""Actual loopback HTTP and installed CLI boundaries for study workspace exports."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

FIXTURE = Path(__file__).parent / "fixtures/study_workspace_assignments.json"


def envelope(page):
    match = re.search(
        r'<script id="workspace-data" type="application/json">(.*?)</script>',
        page.decode(),
        re.DOTALL,
    )
    assert match
    return json.loads(match.group(1))


@contextmanager
def fixture_server(*, fail_assignment=None, raw_id_override=None):
    data = json.loads(FIXTURE.read_text())
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append({"method": "GET", "path": self.path})
            parsed = urlsplit(self.path)
            prefix = "/api/v1/courses/17/assignments/"
            assignment = parsed.path.removeprefix(prefix)
            if not parsed.path.startswith(prefix) or parse_qs(parsed.query) != {
                "include[]": ["submission"],
                "per_page": ["50"],
            }:
                status, body = 400, {"error": "unexpected fixture request"}
            elif self.headers.get("Authorization") != "Bearer study-fixture-token":
                status, body = 401, {"error": "synthetic token missing"}
            elif assignment == fail_assignment:
                status, body = 503, {"error": "deliberate fixture refusal"}
            else:
                original = data.get(assignment, data["81"])
                body = copy.deepcopy(original)
                body["html_url"] = base + "/courses/17/assignments/" + assignment
                body["id"] = (
                    raw_id_override if raw_id_override is not None else int(assignment)
                )
                status = 200
            content = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self):
            requests.append({"method": "POST", "path": self.path})
            self.send_error(405)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = "http://127.0.0.1:" + str(server.server_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield base, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def command(base, output, ids=("81", "82", "83"), *, course="17"):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "canvaspilot.cli",
            "export-study",
            course,
            *ids,
            "--base-url",
            base,
            "--token",
            "study-fixture-token",
            "--out",
            str(output),
        ],
        capture_output=True,
        check=False,
        text=True,
        env=env,
        timeout=20,
    )


def test_real_cli_gets_only_explicit_assignments_and_keeps_reader_metadata(tmp_path):
    before = FIXTURE.read_bytes()
    with fixture_server() as (base, requests):
        output = tmp_path / "study.html"
        result = command(base, output)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert result.stderr == "" and report["ok"] is True
    assert report["assignment_ids"] == ["81", "82", "83"]
    assert len(requests) == 3 and {item["method"] for item in requests} == {"GET"}
    doc = envelope(output.read_bytes())
    source = json.loads(doc["source"])
    first, second, third = [item["brief"] for item in source["assignments"]]
    assert first["points_possible"] == 0
    assert first["rubric"][0]["ratings"][2]["points"] == 0
    assert first["rubric_settings"]["hide_score_total"] is True
    assert first["rubric_warnings"] == [
        "rubric[1].points: invalid value; field omitted"
    ]
    assert second["use_rubric_for_grading"] is False
    assert second["rubric_settings"]["hide_points"] is True
    assert third["rubric"] == [] and third["points_possible"] is None
    assert "UNEXPORTED_SUBMISSION_SENTINEL" not in output.read_text()
    assert "UNEXPORTED_GRADE_SENTINEL" not in output.read_text()
    assert FIXTURE.read_bytes() == before


def test_existing_output_refuses_before_http_and_preserves_bytes_mtime(tmp_path):
    output = tmp_path / "study.html"
    output.write_bytes(b"existing work")
    original = output.stat()
    with fixture_server() as (base, requests):
        result = command(base, output)
    assert result.returncode == 1 and not requests and not result.stdout
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert output.read_bytes() == b"existing work"
    assert output.stat().st_mtime_ns == original.st_mtime_ns


@pytest.mark.parametrize(
    "ids",
    [("81", "81"), ("81", "081"), ("81", "bad/id"), tuple(str(i) for i in range(26))],
)
def test_whole_selection_refuses_without_read_or_output(tmp_path, ids):
    output = tmp_path / "study.html"
    with fixture_server() as (base, requests):
        result = command(base, output, ids)
    assert result.returncode == 1 and not requests and not output.exists()
    assert not result.stdout and json.loads(result.stderr)["ok"] is False


def test_second_read_failure_does_not_publish_a_partial_workspace(tmp_path):
    output = tmp_path / "study.html"
    with fixture_server(fail_assignment="82") as (base, requests):
        result = command(base, output)
    assert result.returncode == 1 and not output.exists() and not result.stdout
    assert len(requests) == 2
    assert json.loads(result.stderr)["error"] == "HTTPStatusError"
    assert not list(tmp_path.glob(".canvaspilot-study-*"))


def test_requested_ids_are_exact_strings_and_raw_response_identity_is_not_claimed(
    tmp_path,
):
    output = tmp_path / "study.html"
    with fixture_server(raw_id_override=999) as (base, requests):
        result = command(base, output, ("9007199254740993",))
    assert result.returncode == 0, result.stderr
    source = json.loads(envelope(output.read_bytes())["source"])
    assert source["assignments"][0]["key"] == "17:9007199254740993"
    assert source["assignments"][0]["brief"]["assignment_id"] == "9007199254740993"
    assert source["source_boundary"]["upstream_response_identity"] == "not_observed"
    assert requests[0]["path"].startswith(
        "/api/v1/courses/17/assignments/9007199254740993?"
    )
    assert (
        hashlib.sha256(envelope(output.read_bytes())["source"].encode()).hexdigest()
        == json.loads(result.stdout)["snapshot_sha256"]
    )


def test_cli_restores_logger_and_closes_client_after_reader_failure(
    tmp_path, monkeypatch, capsys
):
    from canvaspilot.client import CanvasClient
    from canvaspilot.study_workspace import run_export_study

    closed = []

    def refused(*args, **kwargs):
        raise ValueError("deliberate reader failure")

    monkeypatch.setattr(CanvasClient, "request", refused)
    monkeypatch.setattr(CanvasClient, "close", lambda self: closed.append(True))
    logger = logging.getLogger("httpx")
    original_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        with pytest.raises(SystemExit, match="1"):
            run_export_study(
                SimpleNamespace(
                    course_id="17",
                    assignment_ids=["81"],
                    out=tmp_path / "study.html",
                    base_url="https://canvas.fixture.invalid",
                    token="study-fixture-token",
                    profile=str(tmp_path / "unused-profile"),
                )
            )
        assert logger.level == logging.INFO and closed == [True]
    finally:
        logger.setLevel(original_level)
    output = capsys.readouterr()
    assert not output.out and json.loads(output.err)["ok"] is False

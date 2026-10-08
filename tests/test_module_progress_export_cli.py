"""Actual export command, paginated loopback reads, and protected output paths."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

import pytest
from module_progress_fixture import ModuleProgressHTTPFixture


class DownloadLink(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.payload = None
        self.feed(content.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if tag == "a" and fields.get("id") == "download-report":
            self.payload = base64.b64decode(fields["href"].split(",", 1)[1], validate=True)


@pytest.fixture
def server():
    fixture = ModuleProgressHTTPFixture()
    try:
        yield fixture
    finally:
        fixture.close()


def command(server, tmp_path, *arguments, command_name="export-module-progress", out=None, extra_env=None):
    env = {key: value for key, value in os.environ.items()
           if not key.upper().endswith("_PROXY") and not key.startswith("CANVAS")}
    env.update(PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
               PYTHONDONTWRITEBYTECODE="1")
    env.update(extra_env or {})
    argv = [
        sys.executable, "-B", "-m", "canvaspilot.cli", command_name, *arguments,
        "--base-url", server.base_url, "--token", "synthetic-module-export-only",
        "--profile", str(tmp_path / "unused-profile"),
    ]
    if command_name == "export-module-progress":
        argv.extend(["--out", str(out or tmp_path / "progress.html")])
    return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=20, check=False)


def test_actual_cli_json_matches_unchanged_progress_command_and_page_order(server, tmp_path):
    before = deepcopy(server.fixture)
    result = command(server, tmp_path, "42")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    receipt = json.loads(result.stdout)
    content = (tmp_path / "progress.html").read_bytes()
    payload = DownloadLink(content).payload
    assert receipt["sha256"] == hashlib.sha256(content).hexdigest()
    assert receipt["json_sha256"] == hashlib.sha256(payload).hexdigest()
    assert receipt["modules_returned"] == receipt["modules_included"] == 4
    assert [(row["path"], row["query"].get("page", ["1"])[0]) for row in server.requests] == [
        ("/api/v1/courses/42/modules", "1"), ("/api/v1/courses/42/modules", "2"),
        ("/api/v1/courses/42/modules/7/items", "1"), ("/api/v1/courses/42/modules/7/items", "2"),
    ]
    old = command(server, tmp_path, "42", command_name="module-progress")
    assert old.returncode == 0, old.stderr
    assert json.loads(payload) == json.loads(old.stdout)
    assert all(row["method"] == "GET" for row in server.requests)
    assert server.fixture == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["progress.html"]


def test_actual_cli_selection_and_unicode_filename_on_ascii_console(server, tmp_path):
    output = tmp_path / "Café-雪.html"
    result = command(server, tmp_path, "42", "--module-id", "009", out=output,
                     extra_env={"PYTHONIOENCODING": "ascii"})
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert result.stdout.isascii() and receipt["output"] == str(output)
    report = json.loads(DownloadLink(output.read_bytes()).payload)
    assert report["module_id"] == "9" and report["modules_omitted_by_selection"] == 3
    assert report["modules"][0]["state"] == "locked"
    assert report["modules"][0]["prerequisite_module_ids"] == [7]


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling"])
def test_existing_output_entries_are_refused_before_any_canvas_read(server, tmp_path, kind):
    output = tmp_path / "progress.html"
    target = tmp_path / "protected"
    if kind == "file":
        output.write_bytes(b"kept original")
    elif kind == "directory":
        output.mkdir()
    else:
        if kind == "symlink":
            target.write_bytes(b"kept linked original")
        output.symlink_to(target)
    original_stat = output.lstat()
    original_names = sorted(path.name for path in tmp_path.iterdir())
    result = command(server, tmp_path, "42")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert server.requests == []
    assert output.lstat() == original_stat
    assert sorted(path.name for path in tmp_path.iterdir()) == original_names
    if kind == "file":
        assert output.read_bytes() == b"kept original"
    elif kind == "symlink":
        assert target.read_bytes() == b"kept linked original"
    elif kind == "dangling":
        assert not target.exists()


@pytest.mark.parametrize("path,status,error", [
    ("/api/v1/courses/42/modules", 403, "CanvasAuthError"),
    ("/api/v1/courses/42/modules/7/items", 503, "HTTPStatusError"),
])
def test_later_page_failure_never_publishes_partial_html(server, tmp_path, path, status, error):
    server.overrides[(path, "2")] = (status, {"error": "synthetic later-page refusal"}, {})
    result = command(server, tmp_path, "42")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == error
    assert list(tmp_path.iterdir()) == []
    assert all(row["method"] == "GET" for row in server.requests)


def test_selected_report_still_rejects_foreign_identity_elsewhere(server, tmp_path):
    server.fixture["routes"]["GET /api/v1/courses/42/modules"][2]["course_id"] = 99
    result = command(server, tmp_path, "42", "--module-id", "7")
    assert result.returncode == 1 and result.stdout == ""
    assert "different course" in json.loads(result.stderr)["message"]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("arguments", [
    ["0"], ["-1"], ["42", "--module-id", "0"], ["42", "--module-id", "../7"],
])
def test_invalid_cli_identity_stops_before_reads(server, tmp_path, arguments):
    result = command(server, tmp_path, *arguments)
    assert result.returncode == 2 and result.stdout == ""
    assert server.requests == [] and list(tmp_path.iterdir()) == []


def test_competing_creator_between_read_and_publish_is_preserved(server, tmp_path):
    output = tmp_path / "progress.html"
    original_response = server.response

    def race(path, query):
        if path.endswith("/7/items") and query.get("page") == ["2"]:
            output.write_bytes(b"another creator won")
        return original_response(path, query)

    server.response = race
    result = command(server, tmp_path, "42")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert output.read_bytes() == b"another creator won"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["progress.html"]


def test_missing_parent_is_reported_and_retry_to_new_path_succeeds(server, tmp_path):
    result = command(server, tmp_path, "42", out=tmp_path / "missing" / "progress.html")
    assert result.returncode == 1 and result.stdout == ""
    assert json.loads(result.stderr)["error"] == "FileNotFoundError"
    assert list(tmp_path.iterdir()) == []
    retry = command(server, tmp_path, "42")
    assert retry.returncode == 0, retry.stderr
    assert json.loads(retry.stdout)["ok"] is True
    assert sorted(path.name for path in tmp_path.iterdir()) == ["progress.html"]

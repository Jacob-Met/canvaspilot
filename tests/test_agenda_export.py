"""Native CLI and publication receiving; all provider records are authored."""

from __future__ import annotations

import base64
import hashlib
import importlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from contextlib import contextmanager
from copy import deepcopy
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

import canvaspilot

SOURCE = Path(canvaspilot.__file__).resolve().parents[2]
FIXTURE = Path(__file__).with_name("fixtures") / "agenda_view_calendar.json"


def calendars():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@contextmanager
def provider(records=None, assignment_status=200, during_assignment=None):
    records = calendars() if records is None else records
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            target = urlsplit(self.path)
            query = parse_qs(target.query)
            requests.append({"path": target.path, "query": query})
            kind = query.get("type", [""])[0]
            if target.path != "/api/v1/calendar_events" or kind not in records:
                self.send_response(404)
                self.end_headers()
                return
            if kind == "assignment" and during_assignment:
                during_assignment()
            status = assignment_status if kind == "assignment" else 200
            body = json.dumps(records[kind] if status == 200 else {"error": "authored refusal"}).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def cli(base, scratch, command="export-agenda", courses=("42", "77"),
        start="2026-10-08", end="2026-10-15", output=None):
    args = [sys.executable, "-B", "-m", "canvaspilot.cli", command, *courses,
            "--start", start, "--end", end, "--base-url", base,
            "--token", "authored-agenda-view-fixture", "--profile", str(scratch / "unused-profile")]
    if command == "export-agenda":
        args.extend(["--out", str(output or scratch / "agenda.html")])
    env = {key: value for key, value in os.environ.items() if not key.lower().endswith("_proxy")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(SOURCE / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(args, cwd=SOURCE, env=env, capture_output=True, timeout=25, check=False)


def native_report(records=None):
    with provider(records) as (base, requests), tempfile.TemporaryDirectory() as directory:
        result = cli(base, Path(directory), command="agenda")
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert len(requests) == 2
        return report


class View(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.native = None
        self.articles = []
        self.tags = []
        self.text = []
        self.feed(content.decode("utf-8"))

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        self.tags.append((tag, attrs))
        if tag == "a" and attrs.get("id") == "download-native":
            self.native = base64.b64decode(attrs["href"].split(",", 1)[1], validate=True)
            assert hashlib.sha256(self.native).hexdigest() == attrs["data-sha256"]
        if tag == "article":
            self.articles.append(attrs)

    def handle_data(self, data):
        self.text.append(data)


def exporter():
    return importlib.import_module("canvaspilot.agenda_export")


def test_original_native_agenda_control(tmp_path):
    with provider() as (base, requests):
        result = cli(base, tmp_path, command="agenda")
    assert result.returncode == 0, result.stderr
    assert result.stderr == b""
    report = json.loads(result.stdout)
    assert report["counts"] == {"total": 4, "timed": 2, "all_day": 1, "timing_unavailable": 1}
    assert [entry["record"]["id"] for entry in report["timed"]] == [901, "evt-07"]
    assert len(requests) == 2
    assert not (tmp_path / "unused-profile").exists()


def test_complete_cli_view_retains_exact_native_bytes_and_literal_source(tmp_path):
    with provider() as (base, requests):
        original = cli(base, tmp_path, command="agenda")
        requests.clear()
        result = cli(base, tmp_path)
    assert original.returncode == result.returncode == 0, result.stderr
    assert result.stderr == b""
    receipt = json.loads(result.stdout)
    content = (tmp_path / "agenda.html").read_bytes()
    view = View(content)
    assert view.native == original.stdout
    assert receipt["native_report_sha256"] == hashlib.sha256(original.stdout).hexdigest()
    assert receipt["html_sha256"] == hashlib.sha256(content).hexdigest()
    assert receipt["counts"] == json.loads(original.stdout)["counts"]
    assert [(entry["data-course"], entry["data-group"], entry["data-date"]) for entry in view.articles] == [
        ("77", "timed", "2026-10-08"), ("42", "timed", "2026-10-08"),
        ("77", "all_day", "2026-10-09"), ("42", "timing_unavailable", ""),
    ]
    text = "\n".join(view.text)
    assert "Studio critique — bring <poster> & notes" in text
    assert "15:00:00.0000000002+00:00" in text
    assert "Discuss the draft & its sources." in text
    assert '</script><img src=x onerror=alert(1)> remains supplied source' in text
    assert not any(tag in {"img", "iframe", "object", "link"} for tag, _ in view.tags)
    assert sum(tag == "script" for tag, _ in view.tags) == 1
    assert all("src" not in attrs for _, attrs in view.tags)
    assert [request["query"]["type"] for request in requests] == [["event"], ["assignment"]]
    assert all(request["query"]["context_codes[]"] == ["course_42", "course_77"] for request in requests)
    assert not (tmp_path / "unused-profile").exists()
    assert list(tmp_path.glob(".*.tmp")) == []


def test_empty_native_result_is_a_complete_readable_view(tmp_path):
    with provider({"event": [], "assignment": []}) as (base, requests):
        result = cli(base, tmp_path)
    assert result.returncode == 0, result.stderr
    view = View((tmp_path / "agenda.html").read_bytes())
    assert view.articles == []
    assert json.loads(view.native)["counts"]["total"] == 0
    assert "Showing 0 of 0 saved entries" in "".join(view.text)
    assert sum("data-empty" in attrs and "hidden" not in attrs for _, attrs in view.tags) == 3
    assert len(requests) == 2


@pytest.mark.parametrize("courses,start,end", [
    (("42", "042"), "2026-10-08", "2026-10-15"),
    (("42",), "2026-02-30", "2026-10-15"),
    (("42",), "2026-10-15", "2026-10-08"),
])
def test_invalid_selection_refuses_before_http(tmp_path, courses, start, end):
    with provider() as (base, requests):
        result = cli(base, tmp_path, courses=courses, start=start, end=end)
    assert result.returncode == 1
    assert result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert requests == [] and not (tmp_path / "agenda.html").exists()


def test_late_provider_refusal_does_not_publish_partial_calendar(tmp_path):
    with provider(assignment_status=403) as (base, requests):
        result = cli(base, tmp_path)
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["ok"] is False
    assert len(requests) == 2
    assert not (tmp_path / "agenda.html").exists()


def test_late_foreign_course_record_refuses_whole_view(tmp_path):
    records = calendars()
    records["assignment"][0]["effective_context_code"] = "course_999"
    with provider(records) as (base, requests):
        result = cli(base, tmp_path)
    assert result.returncode == 1 and result.stdout == b""
    assert "outside the selected courses" in json.loads(result.stderr)["message"]
    assert len(requests) == 2 and not (tmp_path / "agenda.html").exists()


def test_all_existing_destination_entries_are_preserved_before_http(tmp_path):
    original = tmp_path / "original"
    original.write_bytes(b"keep original source\x00\xff")
    regular, symlink, dangling, hardlink, directory = [tmp_path / name for name in (
        "regular.html", "symlink.html", "dangling.html", "hardlink.html", "directory.html",
    )]
    regular.write_bytes(b"keep existing view")
    symlink.symlink_to(original)
    dangling.symlink_to(tmp_path / "absent")
    os.link(original, hardlink)
    directory.mkdir()
    for output in (regular, symlink, dangling, hardlink, directory):
        before = output.lstat()
        with provider() as (base, requests):
            result = cli(base, tmp_path, output=output)
        assert result.returncode == 1 and result.stdout == b""
        assert json.loads(result.stderr)["error"] == "FileExistsError"
        assert output.lstat().st_ino == before.st_ino and requests == []
    assert original.read_bytes() == b"keep original source\x00\xff"
    assert hardlink.read_bytes() == original.read_bytes()
    assert regular.read_bytes() == b"keep existing view"
    assert symlink.is_symlink() and dangling.is_symlink()


def test_destination_created_during_native_reads_is_not_overwritten(tmp_path):
    target = tmp_path / "agenda.html"
    with provider(during_assignment=lambda: target.write_bytes(b"another writer")) as (base, requests):
        result = cli(base, tmp_path)
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["error"] == "FileExistsError"
    assert target.read_bytes() == b"another writer" and len(requests) == 2
    assert list(tmp_path.glob(".*.tmp")) == []


def test_absent_output_parent_is_an_unsuccessful_complete_read(tmp_path):
    output = tmp_path / "absent" / "agenda.html"
    with provider() as (base, requests):
        result = cli(base, tmp_path, output=output)
    assert result.returncode == 1 and result.stdout == b""
    assert json.loads(result.stderr)["error"] == "FileNotFoundError"
    assert len(requests) == 2 and not output.exists()
    assert not output.parent.exists()


@pytest.mark.parametrize("operation", ["fsync", "link"])
def test_controlled_publication_failure_removes_only_own_temporary(tmp_path, monkeypatch, operation):
    module = exporter()
    original = tmp_path / "original.html"
    original.write_bytes(b"neighbor")

    def refused(*_args, **_kwargs):
        raise OSError("authored publication failure")

    monkeypatch.setattr(module.os, operation, refused)
    with pytest.raises(OSError, match="authored publication failure"):
        module.write_agenda_html(tmp_path / "agenda.html", b"complete prepared HTML")
    assert original.read_bytes() == b"neighbor"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["original.html"]


def test_native_record_limit_is_inclusive_and_refuses_whole_oversize_view():
    module = exporter()
    rows = [{"id": i, "context_code": "course_42", "all_day": True,
             "all_day_date": "2026-10-09"} for i in range(2001)]
    accepted = native_report({"event": rows[:2000], "assignment": []})
    assert len(View(module.render_agenda_html(accepted)).articles) == 2000
    refused = native_report({"event": rows, "assignment": []})
    before = deepcopy(refused)
    with pytest.raises(ValueError, match="2000-record"):
        module.render_agenda_html(refused)
    assert refused == before


def test_native_json_byte_limit_is_inclusive_and_input_is_immutable():
    module = exporter()
    report = native_report()
    report["retained_extra"] = ""
    overhead = len((json.dumps(report, indent=2) + "\n").encode())
    report["retained_extra"] = "a" * (module.MAX_NATIVE_BYTES - overhead)
    exact = (json.dumps(report, indent=2) + "\n").encode()
    assert len(exact) == 4 * 1024 * 1024
    view = View(module.render_agenda_html(report))
    assert view.native == exact
    assert (json.dumps(report, indent=2) + "\n").encode() == exact
    report["retained_extra"] += "b"
    with pytest.raises(ValueError, match="4 MiB"):
        module.render_agenda_html(report)


def test_corrupted_counts_sources_and_group_order_are_refused():
    module = exporter()
    native = native_report()
    corrupted = []
    bad_count = deepcopy(native)
    bad_count["counts"]["total"] = 3
    corrupted.append(bad_count)
    bad_source = deepcopy(native)
    bad_source["timed"][1]["source"]["index"] = 99
    corrupted.append(bad_source)
    wrong_order = deepcopy(native)
    wrong_order["timed"].reverse()
    corrupted.append(wrong_order)
    wrong_group = deepcopy(native)
    wrong_group["timed"][0]["record"]["all_day"] = True
    corrupted.append(wrong_group)
    for report in corrupted:
        with pytest.raises((ValueError, TypeError)):
            module.render_agenda_html(report)
    assert native == native_report()

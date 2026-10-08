"""Deadline export through the existing API and actual CLI, without a Canvas account."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.calendar_export import build_assignment_calendar, write_calendar
from canvaspilot.offline_demo import OfflineOnlyClient

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def assignment(identity=1, due="2026-11-01T01:45:00-07:00", **kwargs):
    return {"id": identity, "name": f"Assignment {identity}", "due_at": due, **kwargs}


class CalendarFixture(OfflineOnlyClient):
    def __init__(self, courses, *, base="https://canvas.fixture.invalid"):
        super().__init__()
        self.base_url = base
        self.fixture = {"routes": {
            f"GET /api/v1/courses/{course}/assignments": copy.deepcopy(rows)
            for course, rows in courses.items()
        }}
        self.calls = []

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, copy.deepcopy(kwargs)))
        return super().request(method, path, **kwargs)


def render(courses, *, base="https://canvas.fixture.invalid", bucket="upcoming", selected=None):
    client = CalendarFixture(courses, base=base)
    before = copy.deepcopy(client.fixture)
    with CanvasAPI(client) as api:
        content, report = build_assignment_calendar(
            api, list(courses) if selected is None else selected, bucket=bucket, generated_at=NOW,
        )
    assert client.fixture == before
    return content, report, client.calls


def unfolded(content):
    return content.decode().replace("\r\n ", "").split("\r\n")


def property_values(content, name):
    return [line[len(name) + 1:] for line in unfolded(content) if line.startswith(name + ":")]


def test_two_courses_offsets_order_stable_identity_and_explicit_omission():
    courses = {
        42: [assignment(1), assignment(2, "2026-11-01T01:15:00-08:00"), assignment(3, None)],
        77: [assignment(1, "2026-11-01T08:30:00Z")],
    }
    content, report, calls = render(courses, selected=["042", 42, 77])
    assert property_values(content, "DTSTART") == ["20261101T083000Z", "20261101T084500Z", "20261101T091500Z"]
    assert len(set(property_values(content, "UID"))) == 3
    assert property_values(content, "DTSTAMP") == ["20261008T120000Z"] * 3
    assert "DTEND" not in content.decode() and "DURATION" not in content.decode()
    assert property_values(content, "TRANSP") == ["TRANSPARENT"] * 3
    assert report["events_exported"] == 3
    assert report["assignments_omitted"] == [{"course_id": "42", "assignment_id": "3", "reason": "no_due_date"}]
    assert report["course_ids"] == ["42", "77"]
    assert report["sha256"] == hashlib.sha256(content).hexdigest()
    assert len(calls) == 2
    assert all(method == "GET" and dict(options["params"])["bucket"] == "upcoming"
               for method, _, options in calls)


def test_uid_survives_name_due_and_equivalent_origin_changes_but_separates_schools():
    old, _, _ = render({42: [assignment()]}, base="https://CANVAS.fixture.invalid:443/")
    new, _, _ = render({42: [assignment(due="2026-12-04T13:00:00Z", name="Revised title")]})
    other, _, _ = render({42: [assignment()]}, base="https://other.fixture.invalid")
    assert property_values(old, "UID") == property_values(new, "UID")
    assert property_values(old, "UID") != property_values(other, "UID")
    assert property_values(old, "DTSTART") != property_values(new, "DTSTART")


def test_crlf_utf8_folding_text_escaping_and_url_punctuation():
    name = "雪😀" * 40 + ", semi; back\\slash\r\nsecond\rthird\nfourth"
    url = "https://canvas.fixture.invalid/courses/42/assignments/1?a=1,2;b=3"
    content, _, _ = render({42: [assignment(name=name, html_url=url)]})
    physical = content.split(b"\r\n")
    assert all(len(line) <= 75 for line in physical)
    assert all(line.decode("utf-8") is not None for line in physical)
    assert b"\n" not in content.replace(b"\r\n", b"")
    title = property_values(content, "SUMMARY")[0]
    assert "\\," in title and "\\;" in title and "back\\\\slash" in title
    assert "\\nsecond\\nthird\\nfourth" in title
    assert property_values(content, "URL") == [url]
    assert content.startswith(b"BEGIN:VCALENDAR\r\n") and content.endswith(b"END:VCALENDAR\r\n")


@pytest.mark.parametrize("due", [
    "", "not-a-date", "2026-11-01", "2026-11-01T12:00:00", "2026-11-01T12:00:00.1Z",
    "2026-11-01T12:00:00.0000001Z", "0001-01-01T00:00:00+14:00",
    "9999-12-31T23:59:59-12:00", "2026-11-01T01:10:00+00:60",
    "2026-11-01T01:10:00-00:60", "2026-11-01T01:10:00+12:99",
    "2026-11-01T01:10:00+24:00", 0, {}, False,
])
def test_invalid_or_unrepresentable_deadline_refuses_export(due):
    with pytest.raises(ValueError, match="timestamp"):
        render({42: [assignment(), assignment(2, due)]})


def test_valid_extreme_offset_preserves_its_exact_instant():
    content, _, _ = render({42: [assignment(due="2026-11-01T00:00:00+23:59")]})
    assert property_values(content, "DTSTART") == ["20261031T000100Z"]


def test_zero_fraction_is_exact_and_early_year_keeps_four_digits():
    content, _, _ = render({42: [assignment(due="0001-01-01T00:00:00.000Z")]})
    assert property_values(content, "DTSTART") == ["00010101T000000Z"]


@pytest.mark.parametrize("rows", [[], [assignment(due=None)]])
def test_no_dated_assignments_does_not_generate_invalid_empty_calendar(rows):
    with pytest.raises(ValueError, match="No dated assignments"):
        render({42: rows})


@pytest.mark.parametrize("identity", [None, True, 0, "-1", "../2", "1/2", 1.5])
def test_invalid_identity_refuses_ambiguous_event(identity):
    with pytest.raises((ValueError, TypeError), match="Canvas ID"):
        render({42: [assignment(identity)]})


def test_duplicate_assignment_identity_refuses_and_all_bucket_uses_existing_reader():
    with pytest.raises(ValueError, match="duplicate assignment"):
        render({42: [assignment(), assignment()]})
    _, _, calls = render({42: [assignment()]}, bucket="all")
    assert "bucket" not in dict(calls[0][2]["params"])


@pytest.mark.parametrize("value", ["bad\x00text", "bad\x7ftext", "bad\ud800text", 23])
def test_invalid_title_refuses_calendar(value):
    with pytest.raises((ValueError, TypeError)):
        render({42: [assignment(name=value)]})


@pytest.mark.parametrize("value", ["https://host/x\r\nSUMMARY:wrong", "javascript:bad", "https://u:p@host/x"])
def test_invalid_url_refuses_calendar(value):
    with pytest.raises(ValueError):
        render({42: [assignment(html_url=value)]})


def test_new_file_publication_preserves_existing_file_and_dangling_symlink(tmp_path):
    content, _, _ = render({42: [assignment()]})
    path = tmp_path / "deadlines.ics"
    write_calendar(path, content)
    with pytest.raises(FileExistsError):
        write_calendar(path, b"changed")
    assert path.read_bytes() == content
    dangling = tmp_path / "dangling.ics"
    dangling.symlink_to(tmp_path / "missing")
    with pytest.raises(FileExistsError):
        write_calendar(dangling, content)
    assert dangling.is_symlink() and not (tmp_path / "missing").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["dangling.ics", "deadlines.ics"]


class DeadlineServer:
    def __init__(self):
        self.requests = []
        self.rows = {
            "42": [assignment(1), assignment(2, None)],
            "77": [assignment(3, "2026-11-01T01:15:00-08:00")],
        }
        self.fail_course = None
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                parsed = urlsplit(self.path)
                owner.requests.append({"method": "GET", "path": parsed.path, "query": parse_qs(parsed.query)})
                course = parsed.path.split("/")[4]
                status = 503 if course == owner.fail_course else 200
                body = owner.rows.get(course, [])
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):
                owner.requests.append({"method": "POST", "path": self.path})
                self.send_error(405)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


def run_cli(server, tmp_path, *extra):
    env = {k: v for k, v in os.environ.items()
           if not k.upper().endswith("_PROXY") and not k.startswith("CANVAS")}
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    return subprocess.run([
        sys.executable, "-m", "canvaspilot.cli", "export-calendar", "42", "77",
        "--base-url", server.url, "--token", "synthetic-receiving-only",
        "--profile", str(tmp_path / "unused-profile"),
        "--out", str(tmp_path / "deadlines.ics"), *extra,
    ], env=env, capture_output=True, text=True, timeout=15, check=False)


def test_actual_cli_reads_selected_courses_publishes_and_preserves_existing_path(tmp_path):
    server = DeadlineServer()
    try:
        result = run_cli(server, tmp_path)
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout)
        content = (tmp_path / "deadlines.ics").read_bytes()
        assert receipt["ok"] is True and receipt["events_exported"] == 2
        assert receipt["sha256"] == hashlib.sha256(content).hexdigest()
        assert property_values(content, "DTSTART") == ["20261101T084500Z", "20261101T091500Z"]
        assert [r["path"] for r in server.requests] == [
            "/api/v1/courses/42/assignments", "/api/v1/courses/77/assignments",
        ]
        assert all(r["query"]["bucket"] == ["upcoming"] for r in server.requests)
        count = len(server.requests)
        repeated = run_cli(server, tmp_path)
        assert repeated.returncode == 1
        assert json.loads(repeated.stderr)["error"] == "FileExistsError"
        assert len(server.requests) == count
        assert (tmp_path / "deadlines.ics").read_bytes() == content
        assert not (tmp_path / "unused-profile").exists()
    finally:
        server.close()


def test_actual_cli_later_course_failure_never_publishes_partial_calendar(tmp_path):
    server = DeadlineServer()
    server.fail_course = "77"
    try:
        result = run_cli(server, tmp_path)
        assert result.returncode == 1 and not result.stdout
        assert json.loads(result.stderr.splitlines()[-1])["error"] == "HTTPStatusError"
        assert not (tmp_path / "deadlines.ics").exists()
        assert [r["path"] for r in server.requests] == [
            "/api/v1/courses/42/assignments", "/api/v1/courses/77/assignments",
        ]
        assert all(r["method"] == "GET" for r in server.requests)
    finally:
        server.close()

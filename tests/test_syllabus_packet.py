"""Source and publication controls for the native syllabus packet."""

from __future__ import annotations

import base64
import errno
import hashlib
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest

from canvaspilot.syllabus_packet import (
    MAX_BODY_BYTES,
    MAX_TOTAL_BODY_BYTES,
    build_syllabus_packet,
    write_syllabus_packet,
)

STAMP = datetime(2026, 10, 8, 12, 30, tzinfo=UTC)


class API:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.client = SimpleNamespace(base_url="https://canvas.example.test")

    def get_course(self, course_id):
        self.calls.append(course_id)
        row = self.rows[course_id]
        if isinstance(row, Exception):
            raise row
        return row


def course(course_id=42, **extra):
    return {"id": course_id, "name": "Field methods", "course_code": "FIELD-42", **extra}


def build(rows, ids=(42,)):
    return build_syllabus_packet(API(rows), ids, captured_at=STAMP)


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.attrs = []
        self.downloads = {}
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        attrs = dict(attrs)
        self.attrs.append((tag, attrs))
        if tag == "a" and attrs.get("download"):
            prefix, encoded = attrs["href"].split(",", 1)
            assert prefix == "data:text/plain;base64"
            self.downloads[attrs["download"]] = base64.b64decode(encoded, validate=True)


def test_course_order_semantic_reading_and_exact_source_download():
    html = (
        "<h2>Week one</h2><p>Read A &amp; B — café.</p>\r\n"
        '<ol start="3" reversed type="A"><li value="7">Bring a notebook.</li></ol>'
        '<table><caption>Sessions</caption><thead><tr><th id="day" scope="col">Day</th>'
        '<th scope="col">Room</th></tr></thead><tbody><tr><td headers="day" rowspan="2">'
        'Friday</td><td>Studio 2</td></tr><tr><td>Lab 3</td></tr></tbody></table>'
        '<pre><code>x &lt; 4\rline 2</code></pre>'
    )
    data, report = build({42: course(syllabus_body=html), 7: course(7, syllabus_body="")}, (7, 42))
    text = data.decode()
    view = Elements(text)
    assert report["course_ids"] == [7, 42]
    assert text.index('id="course-7"') < text.index('id="course-42"')
    assert "<h2>Week one</h2>" in text and "Read A &amp; B — café." in text
    assert ("ol", {"start": "3", "reversed": None, "type": "A"}) in view.attrs
    assert ("li", {"value": "7"}) in view.attrs
    assert ("th", {"id": "source-42-day", "scope": "col"}) in view.attrs
    assert ("td", {"rowspan": "2", "headers": "source-42-day"}) in view.attrs
    assert view.downloads["course-42-syllabus-source.txt"] == html.encode()
    assert view.downloads["course-7-syllabus-source.txt"] == b""
    assert hashlib.sha256(html.encode()).hexdigest() in text
    assert report["captured_at"] == "2026-10-08T12:30:00+00:00"
    assert report["output_bytes"] == len(data)


@pytest.mark.parametrize("extra,status,marker,download", [
    ({}, "not_supplied", "not supplied by Canvas", False),
    ({"syllabus_body": None}, "unavailable", "unavailable (null)", False),
    ({"syllabus_body": ""}, "empty", "explicitly empty", True),
    ({"syllabus_body": "<p></p>"}, "supplied", "Syllabus HTML supplied", True),
])
def test_distinct_source_states(extra, status, marker, download):
    data, report = build({42: course(**extra)})
    text = data.decode()
    assert report["syllabus_statuses"] == [{"course_id": 42, "status": status}]
    assert marker in text
    assert bool(Elements(text).downloads) is download


@pytest.mark.parametrize("ids", [
    (), tuple(range(1, 12)), (42, 42), (42, "042"), (True,), (0,), (-1,),
    (1.0,), ("1/assignments",), ("-3",), ("",), "42",
])
def test_entire_selection_is_validated_before_a_read(ids):
    api = API({})
    with pytest.raises((ValueError, TypeError)):
        build_syllabus_packet(api, ids, captured_at=STAMP)
    assert api.calls == []


@pytest.mark.parametrize("row", [
    None, [], "not JSON", {}, {"id": True}, {"id": 43}, {"id": 42.0},
    course(syllabus_body=7), course(syllabus_body=False),
    course(syllabus_body=[]), course(syllabus_body={}),
    course(name=17), course(course_code=[]), course(name="x" * 4097),
])
def test_unavailable_or_mismatched_course_objects_are_not_empty_syllabi(row):
    with pytest.raises((ValueError, TypeError)):
        build({42: row})


def test_source_id_decimal_text_can_match_without_changing_selection_identity():
    _, report = build({42: course("042", syllabus_body="Text")})
    assert report["course_ids"] == [42]


def test_whole_number_limits_include_the_boundary_and_never_truncate():
    body = "é" * (MAX_BODY_BYTES // 2)
    data, report = build({42: course(syllabus_body=body)})
    assert report["source_body_bytes"] == MAX_BODY_BYTES
    assert Elements(data.decode()).downloads["course-42-syllabus-source.txt"] == body.encode()
    with pytest.raises(ValueError, match="512 KiB"):
        build({42: course(syllabus_body=body + "x")})
    rows = {i: course(i, syllabus_body="x" * MAX_BODY_BYTES) for i in range(1, 6)}
    _, report = build(rows, (1, 2, 3, 4))
    assert report["source_body_bytes"] == MAX_TOTAL_BODY_BYTES
    with pytest.raises(ValueError, match="2 MiB"):
        build(rows, (1, 2, 3, 4, 5))


@pytest.mark.parametrize("body,match", [
    ("<div>" * 257, "nesting"),
    ("<br>" * 20_001, "20,000"),
    ('<table><tr><td colspan="1001">x</td></tr></table>', "colspan"),
    ('<table><tr><td rowspan="-1">x</td></tr></table>', "rowspan"),
    ("\ud800", "surrogates"),
])
def test_bounded_or_unencodable_reading_refuses_instead_of_silently_dropping(body, match):
    with pytest.raises(ValueError, match=match):
        build({42: course(syllabus_body=body)})


def test_active_source_cannot_become_executable_or_auto_loading_markup():
    html = (
        '<h2 onclick="window.BAD=1">Lab</h2>'
        '<script src="https://outside.example/bad.js">window.BAD=2</script>'
        '<style>@import "https://outside.example/bad.css";</style>'
        '<p style="background:url(https://outside.example/pixel)">Visible text.</p>'
        '<img src="/files/9/preview" alt="Bring protective eyewear.">'
        '<iframe src="https://outside.example/lesson" title="Required orientation"></iframe>'
        '<form action="https://outside.example/send"><input value="secret"><button>Send</button></form>'
        '<svg onload="window.BAD=3"><text>Diagram</text></svg>'
        '<math><mi>x</mi></math>'
        '<a href="javascript:window.BAD=4">Bad target</a>'
        '<a href="data:text/html,&lt;script&gt;bad()&lt;/script&gt;">Data target</a>'
        '<a href="/courses/42/files/9/download">Instructions PDF</a>'
        '<a href="mailto:teacher@example.test">Email teacher</a>'
    )
    data, _ = build({42: course(syllabus_body=html)})
    text = data.decode()
    view = Elements(text)
    assert not set(view.tags) & {"script", "iframe", "img", "svg", "math", "form", "input", "button"}
    assert view.tags.count("style") == 1  # Only the packet's fixed local stylesheet.
    for tag, attrs in view.attrs:
        assert not any(key.startswith("on") for key in attrs)
        assert "src" not in attrs and "style" not in attrs
        if tag == "a" and not attrs.get("download"):
            assert not attrs.get("href", "").startswith(("javascript:", "data:", "mailto:"))
    assert "Bring protective eyewear." in text and "Required orientation" in text
    assert "Instructions PDF" in text and "linked content is not included" in text
    assert any(attrs.get("href") == "https://canvas.example.test/courses/42/files/9/download"
               for tag, attrs in view.attrs if tag == "a")
    assert view.downloads["course-42-syllabus-source.txt"] == html.encode()
    assert "not a verified response origin" in text
    assert "separately generated course-summary" in text


def test_nul_cr_and_unicode_remain_exact_in_inert_text_download():
    body = "<p>A\r\nB\rC\x00Ω &amp; &lt;script&gt;</p>"
    data, _ = build({42: course(syllabus_body=body)})
    assert Elements(data.decode()).downloads["course-42-syllabus-source.txt"] == body.encode()
    assert "\x00" not in data.decode()


def test_late_fetch_failure_propagates_without_returning_a_partial_packet():
    api = API({42: course(syllabus_body="First"), 43: RuntimeError("synthetic later failure")})
    with pytest.raises(RuntimeError, match="synthetic later failure"):
        build_syllabus_packet(api, [42, 43], captured_at=STAMP)
    assert api.calls == [42, 43]


def test_naive_capture_time_is_refused_before_reads():
    api = API({})
    with pytest.raises(ValueError, match="timezone"):
        build_syllabus_packet(api, [42], captured_at=STAMP.replace(tzinfo=None))
    assert api.calls == []


def test_successful_new_file_has_complete_bytes_and_no_staging_file(tmp_path):
    path = tmp_path / "packet.html"
    content = b"complete \xce\xa9 packet\n"
    write_syllabus_packet(path, content)
    assert path.read_bytes() == content
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("kind", ["file", "directory", "symlink", "dangling", "hardlink"])
def test_every_existing_destination_survives(tmp_path, kind):
    path = tmp_path / "packet.html"
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"original destination")
    if kind == "file":
        path.write_bytes(b"original destination")
    elif kind == "directory":
        path.mkdir()
    elif kind == "symlink":
        path.symlink_to(sentinel)
    elif kind == "dangling":
        path.symlink_to(tmp_path / "missing")
    else:
        path.hardlink_to(sentinel)
    before = set(tmp_path.iterdir())
    with pytest.raises(FileExistsError):
        write_syllabus_packet(path, b"new content")
    assert sentinel.read_bytes() == b"original destination"
    assert set(tmp_path.iterdir()) == before
    if kind in {"file", "symlink", "hardlink"}:
        assert path.read_bytes() == b"original destination"
    if kind in {"symlink", "dangling"}:
        assert path.is_symlink()


def test_destination_appearing_at_publication_is_preserved(tmp_path, monkeypatch):
    import canvaspilot.syllabus_packet as packet
    actual_link = packet.os.link
    path = tmp_path / "packet.html"

    def raced(source, destination):
        Path(destination).write_bytes(b"concurrent writer")
        actual_link(source, destination)

    monkeypatch.setattr(packet.os, "link", raced)
    with pytest.raises(FileExistsError):
        write_syllabus_packet(path, b"our complete packet")
    assert path.read_bytes() == b"concurrent writer"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("stage", ["fsync", "link"])
def test_staging_or_unsupported_publication_error_cleans_only_own_temp(tmp_path, monkeypatch, stage):
    import canvaspilot.syllabus_packet as packet
    path = tmp_path / "packet.html"

    def fail(*args):
        raise OSError(errno.ENOSPC if stage == "fsync" else errno.EOPNOTSUPP, "synthetic I/O refusal")

    monkeypatch.setattr(packet.os, stage, fail)
    with pytest.raises(OSError, match="synthetic I/O refusal"):
        write_syllabus_packet(path, b"complete packet")
    assert list(tmp_path.iterdir()) == []


def test_malformed_marked_declaration_has_a_handled_whole_packet_refusal():
    with pytest.raises(ValueError, match="unsupported HTML markup"):
        build({42: course(syllabus_body="<![unrecognized]>Visible course text")})


def test_malformed_link_stays_readable_inert_source_evidence():
    body = '<p>Read <a href="http://[broken">the handout</a>.</p>'
    data, _ = build({42: course(syllabus_body=body)})
    text = data.decode()
    assert "the handout" in text and "http://[broken" in text
    assert "destination kept as text only" in text
    assert not any(attrs.get("href") == "http://[broken" for _, attrs in Elements(text).attrs)
    assert Elements(text).downloads["course-42-syllabus-source.txt"] == body.encode()


def test_duplicate_link_attributes_keep_the_first_destination_like_html():
    body = '<a href="https://first.example/handout" href="https://later.example/other">Handout</a>'
    data, _ = build({42: course(syllabus_body=body)})
    attrs = Elements(data.decode()).attrs
    assert any(a.get("href") == "https://first.example/handout" for tag, a in attrs if tag == "a")
    assert not any(a.get("href") == "https://later.example/other" for tag, a in attrs if tag == "a")
    assert Elements(data.decode()).downloads["course-42-syllabus-source.txt"] == body.encode()


@pytest.mark.parametrize("value", [" 3 ", "1000000000", "-2"])
def test_list_numbering_values_reach_the_browser_unchanged(value):
    body = f'<ol start="{value}"><li value="{value}">Numbered instruction</li></ol>'
    data, _ = build({42: course(syllabus_body=body)})
    attrs = Elements(data.decode()).attrs
    assert ("ol", {"start": value}) in attrs
    assert ("li", {"value": value}) in attrs

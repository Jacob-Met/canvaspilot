"""Focused synthetic contracts for explicit, passive page-revision comparison."""

import base64
import json
from copy import deepcopy
from html.parser import HTMLParser

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.page_revision_comparison import (
    build_page_revision_comparison,
    validate_revision_comparison,
)


class API:
    def __init__(self, before, after):
        self.values = [before, after]
        self.calls = []

    def get_page_revision(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.values[len(self.calls) - 1]


class Download(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.attrs = None
        self.tags = []
        self.feed(content.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        values = dict(attrs)
        if values.get("id") == "download-json":
            self.attrs = values

    def payload(self):
        return base64.b64decode(self.attrs["href"].split(",", 1)[1], validate=True)


def envelope(revision_id, body=""):
    return {"revision": {"revision_id": revision_id, "body": body}, "body_text": body}


def build(before, after):
    return build_page_revision_comparison(API(before, after), 42, "p", 7, 9)


def test_complete_original_reader_envelopes_and_literal_document():
    before = {
        "revision_id": "0007", "title": "Brief <old> & Ω", "url": "older-name",
        "updated_at": "2099-not-a-chronology-oracle", "body": "Start\r\nKeep\nGone",
        "body_text": {"server_field": "retained"},
        "unknown": {"values": [1, 1.0, True, None], "literal": "<script>do not execute</script>"},
    }
    after = {
        "revision_id": 9, "title": "", "url": "renamed", "updated_at": None,
        "body": "Start\r\nKeep\nAdded\n", "unknown": {"empty": "", "nullable": None},
    }

    class Reader:
        def __init__(self):
            self.calls = []

        def request(self, method, path, **kwargs):
            self.calls.append((method, path, kwargs))
            return before if path.endswith("/7") else after

    reader = Reader()
    content, report = build_page_revision_comparison(
        CanvasAPI(reader), "0042", "Week / Ω?%#", "0007", 9,
    )
    expected = {
        "schema": "canvaspilot.page-revision-comparison.v1",
        "selection": {
            "course_id": "42", "page_url": "Week / Ω?%#",
            "before_revision": "7", "after_revision": "9",
        },
        "before": {"revision": before, "body_text": "Start Keep Gone"},
        "after": {"revision": after, "body_text": "Start Keep Added"},
        "comparison": {
            "before_body_state": "text", "after_body_state": "text",
            "raw_equal": False, "text_equal": False,
            "line_diff": {
                "status": "computed", "reason": None, "before_lines": 3, "after_lines": 3,
                "rows": [
                    {"kind": "equal", "before_line": 1, "after_line": 1, "text": "Start\r\n"},
                    {"kind": "equal", "before_line": 2, "after_line": 2, "text": "Keep\n"},
                    {"kind": "delete", "before_line": 3, "after_line": None, "text": "Gone"},
                    {"kind": "insert", "before_line": None, "after_line": 3, "text": "Added\n"},
                ],
            },
        },
    }
    assert report == expected
    root = "/api/v1/courses/42/pages/Week%20%2F%20%CE%A9%3F%25%23/revisions/"
    assert reader.calls == [("GET", root + n, {"params": {"summary": False}}) for n in ("7", "9")]
    parsed = Download(content)
    assert parsed.payload() == (json.dumps(
        expected, ensure_ascii=False, indent=2, allow_nan=False,
    ) + "\n").encode()
    assert parsed.attrs["download"] == "canvas-page-revisions-42-7-vs-9.json"
    assert not {"script", "iframe", "img", "form", "link"} & set(parsed.tags)
    assert b"<script>do not execute</script>" not in content
    assert b"default-src 'none'" in content


@pytest.mark.parametrize("left,right", [
    ("a\r\nb\rc\nlast", "a\r\nb\nc\nlast\n"),
    ("same\u2028line\n", "same\u2028line\r\n"),
    ("", "a\x00b\n"), ("a\n", ""), ("\r\n", "\n"),
])
def test_line_rows_reconstruct_both_complete_raw_bodies(left, right):
    _, report = build(envelope(7, left), envelope(9, right))
    rows = report["comparison"]["line_diff"]["rows"]
    assert "".join(r["text"] for r in rows if r["kind"] != "insert") == left
    assert "".join(r["text"] for r in rows if r["kind"] != "delete") == right
    _, reversed_report = build_page_revision_comparison(
        API(envelope(9, right), envelope(7, left)), 42, "p", 9, 7,
    )
    assert reversed_report["before"] == report["after"]
    assert reversed_report["after"] == report["before"]


@pytest.mark.parametrize("left,left_state,right,right_state", [
    ({}, "absent", {"body": None}, "null"),
    ({"body": None}, "null", {"body": ""}, "empty"),
    ({"body": ""}, "empty", {"body": ""}, "empty"),
    ({"body": ""}, "empty", {"body": "x"}, "text"),
])
def test_absent_null_and_empty_are_distinct(left, left_state, right, right_state):
    def raw(identity, fields):
        result = {"revision": {"revision_id": identity, **fields}}
        if "body" in fields:
            result["body_text"] = fields["body"]
        return result
    _, report = build(raw(7, left), raw(9, right))
    c = report["comparison"]
    assert (c["before_body_state"], c["after_body_state"]) == (left_state, right_state)
    comparable = left_state in {"empty", "text"} and right_state in {"empty", "text"}
    assert c["line_diff"]["status"] == ("computed" if comparable else "not-comparable")
    if not comparable:
        assert c["raw_equal"] is c["text_equal"] is None
        assert c["line_diff"]["rows"] == []
    if left_state == right_state == "empty":
        assert c["raw_equal"] is c["text_equal"] is True
        assert c["line_diff"]["before_lines"] == c["line_diff"]["after_lines"] == 0


def test_raw_and_cleaned_equality_are_separate():
    left = envelope(7, "<b>same</b>")
    right = envelope(9, "<i>same</i>")
    left["body_text"] = right["body_text"] = "same"
    _, report = build(left, right)
    assert report["comparison"]["raw_equal"] is False
    assert report["comparison"]["text_equal"] is True


@pytest.mark.parametrize("args", [
    (True, "p", 7, 9), (0, "p", 7, 9), ("１", "p", 7, 9),
    (42, "p", "latest", 9), (42, "p", 7, "latest"), (42, "p", "0007", 7),
    (42, "p", 7, False), (42, "p", 7, 9223372036854775808),
    (42, "", 7, 9), (42, "..", 7, 9), (42, "p\x7f", 7, 9),
    (42, "p\ud800", 7, 9), (42, "Ω" * 1025, 7, 9),
])
def test_invalid_selection_refuses_without_calls(args):
    api = API(envelope(7), envelope(9))
    with pytest.raises((TypeError, ValueError)):
        build_page_revision_comparison(api, *args)
    assert api.calls == []


def test_exact_selector_boundaries_and_current_locator():
    assert validate_revision_comparison("00042", " p / % ", 1, "9223372036854775807") == {
        "course_id": "42", "page_url": " p / % ",
        "before_revision": "1", "after_revision": "9223372036854775807",
    }


@pytest.mark.parametrize("value", [
    None, [], {"revision": []}, {"revision": {"revision_id": 9}},
    {"revision": {"revision_id": 7}, "body_text": None},
    {"revision": {"revision_id": 7, "body": None}},
    {"revision": {"revision_id": 7, "body": None}, "body_text": ""},
    {"revision": {"revision_id": 7, "body": ""}},
    {"revision": {"revision_id": 7, "body": 1}, "body_text": "1"},
])
def test_malformed_first_envelope_stops_before_second_call(value):
    api = API(value, envelope(9))
    with pytest.raises((TypeError, ValueError)):
        build_page_revision_comparison(api, 42, "p", 7, 9)
    assert len(api.calls) == 1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), object(), (1,), b"x", "\udfff"])
def test_non_json_values_refuse_without_coercion(value):
    before = envelope(7)
    before["opaque"] = value
    with pytest.raises((TypeError, ValueError)):
        build(before, envelope(9))


def test_cycles_non_string_keys_and_first_response_detachment():
    before = envelope(7, "old")
    before["cycle"] = before
    with pytest.raises(ValueError):
        build(before, envelope(9))
    with pytest.raises(TypeError):
        build({"revision": {"revision_id": 7}, 1: "bad"}, envelope(9))
    shared = envelope(7, "old")
    shared["outer"] = {"deep": [None, False, 1.25]}

    class Mutator:
        calls = 0

        def get_page_revision(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                shared["revision"]["body"] = "changed during second read"
                shared["outer"]["deep"].append("changed")
                return envelope(9, "new")
            return shared

    expected = deepcopy(shared)
    _, report = build_page_revision_comparison(Mutator(), 42, "p", 7, 9)
    assert report["before"] == expected
    report["before"]["outer"]["deep"].append("report mutation")
    assert shared["outer"]["deep"] == [None, False, 1.25, "changed"]


def test_depth_node_and_compact_envelope_byte_bounds():
    before = {"revision": {"revision_id": 7}}
    nested = None
    for _ in range(62):
        nested = [nested]
    before["revision"]["opaque"] = nested
    build(before, envelope(9))
    before["revision"]["opaque"] = [nested]
    with pytest.raises(ValueError, match="64 container"):
        build(before, envelope(9))
    before = {"revision": {"revision_id": 7}, "opaque": [None] * 99_996}
    build(before, envelope(9))
    before["opaque"].append(None)
    with pytest.raises(ValueError, match="expanded JSON"):
        build(before, envelope(9))
    before = {"revision": {"revision_id": 7}, "opaque": ""}
    overhead = len(json.dumps(before, separators=(",", ":")).encode())
    before["opaque"] = "x" * (1_048_576 - overhead)
    build(before, envelope(9))
    before["opaque"] += "x"
    with pytest.raises(ValueError, match="envelope"):
        build(before, envelope(9))


def test_body_and_work_limits_do_not_truncate_source():
    before = envelope(7, "Ω" * 262_144)
    before["body_text"] = "synthetic inherited projection"
    content, report = build(before, envelope(9))
    assert report["before"] == before
    assert report["comparison"]["line_diff"]["status"] == "limit"
    assert json.loads(Download(content).payload()) == report
    before["revision"]["body"] += "x"
    with pytest.raises(ValueError, match="524288"):
        build(before, envelope(9))
    for length, expected in [(131_072, "computed"), (131_073, "limit")]:
        _, report = build(envelope(7, "x" * length), envelope(9))
        assert report["comparison"]["line_diff"]["status"] == expected
        assert len(report["before"]["revision"]["body"]) == length
    _, report = build(envelope(7, "x\n" * 1000), envelope(9, "x\n" * 1000))
    assert report["comparison"]["line_diff"]["status"] == "computed"
    _, report = build(envelope(7, "x\n" * 1001), envelope(9, "x\n" * 1000))
    assert report["comparison"]["line_diff"]["status"] == "limit"


def test_output_limit_refuses_whole_document():
    before = {"revision": {"revision_id": 7}, "opaque": "&" * 950_000}
    after = {"revision": {"revision_id": 9}, "opaque": "&" * 950_000}
    with pytest.raises(ValueError, match="HTML"):
        build(before, after)

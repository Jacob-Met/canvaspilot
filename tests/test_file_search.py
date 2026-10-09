"""Maintained behavior checks for selected-course file-name search."""

import json
from copy import deepcopy

import pytest

from canvaspilot.file_search import find_files, validate_request


class Reader:
    def __init__(self, courses):
        self.courses = courses
        self.calls = []

    def list_files(self, course_id):
        self.calls.append(course_id)
        value = self.courses[course_id]
        if isinstance(value, Exception):
            raise value
        return value


def test_casefold_order_duplicate_occurrences_and_metadata_preservation():
    row = {
        "id": 7, "display_name": "Straße.pdf", "filename": "STRASSE-original.pdf",
        "size": 0, "url": "javascript:literal-only", "updated_at": None,
        "extra": {"false": False, "empty": [], "unicode": "雪"},
    }
    courses = {"42": [row, deepcopy(row)], "77": []}
    original = deepcopy(courses)
    api = Reader(courses)
    result = find_files(api, ["0042", 77], "strasse")
    assert api.calls == ["42", "77"]
    assert result["query"] == "strasse"
    assert result["source"] == "CanvasAPI.list_files"
    assert result["content_searched"] is False
    assert result["searched_fields"] == ["display_name", "filename"]
    assert result["match_rule"] == "unicode_casefold_substring"
    assert result["totals"] == {
        "courses": 2, "returned_files": 2, "searched_files": 2,
        "matched_files": 2, "rows_with_unavailable_names": 0,
    }
    assert result["courses"][0]["matches"] == [
        {"source_position": position, "matched_fields": ["display_name", "filename"], "file": row}
        for position in [1, 2]
    ]
    assert result["courses"][1] == {
        "course_id": "77", "returned_files": 0, "searched_files": 0,
        "matched_files": 0, "unavailable_names": [], "matches": [],
    }
    assert courses == original


@pytest.mark.parametrize(("query", "display", "filename", "expected"), [
    (".*", "anything.pdf", "literal.*.pdf", ["filename"]),
    ("[1]", "report[1]", "report1", ["display_name"]),
    (" lab ", "collaborative.pdf", " lab notes ", ["filename"]),
    ("ab", "a", "b", []),
    ("cafe", "café.pdf", "cafe\u0301.pdf", ["filename"]),
    ("café", "cafe\u0301.pdf", "CAFÉ.PDF", ["filename"]),
    ("雪", "雪ノート", "notes.pdf", ["display_name"]),
    ("?", "ordinary.pdf", "ordinary?.pdf", ["filename"]),
])
def test_matching_is_literal_per_field_without_normalization(query, display, filename, expected):
    row = {"display_name": display, "filename": filename}
    result = find_files(Reader({"1": [row]}), [1], query)
    assert result["query"] == query
    matches = result["courses"][0]["matches"]
    assert [m["matched_fields"] for m in matches] == ([expected] if expected else [])


def test_unknown_empty_and_partial_names_remain_distinct():
    rows = [
        {},
        {"display_name": None, "filename": []},
        {"display_name": "", "filename": ""},
        {"display_name": "lab", "filename": False},
        {"display_name": {"text": "lab"}, "filename": "elsewhere"},
    ]
    result = find_files(Reader({"9": rows}), [9], "lab")
    course = result["courses"][0]
    assert course["returned_files"] == 5
    assert course["searched_files"] == 3
    assert course["matched_files"] == 1
    assert course["unavailable_names"] == [
        {"source_position": 1, "fields": {"display_name": "missing", "filename": "missing"}},
        {"source_position": 2, "fields": {"display_name": "null", "filename": "unsupported_type"}},
        {"source_position": 4, "fields": {"filename": "unsupported_type"}},
        {"source_position": 5, "fields": {"display_name": "unsupported_type"}},
    ]
    assert course["matches"] == [
        {"source_position": 4, "matched_fields": ["display_name"], "file": rows[3]},
    ]


@pytest.mark.parametrize("ids", [
    [], None, "42", list(range(1, 12)), [0], [True], [1.0], ["+1"],
    ["-1"], [" 1"], ["1 "], ["١"], ["1" * 21], [1, "01"],
])
def test_invalid_course_selection_never_reads(ids):
    api = Reader({})
    with pytest.raises(ValueError):
        find_files(api, ids, "lab")
    assert api.calls == []


@pytest.mark.parametrize("query", ["", " \t\n", None, 12, "x" * 513, "雪" * 171, "\ud800"])
def test_invalid_query_never_reads(query):
    api = Reader({})
    with pytest.raises(ValueError):
        find_files(api, [1], query)
    assert api.calls == []


def test_exact_utf8_query_limit_and_numeric_id_limit():
    query = "雪" * 170 + "xy"
    assert len(query.encode("utf-8")) == 512
    assert validate_request([99999999999999999999], query) == (
        ["99999999999999999999"], query,
    )


def test_later_course_read_error_stops_without_mutation():
    failure = RuntimeError("authored read failure")
    rows = [{"display_name": "lab", "filename": "lab.pdf"}]
    api = Reader({"1": rows, "2": failure, "3": []})
    before = deepcopy(rows)
    with pytest.raises(RuntimeError) as caught:
        find_files(api, [1, 2, 3], "lab")
    assert caught.value is failure
    assert api.calls == ["1", "2"]
    assert rows == before


@pytest.mark.parametrize("rows", [
    None, {}, (), [None], ["lab"],
    [{"display_name": "lab", "extra": float("nan")}],
    [{"display_name": "lab", "extra": float("inf")}],
    [{"display_name": "lab", "extra": {"bad"}}],
    [{"display_name": "lab", "extra": {1: "not a JSON key"}}],
    [{"display_name": "lab", "extra": ("tuple",)}],
    [{"display_name": "\udfff", "filename": "lab"}],
])
def test_bad_metadata_refuses_whole_result_and_stops_later_courses(rows):
    api = Reader({"1": rows, "2": []})
    with pytest.raises(ValueError):
        find_files(api, [1, 2], "lab")
    assert api.calls == ["1"]


def test_exact_row_limits_and_overflow_stop_next_read():
    row = {"display_name": "", "filename": ""}
    accepted = Reader({"1": [row] * 2000, "2": [row] * 2000, "3": [row] * 1000})
    assert find_files(accepted, [1, 2, 3], "x")["totals"]["returned_files"] == 5000
    too_many_course = Reader({"1": [row] * 2001, "2": []})
    with pytest.raises(ValueError):
        find_files(too_many_course, [1, 2], "x")
    assert too_many_course.calls == ["1"]
    too_many_total = Reader({"1": [row] * 2000, "2": [row] * 2000, "3": [row] * 1001, "4": []})
    with pytest.raises(ValueError):
        find_files(too_many_total, [1, 2, 3, 4], "x")
    assert too_many_total.calls == ["1", "2", "3"]


def test_exact_json_row_byte_limit_and_one_byte_over():
    limit = 8 * 1024 * 1024
    row = {"display_name": "lab", "filename": "", "extra": ""}
    overhead = len(json.dumps(row, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())
    row["extra"] = "x" * (limit - overhead)
    accepted = find_files(Reader({"1": [row]}), [1], "lab")
    assert accepted["totals"]["matched_files"] == 1
    row["extra"] += "x"
    rejected = Reader({"1": [row], "2": []})
    with pytest.raises(ValueError):
        find_files(rejected, [1, 2], "lab")
    assert rejected.calls == ["1"]

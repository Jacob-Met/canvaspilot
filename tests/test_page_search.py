"""Native helper and CLI contracts for literal course-page search."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from canvaspilot import CanvasAPI, CanvasClient
from canvaspilot.page_search import find_pages, validate_course, validate_query


def search(rows, query="field journal"):
    fixture = {"routes": {"GET /api/v1/courses/42/pages": rows}}
    with CanvasClient(base_url="https://canvas.invalid", token="", fixture=fixture) as client:
        return find_pages(CanvasAPI(client), 42, query)


def test_body_only_title_both_order_and_exact_source():
    rows = [
        {"page_id": 7, "url": "a", "title": "Notes", "body": "<p>field <b>journal</b></p>", "extra": {"zero": 0, "false": False}},
        {"page_id": 7, "url": "b", "title": "FIELD JOURNAL", "body": "no"},
        {"page_id": 8, "url": "c", "title": "field journal", "body": "field journal"},
    ]
    before = deepcopy(rows)
    result = search(rows)
    assert result["pages_returned"] == result["pages_matched"] == 3
    assert [m["position"] for m in result["matches"]] == [1, 2, 3]
    assert [m["matched_fields"] for m in result["matches"]] == [["body_text"], ["title"], ["title", "body_text"]]
    assert [m["page"] for m in result["matches"]] == rows == before
    result["matches"][0]["page"]["extra"]["zero"] = 99
    assert rows == before


def test_unavailable_is_not_empty_or_no_match():
    rows = [
        {"page_id": 1, "title": "field journal", "block_editor_attributes": {"blocks": "field journal"}},
        {"page_id": 2, "title": None, "body": None},
        {"page_id": 3, "title": "Locked", "body": "field journal", "locked_for_user": True},
        {"page_id": 4, "title": "Empty", "body": ""},
        {"page_id": 5, "body": "field journal", "locked_for_user": False},
    ]
    result = search(rows)
    assert result["titles_searched"] == 3
    assert result["bodies_searched"] == 2
    assert [m["position"] for m in result["matches"]] == [1, 5]
    assert result["matches"][0]["body_text"] is None
    assert [r["reason"] for r in result["unavailable_bodies"]] == ["body_not_supplied", "body_null", "locked_for_user"]
    assert [r["page"] for r in result["unavailable_bodies"]] == rows[:3]


def test_unicode_casefold_expansion_and_literal_metacharacters():
    rows = [{"title": "Straße [a.*]", "body": "STRASSE [a.*]"}]
    assert search(rows, "strasse")["pages_matched"] == 1
    assert search(rows, "[a.*]")["pages_matched"] == 1
    assert search(rows, "a.+")["pages_matched"] == 0


def test_whitespace_preserved_and_no_cross_field_match():
    row = {"title": "field", "body": "<p>journal</p>"}
    assert search([row])["pages_matched"] == 0
    assert search([{"title": " x ", "body": "x"}], " x ")["matches"][0]["matched_fields"] == ["title"]
    assert search([{"title": "café", "body": ""}], "cafe")["pages_matched"] == 0


def test_complete_body_beyond_compact_prefix_and_escaped_markup():
    result = search([{"title": "notes", "body": "<p>" + "z" * 1000 + " field &lt;journal&gt;</p>"}], "<JOURNAL>")
    assert result["pages_matched"] == 1
    assert len(result["matches"][0]["body_text"]) > 1000


def test_empty_collection_and_complete_no_match():
    assert search([])["pages_returned"] == 0
    result = search([{"title": "Other", "body": ""}])
    assert result["pages_matched"] == 0 and result["bodies_searched"] == 1


def test_selection_admission_precedes_reader():
    class NoRead:
        def get_paginated(self, *a, **kw):
            pytest.fail("invalid selection reached reader")
    api = SimpleNamespace(client=NoRead())
    for course in [0, -1, True, 1.0, "a", " 42", "1/2", "9" * 65]:
        with pytest.raises((TypeError, ValueError)):
            find_pages(api, course, "x")
    for query in ["", " \t", None, "\ud800", "\0", "é" * 257]:
        with pytest.raises((TypeError, ValueError)):
            find_pages(api, 42, query)
    assert validate_course("00042") == "42"
    assert validate_query(" x ") == " x "


def test_exact_collection_call_and_failure_propagation():
    class Reader:
        def get_paginated(self, path, *, params):
            assert path == "/api/v1/courses/42/pages"
            assert params == {"include[]": ["body"]}
            raise RuntimeError("later-page refusal")
    with pytest.raises(RuntimeError, match="later-page refusal"):
        find_pages(SimpleNamespace(client=Reader()), "0042", "x")


@pytest.mark.parametrize("bad", [False, {"title": 0}, {"body": []}, {"locked_for_user": "false"}, {"extra": float("nan")}])
def test_malformed_later_row_refuses_complete_result(bad):
    with pytest.raises((TypeError, ValueError)):
        search([{"title": "field journal", "body": "yes"}, bad])


def test_collection_limits_refuse_not_truncate():
    with pytest.raises(ValueError, match="1000"):
        search([{"title": "x"}] * 1001)
    with pytest.raises(ValueError, match="8 MiB"):
        search([{"title": "x", "body": "x" * (8 * 1024 * 1024)}])

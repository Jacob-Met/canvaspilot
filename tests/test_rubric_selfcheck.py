"""Native controls for the separate local rubric self-check consumer."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from html.parser import HTMLParser
from types import SimpleNamespace

import pytest
from test_study_workspace import brief

from canvaspilot.rubric_selfcheck import build_rubric_selfcheck


def envelope(page):
    found = re.search(r'<script id="selfcheck-data" type="application/json">(.*?)</script>', page.decode(), re.DOTALL)
    assert found
    return json.loads(found.group(1))


class Display(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "script":
            self.scripts += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def page_text(page):
    d = Display()
    d.feed(page.decode())
    return " ".join(d.parts), d


def build(row=None):
    record = row or brief()
    return build_rubric_selfcheck(
        SimpleNamespace(assignment_brief=lambda *a: copy.deepcopy(record)),
        "17", ["81"], source_base_url="https://canvas.fixture.invalid",
        exported_at="2026-10-08T00:00:00+00:00",
    )


def test_ordinals_keep_duplicate_and_absent_ids_separate_and_source_exact():
    record = brief()
    record["rubric"] = [
        {"id": "same", "description": "First", "ratings": []},
        {"id": "same", "description": "Second", "ratings": None},
        {"description": "Third", "points": 0},
    ]
    before = copy.deepcopy(record)
    page, report = build(record)
    doc = envelope(page)
    assert list(doc["state"]["criteria"]) == ["17:81:0", "17:81:1", "17:81:2"]
    assert all(x == {"status": "unreviewed", "notes": ""} for x in doc["state"]["criteria"].values())
    assert json.loads(doc["source"])["assignments"][0]["brief"] == before == record
    assert report["criterion_count"] == 3
    assert hashlib.sha256(doc["source"].encode()).hexdigest() == doc["source_sha256"]


@pytest.mark.parametrize("rubric,expected", [(None, "Rubric unavailable."), ([], "The supplied rubric is empty.")])
def test_unavailable_and_empty_stay_distinct(rubric, expected):
    record = brief(); record["rubric"] = rubric
    page, report = build(record)
    text, _ = page_text(page)
    assert expected in text
    assert report["criterion_count"] == 0 and envelope(page)["state"]["criteria"] == {}


def test_large_integer_metadata_is_rendered_before_browser_parsing():
    record = brief()
    record["rubric"] = [{"id": 9007199254740993, "description": "Exact number labels", "points": 9007199254740995,
                         "ratings": [{"description": "Example", "points": -0.0, "id": 9223372036854775807}]}]
    page, _ = build(record)
    text, _ = page_text(page)
    assert "9007199254740993" in text and "9007199254740995" in text and "-0.0" in text
    source = json.loads(envelope(page)["source"])
    assert source["assignments"][0]["brief"]["rubric"] == record["rubric"]


@pytest.mark.parametrize("flag,visible", [(False, True), (True, False), (None, False), (0, False), ("false", False)])
def test_hidden_point_labels_are_conservative_and_source_is_not_redacted(flag, visible):
    record = brief()
    record["rubric_settings"] = {"hide_points": flag, "points_possible": "5555"}
    record["rubric"] = [{"description": "Criterion", "points": 7777, "ratings": [{"points": 8888}]}]
    page, _ = build(record)
    text, _ = page_text(page)
    assert ("7777" in text) is visible
    assert ("8888" in text) is visible
    assert ("5555" in text) is visible
    assert json.loads(envelope(page)["source"])["assignments"][0]["brief"]["rubric"][0]["points"] == 7777


def test_hide_total_keeps_criterion_labels_without_calculating_score():
    record = brief()
    record["rubric_settings"] = {"hide_score_total": True, "points_possible": "5555"}
    record["rubric"] = [{"description": "Criterion", "points": 7777, "ratings": [{"points": 8888}]}]
    page, _ = build(record); text, _ = page_text(page)
    assert "5555" not in text and "7777" in text and "8888" in text


def test_literal_text_and_template_tokens_cannot_create_active_markup():
    record = brief()
    hostile = '</script><img src="https://outside.invalid/x" onerror="alert(1)"> __DATA__ __SCRIPT__ & <b>'
    record.update(title=hostile, prompt=hostile, html_url="javascript:alert(1)")
    record["rubric"] = [{"description": hostile, "long_description": hostile}]
    page, _ = build(record); text, parser = page_text(page)
    assert hostile in text and parser.scripts == 2
    assert b'<img src="https://outside.invalid' not in page
    assert b'href="javascript:' not in page
    assert json.loads(envelope(page)["source"])["assignments"][0]["brief"]["title"] == hostile


def test_capture_freezes_mutable_reader_results_in_selected_order():
    record = brief(); calls = []
    def read(course, assignment):
        calls.append((course, assignment)); record["assignment_id"] = assignment
        record["rubric"] = [{"description": "Assignment " + assignment}]
        return record
    page, _ = build_rubric_selfcheck(SimpleNamespace(assignment_brief=read), "17", ["82", "81"],
                                    source_base_url="https://canvas.fixture.invalid")
    doc = envelope(page); data = json.loads(doc["source"])
    assert calls == [("17", "82"), ("17", "81")]
    assert [x["brief"]["rubric"][0]["description"] for x in data["assignments"]] == ["Assignment 82", "Assignment 81"]
    assert list(doc["state"]["criteria"]) == ["17:81:0", "17:82:0"]  # JSON object canonical key order.
    assert page.index(b'data-criterion-key="17:82:0"') < page.index(b'data-criterion-key="17:81:0"')


@pytest.mark.parametrize("selection", [[], ["81", "081"], ["81", "wrong"], list(map(str, range(1, 27)))])
def test_bad_selection_refuses_before_reader(selection):
    calls = []
    with pytest.raises(ValueError):
        build_rubric_selfcheck(SimpleNamespace(assignment_brief=lambda *x: calls.append(x)),
                               "17", selection, source_base_url="https://canvas.fixture.invalid")
    assert calls == []


def test_criteria_and_rating_caps_refuse_whole_output_not_truncate():
    record = brief(); record["rubric"] = [{"description": "x"} for _ in range(500)]
    _, report = build(record); assert report["criterion_count"] == 500
    record["rubric"].append({"description": "x"})
    with pytest.raises(ValueError, match="500 criteria"):
        build(record)
    record["rubric"] = [{"ratings": [{"description": "r"} for _ in range(5000)]}]
    _, report = build(record); assert report["rating_count"] == 5000
    record["rubric"][0]["ratings"].append({"description": "r"})
    with pytest.raises(ValueError, match="5000 ratings"):
        build(record)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_nested_source_refuses(bad):
    record = brief(); record["rubric"] = [{"points": bad}]
    with pytest.raises(ValueError):
        build(record)


def test_source_size_and_malformed_ratings_refuse():
    record = brief(); record["prompt"] = "x" * (4 * 1024 * 1024)
    with pytest.raises(ValueError, match="4 MiB"):
        build(record)
    record["prompt"] = "small"; record["rubric"] = [{"ratings": [None]}]
    with pytest.raises(ValueError, match="ratings"):
        build(record)


def test_output_style_and_script_hashes_match_exact_embedded_bytes():
    page, _ = build()
    import base64
    for tag in ("style", "script"):
        pattern = rb"<style>(.*?)</style>" if tag == "style" else rb"<script>(.*?)</script>"
        raw = re.search(pattern, page, re.DOTALL).group(1)
        value = base64.b64encode(hashlib.sha256(raw).digest())
        assert b"'sha256-" + value + b"'" in page

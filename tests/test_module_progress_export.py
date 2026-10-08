"""Offline report semantics through the unchanged Canvas module-progress reader."""

from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from html.parser import HTMLParser
from unittest.mock import Mock

import pytest
from module_progress_fixture import course_fixture

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.module_progress_export import (
    build_module_progress_report,
    render_module_progress_report,
)

NOW = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)


class ReportDocument(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.fields = []
        self.text = []
        self.active_field = None
        self.active_text = []
        self.feed(content.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.elements.append((tag, attributes))
        if tag == "dd":
            self.active_field = attributes["data-field"]
            self.active_text = []

    def handle_endtag(self, tag):
        if tag == "dd":
            self.fields.append((self.active_field, json.loads("".join(self.active_text))))
            self.active_field = None

    def handle_data(self, text):
        self.text.append(text)
        if self.active_field is not None:
            self.active_text.append(text)

    def values(self, key):
        return [value for name, value in self.fields if name == key]

    def download(self):
        link = next(attrs for tag, attrs in self.elements
                    if tag == "a" and attrs.get("id") == "download-report")
        assert link["download"] == "module-progress.json"
        prefix = "data:application/json;base64,"
        assert link["href"].startswith(prefix)
        return base64.b64decode(link["href"][len(prefix):], validate=True)


def read(source=None, *, module_id=None):
    fixture = course_fixture() if source is None else source
    with CanvasAPI(CanvasClient(token="", fixture=fixture)) as api:
        return api.module_progress(42, module_id=module_id)


def render(source=None, *, module_id=None):
    report = read(source, module_id=module_id)
    content, receipt = render_module_progress_report(report, generated_at=NOW)
    document = ReportDocument(content)
    assert json.loads(document.download()) == report
    assert receipt["json_sha256"] == hashlib.sha256(document.download()).hexdigest()
    assert receipt["sha256"] == hashlib.sha256(content).hexdigest()
    assert receipt["html_bytes"] == len(content)
    assert receipt["json_bytes"] == len(document.download())
    return report, content, document, receipt


def test_builder_reads_exactly_once_and_does_not_mutate_the_reader_result():
    source = course_fixture()
    before = deepcopy(source)
    expected = read(source, module_id="8")
    with CanvasAPI(CanvasClient(token="", fixture=source)) as api:
        api.module_progress = Mock(wraps=api.module_progress)
        content, receipt = build_module_progress_report(
            api, 42, module_id="8", generated_at=NOW,
        )
        api.module_progress.assert_called_once_with(42, module_id="8")
    assert json.loads(ReportDocument(content).download()) == expected
    assert source == before
    assert receipt["modules_included"] == 1 and receipt["modules_returned"] == 4


def test_visible_fields_keep_completed_one_of_and_locked_unknown_context():
    report, _, doc, _ = render()
    assert doc.values("state") == ["started", "completed", "locked", "unknown"]
    assert doc.values("requirement_type") == ["all", "one", "all", "unknown"]
    assert doc.values("rule") == ["all", "module_completed", "all", "unknown"]
    assert doc.values("incomplete_item_ids") == [[72], [], [91], []]
    assert doc.values("unknown_completion_item_ids") == [[], [], [], [101, 102]]
    assert doc.values("require_sequential_progress") == [True, False, False, None]
    assert doc.values("prerequisite_module_ids") == [[], [], [7], None]
    assert doc.values("collection_complete") == [None]
    assert doc.values("item_access") == ["not_assessed"] * 4
    assert doc.values("completion_requirement") == [
        item["completion_requirement"] for module in report["modules"] for item in module["items"]
    ]
    text = "".join(doc.text)
    assert "incomplete items are alternatives, not a count of required tasks" in text
    assert "whole-course completeness remains unknown" in text
    assert "Some items have no reported requirement" in text
    assert all(tag not in {"script", "form", "input", "iframe", "img", "object"}
               for tag, _ in doc.elements)
    assert not any(key.lower().startswith("on") for _, attrs in doc.elements for key in attrs)


@pytest.mark.parametrize("raw", [
    None, False, {}, "must_view",
    {"type": "future_rule", "completed": True, "extension": ["x", 0, False, None]},
    {"type": "min_score", "min_score": 0, "completed": False},
    {"type": "min_percentage", "min_percentage": 70.25, "completed": None},
])
def test_complete_requirement_payload_and_status_remain_visible(raw):
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules/7/items"][1]["completion_requirement"] = raw
    report, _, doc, _ = render(source)
    item = report["modules"][0]["items"][1]
    assert doc.values("completion_requirement")[1] == raw
    assert doc.values("completion_status")[1] == item["completion_status"]
    assert doc.values("required_action")[1] == item["required_action"]


@pytest.mark.parametrize("count,status", [
    (3, "matches_reported_count"), (4, "shorter_than_reported_count"),
    (2, "more_than_reported_count"), (None, "unknown"), (True, "unknown"),
])
def test_coverage_is_visible_without_upgrading_reader_completeness(count, status):
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules"][0]["items_count"] = count
    _, _, doc, _ = render(source)
    assert doc.values("reported_count")[0] == count
    assert doc.values("returned_count")[0] == 3
    assert doc.values("status")[0] == status
    assert doc.values("collection_complete") == [None]


def test_unsupported_state_rule_and_prerequisites_remain_original_values():
    source = course_fixture()
    module = source["routes"]["GET /api/v1/courses/42/modules"][0]
    module.update(state={"future": True}, requirement_type=["some"],
                  prerequisite_module_ids=[7, "unresolved"], require_sequential_progress="false")
    _, _, doc, _ = render(source)
    assert doc.values("state")[0] == "unknown"
    assert doc.values("reported_state")[0] == {"future": True}
    assert doc.values("requirement_type")[0] == "unknown"
    assert doc.values("reported_requirement_type")[0] == ["some"]
    assert doc.values("prerequisite_module_ids")[0] is None
    assert doc.values("reported_prerequisite_module_ids")[0] == [7, "unresolved"]
    assert doc.values("require_sequential_progress")[0] is None


def test_source_order_selection_and_empty_results_are_not_inferred():
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules"].reverse()
    _, _, doc, _ = render(source)
    assert doc.values("id") == [10, 101, 102, 9, 91, 8, 81, 82, 7, 71, 72, 73]
    _, _, selected, receipt = render(source, module_id="009")
    assert selected.values("id") == [9, 91]
    assert selected.values("module_id")[0] == "9"
    assert selected.values("modules_omitted_by_selection") == [3]
    assert receipt["module_id"] == "9"
    source["routes"]["GET /api/v1/courses/42/modules"] = []
    _, _, empty, receipt = render(source)
    assert receipt["modules_included"] == 0
    assert "No modules were returned." in "".join(empty.text)
    assert empty.values("collection_complete") == [None]


def test_provider_markup_urls_controls_and_unicode_stay_inert_and_exact():
    source = course_fixture()
    module = source["routes"]["GET /api/v1/courses/42/modules"][0]
    module["name"] = '</title><script>globalThis.__injected=1</script> 雪 Café \x00 \ud800'
    item = source["routes"]["GET /api/v1/courses/42/modules/7/items"][0]
    item["title"] = '<img src="https://invalid.example/" onerror="bad()">'
    item["html_url"] = "javascript:globalThis.__injected=2"
    item["completion_requirement"]["extra"] = {"</pre>": "<svg/onload=bad()>", "control": "\x85"}
    report, _, doc, _ = render(source)
    assert doc.values("name")[0] == module["name"]
    assert doc.values("title")[0] == item["title"]
    assert doc.values("html_url")[0] == item["html_url"]
    assert doc.values("completion_requirement")[0] == item["completion_requirement"]
    assert json.loads(doc.download()) == report
    assert not {"script", "img", "svg"} & {tag for tag, _ in doc.elements}
    assert all(attrs["href"].startswith(("#", "data:application/json;base64,"))
               for tag, attrs in doc.elements if tag == "a")
    assert not any("src" in attrs for _, attrs in doc.elements)


def test_json_and_rendered_html_limits_refuse_oversized_export():
    source = course_fixture()
    module = source["routes"]["GET /api/v1/courses/42/modules"][0]
    module["name"] = "x" * (4 * 1024 * 1024)
    with pytest.raises(ValueError, match="JSON exceeds the 4 MiB"):
        render(source)
    module["name"] = "&" * 1_100_000
    with pytest.raises(ValueError, match="HTML exceeds the 16 MiB"):
        render(source)


def test_nonfinite_report_is_refused_and_timestamp_does_not_change_report():
    report = read()
    before = deepcopy(report)
    first, receipt = render_module_progress_report(
        report, generated_at=datetime(2026, 10, 9, 4, 0, tzinfo=timezone(timedelta(hours=13))),
    )
    second, _ = render_module_progress_report(report, generated_at=NOW)
    assert first == second and report == before
    assert receipt["generated_at"] == "2026-10-08T15:00:00Z"
    with pytest.raises(ValueError, match="timezone"):
        render_module_progress_report(report, generated_at=NOW.replace(tzinfo=None))
    report["modules"][0]["items"][0]["completion_requirement"]["extension"] = float("nan")
    with pytest.raises(ValueError):
        render_module_progress_report(report)

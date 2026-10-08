"""Public report semantics through the unchanged native discussion reader."""

from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from html.parser import HTMLParser
from unittest.mock import Mock

import pytest
from test_discussion_thread import fixture

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.discussion_export import (
    build_discussion_report,
    render_discussion_report,
)
from canvaspilot.discussion_thread import build_discussion_thread

NOW = datetime(2026, 10, 8, 19, 0, tzinfo=UTC)


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(content.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, value):
        self.text.append(value)

    def payload(self):
        link = next(attrs for tag, attrs in self.tags
                    if tag == "a" and attrs.get("id") == "download-report")
        assert link["download"] == "discussion-thread.json"
        return base64.b64decode(link["href"].split(",", 1)[1], validate=True)


def render(topic=None, view=None, unread_only=False):
    original_topic, original_view = fixture()
    report = build_discussion_thread(
        original_topic if topic is None else topic,
        original_view if view is None else view,
        unread_only=unread_only,
    )
    content, receipt = render_discussion_report(
        report, course_id="042", topic_id=7, generated_at=NOW,
    )
    doc = Document(content)
    payload = doc.payload()
    assert json.loads(payload) == report
    assert receipt["sha256"] == hashlib.sha256(content).hexdigest()
    assert receipt["html_bytes"] == len(content)
    assert receipt["json_sha256"] == hashlib.sha256(payload).hexdigest()
    assert receipt["json_bytes"] == len(payload)
    assert receipt["course_id"] == "042" and receipt["topic_id"] == "7"
    return report, content, doc, receipt


def test_builder_reads_existing_api_once_and_preserves_all_normalized_fields():
    topic, view = fixture()
    source = {"routes": {
        "GET /api/v1/courses/42/discussion_topics/7": topic,
        "GET /api/v1/courses/42/discussion_topics/7/view": view,
    }}
    before = deepcopy(source)
    expected = build_discussion_thread(topic, view, unread_only=True)
    with CanvasAPI(CanvasClient(token="", fixture=source)) as api:
        api.discussion_thread = Mock(wraps=api.discussion_thread)
        content, receipt = build_discussion_report(
            api, 42, 7, unread_only=True, generated_at=NOW,
        )
        api.discussion_thread.assert_called_once_with(42, 7, unread_only=True)
    assert json.loads(Document(content).payload()) == expected
    assert source == before
    assert receipt["entries_included"] == 4
    assert receipt["selection"] == "unread_with_ancestors"


def test_source_order_parent_links_and_unread_context_use_structural_positions():
    report, _, doc, _ = render(unread_only=True)
    assert [row["entry"]["id"] for row in report["entries"]] == [1, 2, 3, 5]
    assert [attrs["id"] for tag, attrs in doc.tags if tag == "article"] == [
        "entry-0", "entry-1", "entry-2", "entry-3",
    ]
    assert sum("context" in attrs.get("class", "").split()
               for tag, attrs in doc.tags if tag == "article") == 2
    text = " ".join(doc.text)
    assert "Go to parent entry 1" in text and "Go to parent entry 2" in text
    assert "observed" in text.lower() and "999" not in text
    assert "Some supplied unread identifiers are absent" in text
    assert "Paths describe this view only" in text


def test_deleted_unknown_and_media_entries_are_retained_without_invented_text():
    topic, view = fixture()
    view["participants"].append({"id": 9, "display_name": "Ambiguous second author"})
    view["view"][0]["replies"][0].update(deleted=True, message="<p>Retained only as source.</p>")
    view["view"][1].pop("message")
    view["view"][1]["attachment"] = {"filename": "reading.wav", "url": "https://invalid.example/a"}
    report, _, doc, _ = render(topic, view)
    text = " ".join(doc.text)
    assert "Author unavailable or ambiguous" in text
    assert "Author unavailable for this deleted entry" in text
    assert "Deleted entry; body text is unavailable." in text
    assert "The reader returned no body text." in text
    assert report["entries"][1]["message_text"] is None
    assert report["entries"][1]["author"] is None
    assert report["entries"][-2]["entry"]["attachment"]["filename"] == "reading.wav"


@pytest.mark.parametrize("markers", [[], None])
def test_empty_focus_and_unknown_read_markers_remain_distinct(markers):
    topic, view = fixture()
    view["unread_entries"] = markers
    report, _, doc, receipt = render(topic, view, unread_only=markers == [])
    if markers == []:
        assert receipt["entries_included"] == 0
        assert "No entries are included in this selection" in " ".join(doc.text)
    else:
        assert report["counts"]["known_unread_entries"] is None
        assert all(row["read_state"] == "unknown" for row in report["entries"])
        assert "Canvas did not supply unread_entries" in " ".join(doc.text)


def test_markup_urls_controls_and_complete_original_values_stay_inert():
    topic, view = fixture()
    topic["title"] = '</title><script>globalThis.injected=1</script> 雪 Café \0 \ud800'
    view["participants"][0]["display_name"] = '<img src="https://invalid.example/" onerror="bad()">'
    view["view"][0]["message"] = "<p>&lt;svg/onload=bad()&gt; \x85</p>"
    view["view"][0]["opaque"] = {"false": False, "null": None, "zero": 0,
                                "empty": "", "url": "javascript:bad()", "lone": "\udfff"}
    report, _, doc, _ = render(topic, view)
    assert json.loads(doc.payload()) == report
    assert not {"script", "img", "svg", "iframe", "object", "form", "input"} & {
        tag for tag, _ in doc.tags
    }
    assert not any(key.lower().startswith("on") or key == "src"
                   for _, attrs in doc.tags for key in attrs)
    assert all(attrs["href"].startswith(("#", "data:application/json;base64,"))
               for tag, attrs in doc.tags if tag == "a")
    assert "\\u0000" in " ".join(doc.text) and "\\ud800" in " ".join(doc.text)


def test_report_creation_time_is_aware_normalized_and_does_not_mutate_report():
    report = build_discussion_thread(*fixture())
    before = deepcopy(report)
    a, receipt = render_discussion_report(
        report, course_id=42, topic_id=7,
        generated_at=datetime(2026, 10, 9, 8, 0, tzinfo=timezone(timedelta(hours=13))),
    )
    b, _ = render_discussion_report(report, course_id=42, topic_id=7, generated_at=NOW)
    assert a == b and report == before
    assert receipt["generated_at"] == "2026-10-08T19:00:00Z"
    with pytest.raises(ValueError, match="timezone"):
        render_discussion_report(report, course_id=42, topic_id=7, generated_at=NOW.replace(tzinfo=None))


def test_report_and_html_size_limits_refuse_whole_output():
    topic, view = fixture()
    topic["title"] = "x" * (4 * 1024 * 1024)
    with pytest.raises(ValueError, match="JSON exceeds the 4 MiB"):
        render(topic, view)
    topic["title"] = "&" * 1_700_000
    with pytest.raises(ValueError, match="HTML exceeds the 16 MiB"):
        render(topic, view)


def test_nonfinite_source_refuses_without_serializing_a_lossy_report():
    report = build_discussion_thread(*fixture())
    report["topic"]["future_score"] = float("nan")
    with pytest.raises(ValueError):
        render_discussion_report(report, course_id=42, topic_id=7, generated_at=NOW)

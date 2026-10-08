"""Rendering boundaries and new-file publication, using the native feedback API."""

import copy
import json
import os
import stat
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.feedback_export import build_feedback_document, write_feedback_document
from test_feedback_export_native import Document

FIXTURE = Path(__file__).parent / "fixtures" / "submission_feedback.json"
WHEN = datetime(2026, 10, 8, 12, 34, 56, 789123, tzinfo=UTC)


@pytest.fixture
def source():
    return json.loads(FIXTURE.read_text())


def document(source, when=WHEN):
    routes = {
        "GET /api/v1/courses/41/assignments/902": source["assignment"],
        "GET /api/v1/courses/41/assignments/902/submissions/self": source["submission"],
    }
    with CanvasAPI(CanvasClient(fixture={"routes": routes})) as api:
        content, receipt = build_feedback_document(api, 41, 902, captured_at=when)
    return content, receipt, Document(content.decode())


def test_native_duplicate_id_joins_are_not_reconstructed_by_renderer(source):
    source["assignment"]["rubric"] = [
        {"id": "same", "description": "First same ID"},
        {"id": "same", "description": "Second same ID"},
        {"id": "0", "description": "Exact string zero"},
        {"id": 0, "description": "Different numeric zero"},
    ]
    source["submission"]["rubric_assessment"] = {
        "same": {"points": 19, "comments": "Unmatched duplicate."},
        "0": {"points": 0, "comments": "Exact string match."},
    }
    original = copy.deepcopy(source)
    content, receipt, doc = document(source)
    assert "criterion.1.assessment.points" not in doc.fields
    assert "criterion.2.assessment.points" not in doc.fields
    assert doc.field("criterion.3.assessment.points") == "0"
    assert "criterion.4.assessment.points" not in doc.fields
    assert doc.field("unmatched.1.points") == "19"
    assert source == original
    second, second_receipt, _ = document(source)
    assert second == content and second_receipt == receipt


def test_saved_timestamp_retains_precision_and_source_times_are_not_relabelled(source):
    source["submission"]["graded_at"] = "2026-10-07T15:00:00.123456-04:00"
    when = WHEN.astimezone(timezone(timedelta(hours=5, minutes=30)))
    _, receipt, doc = document(source, when)
    assert doc.field("captured_at") == "2026-10-08T12:34:56.789123Z"
    assert receipt["captured_at"] == doc.field("captured_at")
    assert doc.field("submission.graded_at") == "2026-10-07T15:00:00.123456-04:00"


def test_returned_nested_author_record_is_shown_without_guessing_a_role(source):
    comment = source["submission"]["submission_comments"][0]
    comment.update({"author_name": None, "author_id": None,
                    "author": {"display_name": "Supplied name — 学生", "id": 97}})
    _, _, doc = document(source)
    assert doc.field("comment.1.author_name") == "Not returned"
    assert doc.field("comment.1.author.display_name") == "Supplied name — 学生"
    assert doc.field("comment.1.author.id") == "97"
    assert "instructor comments" not in doc.text.lower()


@pytest.mark.parametrize("url", [
    "javascript:alert(1)", "data:text/html,boom", "file:///etc/passwd",
    "//example.invalid/path", "https://user:password@example.invalid/secret",
    "https://example.invalid/\nunsafe", "https://[invalid/",
])
def test_unusable_assignment_urls_are_literal_text_not_active_links(source, url):
    source["assignment"]["html_url"] = url
    _, _, doc = document(source)
    assert not any(tag == "a" for tag, _ in doc.tags)
    assert url in doc.text


def test_empty_settings_and_no_settings_remain_distinct(source):
    source["assignment"]["rubric_settings"] = None
    _, _, missing = document(source)
    source["assignment"]["rubric_settings"] = {}
    _, _, empty = document(source)
    assert "Rubric settings were not returned." in missing.text
    assert "empty rubric settings object" not in missing.text
    assert "empty rubric settings object" in empty.text
    assert "Rubric settings were not returned." not in empty.text


def test_missing_returned_identity_stays_unknown_beside_the_explicit_request(source):
    source["assignment"].update({"id": None, "course_id": None})
    source["submission"]["assignment_id"] = None
    _, _, doc = document(source)
    assert doc.field("requested.course_id") == "41"
    assert doc.field("requested.assignment_id") == "902"
    assert doc.field("assignment.course_id") == "Not returned"
    assert doc.field("assignment.id") == "Not returned"


@pytest.mark.parametrize("course_id,assignment_id,when", [
    (False, 902, WHEN), (41, "../902", WHEN), (0, 902, WHEN),
    (41, -1, WHEN), (41, 902, WHEN.replace(tzinfo=None)),
])
def test_invalid_export_inputs_refuse_before_any_read(course_id, assignment_id, when):
    class NoRead:
        def submission_feedback(self, *args):
            pytest.fail("Invalid export inputs must be rejected before source access")

    with pytest.raises(ValueError):
        build_feedback_document(NoRead(), course_id, assignment_id, captured_at=when)


def test_new_document_is_complete_private_and_does_not_leave_staging_files(tmp_path, source):
    content, _, _ = document(source)
    output = tmp_path / "feedback.html"
    write_feedback_document(output, content)
    assert output.read_bytes() == content
    assert list(tmp_path.iterdir()) == [output]
    if os.name == "posix":
        assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_destination_created_during_publication_is_never_overwritten(tmp_path, monkeypatch):
    output = tmp_path / "existing.html"
    native_link = os.link

    def concurrent_link(source, destination):
        output.write_bytes(b"A file created while the export was being prepared")
        native_link(source, destination)

    monkeypatch.setattr(os, "link", concurrent_link)
    with pytest.raises(FileExistsError):
        write_feedback_document(output, b"new complete export")
    assert output.read_bytes() == b"A file created while the export was being prepared"
    assert list(tmp_path.iterdir()) == [output]


def test_failed_flush_or_unsupported_publication_leaves_no_output(tmp_path, monkeypatch):
    output = tmp_path / "failure.html"

    def denied(*args):
        raise OSError("Authored filesystem refusal")

    with monkeypatch.context() as context:
        context.setattr(os, "fsync", denied)
        with pytest.raises(OSError, match="Authored filesystem refusal"):
            write_feedback_document(output, b"not published")
    assert list(tmp_path.iterdir()) == []
    with monkeypatch.context() as context:
        context.setattr(os, "link", denied)
        with pytest.raises(OSError, match="Authored filesystem refusal"):
            write_feedback_document(output, b"also not published")
    assert list(tmp_path.iterdir()) == []

"""Offline history reports preserve version attribution and the native CLI boundary."""

import base64
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

import pytest

from canvaspilot import api as api_module
from canvaspilot import cli
from canvaspilot import submission_history_export as export

STAMP = datetime(2026, 10, 8, 12, 34, 56, tzinfo=timezone(timedelta(hours=-5)))


def report():
    return {
        "assignment": {"id": 902, "course_id": 71, "name": "Vectors λ <proof>",
                       "html_url": None, "due_at": None, "points_possible": 20},
        "current_submission": {"attempt": 4, "score": 12, "grade": "12",
                               "grade_matches_current_submission": False},
        "history": {"returned": True, "records": [
            {"attempt": 2, "score": 0, "grade": "0",
             "submission_comments": [{"comment": "on second only"}]},
            {"attempt": 1, "score": None, "body": "<p>original first</p>", "late": False},
            {"attempt": 2, "url": "https://fixture.invalid/revision", "vendor": {"other": True}},
            {},
        ]},
        "submission_comments": [{"id": 88, "attempt": 4, "comment": "top-level only"},
                                {"id": 89, "comment": None, "media_comment": {"media_type": "audio"}}],
    }


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.elements = []
        self.href = None
        self.feed(content.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag == "a" and attrs.get("id") == "download-history":
            assert self.href is None
            self.href = attrs["href"]

    def normalized(self):
        assert self.href.startswith("data:application/json;base64,")
        return json.loads(base64.b64decode(self.href.split(",", 1)[1], validate=True))


def render(value):
    return export.render_submission_history_report(
        value, course_id="00071", assignment_id=902, generated_at=STAMP,
    )


def test_complete_report_preserves_duplicate_and_missing_attempts_without_attribution():
    original = report()
    before = deepcopy(original)
    content, summary = render(original)
    saved = Document(content).normalized()
    assert saved == before == original
    assert [row.get("attempt") for row in saved["history"]["records"]] == [2, 1, 2, None]
    assert "grade" not in saved["history"]["records"][1]
    assert "score" not in saved["history"]["records"][2]
    assert "submission_comments" not in saved["history"]["records"][3]
    assert saved["submission_comments"][0]["attempt"] == 4
    assert summary["requested_course_id"] == "71"
    assert summary["generated_at"] == "2026-10-08T17:34:56Z"
    assert summary["history_records_returned"] == 4
    assert b"not assigned to historical" in content
    assert b"earlier attempt" in content
    ids = [attrs.get("id") for _tag, attrs in Document(content).elements]
    assert all(ids.count(f"history-record-{index}") == 1 for index in range(1, 5))


@pytest.mark.parametrize("history,comments", [(None, None), ([], []), (None, []), ([], None)])
def test_unavailable_and_empty_associations_remain_distinct(history, comments):
    value = report()
    value["history"] = {"returned": history is not None, "records": history}
    value["submission_comments"] = comments
    content, summary = render(value)
    assert Document(content).normalized() == value
    assert summary["history_returned"] is (history is not None)
    assert summary["history_records_returned"] == (None if history is None else 0)
    assert summary["top_level_comments_returned"] == (None if comments is None else 0)
    assert (b"history is unavailable" in content) is (history is None)
    assert (b"empty history list" in content) is (history == [])
    assert (b"comments are unavailable" in content) is (comments is None)
    assert (b"empty top-level comment list" in content) is (comments == [])


@pytest.mark.parametrize("flag,phrase", [
    (True, b"Canvas reports that the grade matches"),
    (False, b"does not match the latest submission"),
    (None, b"No match is inferred"),
    ("unknown", b"No match is inferred"),
])
def test_current_grade_context_never_infers_a_match(flag, phrase):
    value = report()
    value["current_submission"]["grade_matches_current_submission"] = flag
    content, _summary = render(value)
    assert phrase in content
    assert Document(content).normalized()["history"] == value["history"]


def test_all_literal_values_and_extra_fields_survive_without_active_content():
    value = report()
    payload = "</pre><img src='https://never.invalid' onerror='alert(1)'><script>alert(1)</script>"
    value["assignment"]["name"] = payload + " λ"
    value["current_submission"]["body"] = payload
    value["current_submission"]["javascript:control"] = "javascript:alert('literal')"
    value["current_submission"]["control"] = "a\x00b\r\n\t\u0085\ud800"
    value["current_submission"]["large_integer"] = 2**100 + 1
    value["current_submission"]["\x00key"] = {"__proto__": {"literal": True}}
    value["history"]["future_history_metadata"] = {"available": False}
    value["future_report_field"] = [None, False, 0, "", [], {}]
    content, _summary = render(value)
    document = Document(content)
    assert document.normalized() == value
    assert str(2**100 + 1).encode() in content
    assert b"Additional history fields" in content and b"Additional report fields" in content
    assert all(tag not in {"script", "img", "iframe", "link", "form", "input", "object", "embed"}
               for tag, _attrs in document.elements)
    assert all(not any(name.startswith("on") for name in attrs)
               for _tag, attrs in document.elements)
    assert all(attrs["href"].startswith(("#", "data:application/json;base64,"))
               for _tag, attrs in document.elements if "href" in attrs)


@pytest.mark.parametrize("replacement", [
    None, [], {"returned": None, "records": None},
    {"returned": False, "records": []},
    {"returned": True, "records": None},
    {"returned": True, "records": [1]},
])
def test_malformed_history_refuses_instead_of_becoming_empty(replacement):
    value = report()
    value["history"] = replacement
    with pytest.raises(ValueError):
        render(value)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), (1, 2), {7: "integer key"}, b"bytes"])
def test_non_json_values_are_not_coerced(invalid):
    value = report()
    value["current_submission"]["extension"] = invalid
    with pytest.raises((TypeError, ValueError)):
        render(value)


def test_cyclic_data_refuses_and_does_not_mutate_the_report():
    value = report()
    loop = []
    loop.append(loop)
    value["current_submission"]["extension"] = loop
    with pytest.raises(ValueError, match="nesting"):
        render(value)
    assert loop[0] is loop


def test_limits_refuse_complete_large_values_without_truncating_them():
    value = report()
    text = "x" * export.MAX_REPORT_BYTES
    value["current_submission"]["body"] = text
    with pytest.raises(ValueError, match="4 MiB"):
        render(value)
    assert value["current_submission"]["body"] is text
    value["current_submission"]["body"] = "<" * (3 * 1024 * 1024)
    with pytest.raises(ValueError, match="16 MiB"):
        render(value)


def test_builder_calls_the_existing_reader_once_and_retains_requested_identity_separately():
    value = report()
    value["assignment"]["course_id"] = None
    value["assignment"]["id"] = 333
    calls = []

    class Reader:
        def submission_history(self, course, assignment):
            calls.append((course, assignment))
            return value

    content, summary = export.build_submission_history_report(
        Reader(), "00071", "000902", generated_at=STAMP,
    )
    assert calls == [("71", "902")]
    assert Document(content).normalized() == value
    assert summary["requested_course_id"] == "71"
    assert summary["requested_assignment_id"] == "902"
    assert b"Requested selectors above remain separate" in content


@pytest.mark.parametrize("stamp", [
    datetime(2026, 10, 8),  # noqa: DTZ001 - intentional naive-time refusal
    "2026-10-08", datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=14))),
])
def test_invalid_creation_time_refuses_before_read(stamp):
    class NoRead:
        def submission_history(self, *_args):
            raise AssertionError("Invalid metadata must not trigger a source read")

    with pytest.raises(ValueError):
        export.build_submission_history_report(NoRead(), 71, 902, generated_at=stamp)


def install_reader(monkeypatch, value, failure=None):
    calls = []

    class Reader:
        def __init__(self, client):
            self.client = client

        def submission_history(self, course, assignment):
            calls.append((course, assignment))
            if failure:
                raise failure
            return deepcopy(value)

        def close(self):
            self.client.close()

    monkeypatch.setattr(api_module, "CanvasAPI", Reader)
    return calls


def test_cli_publishes_once_and_refuses_existing_file_before_a_read(monkeypatch, tmp_path, capsys):
    calls = install_reader(monkeypatch, report())
    target = tmp_path / "history.html"
    arguments = ["export-submission-history", "71", "902", "--out", str(target),
                 "--base-url", "https://fixture.invalid", "--token", "synthetic-test"]
    cli.main(arguments)
    captured = capsys.readouterr()
    assert captured.err == "" and json.loads(captured.out)["ok"] is True
    assert calls == [("71", "902")]
    before = target.read_bytes()
    assert Document(before).normalized() == report()
    with pytest.raises(SystemExit) as exit_:
        cli.main(arguments)
    assert exit_.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == "" and json.loads(captured.err)["error"] == "FileExistsError"
    assert calls == [("71", "902")] and target.read_bytes() == before


def test_cli_source_failure_has_no_file_or_success_output(monkeypatch, tmp_path, capsys):
    from canvaspilot.client import CanvasAuthError

    calls = install_reader(monkeypatch, report(), CanvasAuthError("authored source unavailable"))
    target = tmp_path / "history.html"
    with pytest.raises(SystemExit) as exit_:
        cli.main(["export-submission-history", "71", "902", "--out", str(target),
                  "--base-url", "https://fixture.invalid", "--token", "synthetic-test"])
    assert exit_.value.code == 1 and calls == [("71", "902")]
    captured = capsys.readouterr()
    assert captured.out == "" and json.loads(captured.err)["error"] == "CanvasAuthError"
    assert not target.exists()

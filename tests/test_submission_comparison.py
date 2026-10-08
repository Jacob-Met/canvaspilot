"""Selected-record fidelity, useful text reading, and protected report publication."""

import base64
import json
import re
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path

import pytest

from canvaspilot import submission_comparison as comparison
from canvaspilot.submission_history import build_submission_history

FIXTURE = Path(__file__).parent / "fixtures" / "submission_comparison.json"


def authored_history():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return build_submission_history(fixture["assignment"], fixture["submission"])


def selected(before=None, after=None, **kwargs):
    history = {
        "assignment": {"id": 902, "course_id": 71, "name": "Revision · 波"},
        "current_submission": {} if after is None else after,
        "history": {"returned": True, "records": [{} if before is None else before]},
    }
    return comparison.build_submission_comparison(
        history, course_id="71", assignment_id="902",
        before="history:1", after="current", **kwargs,
    )


def download(html):
    match = re.search(r'href="data:application/json;base64,([^"]+)"', html)
    assert match, "The actual report must carry its exact selected-record download"
    return json.loads(base64.b64decode(match[1], validate=True))


def section(html, name):
    return html.split(f'<section id="{name}">', 1)[1].split("</section>", 1)[0]


class ReturnedAPI:
    def __init__(self, history=None):
        self.history = authored_history() if history is None else history
        self.calls = []

    def submission_history(self, course_id, assignment_id):
        self.calls.append((course_id, assignment_id))
        return self.history


def test_selection_keeps_duplicate_positions_exact_and_does_not_enrich():
    history = authored_history()
    untouched = deepcopy(history)
    result = comparison.build_submission_comparison(
        history, course_id="00071", assignment_id="0902",
        before="history:2", after="history:1",
    )
    assert result["request"] == {"course_id": "71", "assignment_id": "902"}
    assert result["before"] == {"selector": "history:2", "record": history["history"]["records"][1]}
    assert result["after"] == {"selector": "history:1", "record": history["history"]["records"][0]}
    assert result["before"]["record"]["attempt"] == result["after"]["record"]["attempt"] == 2
    assert result["before"]["record"]["submitted_at"] > result["after"]["record"]["submitted_at"]
    assert "submission_comments" not in result
    assert "grade_matches_current_submission" not in result["after"]["record"]
    assert result["after"]["record"]["record_local_comment"]["attempt"] == 2
    assert result["after"]["record"]["attachments"][0]["id"] == 9007199254740993
    result["after"]["record"]["attachments"][0]["filename"] = "local-only"
    assert history == untouched


@pytest.mark.parametrize("selector", [
    "", "CURRENT", " current", "current ", "history:0", "history:01",
    "history:-1", "history:+1", "history:1.0", "history: 1",
    "history:１", "history:1\n",
])
def test_invalid_selectors_fail_before_read_or_output(tmp_path, selector):
    api = ReturnedAPI()
    with pytest.raises(ValueError, match="current or history:N"):
        comparison.export_submission_comparison(
            api, 71, 902, before=selector, after="current", out=tmp_path / "report.html",
        )
    assert api.calls == []
    assert list(tmp_path.iterdir()) == []


def test_identical_selectors_refuse_but_equal_records_at_different_positions_work(tmp_path):
    api = ReturnedAPI()
    with pytest.raises(ValueError, match="different selectors"):
        comparison.export_submission_comparison(
            api, 71, 902, before="history:1", after="history:1", out=tmp_path / "report.html",
        )
    assert api.calls == []
    model = selected({"body": "same"}, {"body": "same"})
    assert model["before"]["selector"] != model["after"]["selector"]
    assert model["before"]["record"] == model["after"]["record"]


@pytest.mark.parametrize("value", [None, [], [{"body": "one"}]])
def test_unavailable_empty_and_out_of_range_history_are_not_substituted(value):
    history = authored_history()
    history["history"] = {"returned": value is not None, "records": value}
    with pytest.raises(ValueError, match="unavailable|outside"):
        comparison.build_submission_comparison(
            history, course_id=71, assignment_id=902, before="history:2", after="current",
        )


def test_arbitrarily_long_index_has_a_controlled_range_error():
    with pytest.raises(ValueError, match="outside the 3 returned history records"):
        comparison.build_submission_comparison(
            authored_history(), course_id=71, assignment_id=902,
            before="history:" + "9" * 5_000, after="current",
        )


@pytest.mark.parametrize("location,field,value", [
    ("assignment", "id", 903), ("assignment", "course_id", "72"),
    ("before", "assignment_id", 903), ("after", "course_id", 72),
    ("before", "assignment_id", False),
])
def test_supplied_identity_mismatch_refuses(location, field, value):
    history = authored_history()
    target = (history["assignment"] if location == "assignment" else
              history["current_submission"] if location == "after" else
              history["history"]["records"][0])
    target[field] = value
    with pytest.raises(ValueError, match="does not match|invalid"):
        comparison.build_submission_comparison(
            history, course_id=71, assignment_id=902, before="history:1", after="current",
        )


def test_missing_identity_stays_unknown_and_reported_numeric_spelling_is_preserved():
    before = {"assignment_id": "0902", "course_id": None}
    after = {"body": "new"}
    model = selected(before, after)
    assert model["before"]["record"] == before
    assert model["after"]["record"] == after
    html = comparison.render_submission_comparison(model)
    assert "Omitted — key not returned" in html
    assert "0902" in html


@pytest.mark.parametrize("before,after,left_label,right_label", [
    ({}, {"body": None}, "Omitted — key not returned", "Null — explicitly returned"),
    ({"body": ""}, {"body": []}, "Blank string", "Empty list"),
    ({"body": {}}, {"body": False}, "Empty object", "false"),
])
def test_omitted_null_blank_and_unsupported_body_values_remain_distinct(before, after, left_label, right_label):
    model = selected(before, after)
    html = comparison.render_submission_comparison(model)
    body = section(html, "body")
    assert "Text highlighting is unavailable" in body
    assert left_label in body and right_label in body
    packet = download(html)
    assert packet["before"]["record"] == before
    assert packet["after"]["record"] == after
    assert ("body" in packet["before"]["record"]) == ("body" in before)


def test_false_zero_empty_list_and_ordered_attachment_metadata_are_type_sensitive():
    model = selected(
        {"url": False, "attachments": [{"id": 2}, {"id": 1}], "media_comment": []},
        {"url": 0, "attachments": [{"id": 1}, {"id": 2}], "media_comment": None},
    )
    html = comparison.render_submission_comparison(model)
    assert "Different returned values" in section(html, "url")
    assert "Different returned values" in section(html, "attachments")
    assert "Different returned values" in section(html, "media")
    packet = download(html)
    assert packet["before"]["record"]["url"] is False
    assert type(packet["after"]["record"]["url"]) is int
    assert packet["before"]["record"]["attachments"] == [{"id": 2}, {"id": 1}]
    assert packet["before"]["record"]["media_comment"] == []
    assert packet["after"]["record"]["media_comment"] is None


def test_readable_changes_and_matching_text_different_markup_are_named():
    html = comparison.render_submission_comparison(selected(
        {"body": "<p>Keep</p><p>period 3</p>"},
        {"body": "<p>Keep</p><p>period 2</p>"},
    ))
    body = section(html, "body")
    assert 'class="diff-line removed"' in body and "period 3" in body
    assert 'class="diff-line added"' in body and "period 2" in body
    assert 'class="diff-line context"' in body and "Keep" in body
    matching = comparison.render_submission_comparison(selected(
        {"body": "<p>Same &amp; literal</p>"},
        {"body": "<div>Same &amp; literal</div>"},
    ))
    assert "Readable text matches, but the exact body source differs" in matching
    assert "&lt;p&gt;Same &amp;amp; literal&lt;/p&gt;" in matching


def test_reading_aid_preserves_text_without_loading_embedded_content():
    body = (
        "<h1>Title</h1><p>café é &amp; 波<br>second line</p>"
        '<img alt="A useful diagram" src="https://probe.invalid/image">'
        "<script>HIDDEN_SCRIPT</script><style>HIDDEN_STYLE</style>"
        "<template><p>HIDDEN_TEMPLATE</p></template><noscript>HIDDEN_NOSCRIPT</noscript>"
    )
    text = comparison.readable_body(body)
    assert text.startswith("Title\n")
    assert "café é & 波\nsecond line" in text
    assert "[Image: A useful diagram]" in text
    assert "HIDDEN" not in text


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_report_source_is_inert_and_download_preserves_large_integer_unicode_and_controls():
    history = authored_history()
    history["current_submission"]["literal_controls"] = "\x00\x1b\u0085\ud800\u202e"
    model = comparison.build_submission_comparison(
        history, course_id=71, assignment_id=902, before="history:1", after="current",
    )
    html = comparison.render_submission_comparison(model)
    html.encode("utf-8")
    parsed = Elements()
    parsed.feed(html)
    assert not any(tag in {"script", "img", "iframe", "object", "embed", "link", "base"} for tag, _ in parsed.elements)
    assert all(not any(key.startswith("on") for key in attrs) for _, attrs in parsed.elements)
    assert all(attrs.get("href", "").startswith(("#", "data:application/json;base64,"))
               for tag, attrs in parsed.elements if tag == "a")
    packet = download(html)
    assert packet == model
    assert packet["after"]["record"]["literal_controls"] == "\x00\x1b\u0085\ud800\u202e"
    assert packet["after"]["record"]["attachments"][0]["id"] == 9007199254740993
    assert "\\ud800" in html and "\\u202e" in html
    assert "https://probe.example.invalid/current.png" in html
    assert "Matching metadata cannot establish equal file bytes" in html


@pytest.mark.parametrize("kind", ["lines", "characters", "line_pairs"])
def test_large_changed_text_is_complete_and_explicitly_not_highlighted(kind):
    if kind == "lines":
        left, right = "\n".join(f"old {i}" for i in range(2_001)), "new"
    elif kind == "characters":
        left, right = "a" * 250_001, "new"
    else:
        left = "\n".join(f"old {i}" for i in range(1_001))
        right = "\n".join(f"new {i}" for i in range(1_000))
    left += "\nCOMPLETE-LEFT-TAIL"
    right += "\nCOMPLETE-RIGHT-TAIL"
    html = comparison.render_submission_comparison(selected({"body": left}, {"body": right}))
    body = section(html, "body")
    assert "Highlighting was not computed for this pair" in body
    assert 'class="diff-line' not in body
    assert "COMPLETE-LEFT-TAIL" in body and "COMPLETE-RIGHT-TAIL" in body
    assert download(html)["before"]["record"]["body"] == left
    assert download(html)["after"]["record"]["body"] == right


@pytest.mark.parametrize("invalid", [float("nan"), (1, 2), {1: "non-string key"}])
def test_non_json_record_values_are_refused(invalid):
    with pytest.raises(ValueError, match="JSON|keys"):
        selected({"future": invalid}, {})


def test_selected_source_limit_refuses_before_publication(tmp_path):
    api = ReturnedAPI()
    api.history["current_submission"]["body"] = "x" * comparison.MAX_SOURCE_BYTES
    with pytest.raises(ValueError, match="2 MiB"):
        comparison.export_submission_comparison(
            api, 71, 902, before="history:1", after="current", out=tmp_path / "report.html",
        )
    assert api.calls == [("71", "902")]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["file", "directory", "dangling_symlink", "missing_parent"])
def test_protected_outputs_fail_before_api_access(tmp_path, kind):
    out = tmp_path / "report.html"
    if kind == "file":
        out.write_bytes(b"existing content")
    elif kind == "directory":
        out.mkdir()
    elif kind == "dangling_symlink":
        out.symlink_to(tmp_path / "absent")
    else:
        out = tmp_path / "missing" / "report.html"
    api = ReturnedAPI()
    with pytest.raises(OSError):
        comparison.export_submission_comparison(
            api, 71, 902, before="history:1", after="current", out=out,
        )
    assert api.calls == []
    if kind == "file":
        assert out.read_bytes() == b"existing content"
    elif kind == "dangling_symlink":
        assert out.is_symlink() and not out.exists()


def test_atomic_publication_preserves_a_target_created_after_preflight(tmp_path, monkeypatch):
    out = tmp_path / "raced.html"
    actual_link = comparison.os.link

    def racing_link(source, target):
        Path(target).write_bytes(b"concurrent owner")
        return actual_link(source, target)

    monkeypatch.setattr(comparison.os, "link", racing_link)
    with pytest.raises(FileExistsError):
        comparison.write_submission_comparison(out, "<!doctype html>complete")
    assert out.read_bytes() == b"concurrent owner"
    assert list(tmp_path.iterdir()) == [out]


def test_write_failure_leaves_no_partial_target_or_temporary_file(tmp_path, monkeypatch):
    def full_disk(_fd):
        raise OSError("authored full-disk refusal")

    monkeypatch.setattr(comparison.os, "fsync", full_disk)
    with pytest.raises(OSError, match="full-disk"):
        comparison.write_submission_comparison(tmp_path / "report.html", "complete")
    assert list(tmp_path.iterdir()) == []


def test_success_reads_api_once_and_writes_complete_exact_report(tmp_path):
    api = ReturnedAPI()
    out = tmp_path / "比較.html"
    result = comparison.export_submission_comparison(
        api, "00071", "0902", before="history:2", after="current", out=out,
    )
    assert api.calls == [("71", "902")]
    assert result == {"output": str(out), "before": "history:2", "after": "current",
                      "history_records_returned": 3}
    html = out.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>") and html.endswith("</html>")
    assert download(html)["before"]["record"] == api.history["history"]["records"][1]
    assert download(html)["after"]["record"] == api.history["current_submission"]
    assert list(tmp_path.iterdir()) == [out]

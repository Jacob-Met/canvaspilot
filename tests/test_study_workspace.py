"""Independent expected behavior of the assignment workspace exporter."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from canvaspilot.study_workspace import (
    BRIEF_FIELDS,
    MAX_SNAPSHOT_BYTES,
    build_study_workspace,
    canvas_id,
    validate_selection,
    write_study_workspace,
)


def brief(course="17", assignment="81"):
    return {
        "course_id": course,
        "assignment_id": assignment,
        "title": "Question & evidence",
        "due_at": None,
        "points_possible": 0,
        "submission_types": [],
        "prompt": "Explain the evidence in your own words.",
        "html_url": None,
        "rubric": None,
        "rubric_settings": None,
        "use_rubric_for_grading": None,
        "rubric_warnings": [],
    }


def envelope(page):
    match = re.search(
        r'<script id="workspace-data" type="application/json">(.*?)</script>',
        page.decode(),
        re.DOTALL,
    )
    assert match
    return json.loads(match.group(1))


@pytest.mark.parametrize(
    "value", ["1", 1, "00081", "9007199254740993", "9223372036854775807"]
)
def test_selection_preserves_decimal_ids_without_browser_rounding(value):
    assert canvas_id(value) == str(int(value))
    assert validate_selection("17", [value]) == ("17", [str(int(value))])


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        0,
        -1,
        "0",
        "+1",
        " 1",
        "１",
        "١",
        "1/2",
        "1.0",
        "",
        "9223372036854775808",
    ],
)
def test_invalid_id_admission(value):
    with pytest.raises(ValueError):
        canvas_id(value)


@pytest.mark.parametrize(
    "selection",
    [[], ["1"] * 2, ["1", "01"], [str(i) for i in range(1, 27)], ["1", "wrong"]],
)
def test_entire_selection_is_validated_before_any_reader_call(selection):
    seen = []
    api = SimpleNamespace(assignment_brief=lambda *args: seen.append(args))
    with pytest.raises(ValueError):
        build_study_workspace(
            api, "17", selection, source_base_url="https://canvas.fixture.invalid"
        )
    assert seen == []


@pytest.mark.parametrize(
    "base",
    [
        "https://user:password@canvas.fixture.invalid",
        "https://canvas.fixture.invalid/?token=x",
        "https://canvas.fixture.invalid/#secret",
        "javascript:alert(1)",
        "//canvas.fixture.invalid",
        "https://canvas.fixture.invalid:bad",
        "https://canvas.fixture.invalid/ bad",
    ],
)
def test_bad_source_url_refuses_before_read(base):
    calls = []
    with pytest.raises(ValueError):
        build_study_workspace(
            SimpleNamespace(assignment_brief=lambda *args: calls.append(args)),
            "17",
            ["81"],
            source_base_url=base,
        )
    assert not calls


def test_snapshot_retains_all_brief_fields_and_freezes_reused_caller_objects():
    shared = brief()
    first = copy.deepcopy(shared)
    calls = []

    def reader(course, assignment):
        calls.append((course, assignment))
        shared["assignment_id"] = assignment
        shared["title"] = "Second" if len(calls) == 2 else shared["title"]
        return shared

    page, report = build_study_workspace(
        SimpleNamespace(assignment_brief=reader),
        "17",
        ["81", "82"],
        source_base_url="https://canvas.fixture.invalid",
        exported_at="2026-10-08T00:00:00+00:00",
    )
    doc = envelope(page)
    source = json.loads(doc["source"])
    assert calls == [("17", "81"), ("17", "82")]
    assert source["assignments"][0]["brief"] == first
    assert set(source["assignments"][0]["brief"]) == BRIEF_FIELDS
    assert source["assignments"][1]["brief"]["title"] == "Second"
    assert hashlib.sha256(doc["source"].encode()).hexdigest() == doc["source_sha256"]
    assert doc["source_sha256"] == report["snapshot_sha256"]
    assert source["source_boundary"]["upstream_response_identity"] == "not_observed"
    assert doc["state"] == {
        "source_sha256": doc["source_sha256"],
        "assignments": {
            "17:81": {"notes": "", "reviewed": False},
            "17:82": {"notes": "", "reviewed": False},
        },
    }


def test_literal_source_cannot_end_data_script_or_replace_template_tokens():
    row = brief()
    row["title"] = (
        "</script><script>window.pwned=1</script> __SCRIPT__ __STYLE__ & \u2028"
    )
    row["prompt"] = '<img src="https://off-origin.invalid/x" onerror="window.pwned=1">'
    page, _ = build_study_workspace(
        SimpleNamespace(assignment_brief=lambda *args: row),
        "17",
        ["81"],
        source_base_url="https://canvas.fixture.invalid",
    )
    doc = envelope(page)
    assert json.loads(doc["source"])["assignments"][0]["brief"] == row
    assert page.count(b"<script") == 2
    assert b"<script>window.pwned" not in page
    assert b"connect-src 'none'" in page and b"form-action 'none'" in page
    assert "Content-Security-Policy" in page.decode()


@pytest.mark.parametrize(
    "change",
    [
        {"assignment_id": "82"},
        {"course_id": "18"},
        {"title": {"unexpected": True}},
        {"submission_types": "online_upload"},
        {"points_possible": True},
        {"points_possible": float("nan")},
        {"points_possible": 10**300},
        {"rubric_warnings": "warning"},
        {"rubric": {}},
        {"submission": {"body": "unowned"}},
    ],
)
def test_unusable_or_expanded_brief_refuses_before_export(change):
    row = brief()
    row.update(change)
    with pytest.raises((ValueError, TypeError)):
        build_study_workspace(
            SimpleNamespace(assignment_brief=lambda *args: row),
            "17",
            ["81"],
            source_base_url="https://canvas.fixture.invalid",
        )


def test_snapshot_byte_limit_applies_to_utf8_not_character_count():
    row = brief()
    row["prompt"] = "あ" * (MAX_SNAPSHOT_BYTES // 3 + 1)
    with pytest.raises(ValueError, match="4 MiB"):
        build_study_workspace(
            SimpleNamespace(assignment_brief=lambda *args: row),
            "17",
            ["81"],
            source_base_url="https://canvas.fixture.invalid",
        )


def test_complete_new_file_and_existing_targets_are_preserved(tmp_path):
    path = tmp_path / "workspace.html"
    write_study_workspace(path, b"complete bytes")
    before = path.stat()
    with pytest.raises(FileExistsError):
        write_study_workspace(path, b"replacement")
    assert path.read_bytes() == b"complete bytes"
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert not list(tmp_path.glob(".canvaspilot-study-*"))


def test_broken_symlink_is_an_existing_target(tmp_path):
    path = tmp_path / "workspace.html"
    path.symlink_to(tmp_path / "missing")
    with pytest.raises(FileExistsError):
        write_study_workspace(path, b"replacement")
    assert path.is_symlink() and not path.exists()


def test_late_destination_race_never_replaces_winner(tmp_path, monkeypatch):
    path = tmp_path / "workspace.html"
    real_link = os.link

    def competing_link(src, dst):
        Path(dst).write_bytes(b"other writer wins")
        return real_link(src, dst)

    monkeypatch.setattr(os, "link", competing_link)
    with pytest.raises(FileExistsError):
        write_study_workspace(path, b"our complete bytes")
    assert path.read_bytes() == b"other writer wins"
    assert not list(tmp_path.glob(".canvaspilot-study-*"))


def test_failure_before_publication_leaves_no_partial_output(tmp_path, monkeypatch):
    path = tmp_path / "workspace.html"

    def failed_flush(fd):
        raise OSError("injected fsync failure")

    monkeypatch.setattr(os, "fsync", failed_flush)
    with pytest.raises(OSError, match="injected"):
        write_study_workspace(path, b"would be complete")
    assert not path.exists() and not list(tmp_path.glob(".canvaspilot-study-*"))

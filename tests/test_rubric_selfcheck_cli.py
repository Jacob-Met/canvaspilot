"""Actual native CLI/HTTP receiving for export-selfcheck, without a Canvas account."""
from __future__ import annotations

import json
import os
import subprocess
import sys

from test_rubric_selfcheck import envelope
from test_study_workspace_cli import fixture_server


def command(base, output, ids=("81", "82", "83")):
    env = os.environ.copy(); env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "canvaspilot.cli", "export-selfcheck", "17", *ids,
         "--base-url", base, "--token", "study-fixture-token", "--out", str(output)],
        capture_output=True, text=True, env=env, timeout=30, check=False,
    )


def test_actual_cli_retains_native_briefs_and_only_reads_explicit_selection(tmp_path):
    with fixture_server() as (base, requests):
        output = tmp_path / "selfcheck.html"
        result = command(base, output)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["assignment_ids"] == ["81", "82", "83"]
    doc = envelope(output.read_bytes()); source = json.loads(doc["source"])
    assert source["reader"] == "CanvasAPI.assignment_brief"
    assert source["source_boundary"]["upstream_response_identity"] == "not_observed"
    assert len(requests) == 3 and all(x["method"] == "GET" for x in requests)
    assert source["assignments"][0]["brief"]["rubric"][0]["ratings"][2]["points"] == 0


def test_preflight_existing_output_and_duplicate_selection_make_no_request(tmp_path):
    existing = tmp_path / "keep.html"; existing.write_bytes(b"keep this exact file")
    with fixture_server() as (base, requests):
        occupied = command(base, existing)
        duplicate = command(base, tmp_path / "absent.html", ("81", "081"))
    assert occupied.returncode == duplicate.returncode == 1
    assert requests == [] and existing.read_bytes() == b"keep this exact file"
    assert not (tmp_path / "absent.html").exists()


def test_failed_later_read_leaves_no_partial_report(tmp_path):
    with fixture_server(fail_assignment="82") as (base, requests):
        output = tmp_path / "absent.html"
        result = command(base, output)
    assert result.returncode == 1 and not output.exists() and result.stdout == ""
    assert len(requests) == 2 and all(x["method"] == "GET" for x in requests)


def test_dangling_output_symlink_is_preserved_without_request(tmp_path):
    target = tmp_path / "missing.html"; link = tmp_path / "linked.html"; link.symlink_to(target)
    with fixture_server() as (base, requests):
        result = command(base, link)
    assert result.returncode == 1 and requests == []
    assert link.is_symlink() and not target.exists()


def test_help_is_available_without_a_live_client():
    result = subprocess.run([sys.executable, "-m", "canvaspilot.cli", "export-selfcheck", "--help"],
                            capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0 and "--out" in result.stdout

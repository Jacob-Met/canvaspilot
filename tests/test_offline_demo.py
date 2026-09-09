import copy
import json
from unittest.mock import patch

import pytest

from canvaspilot.offline_demo import FIXTURE, OfflineOnlyClient, build_review, main


def test_demo_uses_no_http_or_browser_transport(monkeypatch):
    monkeypatch.setenv("CANVAS_API_TOKEN", "synthetic-not-a-secret")
    with patch("canvaspilot.client.broker_health", side_effect=AssertionError("network")), \
         patch("canvaspilot.client.broker_fetch", side_effect=AssertionError("network")), \
         patch("canvaspilot.client.httpx.Client", side_effect=AssertionError("network")):
        result = build_review()
    assert len(result["courses"]) == 2
    assert len(result["assignment_briefs"]) == 2
    assert result["account_required"] is False


def test_demo_preserves_unknown_date_and_plain_prompt():
    r = build_review()
    assert r["unknowns"] == [{"assignment_id": 1002, "reason": "due_date_not_supplied"}]
    assert r["assignment_briefs"][0]["prompt"] == "Identify the controls and limitations."
    assert r["assignment_briefs"][0]["due_at"] == "2026-09-18T18:00:00Z"


def test_demo_is_deterministic_and_keeps_fixture_immutable():
    before = copy.deepcopy(FIXTURE)
    assert build_review() == build_review()
    assert FIXTURE == before


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_demo_denies_all_write_methods(method):
    with OfflineOnlyClient() as client, pytest.raises(ValueError, match="never performs write"):
        client.request(method, "/api/v1/courses")


def test_demo_rejects_unknown_route_without_network():
    with OfflineOnlyClient() as client, pytest.raises(KeyError, match="No exact synthetic route"):
        client.request("GET", "/api/v1/courses/999/assignments")


def test_demo_stdout_is_valid_json(capsys):
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out) == build_review()


def test_demo_does_not_replace_existing_output(tmp_path):
    p = tmp_path / "review.json"
    assert main(["--out", str(p)]) == 0
    before = p.read_bytes()
    assert main(["--out", str(p)]) == 2
    assert p.read_bytes() == before


def test_demo_reports_missing_parent(tmp_path):
    assert main(["--out", str(tmp_path / "missing" / "review.json")]) == 2

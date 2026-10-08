"""Exercise the supplied rubric through the public API, CLI and MCP dispatcher."""

import asyncio
import copy
import json
from pathlib import Path

import pytest

from canvaspilot import client as client_module
from canvaspilot import mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.cli import main as cli_main
from canvaspilot.client import CanvasClient

ASSIGNMENT = json.loads(
    (Path(__file__).parent / "fixtures/assignment_rubric.json").read_text(encoding="utf-8")
)
ROUTE = "/api/v1/courses/17/assignments/311"
ORDINARY_BRIEF = {
    "title": ASSIGNMENT["name"],
    "due_at": ASSIGNMENT["due_at"],
    "points_possible": ASSIGNMENT["points_possible"],
    "submission_types": ASSIGNMENT["submission_types"],
    "prompt": "Write a short analysis. Follow the attached grading rubric.",
    "html_url": ASSIGNMENT["html_url"],
    "course_id": "17",
    "assignment_id": "311",
}


@pytest.fixture(params=["api", "cli", "mcp"])
def read_brief(request, monkeypatch, tmp_path, capsys):
    """Keep the real receiver/client; substitute only its external fixture input."""
    def forbidden(*args, **kwargs):
        raise AssertionError("A fixture brief must not reach an HTTP transport or broker")

    monkeypatch.setattr(client_module, "broker_health", forbidden)
    monkeypatch.setattr(client_module, "broker_fetch", forbidden)
    monkeypatch.setattr(client_module.httpx, "Client", forbidden)
    monkeypatch.setattr(client_module.httpx, "request", forbidden)

    def read(assignment):
        calls = []
        fixture = {"routes": {f"GET {ROUTE}": assignment}}

        class RecordedClient(CanvasClient):
            def request(self, method, path, **kwargs):
                calls.append((method, path, copy.deepcopy(kwargs)))
                return super().request(method, path, **kwargs)

        kwargs = {"fixture": fixture, "token": "", "profile": tmp_path,
                  "base_url": "https://canvas.example.invalid"}
        if request.param == "cli":
            def fixture_client(**client_kwargs):
                return RecordedClient(fixture=fixture, **client_kwargs)

            monkeypatch.setattr(client_module, "CanvasClient", fixture_client)
            cli_main(["brief", "17", "311", "--token", "", "--profile", str(tmp_path),
                      "--base-url", "https://canvas.example.invalid"])
            payload = json.loads(capsys.readouterr().out)
        else:
            with CanvasAPI(RecordedClient(**kwargs)) as api:
                if request.param == "mcp":
                    monkeypatch.setattr(mcp_server, "_api", api)
                    response = asyncio.run(mcp_server.mcp.call_tool(
                        "canvas_assignment_brief", {"course_id": "17", "assignment_id": "311"}
                    ))
                    assert not response.is_error
                    assert len(response.content) == 1
                    payload = json.loads(response.content[0].text)
                else:
                    payload = api.assignment_brief("17", "311")
        assert calls == [("GET", ROUTE, {"params": {"include[]": ["submission"]}})]
        # All three paths must return an ordinary JSON payload, including edge points.
        json.dumps(payload, allow_nan=False)
        return payload

    return read


def test_canonical_rubric_survives_each_public_receiver(read_brief):
    original = copy.deepcopy(ASSIGNMENT)
    result = read_brief(ASSIGNMENT)
    assert {key: result[key] for key in ORDINARY_BRIEF} == ORDINARY_BRIEF
    assert result["rubric"] == ASSIGNMENT["rubric"]
    assert result["rubric_settings"] == ASSIGNMENT["rubric_settings"]
    assert result["use_rubric_for_grading"] is False
    assert result["rubric_warnings"] == []
    assert ASSIGNMENT == original


@pytest.mark.parametrize("supplied", ["absent", None, []])
def test_no_rubric_does_not_invent_requirements(read_brief, supplied):
    assignment = {key: value for key, value in ASSIGNMENT.items()
                  if key not in {"rubric", "rubric_settings", "use_rubric_for_grading"}}
    assignment["due_at"] = None
    if supplied != "absent":
        assignment["rubric"] = supplied
    result = read_brief(assignment)
    expected = [] if supplied == [] else None
    assert result["rubric"] == expected
    assert result["rubric_settings"] is None
    assert result["use_rubric_for_grading"] is None
    assert result["rubric_warnings"] == []
    assert result["due_at"] is None
    assert result["prompt"] == ORDINARY_BRIEF["prompt"]
    assert result["html_url"] == ORDINARY_BRIEF["html_url"]


@pytest.mark.parametrize("supplied", [{"description": "not a list"}, "bad", False, 17])
def test_malformed_optional_containers_preserve_the_brief(read_brief, supplied):
    assignment = copy.deepcopy(ASSIGNMENT)
    assignment.update(rubric=supplied, rubric_settings=["bad"], use_rubric_for_grading="false")
    result = read_brief(assignment)
    assert {key: result[key] for key in ORDINARY_BRIEF} == ORDINARY_BRIEF
    assert result["rubric"] is None
    assert result["rubric_settings"] is None
    assert result["use_rubric_for_grading"] is None
    for path in ("rubric:", "rubric_settings:", "use_rubric_for_grading:"):
        assert any(warning.startswith(path) for warning in result["rubric_warnings"])


def test_malformed_neighbors_and_fields_are_isolated(read_brief):
    assignment = copy.deepcopy(ASSIGNMENT)
    healthy = copy.deepcopy(assignment["rubric"][0])
    damaged = {
        "id": "damaged", "description": "Keep this supplied description", "points": "twelve",
        "criterion_use_range": "false", "ignore_for_scoring": False,
        "ratings": [None, "broken", {"id": "bad", "description": ["wrong type"], "points": True},
                    copy.deepcopy(healthy["ratings"][1])],
    }
    assignment["rubric"] = [None, "broken", {}, damaged, healthy]
    original = copy.deepcopy(assignment)
    result = read_brief(assignment)
    assert result["rubric"][-1] == healthy
    retained = result["rubric"][0]
    assert retained["id"] == "damaged"
    assert retained["description"] == damaged["description"]
    assert "points" not in retained
    assert "criterion_use_range" not in retained
    assert retained["ignore_for_scoring"] is False
    assert retained["ratings"] == [{"id": "bad"}, healthy["ratings"][1]]
    assert any("rubric[3].ratings[2].points:" in warning for warning in result["rubric_warnings"])
    assert any("rubric[3].points:" in warning for warning in result["rubric_warnings"])
    assert result["prompt"] == ORDINARY_BRIEF["prompt"]
    assert assignment == original


def test_missing_and_null_criterion_fields_stay_unknown(read_brief):
    assignment = copy.deepcopy(ASSIGNMENT)
    assignment["rubric"] = [{"description": "A supplied qualitative requirement"},
                            {"id": "optional", "points": None, "ratings": None}]
    result = read_brief(assignment)
    assert result["rubric"] == assignment["rubric"]
    assert result["rubric_warnings"] == []


@pytest.mark.parametrize("ratings", [{"id": "not an array"}, "broken", 4])
def test_malformed_ratings_keep_the_criterion(read_brief, ratings):
    assignment = copy.deepcopy(ASSIGNMENT)
    assignment["rubric"][0]["ratings"] = ratings
    result = read_brief(assignment)
    assert result["rubric"][0]["id"] == "evidence"
    assert result["rubric"][0]["points"] == 12
    assert result["rubric"][0]["ratings"] is None
    assert result["rubric"][1] == assignment["rubric"][1]
    assert any("rubric[0].ratings:" in warning for warning in result["rubric_warnings"])


@pytest.mark.parametrize("use_for_grading", [True, False, None])
def test_grading_and_display_flags_are_supplied_data(read_brief, use_for_grading):
    assignment = copy.deepcopy(ASSIGNMENT)
    assignment["use_rubric_for_grading"] = use_for_grading
    assignment["rubric_settings"].update(hide_points=True, hide_score_total=False,
                                        free_form_criterion_comments=True)
    result = read_brief(assignment)
    assert result["use_rubric_for_grading"] is use_for_grading
    assert result["rubric_settings"] == assignment["rubric_settings"]
    assert result["rubric"] == assignment["rubric"]
    assert result["points_possible"] == 20
    assert result["rubric_settings"]["points_possible"] == "12"
    assert result["rubric_warnings"] == []


@pytest.mark.parametrize("points", [True, float("inf"), float("nan"), "12"])
def test_invalid_points_do_not_poison_json_or_neighbor_ratings(read_brief, points):
    assignment = copy.deepcopy(ASSIGNMENT)
    assignment["rubric"][0]["points"] = points
    result = read_brief(assignment)
    assert "points" not in result["rubric"][0]
    assert result["rubric"][0]["ratings"] == assignment["rubric"][0]["ratings"]
    assert any("rubric[0].points:" in warning for warning in result["rubric_warnings"])


def test_large_integer_points_are_not_forced_through_float(read_brief):
    assignment = copy.deepcopy(ASSIGNMENT)
    assignment["rubric"][0]["points"] = 10 ** 400
    result = read_brief(assignment)
    assert result["rubric"][0]["points"] == 10 ** 400
    assert result["rubric_warnings"] == []


def test_brief_rubric_and_settings_do_not_alias_the_input(read_brief):
    assignment = copy.deepcopy(ASSIGNMENT)
    original = copy.deepcopy(assignment)
    result = read_brief(assignment)
    result["rubric"][0]["ratings"][0]["description"] = "Caller edit"
    result["rubric_settings"]["title"] = "Caller edit"
    assert assignment == original

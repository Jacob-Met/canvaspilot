"""Behavior tests for a learner's Canvas-declared module-progress checklist."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from module_progress_fixture import course_fixture

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient
from canvaspilot.module_progress import module_progress


def read(fixture=None, **kwargs):
    source = course_fixture() if fixture is None else fixture
    with CanvasAPI(CanvasClient(token="", fixture=source)) as api:
        return api.module_progress(42, **kwargs)


def test_course_checklist_keeps_declared_progress_and_real_requirement_choices():
    source = course_fixture()
    before = deepcopy(source)
    result = read(source)
    assert source == before
    assert result["collection_complete"] is None
    assert result["count_scope"] == "returned_modules_and_items"
    assert result["modules_returned"] == result["modules_included"] == 4
    assert result["module_state_counts"] == {
        "locked": 1, "unlocked": 0, "started": 1, "completed": 1, "unknown": 1,
    }
    a, b, c, d = result["modules"]
    assert [module["id"] for module in result["modules"]] == [7, 8, 9, 10]
    assert [item["id"] for item in a["items"]] == [71, 72, 73]
    assert a["items"][0]["title"] == "Read Café notes"
    assert a["requirement_counts"] == {"completed": 1, "incomplete": 1, "unknown": 0, "not_reported": 1}
    assert a["remaining_work"]["incomplete_item_ids"] == [72]
    assert a["items"][1]["completion_requirement"]["min_score"] == 8
    assert a["require_sequential_progress"] is True
    assert b["state"] == "completed" and b["requirement_type"] == "one"
    assert b["requirement_counts"]["incomplete"] == 1
    assert b["remaining_work"]["rule"] == "module_completed"
    assert b["remaining_work"]["incomplete_item_ids"] == []
    assert c["state"] == "locked" and c["prerequisite_module_ids"] == [7]
    assert c["remaining_work"]["module_locked"] is True
    assert c["remaining_work"]["item_access"] == "not_assessed"
    assert d["state"] == "unknown" and d["reported_state"] is None
    assert d["requirement_type"] == "unknown"
    assert d["requirement_counts"]["unknown"] == 2
    assert d["items"][1]["completion_requirement"]["type"] == "future_rule"
    assert d["items"][1]["completion_status"] == "unknown"


def test_changed_completion_changes_worklist_without_inventing_module_completion():
    source = course_fixture()
    first = read(source)["modules"][0]
    source["routes"]["GET /api/v1/courses/42/modules/7/items"][1]["completion_requirement"]["completed"] = True
    changed = read(source)["modules"][0]
    assert first["remaining_work"]["incomplete_item_ids"] == [72]
    assert changed["remaining_work"]["incomplete_item_ids"] == []
    assert changed["requirement_counts"]["completed"] == 2
    assert changed["state"] == "started"
    source["routes"]["GET /api/v1/courses/42/modules"][0]["state"] = "completed"
    completed = read(source)["modules"][0]
    assert completed["state"] == "completed"
    assert completed["remaining_work"]["rule"] == "module_completed"


def test_one_of_rule_does_not_become_all_of_or_override_canvas_state():
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules"][1]["state"] = "started"
    module = read(source, module_id="8")["modules"][0]
    assert module["state"] == "started"
    assert module["remaining_work"]["rule"] == "one"
    assert module["remaining_work"]["incomplete_item_ids"] == [82]
    assert module["requirement_counts"]["completed"] == 1


def test_selection_preserves_source_identity_and_reports_omitted_rows():
    result = read(module_id="009")
    assert result["module_id"] == "9"
    assert result["modules_returned"] == 4 and result["modules_included"] == 1
    assert result["modules_omitted_by_selection"] == 3
    assert result["modules"][0]["id"] == 9
    with pytest.raises(ValueError, match="not present"):
        read(module_id="900")


@pytest.mark.parametrize("completed,status", [(True, "completed"), (False, "incomplete"),
                                                (None, "unknown"), (1, "unknown"), (0, "unknown"),
                                                ("false", "unknown"), ([], "unknown")])
def test_only_reported_boolean_completion_has_a_known_status(completed, status):
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules/7/items"][1]["completion_requirement"]["completed"] = completed
    item = read(source)["modules"][0]["items"][1]
    assert item["completion_status"] == status
    assert item["completion_requirement"]["completed"] == completed


@pytest.mark.parametrize("raw,status", [(None, "not_reported"), ({}, "unknown"),
                                        (False, "unknown"), ("must_view", "unknown"),
                                        ({"type": ["must_view"], "completed": True}, "unknown"),
                                        ({"type": "future", "completed": True}, "unknown")])
def test_unavailable_and_unsupported_requirements_are_not_completed_or_optional(raw, status):
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules/7/items"][0]["completion_requirement"] = raw
    item = read(source)["modules"][0]["items"][0]
    assert item["completion_status"] == status
    assert item["completion_requirement"] == raw


@pytest.mark.parametrize("state", [None, "future_state", True, 1, {}, []])
def test_unknown_module_states_are_retained_without_computing_completion(state):
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules"][0]["state"] = state
    module = read(source)["modules"][0]
    assert module["state"] == "unknown" and module["reported_state"] == state
    assert module["remaining_work"]["module_locked"] is None


@pytest.mark.parametrize("rule", [None, "some", True, [], {}])
def test_missing_or_unsupported_requirement_rules_remain_unknown(rule):
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules"][0]["requirement_type"] = rule
    module = read(source)["modules"][0]
    assert module["requirement_type"] == "unknown"
    assert module["reported_requirement_type"] == rule
    assert module["remaining_work"]["rule"] == "unknown"


@pytest.mark.parametrize("count,expected", [(3, "matches_reported_count"), (4, "shorter_than_reported_count"),
                                           (2, "more_than_reported_count"), (None, "unknown"),
                                           (True, "unknown"), (-1, "unknown")])
def test_item_count_is_an_observation_not_a_course_completeness_claim(count, expected):
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules"][0]["items_count"] = count
    result = read(source)
    assert result["modules"][0]["item_coverage"] == {
        "reported_count": count, "returned_count": 3, "status": expected,
    }
    assert result["collection_complete"] is None


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "", "../42", "42/1", "４２", [], {}])
@pytest.mark.parametrize("argument", ["course_id", "module_id"])
def test_query_identity_is_validated_before_reader_calls(value, argument):
    class API:
        def list_modules(self, *args, **kwargs):
            pytest.fail("Invalid query must not reach the reader")

    arguments = {"course_id": 42, "module_id": None}
    arguments[argument] = value
    with pytest.raises(ValueError, match="numeric Canvas ID"):
        module_progress(API(), **arguments)


def raw_reader(rows):
    return SimpleNamespace(client=SimpleNamespace(mode="fixture"), list_modules=lambda *args, **kwargs: rows)


@pytest.mark.parametrize("rows", [None, {}, [None], [{"id": 1, "items": None}],
                                  [{"id": 1, "items": [None]}],
                                  [{"id": 1, "items": []}, {"id": "01", "items": []}],
                                  [{"id": 1, "course_id": 99, "items": []}],
                                  [{"id": 1, "items": [{"id": 4, "module_id": 2}]}],
                                  [{"id": 1, "items": [{"id": 4}, {"id": "04"}]}],
                                  [{"id": 1, "items": [{"id": 4}]}, {"id": 2, "items": [{"id": 4}]}]])
def test_malformed_or_conflicting_source_identities_cannot_produce_a_digest(rows):
    with pytest.raises(ValueError):
        module_progress(raw_reader(rows), 42)


def test_reader_failures_propagate_without_an_empty_success():
    def fail(*args, **kwargs):
        raise RuntimeError("authored read failure")
    with pytest.raises(RuntimeError, match="authored read failure"):
        module_progress(SimpleNamespace(list_modules=fail), 42)


def test_empty_course_and_declared_empty_module_do_not_infer_completion():
    assert module_progress(raw_reader([]), 42)["modules"] == []
    module = module_progress(raw_reader([{"id": 1, "items_count": 0, "items": []}]), 42)["modules"][0]
    assert module["state"] == "unknown"
    assert module["requirement_counts"] == {"completed": 0, "incomplete": 0, "unknown": 0, "not_reported": 0}


def test_report_keeps_source_order_and_does_not_mutate_requirement_payloads():
    source = course_fixture()
    source["routes"]["GET /api/v1/courses/42/modules"].reverse()
    before = deepcopy(source)
    result = read(source)
    assert [module["id"] for module in result["modules"]] == [10, 9, 8, 7]
    result["modules"][-1]["items"][0]["completion_requirement"]["completed"] = False
    assert source == before

"""Agenda behavior through the real API/client and an authored HTTP boundary."""

from copy import deepcopy

import httpx
import pytest
from course_agenda_fixture import END, START, TOKEN, calendar_records

from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient


def api_for(records, requests):
    def handler(request):
        requests.append(request)
        kind = request.url.params.get("type", "event")
        return httpx.Response(200, json=records[kind])

    client = CanvasClient(base_url="https://authored-calendar.invalid", token=TOKEN)
    client._http = httpx.Client(
        base_url=client.base_url,
        headers={"Authorization": f"Bearer {TOKEN}"},
        transport=httpx.MockTransport(handler),
    )
    return CanvasAPI(client)


def report_for(records, ids=None, **dates):
    requests = []
    api = api_for(records, requests)
    try:
        return api.course_agenda(
            [42, "00077"] if ids is None else ids,
            start_date=dates.get("start_date", START),
            end_date=dates.get("end_date", END),
        ), requests
    finally:
        api.close()


def test_existing_raw_calendar_reader_preserves_response():
    records, requests = calendar_records(), []
    api = api_for(records, requests)
    try:
        assert api.list_calendar_events(
            start_date=START, end_date=END, context_codes=["course_42", "course_77"],
        ) == records["event"]
        assert len(requests) == 1
    finally:
        api.close()


def test_combines_exact_instants_without_losing_original_context():
    records = calendar_records()
    original = deepcopy(records)
    report, requests = report_for(records)
    assert report["schema"] == "canvaspilot.course-agenda.v1"
    assert report["selection"] == {
        "course_ids": ["42", "77"], "context_codes": ["course_42", "course_77"],
        "start_date": START, "end_date": END,
    }
    assert report["collection_counts"] == {"event": 4, "assignment": 2}
    assert report["counts"] == {"total": 6, "timed": 4, "all_day": 1, "timing_unavailable": 1}
    # Exact UTC ties retain collection order. Sub-microsecond values remain ordered.
    assert [(r["kind"], r["source"]["index"]) for r in report["timed"]] == [
        ("event", 0), ("assignment", 0), ("assignment", 1), ("event", 2),
    ]
    assert report["all_day"][0]["record"] == records["event"][1]
    assert report["timing_unavailable"][0]["record"] == records["event"][3]
    assert report["timing_unavailable"][0]["timing_issue"]["field"] == "start_at"
    returned = report["timed"] + report["all_day"] + report["timing_unavailable"]
    for entry in returned:
        assert entry["record"] == original[entry["source"]["collection"]][entry["source"]["index"]]
    assert report["timed"][-1]["course_id"] == "42"
    report["timed"][0]["record"]["child_events"][0]["id"] = "changed only in report"
    assert records == original
    assert [r.method for r in requests] == ["GET", "GET"]
    for request, kind in zip(requests, ("event", "assignment"), strict=True):
        assert request.url.path == "/api/v1/calendar_events"
        assert request.url.params.get("type") == kind
        assert request.url.params.get_list("context_codes[]") == ["course_42", "course_77"]
        assert request.url.params.get("start_date") == START
        assert request.url.params.get("end_date") == END
        assert "undated" not in request.url.params and "all_events" not in request.url.params


@pytest.mark.parametrize("value", [
    None, "", "2026-10-08T09:00:00",
    "2026-02-30T09:00:00Z", "2026-10-08T24:00:00Z", "2026-10-08T09:00:60Z",
    "2026-10-08T09:00:00+24:00", "2026-10-08T09:00:00+00:60", 123,
])
def test_unavailable_timestamp_stays_visible_without_invented_instant(value):
    record = {"id": 1, "context_code": "course_42", "all_day": False, "start_at": value}
    report, _ = report_for({"event": [record], "assignment": []})
    assert report["timed"] == report["all_day"] == []
    assert report["counts"]["total"] == 1
    assert report["timing_unavailable"][0]["record"] == record
    assert report["timing_unavailable"][0]["timing_issue"]["field"] == "start_at"


def test_all_day_dates_and_unknown_flags_are_explicit():
    rows = [
        {"id": 1, "context_code": "course_42", "all_day": True, "all_day_date": "2026-10-12"},
        {"id": 2, "context_code": "course_42", "all_day": True, "all_day_date": "2026-10-09", "start_at": None},
        {"id": 3, "context_code": "course_42", "all_day": True, "all_day_date": "2026-02-30"},
        {"id": 4, "context_code": "course_42", "start_at": "2026-10-08T00:00:00Z"},
        {"id": 5, "context_code": "course_42", "all_day": 0, "start_at": "2026-10-08T00:00:00Z"},
    ]
    report, _ = report_for({"event": rows, "assignment": []})
    assert [r["record"]["id"] for r in report["all_day"]] == [2, 1]
    assert [r["record"]["id"] for r in report["timing_unavailable"]] == [3, 4, 5]
    assert [r["timing_issue"]["field"] for r in report["timing_unavailable"]] == ["all_day_date", "all_day", "all_day"]
    assert report["timed"] == []
    assert all(entry["record"] == rows[entry["source"]["index"]] for entry in report["all_day"])


def test_empty_and_ten_course_same_day_selection():
    report, requests = report_for({"event": [], "assignment": []}, list(range(1, 11)), end_date=START)
    assert report["counts"] == {"total": 0, "timed": 0, "all_day": 0, "timing_unavailable": 0}
    assert report["timed"] == report["all_day"] == report["timing_unavailable"] == []
    assert len(requests) == 2
    assert len(requests[0].url.params.get_list("context_codes[]")) == 10


@pytest.mark.parametrize("ids,dates", [
    ([], {}), (list(range(1, 12)), {}), ([42, "00042"], {}), ([True], {}),
    ([0], {}), (["42/other"], {}), (["４２"], {}), ([42.0], {}), ("42", {}),
    ([42], {"start_date": "20261008"}), ([42], {"end_date": "2026-02-30"}),
    ([42], {"end_date": "2026-10-07"}),
])
def test_invalid_selection_makes_no_request(ids, dates):
    requests = []
    api = api_for(calendar_records(), requests)
    try:
        with pytest.raises(ValueError):
            api.course_agenda(ids, start_date=dates.get("start_date", START), end_date=dates.get("end_date", END))
        assert requests == []
    finally:
        api.close()


@pytest.mark.parametrize("bad", [
    None, False, [], {"id": True, "context_code": "course_42"},
    {"id": 1, "context_code": "course_999"},
    {"id": 1, "context_code": "course_section_9"},
    {"id": 1, "context_code": "course_42", "effective_context_code": "course_77"},
    {"id": 1, "context_code": "user_42", "effective_context_code": "course_42"},
    {"id": 1, "context_code": "course_42", "assignment": {"course_id": 77}},
    {"id": 1, "context_code": "course_42", "assignment": []},
])
def test_invalid_returned_identity_refuses_complete_agenda(bad):
    records = calendar_records()
    records["assignment"].append(bad)
    with pytest.raises(ValueError, match=r"assignment\[2\]"):
        report_for(records)


def test_terminal_single_object_retains_inherited_paginator_boundary():
    raw = {"id": 4, "context_code": "course_42", "all_day": False, "start_at": "2026-10-08T09:00:00Z"}
    report, _ = report_for({"event": raw, "assignment": []})
    assert report["collection_counts"] == {"event": 1, "assignment": 0}
    assert report["timed"][0]["record"] == raw


def test_unknown_local_offset_retains_known_utc_instant():
    records = {
        "event": [
            {"id": "local-offset-unknown", "context_code": "course_42", "all_day": False,
             "start_at": "2026-10-08T09:00:00-00:00"},
            {"id": "utc-reference", "context_code": "course_42", "all_day": False,
             "start_at": "2026-10-08T09:00:00Z"},
        ],
        "assignment": [
            {"id": "earlier", "context_code": "course_77", "all_day": False,
             "start_at": "2026-10-08T08:59:59.999999999Z"},
        ],
    }
    report, _ = report_for(records)
    assert [entry["record"]["id"] for entry in report["timed"]] == [
        "earlier", "local-offset-unknown", "utc-reference",
    ]
    assert report["timing_unavailable"] == report["all_day"] == []
    assert report["timed"][1]["record"] == records["event"][0]

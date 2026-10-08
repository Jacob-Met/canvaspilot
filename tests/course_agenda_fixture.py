"""Authored Calendar Events responses, with no real school or learner data."""

from copy import deepcopy

TOKEN = "synthetic-course-agenda-token"
START, END = "2026-10-08", "2026-10-15"


def calendar_records():
    return {
        "event": [
            {
                "id": 12, "context_code": "course_42", "all_day": False,
                "start_at": "2026-10-08T11:30:00+02:00", "end_at": None,
                "title": "Seminar — 水", "description": "<script>literal()</script>",
                "workflow_state": "locked", "hidden": True,
                "series_uuid": "authored-series", "rrule": "FREQ=WEEKLY",
                "child_events": [{"id": 99, "start_at": "not expanded"}],
            },
            {
                "id": "12", "context_code": "course_77", "all_day": True,
                "all_day_date": "2026-10-10", "start_at": None,
                "title": "Reading day", "location_address": "Room A & B",
            },
            {
                "id": 12, "context_code": "course_section_9",
                "effective_context_code": "course_42", "all_day": False,
                "start_at": "2026-10-08T09:30:00.000000002Z",
                "title": "Section-specific activity", "parent_event_id": 12,
            },
            {
                "id": "unscheduled", "context_code": "course_77", "all_day": False,
                "start_at": None, "title": "Timing unavailable in returned record",
            },
        ],
        "assignment": [
            {
                "id": "assignment_12", "context_code": "course_77", "all_day": False,
                "start_at": "2026-10-08T08:30:00-01:00", "end_at": "2026-10-08T08:30:00-01:00",
                "title": "Reading response", "workflow_state": "published",
                "assignment": {"id": 12, "course_id": 77, "due_at": None, "submission": None},
                "assignment_overrides": [{"id": "05", "course_section_id": 9, "due_at": None}],
            },
            {
                "id": 12, "context_code": "course_42", "all_day": False,
                "start_at": "2026-10-08T09:30:00.000000001Z", "title": "Measured example",
                "assignment": {"id": "12", "course_id": "00042", "due_at": "original string"},
            },
        ],
    }


def copied_records():
    return deepcopy(calendar_records())

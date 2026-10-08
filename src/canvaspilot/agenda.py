"""Read selected Canvas calendars without inventing dates or learner state."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import date
from typing import Any

from canvaspilot.client import CanvasClient

_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_INSTANT = re.compile(
    r"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]+))?(Z|[+-][0-9]{2}:[0-9]{2})"
)


def _course_id(value: Any) -> str:
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        raise ValueError("course IDs must be positive ASCII decimal integers")
    normalized = value.lstrip("0")
    if not normalized:
        raise ValueError("course IDs must be positive ASCII decimal integers")
    return normalized


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or not _DAY.fullmatch(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def agenda_selection(
    course_ids: list[int | str], *, start_date: str, end_date: str,
) -> dict[str, Any]:
    """Admit an explicit calendar selection before making any requests."""
    if not isinstance(course_ids, list) or not 1 <= len(course_ids) <= 10:
        raise ValueError("select between 1 and 10 course IDs")
    ids = [_course_id(value) for value in course_ids]
    if len(set(ids)) != len(ids):
        raise ValueError("course IDs must be distinct after removing leading zeroes")
    start, end = _day(start_date), _day(end_date)
    if start is None or end is None:
        raise ValueError("start_date and end_date must be valid YYYY-MM-DD dates")
    if start > end:
        raise ValueError("start_date must not be after end_date")
    return {
        "course_ids": ids,
        "context_codes": [f"course_{value}" for value in ids],
        "start_date": start_date,
        "end_date": end_date,
    }


def _context_course(value: Any) -> str | None:
    if isinstance(value, str):
        match = re.fullmatch(r"course_([0-9]+)", value)
        if match and match[1].lstrip("0"):
            return match[1].lstrip("0")
    return None


def _record_course(record: dict[str, Any], selected: set[str], location: str) -> str:
    identity = record.get("id")
    if not (type(identity) is int or isinstance(identity, str) and identity.strip()):
        raise ValueError(f"{location}: expected a supplied integer or nonempty string id")
    context = record.get("context_code")
    direct = _context_course(context)
    effective_value = record.get("effective_context_code")
    effective = _context_course(effective_value)
    if effective_value is not None and effective is None:
        raise ValueError(f"{location}: invalid effective_context_code")
    if direct is not None:
        if effective is not None and effective != direct:
            raise ValueError(f"{location}: conflicting course and effective context")
        course = direct
    elif (
        isinstance(context, str)
        and re.fullmatch(r"course_section_[0-9]+", context)
        and context.removeprefix("course_section_").lstrip("0")
        and effective is not None
    ):
        course = effective
    else:
        raise ValueError(f"{location}: no unambiguous course context")
    if course not in selected:
        raise ValueError(f"{location}: returned context is outside the selected courses")
    assignment = record.get("assignment")
    if assignment is not None:
        if not isinstance(assignment, dict):
            raise ValueError(f"{location}: assignment must be an object or null")
        if "course_id" in assignment:
            try:
                assignment_course = _course_id(assignment["course_id"])
            except ValueError as error:
                raise ValueError(f"{location}: invalid assignment.course_id") from error
            if assignment_course != course:
                raise ValueError(f"{location}: assignment.course_id conflicts with context")
    return course


def _instant(value: Any) -> tuple[int, str] | None:
    """An exact sort key; no float rounding or microsecond truncation."""
    if not isinstance(value, str):
        return None
    match = _INSTANT.fullmatch(value)
    if match is None:
        return None
    day = _day(match[1])
    hour, minute, second = (int(match[i]) for i in (2, 3, 4))
    if day is None or hour > 23 or minute > 59 or second > 59:
        return None
    offset = match[6]
    # RFC 3339 section 4.3: -00:00 still identifies UTC time even though the
    # local offset is unknown. Keep that marker in the original record.
    offset_seconds = 0
    if offset != "Z":
        offset_hour, offset_minute = int(offset[1:3]), int(offset[4:6])
        if offset_hour > 23 or offset_minute > 59:
            return None
        offset_seconds = (offset_hour * 60 + offset_minute) * 60
        if offset[0] == "-":
            offset_seconds = -offset_seconds
    whole = day.toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset_seconds
    # Decimal fractions in [0, 1) sort lexically after trailing zero removal.
    return whole, (match[5] or "").rstrip("0")


def _timing(record: dict[str, Any]) -> tuple[str, Any, dict[str, str] | None]:
    flag = record.get("all_day")
    if type(flag) is not bool:
        return "timing_unavailable", None, {
            "field": "all_day", "reason": "expected an explicit boolean",
        }
    if flag:
        supplied = _day(record.get("all_day_date"))
        if supplied is not None:
            return "all_day", supplied, None
        return "timing_unavailable", None, {
            "field": "all_day_date", "reason": "expected a supplied valid YYYY-MM-DD date",
        }
    instant = _instant(record.get("start_at"))
    if instant is not None:
        return "timed", instant, None
    return "timing_unavailable", None, {
        "field": "start_at",
        "reason": "expected a valid timestamp with a known UTC offset; no instant inferred",
    }


def read_course_agenda(
    client: CanvasClient,
    course_ids: list[int | str],
    *,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Combine the current caller's returned events and assignment calendar rows.

    Canvas selects the date range. Reads are sequential, not a simultaneous
    snapshot. The unchanged paginator may wrap a terminal object as one row.
    """
    selection = agenda_selection(course_ids, start_date=start_date, end_date=end_date)
    selected = set(selection["course_ids"])
    groups: dict[str, list[tuple[Any, dict[str, Any]]]] = {
        "timed": [], "all_day": [], "timing_unavailable": [],
    }
    collection_counts = {}
    for kind in ("event", "assignment"):
        params = [("type", kind), ("start_date", start_date), ("end_date", end_date)]
        params.extend(("context_codes[]", code) for code in selection["context_codes"])
        records = client.get_paginated("/api/v1/calendar_events", params=params)
        if not isinstance(records, list):
            raise ValueError(f"{kind}: expected a client-returned collection")  # noqa: TRY004 — invalid response value
        collection_counts[kind] = len(records)
        for index, record in enumerate(records):
            location = f"{kind}[{index}]"
            if not isinstance(record, dict):
                raise ValueError(f"{location}: expected a calendar record object")  # noqa: TRY004 — invalid response value
            course = _record_course(record, selected, location)
            group, sort_key, issue = _timing(record)
            entry = {
                "kind": kind,
                "course_id": course,
                "source": {"collection": kind, "index": index},
                "record": deepcopy(record),
            }
            if issue is not None:
                entry["timing_issue"] = issue
            groups[group].append((sort_key, entry))
    report = {
        "schema": "canvaspilot.course-agenda.v1",
        "selection": selection,
        "collection_counts": collection_counts,
        "counts": {"total": sum(collection_counts.values())},
    }
    for group, entries in groups.items():
        if group != "timing_unavailable":
            entries.sort(key=lambda pair: pair[0])
        report[group] = [entry for _, entry in entries]
        report["counts"][group] = len(entries)
    return report

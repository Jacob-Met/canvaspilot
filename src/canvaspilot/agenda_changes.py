"""Compare recorded values in two saved course-agenda documents, without Canvas I/O."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from typing import Any

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 4096
MAX_DEPTH = 64
GROUPS = ("timed", "all_day", "timing_unavailable")
KINDS = ("event", "assignment")
CLASSIFICATIONS = ("unchanged", "changed", "before_only", "after_only", "ambiguous")
LIMITATIONS = (
    "Before and after are caller-selected document roles, not a chronology or freshness claim.",
    "These reports do not establish provider, account, capture time or complete course obligations.",
    "One-sided presence does not establish creation, deletion or changed access in Canvas.",
    "Repeated identities are retained without an inferred correspondence between occurrences.",
    "Admission validates saved-report structure; recorded timing is not recalculated or authenticated.",
)


def _same(left: Any, right: Any) -> bool:
    """Decoded-value equality, deliberately unlike bool/int Python equality."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(v, right[k]) for k, v in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(_same(a, b) for a, b in zip(left, right))
    return left == right


def _object(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or value.keys() != keys:
        raise ValueError(f"{label}: expected exactly the documented object fields")


def _integer(value: Any, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label}: expected a nonnegative integer")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ValueError(f"nonfinite JSON constant: {value}")


def _values(root: Any) -> None:
    pending = [(root, 1)]
    while pending:
        value, depth = pending.pop()
        if isinstance(value, (dict, list)):
            if depth > MAX_DEPTH:
                raise ValueError("saved agenda exceeds the container-depth limit")
            children = value.values() if isinstance(value, dict) else value
            pending.extend((child, depth + 1) for child in children)
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError("saved agenda contains a nonfinite number")


def _course(value: Any, *, canonical: bool = False) -> str:
    if type(value) not in (int, str):
        raise ValueError("expected a positive decimal course ID")
    text = str(value)
    if not re.fullmatch(r"[0-9]+", text) or not text.lstrip("0"):
        raise ValueError("expected a positive decimal course ID")
    normalized = text.lstrip("0")
    if canonical and (type(value) is not str or normalized != value):
        raise ValueError("selection and occurrence course IDs must be canonical strings")
    return normalized


def _context(value: Any) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"course_[0-9]+", value):
        return value.removeprefix("course_").lstrip("0") or None
    return None


def _record_course(record: dict[str, Any], course: str) -> None:
    context = record.get("context_code")
    direct = _context(context)
    effective_value = record.get("effective_context_code")
    effective = _context(effective_value)
    if effective_value is not None and effective is None:
        raise ValueError("invalid effective course context")
    if direct is not None:
        if direct != course or effective not in (None, direct):
            raise ValueError("record course context conflicts with its occurrence")
    elif not (
        isinstance(context, str)
        and re.fullmatch(r"course_section_[0-9]+", context)
        and context.removeprefix("course_section_").lstrip("0")
        and effective == course
    ):
        raise ValueError("record has no matching unambiguous course context")
    assignment = record.get("assignment")
    if assignment is not None:
        if not isinstance(assignment, dict):
            raise ValueError("nested assignment must be an object or null")
        if "course_id" in assignment and _course(assignment["course_id"]) != course:
            raise ValueError("nested assignment course conflicts with its occurrence")


def _selection(value: Any) -> None:
    _object(value, {"course_ids", "context_codes", "start_date", "end_date"}, "selection")
    courses = value["course_ids"]
    if not isinstance(courses, list) or not 1 <= len(courses) <= 10:
        raise ValueError("selection must contain between 1 and 10 course IDs")
    ids = [_course(c, canonical=True) for c in courses]
    if len(set(ids)) != len(ids) or value["context_codes"] != ["course_" + c for c in ids]:
        raise ValueError("selection has duplicate courses or inconsistent contexts")
    days = []
    for field in ("start_date", "end_date"):
        text = value[field]
        if not isinstance(text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
            raise ValueError("selection dates must use YYYY-MM-DD")
        days.append(date.fromisoformat(text))
    if days[0] > days[1]:
        raise ValueError("selection date interval is reversed")


def _admit(raw: bytes, label: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if type(raw) is not bytes:
        raise TypeError(f"{label}: expected UTF-8 JSON bytes")
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"{label}: input exceeds the byte limit")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"{label}: UTF-8 BOM is not supported")
    try:
        report = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
        _values(report)
    except (UnicodeError, RecursionError) as error:
        raise ValueError(f"{label}: invalid UTF-8 or excessive JSON nesting") from error
    _object(report, {"schema", "selection", "collection_counts", "counts", *GROUPS}, label)
    if report["schema"] != "canvaspilot.course-agenda.v1":
        raise ValueError(f"{label}: unsupported agenda schema")
    _selection(report["selection"])
    _object(report["collection_counts"], set(KINDS), label + " collection_counts")
    _object(report["counts"], {"total", *GROUPS}, label + " counts")
    for counts in (report["counts"], report["collection_counts"]):
        for field, value in counts.items():
            _integer(value, label + " " + field)
    if report["counts"]["total"] > MAX_RECORDS:
        raise ValueError(f"{label}: record limit exceeded")
    by_kind: dict[str, dict[int, dict[str, Any]]] = {k: {} for k in KINDS}
    total = 0
    for group in GROUPS:
        rows = report[group]
        if not isinstance(rows, list) or len(rows) != report["counts"][group]:
            raise ValueError(f"{label}: inconsistent {group} count")
        total += len(rows)
        if total > MAX_RECORDS:
            raise ValueError(f"{label}: record limit exceeded")
        for row in rows:
            keys = {"kind", "course_id", "source", "record"}
            if group == "timing_unavailable":
                keys.add("timing_issue")
            _object(row, keys, label + " occurrence")
            kind = row["kind"]
            if kind not in KINDS:
                raise ValueError(f"{label}: unsupported collection kind")
            course = _course(row["course_id"], canonical=True)
            if course not in report["selection"]["course_ids"]:
                raise ValueError(f"{label}: occurrence outside selected courses")
            _object(row["source"], {"collection", "index"}, label + " source")
            index = row["source"]["index"]
            _integer(index, label + " source index")
            if row["source"]["collection"] != kind or index in by_kind[kind]:
                raise ValueError(f"{label}: inconsistent or duplicate source occurrence")
            record = row["record"]
            if not isinstance(record, dict):
                raise ValueError(f"{label}: record must be an object")  # noqa: TRY004 - malformed decoded JSON value
            identity = record.get("id")
            if not (type(identity) is int or isinstance(identity, str) and identity.strip()):
                raise ValueError(f"{label}: expected an integer or nonblank string record ID")
            _record_course(record, course)
            if group == "timing_unavailable":
                issue = row["timing_issue"]
                _object(issue, {"field", "reason"}, label + " timing issue")
                if not all(isinstance(v, str) for v in issue.values()):
                    raise ValueError(f"{label}: timing issue values must be strings")
            by_kind[kind][index] = {"group": group, "entry": row}
    if total != report["counts"]["total"]:
        raise ValueError(f"{label}: inconsistent total count")
    ordered = []
    for kind in KINDS:
        rows = by_kind[kind]
        if len(rows) != report["collection_counts"][kind] or set(rows) != set(range(len(rows))):
            raise ValueError(f"{label}: collection count or contiguous source indices disagree")
        ordered.extend(rows[index] for index in range(len(rows)))
    return report, ordered


def _key(occurrence: dict[str, Any]) -> tuple[str, str, str, int | str]:
    entry = occurrence["entry"]
    identity = entry["record"]["id"]
    return entry["kind"], entry["course_id"], "integer" if type(identity) is int else "string", identity


def _fields(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for field in sorted(before.keys() | after.keys()):
        if field in before and field in after and _same(before[field], after[field]):
            continue
        result.append({
            "field": field,
            "before": {"state": "present", "value": before[field]} if field in before else {"state": "missing"},
            "after": {"state": "present", "value": after[field]} if field in after else {"state": "missing"},
        })
    return result


def compare_saved_agendas(before: bytes, after: bytes) -> dict[str, Any]:
    """Compare complete saved documents; no external state or file writes."""
    old, old_rows = _admit(before, "before")
    new, new_rows = _admit(after, "after")
    if not _same(old["selection"], new["selection"]):
        raise ValueError("both reports must have the same ordered course/date selection")
    left: dict[tuple, list[dict[str, Any]]] = {}
    right: dict[tuple, list[dict[str, Any]]] = {}
    for rows, target in ((old_rows, left), (new_rows, right)):
        for occurrence in rows:
            target.setdefault(_key(occurrence), []).append(occurrence)
    keys = list(left) + [key for key in right if key not in left]
    counts = dict.fromkeys(CLASSIFICATIONS, 0)
    groups = []
    for key in keys:
        a, b = left.get(key, []), right.get(key, [])
        changes = []
        if len(a) > 1 or len(b) > 1:
            classification = "ambiguous"
        elif not a:
            classification = "after_only"
        elif not b:
            classification = "before_only"
        else:
            changes = _fields(a[0]["entry"]["record"], b[0]["entry"]["record"])
            classification = "changed" if changes else "unchanged"
        counts[classification] += 1
        groups.append({
            "identity": dict(zip(("kind", "course_id", "id_type", "id"), key)),
            "classification": classification, "before": a, "after": b, "field_changes": changes,
        })
    result = {
        "schema": "canvaspilot.agenda-changes.v1", "selection": old["selection"],
        "inputs": {
            "before": {"bytes": len(before), "sha256": hashlib.sha256(before).hexdigest(), "report": old},
            "after": {"bytes": len(after), "sha256": hashlib.sha256(after).hexdigest(), "report": new},
        },
        "document_equal": _same(old, new),
        "counts": {"before_occurrences": len(old_rows), "after_occurrences": len(new_rows), **counts},
        "groups": groups, "limitations": list(LIMITATIONS),
    }
    # The pure API obeys the complete-result budget too.
    render_agenda_changes(result, format="json")
    return result


def _quoted(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True)


def render_agenda_changes(report: dict[str, Any], *, format: str = "text") -> bytes:
    """Prepare all output before emission; artifact text is always JSON-quoted."""
    if format == "json":
        pieces = json.JSONEncoder(ensure_ascii=True, allow_nan=False, sort_keys=True).iterencode(report)
    elif format == "text":
        def text_lines():
            yield "Recorded agenda changes\n"
            yield "Selection: " + _quoted(report["selection"]) + "\n"
            yield "Decoded documents equal: " + _quoted(report["document_equal"]) + "\n"
            yield "Counts (keys by class; occurrence totals separate): " + _quoted(report["counts"]) + "\n"
            for side in ("before", "after"):
                source = report["inputs"][side]
                yield f"{side}: {source['bytes']} bytes; SHA-256 {source['sha256']}\n"
            for limit in report["limitations"]:
                yield "Limit: " + limit + "\n"
            for group in report["groups"]:
                yield "\n" + group["classification"] + ": " + _quoted(group["identity"]) + "\n"
                yield f"Occurrences before={len(group['before'])}, after={len(group['after'])}\n"
                for change in group["field_changes"]:
                    yield ("Field " + _quoted(change["field"]) + ": " + _quoted(change["before"])
                           + " -> " + _quoted(change["after"]) + "\n")
                for side in ("before", "after"):
                    for occurrence in group[side]:
                        yield side + " occurrence: " + _quoted(occurrence) + "\n"
        pieces = text_lines()
    else:
        raise ValueError("format must be text or json")
    result = bytearray()
    for piece in pieces:
        data = piece.encode("utf-8")
        if len(result) + len(data) + 1 > MAX_OUTPUT_BYTES:
            raise ValueError("complete comparison output exceeds the byte limit")
        result.extend(data)
    if not result.endswith(b"\n"):
        result.extend(b"\n")
    return bytes(result)
